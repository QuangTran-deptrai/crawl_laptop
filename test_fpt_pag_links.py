import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay?trang=1')
    time.sleep(5)
    page.evaluate('window.scrollBy(0, 3000);')
    time.sleep(2)
    first_few = page.evaluate('''() => {
        return Array.from(document.querySelectorAll("a[href^='/may-tinh-xach-tay/']")).map(a => a.getAttribute('href')).filter(l => l.length > 25).slice(0, 3)
    }''')
    print('Trang 1:', first_few)
    
    page.goto('https://fptshop.com.vn/may-tinh-xach-tay?trang=2')
    time.sleep(5)
    page.evaluate('window.scrollBy(0, 3000);')
    time.sleep(2)
    first_few3 = page.evaluate('''() => {
        return Array.from(document.querySelectorAll("a[href^='/may-tinh-xach-tay/']")).map(a => a.getAttribute('href')).filter(l => l.length > 25).slice(0, 3)
    }''')
    print('Trang 2:', first_few3)
    
    browser.close()
