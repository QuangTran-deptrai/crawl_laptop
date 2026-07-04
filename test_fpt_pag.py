import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay?trang=2')
    time.sleep(5)
    first_few = page.evaluate('''() => {
        return Array.from(document.querySelectorAll("a[href^='/may-tinh-xach-tay/']")).slice(0, 3).map(a => a.getAttribute('href'))
    }''')
    print('Trang 2:', first_few)
    
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay?trang=3')
    time.sleep(5)
    first_few3 = page.evaluate('''() => {
        return Array.from(document.querySelectorAll("a[href^='/may-tinh-xach-tay/']")).slice(0, 3).map(a => a.getAttribute('href'))
    }''')
    print('Trang 3:', first_few3)
    
    browser.close()
