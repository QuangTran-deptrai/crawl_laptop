import time
from patchright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay')
    time.sleep(5)
    
    last_count = 0
    loop_count = 0
    
    while True:
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(1)
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(2)
        
        current_count = page.evaluate('document.querySelectorAll("a[href^=\'/may-tinh-xach-tay/\'], a[href^=\'/laptop\']").length')
        
        if current_count == last_count:
            btn = page.locator('button', has=page.locator('text=/(xem thêm.*kết quả|xem thêm.*sản phẩm)/i')).first
            if btn.count() == 0:
                btn = page.locator('button', has_text=re.compile(r'xem thêm', re.IGNORECASE)).first
                
            if btn.count() > 0:
                print('Clicking button...')
                btn.first.click(force=True)
                time.sleep(4)
                new_count = page.evaluate('document.querySelectorAll("a[href^=\'/may-tinh-xach-tay/\'], a[href^=\'/laptop\']").length')
                if new_count <= current_count:
                    time.sleep(3)
                    new_count = page.evaluate('document.querySelectorAll("a[href^=\'/may-tinh-xach-tay/\'], a[href^=\'/laptop\']").length')
                    if new_count <= current_count:
                        print('Count did not increase after click.')
                        break
                current_count = new_count
            else:
                print('No button found.')
                break
                
        last_count = current_count
        loop_count += 1
        print(f'Loop {loop_count}: {current_count} items')
        if loop_count > 25:
            break
            
    browser.close()
