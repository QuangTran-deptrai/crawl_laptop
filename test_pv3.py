import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    texts = page.evaluate('''
        Array.from(document.querySelectorAll('div, a'))
            .filter(el => el.innerText && el.innerText.includes('Xem thêm sản phẩm'))
            .map(el => el.outerHTML)
    ''')
    for i, t in enumerate(texts):
        print(f"--- Element {i} ---")
        print(t[:200] + "...")
        
    browser.close()
