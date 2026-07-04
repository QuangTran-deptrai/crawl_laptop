import pandas as pd
from datetime import datetime
import time
import argparse
import math
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

BASE_URL = "https://cellphones.com.vn"
SEARCH_URL = "https://cellphones.com.vn/laptop.html"

def calculate_discount(current_price, original_price, scraped_discount=""):
    try:
        import re
        c = int(re.sub(r'[^\d]', '', str(current_price)))
        o = int(re.sub(r'[^\d]', '', str(original_price)))
        if o > c and o > 0:
            percent = round((o - c) / o * 100)
            return f"-{percent}%"
    except Exception:
        pass
        
    if scraped_discount and str(scraped_discount).strip():
        d = str(scraped_discount).strip()
        if d.endswith('%') and not d.startswith('-'):
            d = f"-{d}"
        return d
        
    return ""

def close_popup(page):
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.evaluate('''() => {
            // 1. Xoá toàn bộ iframe (đặc biệt iframe quảng cáo/youtube) và video
            document.querySelectorAll('iframe, video').forEach(el => el.remove());
            // 2. Click các nút đóng popup truyền thống
            document.querySelectorAll('.cancel-button, .close-modal, .btn-close, .modal-close').forEach(el => el.click());
            
            // 3. Quét và xóa các thanh thông báo Cookies hoặc overlay quảng cáo fixed
            document.querySelectorAll('div, section').forEach(el => {
                let style = window.getComputedStyle(el);
                let z = parseInt(style.zIndex) || 0;
                let text = (el.innerText || "").toLowerCase();
                
                // Banner cookies
                if ((style.position === 'fixed' || style.position === 'sticky') && (text.includes("cookie") || text.includes("chấp nhận"))) {
                    el.remove();
                }
                
                // Mọi overlay che khuất màn hình
                if ((style.position === 'fixed' || style.position === 'absolute') && z >= 90) {
                    el.remove();
                }
            });
            // 4. Mở lại thanh cuộn nếu bị khoá
            document.body.style.overflow = 'auto';
        }''')
    except Exception:
        pass

def crawl_cellphones_to_excel(chunk=1, total_chunks=1):
    import time
    import glob
    import os
    
    timestamp = int(time.time())
    EXCEL_FILE = f"laptop_cellphones_chunk_{chunk}_{timestamp}.xlsx"
    PENDING_FILE = f"cellphones_pending_chunk_{chunk}.txt"
    
    is_retry_run = len(glob.glob("*_pending_chunk_*.txt")) > 0
    if is_retry_run and not os.path.exists(PENDING_FILE):
        print(f"Mảnh {chunk} đã hoàn thành từ trước. Bỏ qua.")
        return
        
    print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM CELLPHONES ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # Chặn các tab/popup mới bật lên (không tính tab chính) để không làm gián đoạn script
        context.on("page", lambda p: p.close() if p != page else None)
        
        product_links = []
        
        if os.path.exists(PENDING_FILE):
            print(f"=== ĐANG CHẠY TIẾP TỤC MẢNH {chunk} (RETRY) ===")
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                product_links = [line.strip() for line in f if line.strip()]
        else:
            page.goto(SEARCH_URL, wait_until="domcontentloaded")
            time.sleep(3)
            close_popup(page)
            
            print("    >> Đang tải tất cả sản phẩm (bấm Xem thêm)...")
            load_more_count = 0
            while True:
                # Cuộn xuống từ từ để hiển thị nút
                page.evaluate("window.scrollBy(0, 1000);")
                time.sleep(1)
                page.evaluate("window.scrollBy(0, 1000);")
                time.sleep(2)
                
                close_popup(page)
                
                # Dùng Javascript để click chính xác nút Xem thêm sản phẩm (bỏ qua mọi lỗi che khuất của giao diện)
                clicked = page.evaluate('''() => {
                    let btns = document.querySelectorAll('.cps-block-content_btn-showmore a, .button__show-more-product');
                    for (let btn of btns) {
                        let text = btn.innerText.toLowerCase();
                        // Đảm bảo chỉ click nút chứa chữ "xem thêm" và "sản phẩm", tránh nút bình luận
                        if (text.includes("xem thêm") && text.includes("sản phẩm")) {
                            btn.scrollIntoView({block: "center"});
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                    
                if clicked:
                    load_more_count += 1
                    print(f"    >> Đã bấm 'Xem thêm' lần {load_more_count}")
                    time.sleep(4)
                    continue
                else:
                    break
                
            time.sleep(2)
            
            html_content = page.content()
            search_page = Adaptor(html_content, url=SEARCH_URL)
            
            # Chỉ lấy sản phẩm chính trong .filter-sort__list-product
            product_blocks = search_page.css('.filter-sort__list-product .product-info-container a.product__link')
            
            for a_tag in product_blocks:
                relative_link = a_tag.css('::attr(href)').get(default="")
                if relative_link:
                    full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                    if full_link not in product_links:
                        product_links.append(full_link)
                        
            print(f"--> Tìm thấy tổng cộng {len(product_links)} link laptop từ trang tìm kiếm CellphoneS.")
            
            # Sort danh sách để đảm bảo phân rã đều giữa các shard
            product_links = sorted(list(set(product_links)))
            
            # Chia nhỏ danh sách link (Sharding)
            chunk_size = math.ceil(len(product_links) / total_chunks)
            start_idx = (chunk - 1) * chunk_size
            end_idx = start_idx + chunk_size
            product_links = product_links[start_idx:end_idx]
            
            print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
            
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN ===")
        
        final_results = []
        consecutive_cf_fails = 0
        
        for index, url in enumerate(product_links, start=1):
            print(f"[{index}/{len(product_links)}] Đang xử lý: {url}")
            
            try:
                crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(4)
                close_popup(page)
                
                # Cuộn trang từ từ để không vô tình kích hoạt video autoplay và tìm mục cấu hình
                page.evaluate("window.scrollBy(0, 700);")
                time.sleep(1)
                page.evaluate("window.scrollBy(0, 700);")
                time.sleep(2)
                close_popup(page)
                
                # Mở modal cấu hình chi tiết (nếu có)
                try:
                    # Nút xem cấu hình chi tiết có class .button__show-modal-technical và text "Xem tất cả"
                    btn_specs = page.locator('#thong-so-ky-thuat, .cps-block-technicalInfo').get_by_text("Xem tất cả", exact=False).first
                    
                    if btn_specs.is_visible():
                        btn_specs.click(force=True)
                        time.sleep(3)
                except Exception:
                    pass
                
                prod_html = page.content()
                prod_page = Adaptor(prod_html, url=url)
                
                # 1. Tên sản phẩm
                product_name = prod_page.css('.box-product-name h1::text').get(default="").strip()
                if not product_name:
                    product_name = prod_page.css('h1::text').get(default="").strip()
                
                # 2. Cấu hình chi tiết
                specs_dict = {}
                spec_items = prod_page.css('.modal-content .item-technical-content, tr.technical-content-item')
                if not spec_items:
                    spec_items = prod_page.css('ul.technical-content li')
                
                for item in spec_items:
                    tds = item.css('td')
                    if len(tds) >= 2:
                        key = tds[0].css('::text').get(default="").strip()
                        val = " ".join([v.strip() for v in tds[1].css('*::text').getall() if v.strip()])
                    else:
                        key = item.css('.item-technical-name::text, p:nth-child(1)::text').get(default="").strip()
                        val = " ".join([v.strip() for v in item.css('.item-technical-value *::text, p:nth-child(2) *::text, div *::text').getall() if v.strip() and v.strip() != key])
                    
                    if key and val:
                        specs_dict[key] = val
                        
                specs_string = " | ".join([f"{k}: {v}" for k, v in specs_dict.items()])
                
                # 3. Giá hiện tại & Giá gốc (Chỉ quét trong khung giá chính để tránh lấy nhầm giá phụ kiện)
                current_price = ""
                original_price = ""
                discount_percent = ""
                price_box = prod_page.css('.box-product-price-wrapper, .box-info__box-price, .tpt-box-price')
                if price_box:
                    main_box = price_box[0]
                    current_price = main_box.css('.tpt-price::text, .product__price--show::text, .sale-price::text').get(default="").strip()
                    original_price = main_box.css('.tpt-price-through::text, .product__price--through::text, .base-price::text').get(default="").strip()
                    discount_percent = main_box.css('.product__price--percent-detail span::text').get(default="").strip()
                    
                discount_percent = calculate_discount(current_price, original_price, discount_percent)
                
                # 4. Khuyến mãi
                promo_list = []
                try:
                    promos = page.evaluate('''() => {
                        let items = [];
                        let selectors = [
                            '.box-promotions .promotion-item', 
                            '.item-promotions',
                            '.block-smem-price',
                            '.exclusive-price-block .txt',
                            '.trade-price-label',
                            '.box-product-promotion-content .button__promotion'
                        ];
                        document.querySelectorAll(selectors.join(', ')).forEach(el => {
                            let textObj = el.cloneNode(true);
                            // Xoá các nút bấm hoặc link dư thừa
                            textObj.querySelectorAll('a, button, .icon-pc, .btn-estimate-price-trade, .dang_nhap_xem_gia').forEach(e => e.remove());
                            
                            let text = textObj.textContent.trim();
                            // Dọn dẹp khoảng trắng và dấu gạch nối thừa
                            text = text.replace(/\\n+/g, " - ");
                            text = text.replace(/\\s+/g, " ");
                            text = text.replace(/ -\\s+-/g, " -");
                            text = text.replace(/^-\\s*/, "").replace(/\\s*-$/, "").trim();
                            if (text && text !== "-" && !items.includes(text)) items.push(text);
                        });
                        return items;
                    }''')
                    if promos:
                        promo_list = promos
                except Exception:
                    pass
                
                promo_string = " | ".join(promo_list) if promo_list else ""
                
                laptop_data = {
                    "Tên Sản Phẩm": product_name,
                    "Giá Hiện Tại": current_price,
                    "Giá Gốc": original_price,
                    "Giảm Giá": discount_percent,
                    "Khuyến Mãi": promo_string,
                    "Cấu Hình Chi Tiết": specs_string,
                    "Link Sản Phẩm": url,
                    "Ngày Giờ Crawl": crawl_time
                }
                
                final_results.append(laptop_data)
                print(f"    ✓ Đã lấy: {product_name}")
                
            except Exception as e:
                print(f"    ! Gặp lỗi khi xử lý link {url}: {e}")
                consecutive_cf_fails += 1
                
                if consecutive_cf_fails >= 3:
                    print(f"\n    🔴 Bị chặn hoặc lỗi IP sau {index} link! Dừng script sớm để bảo toàn dữ liệu đã cào.")
                    
                    failed_start_idx = max(0, index - 1 - 2)
                    remaining_links = product_links[failed_start_idx:]
                    with open(PENDING_FILE, "w", encoding="utf-8") as f:
                        for r_link in remaining_links:
                            f.write(r_link + "\n")
                    print(f"    💾 Đã lưu {len(remaining_links)} link dang dở vào {PENDING_FILE}")
                    
                    break
            else:
                consecutive_cf_fails = 0
        
        browser.close()
        
        if consecutive_cf_fails < 3 and os.path.exists(PENDING_FILE):
            os.remove(PENDING_FILE)
            print(f"    ✨ Đã hoàn thành mảnh {chunk}, xóa file pending!")
            
    # --- XỬ LÝ XUẤT FILE EXCEL ---
    if final_results:
        output_file = EXCEL_FILE
        df = pd.DataFrame(final_results)
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n=== HOÀN THÀNH MẢNH {chunk}! Đã lưu {len(final_results)} laptop vào '{output_file}' ===")
    else:
        print("\nKhông thu thập được dữ liệu nào hợp lệ để xuất file.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk', type=int, default=1, help='Phần hiện tại (bắt đầu từ 1)')
    parser.add_argument('--total-chunks', type=int, default=1, help='Tổng số phần chia')
    args = parser.parse_args()
    
    crawl_cellphones_to_excel(chunk=args.chunk, total_chunks=args.total_chunks)
