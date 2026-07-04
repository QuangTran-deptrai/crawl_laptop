import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    page.evaluate('window.scrollBy(0, document.body.scrollHeight);')
    time.sleep(2)
    
    c1 = page.evaluate("document.querySelectorAll('a[href*=\"-s\"]').length")
    print(f'Items before: {c1}')
    
    btn = page.get_by_text("Xem thêm sản phẩm", exact=False).last
    if btn.count() == 0:
        btn = page.locator(".button-text:has-text('Xem thêm')").last
        
    if btn.count() > 0:
        print('Button found.')
        btn.first.scroll_into_view_if_needed()
        try:
            btn.first.click(force=True)
        except Exception as e:
            print('Click error:', e)
        time.sleep(5)
        c2 = page.evaluate("document.querySelectorAll('a[href*=\"-s\"]').length")
        print(f'Items after: {c2}')
        print(f'Pages open: {len(browser.contexts[0].pages)}')
    else:
        print('Button not found')
        
    browser.close()
