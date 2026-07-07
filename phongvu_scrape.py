import urllib.parse
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from patchright.sync_api import sync_playwright

SEARCH_URL = "https://phongvu.vn/c/laptop"

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
    """Xóa các popup/modal làm che khuất màn hình."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.evaluate('''() => {
            let modals = document.querySelectorAll('[role="dialog"], .ReactModalPortal, .modal, .popup');
            modals.forEach(m => m.style.display = 'none');
            document.body.style.overflow = 'auto';
        }''')
    except Exception:
        pass

import os
import math
import argparse

def crawl_phongvu_to_excel(chunk=1, total_chunks=1, get_links_only=False):
    import time
    import glob
    import os
    
    timestamp = int(time.time())
    EXCEL_FILE = f"laptop_phongvu_chunk_{chunk}_{timestamp}.xlsx"
    PENDING_FILE = f"phongvu_pending_chunk_{chunk}.txt"
    
    is_retry_run = len(glob.glob("*_pending_chunk_*.txt")) > 0
    if is_retry_run and not os.path.exists(PENDING_FILE):
        print(f"Mảnh {chunk} đã hoàn thành từ trước. Bỏ qua.")
        return
    
    print("Khởi tạo Patchright cho Phong Vũ...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--window-size=1920,1080"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM PHONG VŨ ===")
        
        product_links = []
        LINKS_FILE = "phongvu_links.txt"
        
        if os.path.exists(PENDING_FILE):
            print(f"=== ĐANG CHẠY TIẾP TỤC MẢNH {chunk} (RETRY) ===")
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                product_links = [line.strip() for line in f if line.strip()]
        elif not get_links_only and os.path.exists(LINKS_FILE):
            print(f"=== TÌM THẤY FILE {LINKS_FILE}, BỎ QUA LEVEL 0 ===")
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                product_links = [line.strip() for line in f if line.strip()]
        else:
            # Thử tối đa 3 lần tải lại trang nếu bị kẹt ở Cloudflare
            for attempt in range(3):
                page.goto(SEARCH_URL, wait_until="domcontentloaded")
                print(f"Đang kiểm tra Cloudflare (lần thử {attempt + 1})...")
                
                for _ in range(12):
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
            
            time.sleep(3)
            print(f"Tiêu đề trang: {page.title()}")
            close_popup(page)
            
            print("    >> Đang gọi API lấy danh sách toàn bộ sản phẩm (ẩn)...")
            
            # Inject JavaScript để fetch API danh sách sản phẩm của Phong Vũ (bỏ qua giới hạn hiển thị của frontend)
            js_fetch_all = """
            async () => {
                let allLinks = [];
                let page = 1;
                while (true) {
                    try {
                        let response = await fetch('https://discovery.tekoapis.com/api/v2/search-skus-v2', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                terminalId: 4,
                                page: page,
                                pageSize: 40,
                                slug: '/c/laptop',
                                filter: {},
                                sorting: {sort: 'SORT_BY_CREATED_AT', order: 'ORDER_BY_DESCENDING'}
                            })
                        });
                        
                        let data = await response.json();
                        let products = data?.data?.products || [];
                        
                        if (products.length === 0) {
                            break;
                        }
                        
                        for (let p of products) {
                            if (p.canonical) {
                                allLinks.push('https://phongvu.vn/' + p.canonical);
                            }
                        }
                        
                        page++;
                    } catch (e) {
                        break;
                    }
                }
                return allLinks;
            }
            """
            product_links = page.evaluate(js_fetch_all)
            product_links = sorted(list(set(product_links)))
            
            print(f"--> Tìm thấy tổng cộng {len(product_links)} link laptop từ trang tìm kiếm Phong Vũ.")
            if len(product_links) == 0:
                print("❌ Lỗi: Không tìm thấy link nào từ trang chủ (có thể do bị Cloudflare chặn cứng). Dừng script.")
                browser.close()
                import sys
                sys.exit(1)
                
            if get_links_only:
                with open(LINKS_FILE, "w", encoding="utf-8") as f:
                    for link in product_links:
                        f.write(link + "\n")
                print(f"--> Đã lưu {len(product_links)} link ra file {LINKS_FILE}")
                browser.close()
                return
                
        if not os.path.exists(PENDING_FILE):
            product_links = sorted(list(set(product_links)))
            
            # Chia nhỏ danh sách link (Sharding)
            chunk_size = math.ceil(len(product_links) / total_chunks)
            start_idx = (chunk - 1) * chunk_size
            end_idx = start_idx + chunk_size
            product_links = product_links[start_idx:end_idx]
            
            print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(product_links)} link (từ {start_idx} đến {end_idx-1})")
                
        import random
        random.shuffle(product_links)
        
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ TRÍCH XUẤT THÔNG TIN ===")
        
        final_results = []
        consecutive_cf_fails = 0  # Đếm số lần bị Cloudflare chặn liên tiếp
            
        for i, link in enumerate(product_links, 1):
            print(f"[{i}/{len(product_links)}] Đang xử lý: {link}")
            
            max_retries = 3
            success = False
            for retry in range(max_retries):
                try:
                    page.goto(link, wait_until="domcontentloaded", timeout=40000)
                    
                    # Đợi Cloudflare check (nếu có)
                    cf_cleared = False
                    for _ in range(15):
                        title = page.title()
                        try:
                            h1_text = page.evaluate("document.querySelector('h1') ? document.querySelector('h1').innerText : ''")
                        except:
                            h1_text = ""
                        
                        is_cf = ("Just a moment" in title) or ("Cloudflare" in title) or (h1_text and "phongvu.vn" in h1_text.lower())
                        if not is_cf:
                            cf_cleared = True
                            break
                        time.sleep(2)
                        
                    if not cf_cleared:
                        raise Exception("Kẹt ở Cloudflare quá lâu!")
                        
                    time.sleep(3)
                    success = True
                    break
                except Exception as e:
                    if retry < max_retries - 1:
                        print(f"    ! Lỗi goto (lần {retry+1}): {e}. Đang thử lại...")
                        # Xoá phiên cũ để đổi session với Cloudflare
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
                    print(f"\n    🔴 Bị Cloudflare chặn cứng IP sau {i} link! Dừng script sớm để bảo toàn dữ liệu đã cào.")
                    
                    failed_start_idx = max(0, i - 1 - 2) # i là enumerate start=1, nên index 0-based là i-1
                    remaining_links = product_links[failed_start_idx:]
                    with open(PENDING_FILE, "w", encoding="utf-8") as f:
                        for r_link in remaining_links:
                            f.write(r_link + "\n")
                    print(f"    💾 Đã lưu {len(remaining_links)} link dang dở vào {PENDING_FILE}")
                    
                    break
                continue
                
            # Chạy thành công
            consecutive_cf_fails = 0
            
            # Reset bộ đếm khi thành công
            consecutive_cf_fails = 0
                
            try:
                close_popup(page)
                
                # Cuộn từ từ xuống cuối trang để ép load toàn bộ nội dung (đặc biệt là bảng thông số bị lazy-load)
                for _ in range(1, 4):
                    page.evaluate("window.scrollBy(0, document.body.scrollHeight / 3);")
                    time.sleep(0.5)
                
                # Cuộn ngược lên một chút để tìm bảng thông số (thường nằm ở giữa trang)
                page.evaluate("window.scrollBy(0, -500);")
                time.sleep(1)
                
                # Cố gắng tìm và click nút "Xem thêm" thông số kỹ thuật (để mở rộng bảng)
                try:
                    page.evaluate('''() => {
                        document.querySelectorAll('button').forEach(btn => {
                            if ((btn.innerText || "").includes("Xem thêm")) {
                                btn.scrollIntoView({block: 'center'});
                                btn.click();
                            }
                        });
                    }''')
                    time.sleep(3) # Chờ render
                except Exception:
                    pass
                
                detail_html = page.content()
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                
                # Tên sản phẩm
                h1_tag = detail_soup.find("h1")
                name = h1_tag.get_text(strip=True) if h1_tag else "N/A"
                if name == "N/A":
                    print("    x Lỗi: Không lấy được tên sản phẩm, bỏ qua.")
                    continue
                
                # Giá bán & Giá gốc
                price = "N/A"
                original_price = "N/A"
                
                # Giá bán thường nằm trong div type="title" color="primary500"
                price_tag = detail_soup.find("div", {"type": "title", "color": "primary500"})
                if price_tag:
                    price = price_tag.get_text(strip=True)
                
                # Giá gốc thường nằm trong div type="body" color="textSecondary" gần phần % giảm giá
                orig_tags = detail_soup.find_all("div", {"type": "body", "color": "textSecondary"})
                for t in orig_tags:
                    text = t.get_text(strip=True)
                    if "₫" in text and text != price:
                        parent = t.parent
                        if parent and parent.get("direction") == "row":
                            original_price = text
                            break
                
                # Khuyến mãi
                promos = []
                direct_promos = detail_soup.find_all("div", {"color": "textTitle"})
                for dp in direct_promos:
                    txt = dp.get_text(strip=True)
                    if "Giảm" in txt or "áp dụng" in txt:
                        promos.append(txt)
                
                promo_uls = detail_soup.find_all("ul")
                for ul in promo_uls:
                    for li in ul.find_all("li"):
                        span = li.find("span")
                        if span:
                            promos.append(span.get_text(strip=True))
                
                promo_text = " | ".join(set(promos))
                
                # Cấu hình chi tiết
                specs = ""
                spec_rows = detail_soup.find_all("div", {"direction": "row", "width": "100%"})
                for row in spec_rows:
                    divs = row.find_all("div", recursive=False)
                    if len(divs) >= 2:
                        key = divs[0].get_text(strip=True)
                        val = divs[1].get_text(strip=True)
                        if key and val and key.lower() not in ['xem thêm', 'thông số kỹ thuật']:
                            specs += f"{key}: {val}\n"
                
                print(f"    ✓ Đã lấy: {name}")
                final_results.append({
                    "Tên Sản Phẩm": name,
                    "Giá Hiện Tại": price,
                    "Giá Gốc": original_price,
                    "Giảm Giá": calculate_discount(price, original_price, ""),
                    "Khuyến Mãi": promo_text,
                    "Cấu Hình Chi Tiết": specs.strip(),
                    "URL": link,
                    "Ngày Thu Thập": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"    x Lỗi khi xử lý {link}: {e}")
                try:
                    context.close()
                    time.sleep(1)
                    context = browser.new_context(viewport={"width": 1920, "height": 1080})
                    page = context.new_page()
                except:
                    pass
            
            # Nghỉ ngẫu nhiên 3-6 giây để giống người thật
            time.sleep(random.uniform(3, 6))
            
            # Mỗi 25 link, nghỉ dài 30-60 giây và lưu kết quả trung gian
            if i % 25 == 0:
                pause = random.uniform(30, 60)
                print(f"    ⏸ Nghỉ giữa hiệp {pause:.0f}s để tránh bị chặn...")
                time.sleep(pause)
                
                # Lưu kết quả trung gian (phòng trường hợp bị sập giữa chừng)
                if final_results:
                    df_temp = pd.DataFrame(final_results)
                    df_temp.to_excel(EXCEL_FILE, index=False)
                    print(f"    💾 Đã lưu tạm {len(final_results)} laptop.")
        
        browser.close()
        
        if consecutive_cf_fails < 3 and os.path.exists(PENDING_FILE):
            os.remove(PENDING_FILE)
            print(f"    ✨ Đã hoàn thành mảnh {chunk}, xóa file pending!")
            
        # Lưu file
        if final_results:
            df = pd.DataFrame(final_results)
            df.to_excel(EXCEL_FILE, index=False)
            print(f"\n=== HOÀN THÀNH MẢNH {chunk}! Đã lưu {len(final_results)} laptop vào '{EXCEL_FILE}' ===")
        else:
            print("\n=== LỖI: Không có dữ liệu nào được thu thập. ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk', type=int, default=1, help='Số thứ tự của mảnh hiện tại (1-based)')
    parser.add_argument('--total-chunks', type=int, default=1, help='Tổng số mảnh cần chia')
    parser.add_argument('--get-links-only', action='store_true', help='Chỉ quét link và lưu ra file')
    args = parser.parse_args()
    
    crawl_phongvu_to_excel(chunk=args.chunk, total_chunks=args.total_chunks, get_links_only=args.get_links_only)
