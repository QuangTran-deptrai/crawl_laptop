import pandas as pd
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import time
import argparse
import math
import re
import httpx
import xml.etree.ElementTree as ET
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

# Cấu hình URL hệ thống Thế Giới Di Động — dùng sitemap để lấy link sản phẩm
SITEMAP_INDEX_URL = "https://www.thegioididong.com/newsitemap/sitemap-product"
BASE_URL = "https://www.thegioididong.com"

def calculate_discount(current_price, original_price, scraped_discount=""):
    try:
        import re
        # Bỏ qua nếu giá chứa text "liên hệ"
        if 'liên hệ' in str(current_price).lower() or 'liên hệ' in str(original_price).lower():
            return ""
        c = int(re.sub(r'[^\d]', '', str(current_price)))
        o = int(re.sub(r'[^\d]', '', str(original_price)))
        if o > c and o > 0 and c > 0:
            percent = round((o - c) / o * 100)
            # Sanity check: giảm giá quá 70% thì rất khả nghi, ưu tiên dùng giá trị scraped nếu có
            if percent <= 70:
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

def fetch_laptop_links_from_category():
    """Lấy danh sách link laptop trực tiếp từ trang danh mục TGDĐ bằng Playwright"""
    print("  >> Đang mở trình duyệt để lấy toàn bộ danh sách laptop từ web (mô phỏng người dùng)...")
    product_links = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            page.goto("https://www.thegioididong.com/laptop", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            # Đóng popup nếu có
            try:
                page.evaluate("document.querySelectorAll('.popup-login-mdm, .popup__login__overlay').forEach(e => e.style.display = 'none')")
            except Exception:
                pass
            
            # Bấm nút "Xem thêm XXX Laptop" cho đến khi hết
            clicks = 0
            last_count = 0
            max_clicks = 50
            while clicks < max_clicks:
                try:
                    # Nút "Xem thêm" trên TGDĐ mới là <button> chứa text "Xem thêm ... Laptop"
                    btn = page.locator('button:has-text("Laptop")').filter(has_text="Xem thêm")
                    if btn.count() == 0:
                        btn = page.locator('button:has-text("Xem thêm")')
                    
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        btn.first.click()
                        clicks += 1
                        time.sleep(3)
                        
                        new_count = page.evaluate('''() => {
                            let links = new Set();
                            document.querySelectorAll('a[href*="/laptop/"]').forEach(a => {
                                let href = a.href;
                                if (href && !href.includes('#') && !href.includes('?')) links.add(href);
                            });
                            return links.size;
                        }''')
                        print(f"     --> Đã bấm 'Xem thêm' lần {clicks} - Hiện có: {new_count} link laptop unique")
                        
                        if new_count <= last_count:
                            print("     --> Số lượng link unique không tăng thêm, dừng load.")
                            break
                        last_count = new_count
                    else:
                        print("     --> Không còn nút 'Xem thêm', đã tải hết.")
                        break
                except Exception as e:
                    print(f"     --> Lỗi khi click: {e}")
                    break
                    
            print("  >> Đã tải hết trang, đang trích xuất link...")
            
            # Trích xuất tất cả link laptop unique
            all_links = page.evaluate('''() => {
                let links = new Set();
                document.querySelectorAll('a[href*="/laptop/"]').forEach(a => {
                    let href = a.href;
                    if (href && !href.includes('#') && !href.includes('?')) {
                        links.add(href);
                    }
                });
                return [...links];
            }''')
            
            for link in all_links:
                product_links[link] = ""
                    
        except Exception as e:
            print(f"  ! Lỗi khi crawl trang danh mục: {e}")
        finally:
            browser.close()
            
    print(f"  >> Tìm thấy {len(product_links)} link laptop từ giao diện web.")
    return product_links

def crawl_tgdd_to_excel(chunk=1, total_chunks=1, get_links_only=False):
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
        
    print("=== [LEVEL 0] LẤY LINK LAPTOP TỪ SITEMAP TGDĐ ===")
    
    product_links = []  # list of url
    lastmod_map = {}    # {url: lastmod}
    LINKS_FILE = "tgdd_links.txt"
    
    if os.path.exists(PENDING_FILE):
        print(f"=== ĐANG CHẠY TIẾP TỤC MẢNH {chunk} (RETRY) ===")
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                url = parts[0]
                lastmod = parts[1] if len(parts) > 1 else ""
                product_links.append(url)
                lastmod_map[url] = lastmod
    elif not get_links_only and os.path.exists(LINKS_FILE):
        print(f"=== TÌM THẤY FILE {LINKS_FILE}, BỎ QUA LEVEL 0 ===")
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                url = parts[0]
                lastmod = parts[1] if len(parts) > 1 else ""
                product_links.append(url)
                lastmod_map[url] = lastmod
    else:
        # Lấy link từ giao diện category
        sitemap_data = fetch_laptop_links_from_category()
        
        if not sitemap_data:
            print("❌ Lỗi: Không thể lấy link laptop từ sitemap TGDĐ. Dừng script.")
            import sys
            sys.exit(1)
        
        for url, lastmod in sitemap_data.items():
            product_links.append(url)
            lastmod_map[url] = lastmod
        
        print(f"\n=== TỔNG CỘNG: {len(product_links)} link laptop từ sitemap (đã loại trùng) ===")
        
        # Sort để đảm bảo sharding đều
        product_links = sorted(product_links)
        
        if get_links_only:
            with open(LINKS_FILE, "w", encoding="utf-8") as f:
                for link in product_links:
                    f.write(f"{link}\t{lastmod_map.get(link, '')}\n")
            print(f"--> Đã lưu {len(product_links)} link ra file {LINKS_FILE}")
            return
    
    if not os.path.exists(PENDING_FILE):
        # Sort danh sách để đảm bảo phân rã đều giữa các shard
        product_links = sorted(list(set(product_links)))
        
        # Chia nhỏ danh sách link (Sharding)
        chunk_size = math.ceil(len(product_links) / total_chunks)
        start_idx = (chunk - 1) * chunk_size
        end_idx = start_idx + chunk_size
        product_links = product_links[start_idx:end_idx]
        
        print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
    
    print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        final_results = []
        consecutive_cf_fails = 0
        
        for index, url in enumerate(product_links, start=1):
            print(f"[{index}/{len(product_links)}] Đang xử lý: {url}")
            
            try:
                crawl_time = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")
                
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(2)
                close_popup(page)
                
                # Cuộn xuống để load các thông tin lazy (TGDĐ load thông số kỹ thuật khi cuộn)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(1)
                
                # Mở rộng cấu hình chi tiết (Giao diện Next.js mới)
                try:
                    accordion_headers = page.locator('div.cursor-pointer:has(h3)')
                    for i in range(accordion_headers.count()):
                        header = accordion_headers.nth(i)
                        header.scroll_into_view_if_needed()
                        if header.is_visible():
                            header.click()
                            time.sleep(0.5)
                except Exception:
                    pass
                
                # Bấm "Xem thêm" (nếu có nút Xem thêm chung)
                try:
                    view_more = page.locator('button:has-text("Xem thêm")')
                    for i in range(view_more.count()):
                        if view_more.nth(i).is_visible():
                            view_more.nth(i).click()
                            time.sleep(0.5)
                except Exception:
                    pass
                
                prod_html = page.content()
                prod_page = Adaptor(prod_html, url=url)
                
                # 1. Tên sản phẩm
                product_name = prod_page.css('h1::text').get(default="").strip()
                
                # 2. Cấu hình chi tiết
                specs_dict = {}
                spec_items = prod_page.css('.parameter__list li, .parameter li, .text-specifi li, ul.overflow-hidden li.border-b')
                for li in spec_items:
                    key = li.css('aside:nth-child(1)::text, .lileft::text, p[class*="left"]::text, div[class*="left"]::text, div.w-200px::text, div.font-600::text').get(default="").strip()
                    if not key:
                        key = " ".join([v.strip() for v in li.css('aside:nth-child(1) *::text, .lileft *::text').getall() if v.strip()])
                        
                    val = " ".join([v.strip() for v in li.css('aside:nth-child(2) *::text, .liright *::text, p[class*="right"] *::text, div[class*="right"] *::text, div.flex-1 *::text').getall() if v.strip()])
                    if not val:
                        val = li.css('aside:nth-child(2)::text, .liright::text, p[class*="right"]::text, div[class*="right"]::text').get(default="").strip()
                    
                    if key and val:
                        if key.endswith(':'): key = key[:-1].strip()
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
                current_price = prod_page.css('span.text-24.font-700.text-red-5::text, .active[data-pack] span b::text, .active[data-id] span b::text, .box-price-present::text, .price::text').get(default="").strip()
                current_price = current_price.replace("*", "").strip()
                    
                original_price = prod_page.css('.box-price-old::text, .price-old::text, del.text-gray-5::text, .active[data-pack] span em::text, .active[data-id] span em::text').get(default="").strip()
                
                # Sanity check: giá gốc không thể nhỏ hơn giá hiện tại (tránh bắt nhầm giá quà tặng/voucher)
                try:
                    c_val = int(re.sub(r'[^\d]', '', current_price)) if current_price else 0
                    o_val = int(re.sub(r'[^\d]', '', original_price)) if original_price else 0
                    if o_val > 0 and c_val > 0 and o_val < c_val:
                        original_price = ""
                except Exception:
                    pass
                    
                discount_percent = prod_page.css('del + span.text-red-5::text, .percent::text, .box-price-percent::text').get(default="").strip()
                discount_percent = calculate_discount(current_price, original_price, discount_percent)
                
                # 4. Khuyến mãi (Giao diện Next.js mới)
                promo_list = []
                try:
                    promos = prod_page.css('.bg-orange-6 .text-12::text, .bg-orange-6 .text-14::text, .border.rounded-12px .bg-white span[class*="text-blue"]::text').getall()
                    
                    if not promos:
                        promos = page.evaluate('''() => {
                            let items = [];
                            document.querySelectorAll('.divb-right, .pr-item .divb-right, .border.rounded-12px .bg-white span.text-12').forEach(el => {
                                let text = el.innerText.trim();
                                text = text.replace(/\\n+/g, " - ");
                                if (text && !items.includes(text)) items.push(text);
                            });
                            return items;
                        }''')
                    if promos:
                        valid_promos = []
                        for p in promos:
                            p = p.strip()
                            if p and p != "Chọn 1 trong các quà:" and "Đang chọn KM" not in p:
                                valid_promos.append(p)
                        promo_list = list(set(valid_promos))
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
                    "Ngày Cập Nhật (Sitemap)": lastmod_map.get(url, ""),
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
                            f.write(f"{r_link}\t{lastmod_map.get(r_link, '')}\n")
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
    parser.add_argument('--chunk', type=int, default=1, help='Số thứ tự của mảnh hiện tại (1-based)')
    parser.add_argument('--total-chunks', type=int, default=1, help='Tổng số mảnh cần chia')
    parser.add_argument('--get-links-only', action='store_true', help='Chỉ quét link và lưu ra file')
    args = parser.parse_args()
    
    crawl_tgdd_to_excel(chunk=args.chunk, total_chunks=args.total_chunks, get_links_only=args.get_links_only)
