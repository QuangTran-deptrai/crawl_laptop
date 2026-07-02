import pandas as pd
from datetime import datetime
import time
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

# Cấu hình URL hệ thống
SEARCH_URL = "https://gearvn.com/search?q=laptop%20gaming%20rtx%203050"
BASE_URL = "https://gearvn.com"

def close_popup(page):
    """Đóng popup quảng cáo nếu xuất hiện — thử nhiều lần."""
    js_close = '''() => {
        let closed = false;
        // Thử jQuery Bootstrap
        if (typeof $ !== 'undefined' && typeof $.fn.modal !== 'undefined') {
            try { $('.modal').modal('hide'); closed = true; } catch(e) {}
        }
        // Xóa backdrop
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        // Ẩn tất cả modal
        document.querySelectorAll('.modal').forEach(m => {
            if (m.style.display !== 'none') closed = true;
            m.style.display = 'none';
            m.classList.remove('show', 'in');
            m.setAttribute('aria-hidden', 'true');
        });
        // Cho phép scroll lại
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        return closed;
    }'''
    
    # Thử đóng popup 3 lần, mỗi lần cách 2 giây
    for attempt in range(3):
        try:
            result = page.evaluate(js_close)
            if result:
                print(f"    >> Đã đóng popup quảng cáo (lần {attempt + 1}).")
                time.sleep(1)
                return
        except Exception:
            pass
        time.sleep(2)

def crawl_laptop_gearvn_to_excel():
    print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM ĐỂ LẤY LINK PRODUCT ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Truy cập trang tìm kiếm
        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        
        # Đóng popup quảng cáo nếu có
        time.sleep(3)
        close_popup(page)
        
        # Chờ sản phẩm load xong
        try:
            page.wait_for_selector('.proloop-name a', timeout=15000)
        except Exception:
            print("    ! Timeout chờ sản phẩm load.")
        
        time.sleep(2)
        
        # Bấm nút "Xem thêm sản phẩm" để load hết tất cả sản phẩm
        load_more_count = 0
        while True:
            try:
                load_more_btn = page.locator('#load_more_search')
                if load_more_btn.count() == 0 or not load_more_btn.is_visible():
                    break
                
                # Cuộn trang xuống để nút hiện ra
                load_more_btn.scroll_into_view_if_needed()
                time.sleep(0.5)
                load_more_btn.click()
                load_more_count += 1
                print(f"    >> Đã bấm 'Xem thêm sản phẩm' lần {load_more_count}, đang chờ load...")
                time.sleep(3)
            except Exception:
                break
        
        if load_more_count > 0:
            print(f"    >> Đã load thêm {load_more_count} lần.")
        
        time.sleep(1)
        
        # Parse HTML bằng Adaptor của scrapling
        html_content = page.content()
        search_page = Adaptor(html_content, url=SEARCH_URL)
        product_blocks = search_page.css('.proloop-block')
        
        # Lấy TẤT CẢ link sản phẩm (không lọc theo tên ở trang search)
        # Vì tên laptop không chứa "3050", cần vào trang chi tiết để kiểm tra card đồ họa
        product_links = []
        
        for block in product_blocks:
            name_at_search = block.css('.proloop-name a::text').get(default="").strip()
            
            # Chỉ lấy sản phẩm là Laptop (bỏ qua Card màn hình, phụ kiện, v.v.)
            if not name_at_search or not name_at_search.lower().startswith("laptop"):
                continue
            
            relative_link = block.css('.proloop-name a::attr(href)').get(default="")
            if relative_link:
                full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                if full_link not in product_links:
                    product_links.append(full_link)
                    
        print(f"--> Tìm thấy {len(product_links)} link laptop từ trang tìm kiếm.")
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ KIỂM TRA CÓ RTX 3050 KHÔNG ===")
        
        final_results = []
        
        for index, url in enumerate(product_links, start=1):
            print(f"[{index}/{len(product_links)}] Đang xử lý: {url}")
            
            try:
                crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Truy cập trang chi tiết sản phẩm
                page.goto(url, wait_until="domcontentloaded")
                
                # Đóng popup quảng cáo nếu có
                time.sleep(2)
                close_popup(page)
                
                # Chờ khối thông tin sản phẩm load
                try:
                    page.wait_for_selector('.product-info', timeout=15000)
                except Exception:
                    print(f"    ! Timeout chờ .product-info tại {url}")
                
                # Chờ thêm để bảng specs load xong
                time.sleep(2)
                
                # Chờ phần khuyến mãi load xong (được inject bằng JS bên ngoài)
                try:
                    # Chờ 1 trong 2 cấu trúc khuyến mãi xuất hiện
                    page.wait_for_function('''() => {
                        return document.querySelector('#gvn-promotions .gvn-promo-item') || 
                               document.querySelector('#gift-promo--app .gift-promo--lists li');
                    }''', timeout=8000)
                except Exception:
                    pass  # Có thể sản phẩm không có khuyến mãi
                
                time.sleep(1)
                
                # Parse HTML
                prod_html = page.content()
                prod_page = Adaptor(prod_html, url=url)
                info_block = prod_page.css('.product-info')
                
                if not info_block:
                    print(f"    ! Không tìm thấy .product-info tại {url}")
                    continue
                
                # --- KIỂM TRA CARD ĐỒ HỌA CÓ RTX 3050 KHÔNG ---
                specs_dict = {}
                spec_rows = prod_page.css('#gvn-specs-container-table tr.gvn-spec-row')
                
                has_rtx3050 = False
                for row in spec_rows:
                    if row.css('th[colspan]'):
                        continue
                    
                    key = row.css('th::text').get(default="").strip()
                    # Lấy toàn bộ text trong td (bao gồm cả trong thẻ con)
                    val_parts = row.css('td::text').getall()
                    val = " ".join([v.strip() for v in val_parts if v.strip()])
                    
                    if key and val:
                        specs_dict[key] = val
                    
                    # Kiểm tra card đồ họa
                    if "card" in key.lower() or "đồ họa" in key.lower() or "vga" in key.lower() or "gpu" in key.lower():
                        if "3050" in val:
                            has_rtx3050 = True
                
                if not has_rtx3050:
                    print(f"    → Bỏ qua: Không có RTX 3050")
                    continue
                
                # 1. Tên sản phẩm
                product_name = info_block.css('.product-name h1::text').get(default="").strip()
                
                # 2. Giá hiện tại
                current_price = info_block.css('.product-price .pro-price::text').get(default="").strip()
                
                # 3. Giá gốc (nếu có giảm giá)
                original_price = info_block.css('.product-price del::text').get(default="").strip()
                
                # 4. Phần trăm giảm giá
                discount_percent = info_block.css('.product-price .pro-percent::text').get(default="").strip()
                
                # 5. Khuyến mãi (hỗ trợ cả 2 cấu trúc)
                promo_list = []
                try:
                    # Dùng JS lấy trực tiếp text trên trình duyệt sẽ chính xác và gom được cả desc
                    promos = page.evaluate('''() => {
                        let items = [];
                        
                        // Cấu trúc 1: #gvn-promotions .gvn-promo-item
                        document.querySelectorAll('#gvn-promotions .gvn-promo-item').forEach(el => {
                            let title = el.querySelector('.gvn-promo-title');
                            let desc = el.querySelector('.gvn-promo-desc');
                            let text = "";
                            if (title) text += title.innerText.trim();
                            if (desc && desc.innerText.trim() !== "") text += " (" + desc.innerText.trim() + ")";
                            if (text) items.push(text);
                        });
                        
                        // Cấu trúc 2: #gift-promo--app .gift-promo--lists li
                        document.querySelectorAll('#gift-promo--app .gift-promo--lists li').forEach(el => {
                            if (el && el.innerText.trim() !== "") {
                                items.push(el.innerText.trim());
                            }
                        });
                        
                        return items;
                    }''')
                    if promos:
                        promo_list = promos
                except Exception as e:
                    pass
                
                # 6. Mô tả ngắn / quà tặng bổ sung từ .product-desc-short
                desc_short_parts = info_block.css('.product-desc-short::text').getall()
                desc_short_all = info_block.css('.product-desc-short *::text').getall()
                desc_short = " | ".join([t.strip() for t in desc_short_all if t.strip()])
                
                # Cấu hình chi tiết
                specs_string = " | ".join([f"{k}: {v}" for k, v in specs_dict.items()])
                
                # Khuyến mãi gộp
                promo_string = " | ".join(promo_list) if promo_list else ""
                
                laptop_data = {
                    "Tên Sản Phẩm": product_name,
                    "Giá Hiện Tại": current_price,
                    "Giá Gốc": original_price,
                    "Giảm Giá": discount_percent,
                    "Khuyến Mãi": promo_string,
                    "Quà Tặng / Ghi Chú": desc_short,
                    "Cấu Hình Chi Tiết": specs_string,
                    "Link Sản Phẩm": url,
                    "Ngày Giờ Crawl": crawl_time
                }
                
                final_results.append(laptop_data)
                print(f"    ✓ RTX 3050 - Đã lấy: {product_name}")
                
                # Delay giữa các sản phẩm
                time.sleep(1.5)
                
            except Exception as e:
                print(f"    ! Gặp lỗi khi xử lý link {url}: {e}")
        
        # Đóng trình duyệt
        browser.close()
            
    # --- XỬ LÝ XUẤT FILE EXCEL BẰNG PANDAS ---
    if final_results:
        output_file = "laptop_rtx3050_gearvn.xlsx"
        
        df = pd.DataFrame(final_results)
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop RTX 3050 vào '{output_file}' ===")
    else:
        print("\nKhông thu thập được dữ liệu nào hợp lệ để xuất file.")

if __name__ == "__main__":
    crawl_laptop_gearvn_to_excel()