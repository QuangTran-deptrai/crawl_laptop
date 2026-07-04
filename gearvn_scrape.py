import pandas as pd
from datetime import datetime
import time
import argparse
import math
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

# Cấu hình URL hệ thống GearVN — crawl nhiều trang collection
COLLECTION_URLS = [
    "https://gearvn.com/collections/laptop-gaming-gia-tu-20-den-25-trieu",
    "https://gearvn.com/collections/laptop-gaming-ban-chay",
    "https://gearvn.com/collections/laptop-gaming-gia-tu-25-den-35-trieu",
    "https://gearvn.com/collections/laptop-gaming-tren-35-trieu",
    "https://gearvn.com/collections/laptop-van-phong-ban-chay",
    "https://gearvn.com/collections/laptop-hoc-tap-va-lam-viec-duoi-15tr",
    "https://gearvn.com/collections/laptop-hoc-tap-va-lam-viec-tu-15tr-den-20tr",
    "https://gearvn.com/collections/laptop-hoc-tap-va-lam-viec-tren-20-trieu"
]
BASE_URL = "https://gearvn.com"
SEARCH_URL = "https://gearvn.com/collections/laptop"

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
        return ""

def crawl_gearvn_to_excel(chunk=1, total_chunks=1):
    import time
    import glob
    import os
    
    timestamp = int(time.time())
    EXCEL_FILE = f"laptop_gearvn_chunk_{chunk}_{timestamp}.xlsx"
    PENDING_FILE = f"gearvn_pending_chunk_{chunk}.txt"
    
    is_retry_run = len(glob.glob("*_pending_chunk_*.txt")) > 0
    if is_retry_run and not os.path.exists(PENDING_FILE):
        print(f"Mảnh {chunk} đã hoàn thành từ trước. Bỏ qua.")
        return
        
    print("=== [LEVEL 0] ĐANG QUÉT DANH MỤC TRÊN GEARVN ===")
    
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
            for col_index, collection_url in enumerate(COLLECTION_URLS, start=1):
                print(f"\n--- [{col_index}/{len(COLLECTION_URLS)}] Đang quét: {collection_url} ---")
                
                page.goto(collection_url, wait_until="domcontentloaded")
                
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
                        load_more_btn = page.locator('#load_more, #load_more_search')
                        if load_more_btn.count() == 0 or not load_more_btn.first.is_visible():
                            break
                        
                        load_more_btn.first.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        load_more_btn.first.click()
                        load_more_count += 1
                        print(f"    >> Đã bấm 'Xem thêm sản phẩm' lần {load_more_count}, đang chờ load...")
                        time.sleep(3)
                    except Exception:
                        break
                
                if load_more_count > 0:
                    print(f"    >> Đã load thêm {load_more_count} lần.")
                
                time.sleep(1)
                
                # Parse HTML bằng Adaptor
                html_content = page.content()
                search_page = Adaptor(html_content, url=collection_url)
                product_blocks = search_page.css('.proloop-block')
                
                count_new = 0
                for block in product_blocks:
                    name_at_search = block.css('.proloop-name a::text').get(default="").strip()
                    
                    # Chỉ lấy sản phẩm là Laptop
                    if not name_at_search or not name_at_search.lower().startswith("laptop"):
                        continue
                    
                    relative_link = block.css('.proloop-name a::attr(href)').get(default="")
                    if relative_link:
                        full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                        if full_link not in product_links:
                            product_links.append(full_link)
                            count_new += 1
                
                print(f"    --> Tìm thấy {count_new} link mới (tổng: {len(product_links)})")
            
            print(f"\n=== TỔNG CỘNG: {len(product_links)} link laptop (đã loại trùng) ===")
            
            # Sort danh sách để đảm bảo phân rã đều giữa các shard
            product_links = sorted(list(set(product_links)))
            
            # Chia nhỏ danh sách link (Sharding)
            chunk_size = math.ceil(len(product_links) / total_chunks)
            start_idx = (chunk - 1) * chunk_size
            end_idx = start_idx + chunk_size
            product_links = product_links[start_idx:end_idx]
            
            print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN CHI TIẾT ===")
        
        final_results = []
        consecutive_cf_fails = 0
        
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
                
                # Chờ thêm để trang load xong
                time.sleep(2)
                
                # Cuộn xuống và click nút "Đọc tiếp bài viết" để mở rộng bảng cấu hình
                try:
                    expand_btn = page.locator('button.expandable-btn')
                    if expand_btn.count() > 0 and expand_btn.first.is_visible():
                        expand_btn.first.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        expand_btn.first.click()
                        time.sleep(1.5)
                        print(f"    >> Đã click 'Đọc tiếp bài viết'")
                except Exception:
                    pass
                
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
                
                # Parse HTML (sau khi đã mở rộng bài viết)
                prod_html = page.content()
                prod_page = Adaptor(prod_html, url=url)
                info_block = prod_page.css('.product-info')
                
                if not info_block:
                    print(f"    ! Không tìm thấy .product-info tại {url}")
                    continue
                
                # --- LẤY CẤU HÌNH CHI TIẾT TỪ BẢNG #tblGeneralAttribute ---
                specs_dict = {}
                spec_rows = prod_page.css('#tblGeneralAttribute tr')
                
                for row in spec_rows:
                    tds = row.css('td')
                    if len(tds) >= 2:
                        # Cột 1: tên thông số (nằm trong <strong> hoặc text trực tiếp)
                        key = " ".join(tds[0].css('*::text').getall()).strip()
                        # Cột 2: giá trị thông số
                        val = " ".join(tds[1].css('*::text').getall()).strip()
                        
                        if key and val:
                            specs_dict[key] = val
                
                # Fallback: nếu không có #tblGeneralAttribute, thử lấy từ bảng specs sidebar cũ
                if not specs_dict:
                    spec_rows_fallback = prod_page.css('#gvn-specs-container-table tr.gvn-spec-row')
                    for row in spec_rows_fallback:
                        if row.css('th[colspan]'):
                            continue
                        key = row.css('th::text').get(default="").strip()
                        val_parts = row.css('td::text').getall()
                        val = " ".join([v.strip() for v in val_parts if v.strip()])
                        if key and val:
                            specs_dict[key] = val
                
                # 1. Tên sản phẩm
                product_name = info_block.css('.product-name h1::text').get(default="").strip()
                
                # 2. Giá hiện tại
                current_price = info_block.css('.product-price .pro-price::text').get(default="").strip()
                
                # 3. Giá gốc (nếu có giảm giá)
                original_price = info_block.css('.product-price del::text').get(default="").strip()
                
                # 4. Phần trăm giảm giá
                discount_percent = info_block.css('.product-price .pro-percent::text, .product-price .product-discount::text').get(default="").strip()
                discount_percent = calculate_discount(current_price, original_price, discount_percent)
                
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
                print(f"    ✓ Đã lấy: {product_name}")
                
                # Delay giữa các sản phẩm
                time.sleep(1.5)
                
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
        
        # Đóng trình duyệt
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
    
    crawl_gearvn_to_excel(chunk=args.chunk, total_chunks=args.total_chunks)
