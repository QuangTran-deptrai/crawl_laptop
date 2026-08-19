import pandas as pd
from datetime import datetime, timezone, timedelta
import time
import argparse
import math
import httpx
import xml.etree.ElementTree as ET
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

# Cấu hình URL hệ thống GearVN — dùng sitemap để lấy link sản phẩm
SITEMAP_URLS = [
    "https://gearvn.com/sitemap_products_1.xml",
    "https://gearvn.com/sitemap_products_2.xml",
    "https://gearvn.com/sitemap_products_3.xml",
    "https://gearvn.com/sitemap_products_4.xml",
    "https://gearvn.com/sitemap_products_5.xml",
]
BASE_URL = "https://gearvn.com"

def calculate_discount(current_price, original_price, scraped_discount=""):
    try:
        import re
        if 'liên hệ' in str(current_price).lower() or 'liên hệ' in str(original_price).lower():
            return ""
        c = int(re.sub(r'[^\d]', '', str(current_price)))
        o = int(re.sub(r'[^\d]', '', str(original_price)))
        if o > c and o > 0 and c > 0:
            percent = round((o - c) / o * 100)
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

def fetch_laptop_links_from_sitemap():
    """Lấy danh sách link laptop + lastmod từ sitemap XML của GearVN (không cần browser)."""
    NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    product_links = {}  # {url: lastmod}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for sitemap_url in SITEMAP_URLS:
        print(f"  >> Đang tải sitemap: {sitemap_url}")
        for attempt in range(3):
            try:
                resp = httpx.get(sitemap_url, headers=headers, timeout=60, follow_redirects=True)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                
                count = 0
                for url_el in root.findall("ns:url", NS):
                    loc = url_el.findtext("ns:loc", default="", namespaces=NS)
                    lastmod = url_el.findtext("ns:lastmod", default="", namespaces=NS)
                    
                    # Chỉ lấy link laptop (slug chứa /products/laptop)
                    if loc and "/products/laptop" in loc.lower():
                        if loc not in product_links:
                            product_links[loc] = lastmod
                            count += 1
                
                print(f"     --> Tìm thấy {count} link laptop mới (tổng: {len(product_links)})")
                break
            except Exception as e:
                print(f"     ! Lỗi khi tải {sitemap_url} (lần {attempt+1}/3): {e}")
                time.sleep(3)
    
    return product_links

def crawl_gearvn_to_excel(chunk=1, total_chunks=1, get_links_only=False):
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
        
    print("=== [LEVEL 0] LẤY LINK LAPTOP TỪ SITEMAP GEARVN ===")
    
    product_links = []  # list of (url, lastmod)
    lastmod_map = {}    # {url: lastmod}
    LINKS_FILE = "gearvn_links.txt"
    
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
        # Lấy link từ sitemap (không cần browser)
        sitemap_data = fetch_laptop_links_from_sitemap()
        
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
        # Chia nhỏ danh sách link (Sharding)
        product_links = sorted(list(set(product_links)))
        chunk_size = math.ceil(len(product_links) / total_chunks)
        start_idx = (chunk - 1) * chunk_size
        end_idx = start_idx + chunk_size
        product_links = product_links[start_idx:end_idx]
        
        print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
    
    print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN CHI TIẾT ===")
    
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
                
                # Truy cập trang chi tiết sản phẩm
                page.goto(url, wait_until="domcontentloaded")
                
                # Chờ h1 (tên sản phẩm) load — selector ổn định nhất
                try:
                    page.wait_for_selector('h1', timeout=15000)
                except Exception:
                    print(f"    ! Timeout chờ h1 tại {url}")
                
                # Chờ thêm để trang render xong (Next.js hydration)
                time.sleep(3)
                
                # === LẤY DỮ LIỆU TỪ JSON-LD (chuẩn SEO, ổn định nhất) ===
                json_ld_data = page.evaluate('''() => {
                    let scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (let s of scripts) {
                        try {
                            let data = JSON.parse(s.textContent);
                            if (data["@type"] === "Product") return data;
                        } catch(e) {}
                    }
                    return null;
                }''')
                
                if not json_ld_data:
                    print(f"    ! Không tìm thấy JSON-LD Product tại {url}")
                    continue
                
                # 1. Tên sản phẩm (từ JSON-LD)
                product_name = json_ld_data.get("name", "").strip()
                
                # 2-3. Giá hiện tại & giá gốc (từ DOM, scope vào khu vực sản phẩm chính)
                price_data = page.evaluate('''() => {
                    // Scope vào khu vực thông tin sản phẩm chính (tránh bắt nhầm giá từ "Sản phẩm tương tự")
                    let region = document.querySelector('[data-product-summary-region="true"]');
                    if (!region) region = document;
                    
                    // Giá hiện tại: chữ đỏ lớn, class chứa "red" và "bold"
                    let currentEl = region.querySelector('span[class*="red-700"][class*="bold"]');
                    let currentPrice = currentEl ? currentEl.innerText.trim() : "";
                    
                    // Giá gốc: chữ gạch ngang (line-through) — chỉ trong khu vực sản phẩm chính
                    let originalEl = region.querySelector('span[class*="line-through"]');
                    let originalPrice = originalEl ? originalEl.innerText.trim() : "";
                    
                    // Phần trăm giảm giá
                    let discountEl = region.querySelector('span[class*="red-600"][class*="red-50"]');
                    let discount = discountEl ? discountEl.innerText.trim() : "";
                    
                    return { currentPrice, originalPrice, discount };
                }''')
                
                current_price = price_data.get("currentPrice", "")
                original_price = price_data.get("originalPrice", "")
                discount_percent = price_data.get("discount", "")
                
                # Fallback giá từ JSON-LD nếu DOM không lấy được
                if not current_price:
                    offers = json_ld_data.get("offers", {})
                    price_val = offers.get("price", "")
                    if price_val:
                        current_price = f"{int(price_val):,}đ".replace(",", ".")
                    
                    price_spec = offers.get("priceSpecification", {})
                    orig_val = price_spec.get("price", "")
                    if orig_val and not original_price:
                        original_price = f"{int(orig_val):,}đ".replace(",", ".")
                
                discount_percent = calculate_discount(current_price, original_price, discount_percent)
                
                # 4. Cấu hình chi tiết (từ JSON-LD additionalProperty)
                specs_dict = {}
                for prop in json_ld_data.get("additionalProperty", []):
                    key = prop.get("name", "").strip()
                    val = prop.get("value", "").strip()
                    if key and val:
                        specs_dict[key] = val
                
                # 5. Khuyến mãi (từ DOM — section "Ưu đãi đi kèm")
                promo_list = []
                try:
                    promos = page.evaluate('''() => {
                        let items = [];
                        
                        // Cấu trúc mới (Next.js): section chứa "Ưu đãi đi kèm"
                        // Tìm tất cả các div con chứa icon gift/tag + text khuyến mãi
                        let promoSection = document.querySelector('section[class*="surface-red"]');
                        if (promoSection) {
                            // Lấy từng block khuyến mãi (mỗi block có border-b)
                            let promoBlocks = promoSection.querySelectorAll('div[class*="border-b"], div:not([class*="border-b"]):last-child');
                            promoSection.querySelectorAll('div[class*="gap"][class*="py"]').forEach(el => {
                                let text = el.innerText.trim();
                                if (text && text.length > 5) {
                                    // Loại bỏ label "Ưu đãi theo phạm vi" nếu có, chỉ lấy nội dung
                                    text = text.replace(/^Ưu đãi theo phạm vi\\s*/i, '').trim();
                                    if (text) items.push(text);
                                }
                            });
                        }
                        
                        // Fallback: cấu trúc cũ (nếu còn tồn tại)
                        if (items.length === 0) {
                            document.querySelectorAll('#gvn-promotions .gvn-promo-item').forEach(el => {
                                let title = el.querySelector('.gvn-promo-title');
                                let desc = el.querySelector('.gvn-promo-desc');
                                let text = "";
                                if (title) text += title.innerText.trim();
                                if (desc && desc.innerText.trim() !== "") text += " (" + desc.innerText.trim() + ")";
                                if (text) items.push(text);
                            });
                            document.querySelectorAll('#gift-promo--app .gift-promo--lists li').forEach(el => {
                                if (el && el.innerText.trim() !== "") {
                                    items.push(el.innerText.trim());
                                }
                            });
                        }
                        
                        return items;
                    }''')
                    if promos:
                        promo_list = promos
                except Exception:
                    pass
                
                # 6. Mô tả ngắn (không còn trong giao diện mới, bỏ qua)
                desc_short = ""
                
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
                    "Ngày Cập Nhật (Sitemap)": lastmod_map.get(url, ""),
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
                            f.write(f"{r_link}\t{lastmod_map.get(r_link, '')}\n")
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
    parser.add_argument('--chunk', type=int, default=1, help='Số thứ tự của mảnh hiện tại (1-based)')
    parser.add_argument('--total-chunks', type=int, default=1, help='Tổng số mảnh cần chia')
    parser.add_argument('--get-links-only', action='store_true', help='Chỉ quét link và lưu ra file')
    args = parser.parse_args()
    
    crawl_gearvn_to_excel(chunk=args.chunk, total_chunks=args.total_chunks, get_links_only=args.get_links_only)
