import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    # Close popup if exists
    try:
        page.keyboard.press('Escape')
        time.sleep(1)
        page.evaluate('''() => {
            document.querySelectorAll('.popup, .banner, .cookie-banner').forEach(el => {
                el.style.display = 'none';
            });
            document.body.style.overflow = 'auto';
        }''')
    except:
        pass
        
    for _ in range(5):
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(2)
        
    # Get all elements with text containing 'Xem thêm'
    btns = page.locator('button, div').filter(has_text='Xem thêm').all()
    for i, btn in enumerate(btns):
        try:
            print(f'Xem thêm {i}: class="{btn.get_attribute("class")}" text="{btn.inner_text().replace(chr(10), " ")}"')
        except:
            pass
            
    # Also check pagination like 'Tiếp' or 'Trang'
    paginations = page.locator('a, button, div').filter(has_text='Tiếp').all()
    for i, p in enumerate(paginations):
        try:
            print(f'Tiếp {i}: class="{p.get_attribute("class")}" text="{p.inner_text().replace(chr(10), " ")}"')
        except:
            pass
            
    # Check what stops it at 180
    print('Total links:', page.evaluate('document.querySelectorAll("a[href*=\'-s\']").length'))
    browser.close()
