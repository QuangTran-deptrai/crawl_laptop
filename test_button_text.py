import time
from patchright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto('https://phongvu.vn/c/laptop', wait_until='domcontentloaded')
        time.sleep(5)
        
        c0 = page.evaluate('document.querySelectorAll(".css-1y2krk0 .product-card a, .css-1jrdcrk .product-card a, .product-card a").length')
        print(f'Initial count: {c0}')
        
        for i in range(5):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(2)
            
            try:
                btn = page.locator('.button-text:has-text("Xem thêm sản phẩm")').last
                if btn.count() > 0:
                    btn.click(force=True, timeout=2000)
                    print(f'Clicked Xem them {i+1}')
                    time.sleep(4)
            except Exception as e:
                print('Error clicking:', type(e).__name__)
            
            c = page.evaluate('document.querySelectorAll(".css-1y2krk0 .product-card a, .css-1jrdcrk .product-card a, .product-card a").length')
            print(f'Count after click {i+1}: {c}')
            
        browser.close()
test()
