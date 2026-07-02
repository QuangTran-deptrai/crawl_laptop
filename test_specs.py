import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

options = uc.ChromeOptions()
driver = uc.Chrome(options=options)
url = 'https://phongvu.vn/may-tinh-xach-tay-laptop-lenovo-ideapad-slim-3-16iph11-83us002wvn-ultra-7-355-xam--s260602917'
try:
    driver.get(url)
    time.sleep(5)
    
    # Đóng popup
    driver.execute_script('''
        document.querySelectorAll('img[src*="teko-gae"], img[src*="POP"], img.css-qi53z0').forEach(el => {
            let parent = el.closest('div[class]');
            if (parent) parent.remove(); else el.remove();
        });
        document.querySelectorAll('[class*="popup"], .css-vkbz44, .css-5h8scr, [name="giqalwnk"], .css-11y3uql').forEach(el => el.remove());
        document.querySelectorAll('div').forEach(el => {
            let style = window.getComputedStyle(el);
            let z = parseInt(style.zIndex) || 0;
            if ((style.position === 'fixed' || style.position === 'absolute') && z >= 90) el.remove();
        });
    ''')
    time.sleep(1)
    
    driver.execute_script('window.scrollBy(0, 1000);')
    time.sleep(1)
    
    btns = driver.find_elements(By.XPATH, "//button[.//div[contains(text(), 'Xem thêm')]] | //div[contains(@class, 'button-text') and contains(text(), 'Xem thêm')]")
    for btn in btns:
        if btn.is_displayed():
            try:
                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn)
                time.sleep(0.5)
                # Dùng JS click
                driver.execute_script('arguments[0].click();', btn)
                print('JS Clicked Xem them!')
            except Exception as e:
                print('Error:', e)
    
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    spec_rows = soup.find_all('div', {'direction': 'row', 'width': '100%'})
    print(f'Found {len(spec_rows)} spec rows using width=100%.')
    
    # Alternative: find table block
    # In the HTML user provided: The specs are inside a div containing text "Thông số kỹ thuật"
    desc = soup.find('div', id='desktop-product-description')
    if desc:
        count = 0
        for d in desc.find_all('div', {'color': 'textSecondary'}):
            parent = d.parent
            if parent and parent.get('direction') == 'row':
                count += 1
        print(f'Found {count} spec rows using description block structure.')
        
except Exception as e:
    print(e)
finally:
    driver.quit()
