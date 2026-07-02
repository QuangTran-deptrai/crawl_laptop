import time
import urllib.parse
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

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

SEARCH_URL = "https://phongvu.vn/c/laptop"
TEST_MODE = False
MAX_TEST_ITEMS = 5

def close_popup(driver):
    """Xóa sạch mọi popup/overlay đang chặn màn hình."""
    try:
        driver.execute_script('''
            // Xóa popup hình ảnh cụ thể từ teko-gae (popup quảng cáo chính)
            document.querySelectorAll('img[src*="teko-gae"], img[src*="POP"], img.css-qi53z0').forEach(el => {
                let parent = el.closest('div[class]');
                if (parent) parent.remove();
                else el.remove();
            });
            // Xóa theo class/tên cụ thể
            document.querySelectorAll('[class*="popup"], .css-vkbz44, .css-5h8scr, [name="giqalwnk"], [data-id="giqalwnk"], .css-11y3uql, .css-qi53z0').forEach(el => el.remove());
            // Xóa mọi overlay fixed/absolute có z-index cao
            document.querySelectorAll('div').forEach(el => {
                let style = window.getComputedStyle(el);
                let z = parseInt(style.zIndex) || 0;
                if ((style.position === 'fixed' || style.position === 'absolute') && z >= 90) {
                    el.remove();
                }
            });
            // Khôi phục thanh cuộn
            document.body.style.overflow = 'auto';
        ''')
    except Exception:
        pass

def crawl_phongvu_to_excel():
    print("=== [LEVEL 0] ĐANG QUÉT TRANG TÌM KIẾM PHONG VŨ ===")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument('--window-size=1920,1080')
    # Xử lý lỗi lệch version giữa Chrome cài sẵn trên server và ChromeDriver tải về
    try:
        driver = uc.Chrome(options=options)
    except Exception as e:
        error_msg = str(e)
        if "This version of ChromeDriver only supports Chrome version" in error_msg:
            import re
            match = re.search(r"Current browser version is (\d+)", error_msg)
            if match:
                version = int(match.group(1))
                print(f"-> Đã phát hiện Chrome version {version}. Đang thử lại với version_main={version}...")
                
                # BẮT BUỘC TẠO LẠI OPTIONS VÌ UC KHÔNG CHO PHÉP TÁI SỬ DỤNG
                options2 = uc.ChromeOptions()
                options2.add_argument("--start-maximized")
                
                driver = uc.Chrome(options=options2, version_main=version)
            else:
                raise e
        else:
            raise e
            
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        
        # Thử tối đa 3 lần tải lại trang nếu bị kẹt ở Cloudflare
        for attempt in range(3):
            driver.get(SEARCH_URL)
            print(f"Đang kiểm tra Cloudflare (lần thử {attempt + 1})...")
            
            for _ in range(12):
                if "Just a moment" in driver.title or "Cloudflare" in driver.title:
                    time.sleep(2)
                    try:
                        iframe = driver.find_element(By.TAG_NAME, "iframe")
                        driver.switch_to.frame(iframe)
                        cb = driver.find_element(By.TAG_NAME, "input")
                        if cb:
                            # Dùng ActionChains để click mô phỏng chuột thật thay vì Javascript
                            ActionChains(driver).move_to_element(cb).click().perform()
                        driver.switch_to.default_content()
                    except Exception:
                        driver.switch_to.default_content()
                else:
                    break
                    
            if "Just a moment" not in driver.title and "Cloudflare" not in driver.title:
                break # Đã vượt qua thành công
                
        time.sleep(5)
        
        print("    >> Đang tải tất cả sản phẩm (scroll)...")
        last_count = 0
        load_more_count = 0
        
        while True:
            close_popup(driver)
            
            # Cuộn từ từ xuống cuối
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(1.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Đếm sản phẩm hiện có
            current_count = driver.execute_script("return document.querySelectorAll('a[href*=\"-s\"]').length")
            
            if current_count == last_count:
                clicked = False
                try:
                    # Tìm nút "Xem thêm sản phẩm"
                    elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Xem thêm sản phẩm')]")
                    if not elements:
                        elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'button-text') and contains(text(), 'Xem thêm')]")
                    
                    if elements:
                        btn = elements[0]
                        # Cuộn nút vào giữa màn hình
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(2)
                        
                        # XÓA POPUP NGAY TRƯỚC KHI CLICK (popup hay xuất hiện lại sau cuộn)
                        close_popup(driver)
                        time.sleep(0.5)
                        
                        # Xóa target="_blank" trên thẻ <a> cha để không mở tab mới
                        driver.execute_script('''
                            let el = arguments[0];
                            let a = el.closest('a');
                            if (a) { a.removeAttribute('target'); a.removeAttribute('rel'); }
                        ''', btn)
                        
                        # Click
                        try:
                            btn.click()
                            clicked = True
                        except Exception:
                            # Fallback: JS click
                            driver.execute_script("arguments[0].click();", btn)
                            clicked = True
                except Exception:
                    pass
                
                if clicked:
                    load_more_count += 1
                    print(f"    >> Đã bấm 'Xem thêm' lần {load_more_count}")
                    time.sleep(5) 
                    
                    new_count = driver.execute_script("return document.querySelectorAll('a[href*=\"-s\"]').length")
                    if new_count <= current_count:
                        time.sleep(3)
                        new_count = driver.execute_script("return document.querySelectorAll('a[href*=\"-s\"]').length")
                        if new_count <= current_count:
                            break
                    current_count = new_count
                else:
                    break
                    
            last_count = current_count
            
        time.sleep(2)
        
        html = driver.page_source
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
        print("\n=== [LEVEL 1] TRUY CẬP TỪNG LINK ĐỂ TRÍCH XUẤT THÔNG TIN ===")
        
        final_results = []
        links_to_process = product_links
        if TEST_MODE and len(links_to_process) > MAX_TEST_ITEMS:
            links_to_process = links_to_process[:MAX_TEST_ITEMS]
            print(f"*** CHẾ ĐỘ TEST: Chỉ chạy {MAX_TEST_ITEMS} sản phẩm đầu tiên ***")
            
        for i, link in enumerate(links_to_process, 1):
            print(f"[{i}/{len(links_to_process)}] Đang xử lý: {link}")
            try:
                driver.get(link)
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                except TimeoutException:
                    pass
                
                time.sleep(2)
                close_popup(driver)
                
                # Cuộn từ từ xuống cuối trang để ép load toàn bộ nội dung (đặc biệt là bảng thông số bị lazy-load)
                for i in range(1, 4):
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {i} / 3);")
                    time.sleep(0.5)
                
                # Cuộn ngược lên một chút để tìm bảng thông số (thường nằm ở giữa trang)
                driver.execute_script("window.scrollBy(0, -500);")
                time.sleep(1)
                
                # Cố gắng tìm và click nút "Xem thêm" thông số kỹ thuật (để mở rộng bảng)
                try:
                    # Chỉ tìm các thẻ <button> có chứa chữ Xem thêm (tránh tìm cả thẻ <div> bên trong gây click đúp)
                    spec_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Xem thêm')]")
                    for btn in spec_btns:
                        try:
                            # Tránh click lại nút đã chuyển thành "Thu gọn"
                            if "Xem thêm" in btn.text:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1) # Nghỉ một lát giữa các lần click
                        except Exception:
                            pass
                    # CHỜ 3 GIÂY ĐỂ BẢNG THÔNG SỐ RENDER ĐẦY ĐỦ (React cần thời gian)
                    time.sleep(3)
                except Exception:
                    pass
                
                detail_html = driver.page_source
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
                # Thử tìm thẻ có text chứa '₫' và gạch ngang hoặc nằm trong nhóm giá
                orig_tags = detail_soup.find_all("div", {"type": "body", "color": "textSecondary"})
                for t in orig_tags:
                    text = t.get_text(strip=True)
                    if "₫" in text and text != price:
                        # Kiểm tra xem nó có nằm cạnh thẻ giảm giá (vd: -9%) không
                        parent = t.parent
                        if parent and parent.get("direction") == "row":
                            original_price = text
                            break
                
                # Khuyến mãi
                promos = []
                # Tìm các thẻ div giảm giá trực tiếp
                direct_promos = detail_soup.find_all("div", {"color": "textTitle"})
                for dp in direct_promos:
                    txt = dp.get_text(strip=True)
                    if "Giảm" in txt or "áp dụng" in txt:
                        promos.append(txt)
                
                # Tìm trong danh sách ul li (Khuyến mãi liên quan)
                promo_uls = detail_soup.find_all("ul")
                for ul in promo_uls:
                    for li in ul.find_all("li"):
                        span = li.find("span")
                        if span:
                            promos.append(span.get_text(strip=True))
                
                promo_text = " | ".join(set(promos))
                
                # Cấu hình chi tiết
                specs = ""
                # Bảng thông số thường là các hàng div direction="row" width="100%"
                spec_rows = detail_soup.find_all("div", {"direction": "row", "width": "100%"})
                for row in spec_rows:
                    divs = row.find_all("div", recursive=False)
                    if len(divs) >= 2:
                        key = divs[0].get_text(strip=True)
                        val = divs[1].get_text(strip=True)
                        # Bỏ qua các hàng không phải là thông số (ví dụ: nút xem thêm, tiêu đề)
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
                    "Link Sản Phẩm": link
                })
            except Exception as e:
                print(f"    x Lỗi khi xử lý {link}: {e}")
                continue
                
    except Exception as e:
        print(f"Lỗi trong quá trình quét: {e}")
    finally:
        try:
            driver.quit()
        except OSError:
            pass
        
    if final_results:
        df = pd.DataFrame(final_results)
        df.to_excel("laptop_phongvu_all.xlsx", index=False)
        print(f"\n=== HOÀN THÀNH! Đã lưu {len(final_results)} laptop vào 'laptop_phongvu_all.xlsx' ===")

if __name__ == "__main__":
    crawl_phongvu_to_excel()
