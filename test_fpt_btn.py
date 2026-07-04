import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay')
    time.sleep(5)
    page.evaluate('window.scrollBy(0, 3000);')
    time.sleep(2)
    
    btn_html = page.evaluate('''() => {
        let btn = document.querySelector('button.bg-bgWhiteDefault');
        if(!btn) {
            btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.match(/xem thêm/i));
        }
        return btn ? btn.outerHTML : 'Not found';
    }''')
    print('Button HTML:', btn_html)
    browser.close()
