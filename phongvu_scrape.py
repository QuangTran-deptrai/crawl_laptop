import urllib.parse
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from patchright.sync_api import sync_playwright

SEARCH_URL = "https://phongvu.vn/c/laptop"

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

def crawl_phongvu_to_excel():
    print("Khởi tạo Patchright cho Phong Vũ...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--window-size=1920,1080"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM PHONG VŨ ===")
            
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
                
        time.sleep(5)
        
        print("    >> Đang tải tất cả sản phẩm (scroll)...")
        no_change_count = 0
        last_count = 0
        
        while True:
            close_popup(page)
            
            # Cuộn từ từ xuống cuối
            page.evaluate("window.scrollBy(0, window.innerHeight);")
            time.sleep(1.5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Đếm sản phẩm hiện có
            current_count = page.evaluate("document.querySelectorAll('a[href*=\"-s\"]').length")
            
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 3:
                    break
            else:
                no_change_count = 0
                last_count = current_count
                
        print(f"--> Tìm thấy {current_count} link laptop từ trang tìm kiếm Phong Vũ.")
            
        time.sleep(2)
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        product_links = []
        
        # Bắt tất cả thẻ <a> có link chứa "-s" (mã SKU của Phong Vũ) và liên quan đến laptop
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "-s" in href and ("laptop" in href.lower() or "apple-macbook" in href.lower()):
                full_link = urllib.parse.urljoin("https://phongvu.vn", href)
                if full_link not in product_links:
                    product_links.append(full_link)
        
        # Nếu vẫn không thấy, thử tìm tất cả link trong các thẻ div có class chứa 'product'
        if not product_links:
            for div in soup.find_all("div", class_=lambda c: c and "product" in c.lower()):
                for a_tag in div.find_all("a", href=True):
                    href = a_tag["href"]
                    full_link = urllib.parse.urljoin("https://phongvu.vn", href)
                    if full_link not in product_links:
                        product_links.append(full_link)
                        
        print(f"--> Tìm thấy {len(product_links)} link laptop từ trang tìm kiếm Phong Vũ.")
        if len(product_links) == 0:
            browser.close()
            return
            
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ TRÍCH XUẤT THÔNG TIN ===")
        
        final_results = []
            
        for i, link in enumerate(product_links, 1):
            print(f"[{i}/{len(product_links)}] Đang xử lý: {link}")
            try:
                page.goto(link, wait_until="domcontentloaded")
                
                time.sleep(3)
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
                # Phục hồi (Reset) tab trình duyệt
                try:
                    page.close()
                    page = context.new_page()
                except:
                    pass
        
        browser.close()
        
        if final_results:
            df = pd.DataFrame(final_results)
            df.to_excel("laptop_phongvu_all.xlsx", index=False)
            print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop vào 'laptop_phongvu_all.xlsx' ===")
        else:
            print("\n=== LỖI: Không có dữ liệu nào được thu thập. ===")

if __name__ == "__main__":
    crawl_phongvu_to_excel()
