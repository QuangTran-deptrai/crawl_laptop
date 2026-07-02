import pandas as pd
from datetime import datetime
import time
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

SEARCH_URL = "https://cellphones.com.vn/laptop.html"
BASE_URL = "https://cellphones.com.vn"

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

def crawl_cellphones_to_excel():
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
        product_links = []
        
        for a_tag in product_blocks:
            relative_link = a_tag.css('::attr(href)').get(default="")
            if relative_link:
                full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                if full_link not in product_links:
                    product_links.append(full_link)
                    
        print(f"--> Tìm thấy {len(product_links)} link laptop từ trang tìm kiếm CellphoneS.")
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN ===")
        
        TEST_MODE = False
        MAX_TEST_ITEMS = 5
        if TEST_MODE and len(product_links) > MAX_TEST_ITEMS:
            product_links = product_links[:MAX_TEST_ITEMS]
            print(f"*** CHẾ ĐỘ TEST: Chỉ chạy {MAX_TEST_ITEMS} sản phẩm đầu tiên ***")
            
        final_results = []
        
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
                current_price = prod_page.css('.box-info__box-price .product__price--show::text, .box-product-price-wrapper .sale-price::text, .box-product-price-wrapper .product__price--show::text').get(default="").strip()
                original_price = prod_page.css('.box-info__box-price .product__price--through::text, .box-product-price-wrapper .base-price::text, .box-product-price-wrapper .product__price--through::text').get(default="").strip()
                discount_percent = prod_page.css('.box-info__box-price .product__price--percent-detail span::text').get(default="").strip()
                
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
        
        browser.close()
            
    if final_results:
        output_file = "laptop_cellphones_all.xlsx"
        df = pd.DataFrame(final_results)
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop vào '{output_file}' ===")
    else:
        print("\nKhông thu thập được dữ liệu nào hợp lệ để xuất file.")

if __name__ == "__main__":
    crawl_cellphones_to_excel()
