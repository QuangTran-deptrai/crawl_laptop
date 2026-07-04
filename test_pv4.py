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
    
    # Locate the a tag directly
    btn = page.locator('a', has_text='Xem thêm sản phẩm').first
        
    if btn.count() > 0:
        print('Button found.')
        btn.scroll_into_view_if_needed()
        
        # Xóa target="_blank" trên thẻ a
        btn.evaluate('node => node.removeAttribute("target")')
        
        try:
            btn.click()
        except Exception as e:
            print('Click error:', e)
        time.sleep(5)
        c2 = page.evaluate("document.querySelectorAll('a[href*=\"-s\"]').length")
        print(f'Items after: {c2}')
        print(f'Pages open: {len(browser.contexts[0].pages)}')
    else:
        print('Button not found')
        
    browser.close()
