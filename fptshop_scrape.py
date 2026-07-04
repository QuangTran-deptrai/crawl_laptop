import pandas as pd
from datetime import datetime
import time
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor
from bs4 import BeautifulSoup

BASE_URL = "https://fptshop.com.vn"
SEARCH_URL = "https://fptshop.com.vn/may-tinh-xach-tay"

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
    """Đóng popup quảng cáo hoặc banner nếu xuất hiện."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.evaluate('''() => {
            document.querySelectorAll('.popup, .banner, .cookie-banner').forEach(el => {
                el.style.display = 'none';
            });
            document.body.style.overflow = 'auto';
        }''')
    except Exception:
        pass

import os
import math
import argparse

def crawl_fptshop_to_excel(chunk=1, total_chunks=1):
    EXCEL_FILE = f"laptop_fptshop_chunk_{chunk}.xlsx"
    
    print("Khởi tạo Patchright cho FPT Shop...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--window-size=1920,1080"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM FPT SHOP ===")
        
        product_links = []
        
        # Bắt đầu quét sitemap
            # Thử tối đa 3 lần tải lại trang nếu bị kẹt ở Cloudflare
            for attempt in range(3):
                page.goto(SEARCH_URL, wait_until="domcontentloaded")
                print(f"Đang kiểm tra Cloudflare (lần thử {attempt + 1})...")
                
                for _ in range(15):
                    title = page.title()
                    if "Just a moment" in title or "Cloudflare" in title:
                        time.sleep(2)
                        try:
                            # Dùng Playwright frame_locator để click vào Turnstile
                            cb = page.frame_locator("iframe").locator("input").first
                            if cb.is_visible(timeout=1000):
                                cb.click(force=True)
                        except Exception:
                            pass
                    else:
                        break
                        
                title = page.title()
                if "Just a moment" not in title and "Cloudflare" not in title:
                    break # Đã vượt qua thành công
                    
            # FPT Shop có sitemap riêng cho laptop, chứa toàn bộ link
            sitemap_url = "https://fptshop.com.vn/products/sitemap-may-tinh-xach-tay.xml"
            page.goto(sitemap_url, timeout=60000)
            
            # Đợi Cloudflare nếu có
            for _ in range(15):
                title = page.title()
                if "Just a moment" not in title and "Cloudflare" not in title:
                    break
                time.sleep(2)
                
            time.sleep(2)
            
            import re
            xml_content = page.content()
            
            # Lấy tất cả các thẻ <loc> trong sitemap
            sitemap_links = re.findall(r'<loc>(.*?)</loc>', xml_content)
            
            for link in sitemap_links:
                if '/may-tinh-xach-tay/' in link:
                    last_part = link.split('/')[-1]
                    # Lọc link hợp lệ (có dấu gạch ngang, dài hơn 20 ký tự, không phải link rác)
                    if '-' in last_part and len(last_part) > 20 and "linh-kien" not in link:
                        product_links.append(link)
                        
            # Nếu Playwright không đọc được XML (do bị format lại thành HTML), fallback qua BeautifulSoup
            if not product_links:
                try:
                    soup = BeautifulSoup(xml_content, "html.parser")
                    for loc in soup.find_all("loc"):
                        link = loc.text.strip()
                        if '/may-tinh-xach-tay/' in link:
                            last_part = link.split('/')[-1]
                            if '-' in last_part and len(last_part) > 20 and "linh-kien" not in link:
                                product_links.append(link)
                except Exception:
                    pass
                    
            # Loại bỏ trùng lặp và sắp xếp để đảm bảo thứ tự
            product_links = sorted(list(set(product_links)))
        
        print(f"--> Tìm thấy tổng cộng {len(product_links)} link laptop từ sitemap FPTSHOP.")
        
        if len(product_links) == 0:
            print("Không tìm thấy link, kết thúc.")
            browser.close()
            return
            
        # Chia nhỏ danh sách link (Sharding)
        chunk_size = math.ceil(len(product_links) / total_chunks)
        start_idx = (chunk - 1) * chunk_size
        end_idx = start_idx + chunk_size
        product_links = product_links[start_idx:end_idx]
        
        print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
            
        import random
        random.shuffle(product_links)
        
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN ===")
        
        final_results = []
        consecutive_cf_fails = 0
        
        for i, url in enumerate(product_links):
            print(f"[{i+1}/{len(product_links)}] Đang xử lý: {url}")
            
            max_retries = 3
            success = False
            
            for retry in range(max_retries):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    
                    # Đợi Cloudflare check (nếu có)
                    cf_cleared = False
                    for _ in range(15):
                        title = page.title()
                        try:
                            h1_text = page.evaluate("document.querySelector('h1') ? document.querySelector('h1').innerText : ''")
                        except:
                            h1_text = ""
                        
                        is_cf = ("Just a moment" in title) or ("Cloudflare" in title) or (h1_text and "fptshop.com.vn" in h1_text.lower())
                        if not is_cf:
                            cf_cleared = True
                            break
                        time.sleep(2)
                        
                    if not cf_cleared:
                        raise Exception("Kẹt ở Cloudflare quá lâu!")
                        
                    time.sleep(2)
                    success = True
                    break
                except Exception as e:
                    if retry < max_retries - 1:
                        print(f"    ! Lỗi goto (lần {retry+1}): {e}. Đang thử lại...")
                        try:
                            context.close()
                            time.sleep(1)
                            context = browser.new_context(viewport={"width": 1920, "height": 1080})
                            page = context.new_page()
                        except:
                            pass
                        time.sleep(3)
                    else:
                        print(f"    ! Bỏ qua link do lỗi goto: {e}")
                        
            if not success:
                consecutive_cf_fails += 1
                
                # Nếu bị chặn liên tiếp 3 link → Cloudflare đã chặn IP cứng, thoát script để lưu data
                if consecutive_cf_fails >= 3:
                    print(f"\n    🔴 Bị Cloudflare chặn cứng IP sau {i+1} link! Dừng script sớm để bảo toàn dữ liệu đã cào.")
                    break
                continue
            
            # Reset bộ đếm khi thành công
            consecutive_cf_fails = 0
            
            try:
                crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Cố gắng đóng popup (nếu có)
                close_popup(page)
                
                # Cuộn trang sâu hơn để hiển thị bảng thông số
                page.evaluate("window.scrollBy(0, 1000);")
                time.sleep(1)
                page.evaluate("window.scrollBy(0, 1000);")
                time.sleep(2)
                close_popup(page)
                
                # Đóng cookie banner (nếu có) để tránh chặn sự kiện click
                try:
                    page.evaluate('''() => {
                        document.querySelectorAll('button').forEach(btn => {
                            if (btn.innerText && btn.innerText.includes("Chấp nhận")) btn.click();
                        });
                    }''')
                    time.sleep(1)
                except:
                    pass
                
                # Cố gắng bấm nút Xem cấu hình chi tiết
                try:
                    page.evaluate('''() => {
                        document.querySelectorAll('button, a, span').forEach(el => {
                            let text = (el.innerText || "").toLowerCase();
                            if (text.includes("xem tất cả thông số") || text.includes("thông số kỹ thuật")) {
                                el.click();
                            }
                        });
                    }''')
                    time.sleep(2)
                except Exception as e:
                    pass
                
                html_detail = page.content()
                prod_page = Adaptor(html_detail, url=url)
                
                soup = BeautifulSoup(html_detail, 'html.parser')

                # 1. Tên sản phẩm
                h1_tag = soup.find('h1')
                product_name = " ".join(h1_tag.get_text(separator=" ", strip=True).split()) if h1_tag else ""
                
                # 2. Giá hiện tại & Giá gốc
                current_price = prod_page.css('.text-black-opacity-100.h4-bold::text, #price-product span.text-black-opacity-100::text, .st-price-main::text, .text-black-opacity-100.h6-semibold::text').get(default="").strip()
                original_price = prod_page.css('.text-neutral-gray-5.line-through::text, .text-textOnWhiteSecondary.line-through::text, .st-price-sub::text').get(default="").strip()
                
                # 3. Khuyến mãi
                # Lấy text trong danh sách thẻ li của phần "Ưu đãi được hưởng"
                promos = prod_page.css('li.flex.items-start span.text-textOnWhitePrimary::text, span.text-textOnWhitePrimary.f1-regular::text').getall()
                if not promos:
                    promos = prod_page.css('p.relative.pl-5.f1-regular::text, p.line-clamp-1.text-textOnWhitePrimary::text, p.text-textOnWhitePrimary.f1-regular.pc\\:b2-regular::text').getall()
                if not promos:
                    promos = prod_page.css('.promo-item *::text, .promotion-item *::text').getall()
                promos_clean = [p.strip() for p in promos if p.strip()]
                promo_string = " | ".join(promos_clean)
                
                # 4. Cấu hình chi tiết
                specs_dict = {}
                search_root = soup.select_one('[class*="modal"], [class*="popup"], .relative.z-50')
                if not search_root:
                    search_root = soup
                    
                rows = search_root.select('.border-dashed')
                for row in rows:
                    children = [c for c in row.children if c.name]
                    if len(children) == 2:
                        k = children[0].get_text(strip=True)
                        v = children[1].get_text(strip=True)
                        if k and v:
                            specs_dict[k] = v
                            
                # Fallback nếu không có .border-dashed
                if not specs_dict:
                    spec_rows = prod_page.css('table tr, .technical-content-item')
                    for row in spec_rows:
                        tds = row.css('td, th')
                        if len(tds) >= 2:
                            k = " ".join(tds[0].css('*::text').getall()).strip()
                            v = " ".join(tds[1].css('*::text').getall()).strip()
                            if k and v:
                                specs_dict[k] = v
                                
                specs_string = " | ".join([f"{k}: {v}" for k, v in specs_dict.items()])
                
                laptop_data = {
                    "Tên Sản Phẩm": product_name,
                    "Giá Hiện Tại": current_price,
                    "Giá Gốc": original_price,
                    "Giảm Giá": calculate_discount(current_price, original_price, ""),
                    "Khuyến Mãi": promo_string,
                    "Cấu Hình Chi Tiết": specs_string,
                    "URL": url,
                    "Ngày Thu Thập": crawl_time
                }
                
                final_results.append(laptop_data)
                print(f"    ✓ Đã lấy: {product_name}")
                
            except Exception as e:
                print(f"    x Lỗi trích xuất: {e}")
                
                # Phục hồi (Reset) lại tab trình duyệt nếu trang bị lỗi
                try:
                    context.close()
                    time.sleep(1)
                    context = browser.new_context(viewport={"width": 1920, "height": 1080})
                    page = context.new_page()
                except Exception:
                    pass
                    
            # Nghỉ ngẫu nhiên 3-6 giây để giống người thật
            time.sleep(random.uniform(3, 6))
            
            # Mỗi 25 link, nghỉ dài 30-60 giây để Cloudflare "quên" mình
            if (i + 1) % 25 == 0:
                pause = random.uniform(30, 60)
                print(f"    ⏸ Nghỉ giữa hiệp {pause:.0f}s để tránh bị chặn...")
                time.sleep(pause)
                
                # Lưu kết quả trung gian (phòng trường hợp bị sập giữa chừng)
                if final_results:
                    df_temp = pd.DataFrame(final_results)
                    df_temp.to_excel(EXCEL_FILE, index=False)
                    print(f"    💾 Đã lưu tạm {len(final_results)} laptop.")
        browser.close()
        
        # Lưu file
        if final_results:
            df = pd.DataFrame(final_results)
            df.to_excel(EXCEL_FILE, index=False)
            print(f"\n=== HOÀN THÀNH MẢNH {chunk}! Đã lưu {len(final_results)} laptop vào '{EXCEL_FILE}' ===")
        else:
            print("\n=== LỖI: Không có dữ liệu nào được thu thập. ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk', type=int, default=1, help='Phần hiện tại (bắt đầu từ 1)')
    parser.add_argument('--total-chunks', type=int, default=1, help='Tổng số phần chia')
    args = parser.parse_args()
    
    crawl_fptshop_to_excel(chunk=args.chunk, total_chunks=args.total_chunks)
