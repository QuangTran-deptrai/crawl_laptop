"""Test script: Tìm và click nút 'Xem thêm sản phẩm' trên Phong Vũ - v2"""
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def nuke_popups(driver):
    """Xóa sạch mọi popup/overlay đang chặn màn hình."""
    driver.execute_script('''
        // Xóa popup hình ảnh cụ thể từ teko-gae
        document.querySelectorAll('img[src*="teko-gae"], img[src*="POP"], img.css-qi53z0').forEach(el => {
            // Xóa cả phần tử cha chứa nó (thường là div overlay)
            let parent = el.closest('div[class]');
            if (parent) parent.remove();
            else el.remove();
        });
        // Xóa theo class cụ thể
        document.querySelectorAll('[class*="popup"], .css-vkbz44, .css-5h8scr, [name="giqalwnk"], [data-id="giqalwnk"], .css-11y3uql, .css-qi53z0').forEach(el => el.remove());
        // Xóa mọi overlay fixed/absolute có z-index cao
        document.querySelectorAll('div').forEach(el => {
            let style = window.getComputedStyle(el);
            let z = parseInt(style.zIndex) || 0;
            if ((style.position === 'fixed' || style.position === 'absolute') && z >= 90) {
                el.remove();
            }
        });
        document.body.style.overflow = 'auto';
    ''')

options = uc.ChromeOptions()
options.add_argument("--start-maximized")
driver = uc.Chrome(options=options)

try:
    driver.get("https://phongvu.vn/c/laptop")
    time.sleep(5)
    nuke_popups(driver)
    
    count_before = driver.execute_script("return document.querySelectorAll('.product-card a').length")
    print(f"[1] Số sản phẩm ban đầu: {count_before}")
    
    # Tìm nút
    btns = driver.find_elements(By.XPATH, "//*[contains(text(), 'Xem thêm sản phẩm')]")
    print(f"[2] Tìm thấy {len(btns)} phần tử")
    
    if btns:
        btn = btns[0]
        
        # Cuộn đến nút
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(2)
        
        # XÓA POPUP LẦN NỮA ngay trước khi click (popup hay xuất hiện lại sau khi cuộn)
        nuke_popups(driver)
        time.sleep(0.5)
        
        # Xóa target="_blank" trên thẻ <a> cha
        driver.execute_script('''
            let el = arguments[0];
            let a = el.closest('a');
            if (a) {
                a.removeAttribute('target');
                a.removeAttribute('rel');
            }
        ''', btn)
        
        tabs_before = len(driver.window_handles)
        
        # Thử click bình thường
        try:
            btn.click()
            print("[3] Click Selenium thành công!")
        except Exception as e:
            print(f"[3] Click Selenium lỗi: {e.__class__.__name__}")
            # Fallback: JS click
            driver.execute_script("arguments[0].click();", btn)
            print("[3] Click JS thành công!")
        
        time.sleep(5)
        
        # Kiểm tra tab mới
        tabs_after = len(driver.window_handles)
        if tabs_after > tabs_before:
            print(f"   !! Mở tab mới: {tabs_before} -> {tabs_after}")
            driver.switch_to.window(driver.window_handles[-1])
            print(f"   !! URL tab mới: {driver.current_url}")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        
        count_after = driver.execute_script("return document.querySelectorAll('.product-card a').length")
        print(f"[4] Số sản phẩm sau click: {count_after} (trước: {count_before})")
        
        if count_after > count_before:
            print("==> THÀNH CÔNG!")
        else:
            print("==> Chưa có thêm. Thử click lần 2...")
            nuke_popups(driver)
            # Tìm lại nút
            btns2 = driver.find_elements(By.XPATH, "//*[contains(text(), 'Xem thêm sản phẩm')]")
            if btns2:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btns2[0])
                time.sleep(1)
                nuke_popups(driver)
                driver.execute_script("arguments[0].click();", btns2[0])
                print("[5] Click JS lần 2")
                time.sleep(5)
                count_final = driver.execute_script("return document.querySelectorAll('.product-card a').length")
                print(f"[6] Số sản phẩm cuối: {count_final}")
    else:
        print("KHÔNG TÌM THẤY NÚT!")

    input("Nhấn Enter để đóng...")
except Exception as e:
    print(f"LỖI: {e}")
finally:
    try:
        driver.quit()
    except:
        pass
