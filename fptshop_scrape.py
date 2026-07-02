import time
import pandas as pd
from datetime import datetime
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

BASE_URL = "https://fptshop.com.vn"
SEARCH_URL = "https://fptshop.com.vn/may-tinh-xach-tay"

def close_popup(page):
    try:
        page.evaluate('''() => {
            document.querySelectorAll('iframe, video').forEach(el => el.remove());
            document.querySelectorAll('.cancel-button, .close-modal, .insider-opt-in-notification-button').forEach(el => el.click());
        }''')
        time.sleep(0.5)
    except Exception:
        pass

def crawl_fptshop_to_excel():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--mute-audio"])
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        context.on("page", lambda p: p.close() if p != page else None)
        
        print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM FPT SHOP ===")
        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        time.sleep(4)
        close_popup(page)
        
        print("    >> Đang tải tất cả sản phẩm (bấm Xem thêm)...")
        load_more_count = 0
        retry_count = 0
        while True:
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(1)
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(2)
            
            clicked = page.evaluate('''() => {
                // FPT Shop có nhiều nút xem thêm, nút mở rộng sản phẩm thường kèm chữ "kết quả" hoặc "sản phẩm"
                let btns = document.querySelectorAll('button');
                for (let btn of btns) {
                    let text = btn.innerText.toLowerCase();
                    if (text.includes("xem thêm") && (text.includes("kết quả") || text.includes("sản phẩm"))) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }''')
                
            if clicked:
                load_more_count += 1
                retry_count = 0
                print(f"    >> Đã bấm 'Xem thêm' lần {load_more_count}")
                time.sleep(4)
                continue
            else:
                retry_count += 1
                if retry_count >= 3:
                    break
                print(f"    >> Chờ tải thêm (thử lại {retry_count}/3)...")
                time.sleep(3)
            
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
                    cookie_btn = page.locator('button:has-text("Chấp nhận")').first
                    if cookie_btn.is_visible(timeout=1000):
                        cookie_btn.click()
                        time.sleep(1)
                except:
                    pass
                
                # Cố gắng bấm nút Xem cấu hình chi tiết
                try:
                    btn = page.locator('button:has-text("Xem tất cả thông số"), a:has-text("Xem tất cả thông số"), span:has-text("Thông số kỹ thuật")').first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        time.sleep(2)
                except Exception as e:
                    pass
                
                html_detail = page.content()
                prod_page = Adaptor(html_detail, url=url)
                
                from bs4 import BeautifulSoup
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
                promos_clean = [p.strip() for p in promos if p.strip() and "Trả góp" not in p and "Giảm ngay" not in p] 
                # Lấy tất cả trừ "Trả góp 0%", nếu user cần thì bỏ filter đi
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
                    "Khuyến Mãi": promo_string,
                    "Cấu Hình Chi Tiết": specs_string,
                    "URL": url,
                    "Ngày Thu Thập": crawl_time
                }
                
                final_results.append(laptop_data)
                print(f"    ✓ Đã lấy: {product_name}")
                
            except Exception as e:
                print(f"    ! Gặp lỗi khi xử lý link {url}: {e}")
                
        browser.close()
        
        if final_results:
            df = pd.DataFrame(final_results)
            df.to_excel("laptop_fptshop_all.xlsx", index=False)
            print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop vào 'laptop_fptshop_all.xlsx' ===")
        else:
            print("\n=== LỖI: Không có dữ liệu nào được thu thập. ===")

if __name__ == "__main__":
    crawl_fptshop_to_excel()
