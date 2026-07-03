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

def crawl_fptshop_to_excel():
    print("Khởi tạo Patchright cho FPT Shop...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--window-size=1920,1080"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM FPT SHOP ===")
        
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
                
        time.sleep(4)
        print(f"Tiêu đề trang: {page.title()}")
        close_popup(page)
        
        print("    >> Đang tải tất cả sản phẩm (bấm Xem thêm)...")
        load_more_count = 0
        last_count = 0
        
        while True:
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(1)
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(2)
            
            current_count = page.evaluate("document.querySelectorAll('a[href^=\"/may-tinh-xach-tay/\"], a[href^=\"/laptop\"]').length")
            
            if current_count == last_count:
                clicked = False
                try:
                    import re
                    # FPT Shop: Nút thường chứa "Xem thêm ... kết quả"
                    btn = page.get_by_text(re.compile(r'xem thêm.*kết quả|xem thêm.*sản phẩm', re.IGNORECASE)).locator("ancestor::button").first
                    if btn.count() == 0:
                        btn = page.locator("button", has_text=re.compile(r'xem thêm', re.IGNORECASE)).first
                        
                    if btn.count() > 0:
                        btn.first.scroll_into_view_if_needed()
                        # Dùng Playwright native click với force=True để ép click qua React
                        btn.first.click(force=True)
                        clicked = True
                except Exception:
                    pass
                
                if clicked:
                    load_more_count += 1
                    print(f"    >> Đã bấm 'Xem thêm' lần {load_more_count}")
                    time.sleep(4)
                    new_count = page.evaluate("document.querySelectorAll('a[href^=\"/may-tinh-xach-tay/\"], a[href^=\"/laptop\"]').length")
                    if new_count <= current_count:
                        time.sleep(3)
                        new_count = page.evaluate("document.querySelectorAll('a[href^=\"/may-tinh-xach-tay/\"], a[href^=\"/laptop\"]').length")
                        if new_count <= current_count:
                            break
                    current_count = new_count
                else:
                    break
                    
            last_count = current_count
            
        # Cuộn thêm vài lần để đảm bảo render hết toàn bộ thẻ
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(1)
        
        html_content = page.content()
        search_page = Adaptor(html_content, url=SEARCH_URL)
        
        # FPT Shop có thể chứa sản phẩm trong nhiều class khác nhau, lấy tất cả a tag có link laptop
        product_blocks = search_page.css('a[href^="/may-tinh-xach-tay/"], a[href^="/laptop"]')
        product_links = []
        
        for a_tag in product_blocks:
            relative_link = a_tag.css('::attr(href)').get(default="")
            last_part = relative_link.split('/')[-1] if '/' in relative_link else relative_link
            
            # Loại bỏ các link danh mục hãng (chỉ có 1 vài chữ) hoặc phụ kiện. Link sản phẩm thật luôn có dấu gạch ngang và rất dài
            if relative_link and '-' in last_part and len(last_part) > 15 and "linh-kien" not in relative_link and "phu-kien" not in relative_link:
                full_link = BASE_URL + relative_link if relative_link.startswith('/') else relative_link
                if full_link not in product_links:
                    product_links.append(full_link)
                    
        print(f"--> Tìm thấy {len(product_links)} link laptop từ trang tìm kiếm FPTSHOP.")
        if len(product_links) == 0:
            print("Không tìm thấy link, kết thúc.")
            browser.close()
            return

        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ LẤY THÔNG TIN ===")
        final_results = []
        
        for index, url in enumerate(product_links, start=1):
            print(f"[{index}/{len(product_links)}] Đang xử lý: {url}")
            
            try:
                crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(4)
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
                print(f"    ! Gặp lỗi khi xử lý link {url}: {e}")
                # Phục hồi (Reset) lại tab trình duyệt nếu trang bị lỗi
                try:
                    page.close()
                    page = context.new_page()
                    context.on("page", lambda p: p.close() if p != page else None)
                except Exception:
                    pass
                
        browser.close()
        
        if final_results:
            df = pd.DataFrame(final_results)
            df.to_excel("laptop_fptshop_all.xlsx", index=False)
            print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop vào 'laptop_fptshop_all.xlsx' ===")
        else:
            print("\n=== LỖI: Không có dữ liệu nào được thu thập. ===")

if __name__ == "__main__":
    crawl_fptshop_to_excel()
