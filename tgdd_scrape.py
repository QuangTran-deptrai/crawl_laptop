import pandas as pd
from datetime import datetime
import time
import argparse
import math
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

# Cấu hình URL hệ thống Thế Giới Di Động
SEARCH_URL = "https://www.thegioididong.com/laptop"
BASE_URL = "https://www.thegioididong.com"

def calculate_discount(current_price, original_price, scraped_discount=""):
    if scraped_discount and str(scraped_discount).strip():
        return str(scraped_discount).strip()
    try:
        import re
        c = int(re.sub(r'[^\d]', '', str(current_price)))
        o = int(re.sub(r'[^\d]', '', str(original_price)))
        if o > c and o > 0:
            percent = round((o - c) / o * 100)
            return f"-{percent}%"
    except Exception:
        pass
    return ""

def close_popup(page):
    """Đóng popup quảng cáo hoặc thông báo nếu xuất hiện."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        # Ẩn các modal/popup nếu có
        page.evaluate('''() => {
            document.querySelectorAll('.popup-login-mdm, .popup__login__overlay, .popup__detail__overlay, .popup-voucher-block').forEach(el => {
                el.style.display = 'none';
            });
            document.body.style.overflow = 'auto';
        }''')
    except Exception:
        pass

def crawl_tgdd_to_excel(chunk=1, total_chunks=1):
    import time
    import glob
    import os
    
    timestamp = int(time.time())
    EXCEL_FILE = f"laptop_tgdd_chunk_{chunk}_{timestamp}.xlsx"
    PENDING_FILE = f"tgdd_pending_chunk_{chunk}.txt"
    
    is_retry_run = len(glob.glob("*_pending_chunk_*.txt")) > 0
    if is_retry_run and not os.path.exists(PENDING_FILE):
        print(f"Mảnh {chunk} đã hoàn thành từ trước. Bỏ qua.")
        return
        
    print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM TGDĐ ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        product_links = []
        
        if os.path.exists(PENDING_FILE):
            print(f"=== ĐANG CHẠY TIẾP TỤC MẢNH {chunk} (RETRY) ===")
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                product_links = [line.strip() for line in f if line.strip()]
        else:
            # TGDĐ thường kiểm tra location, ta set mặc định hoặc cứ bypass
            page.goto(SEARCH_URL, wait_until="domcontentloaded")
            time.sleep(3)
            close_popup(page)
            
            print("    >> Đang tải tất cả sản phẩm (bấm Xem thêm)...")
            load_more_count = 0
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                try:
                    clicked = page.evaluate('''() => {
                        let btns = document.querySelectorAll('.view-more a, .see-more-btn');
                        for (let btn of btns) {
                            let text = (btn.innerText || "").toLowerCase();
                            // Phải đảm bảo nút thực sự hiển thị (không bị display: none) và chứa chữ "laptop"
                            if (btn.offsetWidth > 0 && btn.offsetHeight > 0 && text.includes("xem thêm") && text.includes("laptop")) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    
                    if clicked:
                        load_more_count += 1
                        print(f"    >> Đã bấm 'Xem thêm' lần {load_more_count}")
                        time.sleep(3)
                        continue
                except Exception:
                    pass
                    
                break # Thoát nếu không tìm thấy nút hoặc không bấm được nữa
                
            time.sleep(2)
            
            html_content = page.content()
            search_page = Adaptor(html_content, url=SEARCH_URL)
            
            # Link sản phẩm nằm trong .item a.main-contain
            product_blocks = search_page.css('li.item a.main-contain')
            
            for a_tag in product_blocks:
                relative_link = a_tag.css('::attr(href)').get(default="")
                if relative_link:
                    full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                    if full_link not in product_links:
                        product_links.append(full_link)
                        
            print(f"--> Tìm thấy tổng cộng {len(product_links)} link laptop từ trang tìm kiếm TGDĐ.")
            
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
                time.sleep(2)
                close_popup(page)
                
                # Cuộn xuống để load các thông tin lazy (TGDĐ load thông số kỹ thuật khi cuộn)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(1)
                
                # Mở rộng cấu hình chi tiết (nếu có nút "Xem thêm cấu hình chi tiết" chung)
                try:
                    view_more_specs = page.locator('.btn-detail, .btn-short-spec, button:has-text("Xem thêm")')
                    for i in range(view_more_specs.count()):
                        if view_more_specs.nth(i).is_visible():
                            view_more_specs.nth(i).click()
                            time.sleep(1)
                except Exception:
                    pass
                
                # Bấm vào từng nhóm cấu hình (accordion) để load đầy đủ
                try:
                    box_specifi_links = page.locator('.box-specifi > a')
                    for i in range(box_specifi_links.count()):
                        link = box_specifi_links.nth(i)
                        link.scroll_into_view_if_needed()
                        if link.is_visible() and "active" not in (link.get_attribute("class") or ""):
                            link.click()
                            time.sleep(1.5) # làm từ từ để tránh bị block
                except Exception:
                    pass
                
                # Bấm "Xem thêm khuyến mãi" (nếu có)
                try:
                    promo_view_more = page.locator('.pr-viewmore')
                    if promo_view_more.count() > 0 and promo_view_more.first.is_visible():
                        promo_view_more.first.scroll_into_view_if_needed()
                        promo_view_more.first.click()
                        time.sleep(0.5)
                except Exception:
                    pass
                
                prod_html = page.content()
                prod_page = Adaptor(prod_html, url=url)
                
                # 1. Tên sản phẩm
                product_name = prod_page.css('h1::text').get(default="").strip()
                
                # 2. Cấu hình chi tiết
                specs_dict = {}
                spec_items = prod_page.css('.parameter__list li, .parameter li, .text-specifi li')
                for li in spec_items:
                    key = li.css('aside:nth-child(1)::text, .lileft::text, p[class*="left"]::text, div[class*="left"]::text').get(default="").strip()
                    if not key:
                        key = " ".join([v.strip() for v in li.css('aside:nth-child(1) *::text, .lileft *::text').getall() if v.strip()])
                        
                    val = " ".join([v.strip() for v in li.css('aside:nth-child(2) *::text, .liright *::text, p[class*="right"] *::text, div[class*="right"] *::text').getall() if v.strip()])
                    if not val:
                        val = li.css('aside:nth-child(2)::text, .liright::text, p[class*="right"]::text, div[class*="right"]::text').get(default="").strip()
                    
                    if key and val:
                        specs_dict[key] = val
                    else:
                        # Fallback nếu cấu trúc khác
                        text = " ".join(li.css('::text').getall()).strip()
                        if ":" in text:
                            k, v = text.split(":", 1)
                            specs_dict[k.strip()] = v.strip()
                            key = k
                            val = v
                
                # 3. Giá hiện tại & Giá gốc
                # Ưu tiên lấy giá từ Gói dịch vụ đang active (giá thực tế khi mua online)
                current_price = prod_page.css('.active[data-pack] span b::text, .active[data-id] span b::text').get(default="").strip()
                if not current_price:
                    current_price = prod_page.css('.box-price-present::text').get(default="").strip()
                if not current_price:
                    current_price = prod_page.css('.price::text').get(default="").strip()
                current_price = current_price.replace("*", "").strip()
                    
                original_price = prod_page.css('.active[data-pack] span em::text, .active[data-id] span em::text').get(default="").strip()
                if not original_price:
                    original_price = prod_page.css('.box-price-old::text').get(default="").strip()
                if not original_price:
                    original_price = prod_page.css('.price-old::text').get(default="").strip()
                    
                discount_percent = prod_page.css('.percent::text, .box-price-percent::text').get(default="").strip()
                discount_percent = calculate_discount(current_price, original_price, discount_percent)
                
                # 4. Khuyến mãi (TGDĐ thường nằm trong .divb-right)
                promo_list = []
                try:
                    promos = page.evaluate('''() => {
                        let items = [];
                        // Khuyến mãi thông thường
                        document.querySelectorAll('.divb-right, .pr-item .divb-right').forEach(el => {
                            let text = el.innerText.trim();
                            // Loại bỏ các khoảng trắng và newline thừa
                            text = text.replace(/\\n+/g, " - ");
                            if (text && !items.includes(text)) items.push(text);
                        });
                        // Khuyến mãi Back to school hoặc các ưu đãi tương tự
                        document.querySelectorAll('.backtoschool > div').forEach(el => {
                            let title = el.querySelector('b') ? el.querySelector('b').innerText.trim() : "";
                            let desc = el.querySelector('span') ? el.querySelector('span').innerText.trim() : "";
                            let text = (title + " - " + desc).trim();
                            text = text.replace(/\\n+/g, " ");
                            if (text && text !== "-" && !items.includes(text)) items.push(text);
                        });
                        return items;
                    }''')
                    if promos:
                        promo_list = promos
                except Exception:
                    pass
                
                # Gộp thông tin
                specs_string = " | ".join([f"{k}: {v}" for k, v in specs_dict.items()])
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
                    
                # Phục hồi (Reset) lại tab trình duyệt nếu trang trước đó bị lỗi Timeout hoặc ngắt kết nối
                try:
                    page.close()
                    page = context.new_page()
                    context.on("page", lambda p: p.close() if p != page else None)
                except Exception:
                    pass
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
    
    crawl_tgdd_to_excel(chunk=args.chunk, total_chunks=args.total_chunks)
