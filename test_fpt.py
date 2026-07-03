import time
from patchright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay')
    time.sleep(5)
    
    page.evaluate('window.scrollBy(0, 1000);')
    time.sleep(2)
    
    c1 = page.evaluate('document.querySelectorAll("a[href^=\'/may-tinh-xach-tay/\'], a[href^=\'/laptop\']").length')
    print(f'Items before: {c1}')
    
    btn = page.locator('button', has=page.locator('text=/(xem thêm.*kết quả|xem thêm.*sản phẩm)/i')).first
    if btn.count() == 0:
        btn = page.locator('button', has_text=re.compile(r'xem thêm', re.IGNORECASE)).first
    
    if btn.count() > 0:
        print('Button found.')
        btn.first.click(force=True)
        time.sleep(5)
        c2 = page.evaluate('document.querySelectorAll("a[href^=\'/may-tinh-xach-tay/\'], a[href^=\'/laptop\']").length')
        print(f'Items after: {c2}')
    else:
        print('Button not found')
        
    browser.close()
