import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    # Cuộn 10 lần để tới cuối
    for _ in range(10):
        page.evaluate('window.scrollBy(0, window.innerHeight);')
        time.sleep(1)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
        time.sleep(3)
    
    # Lấy HTML của toàn bộ footer hoặc phần tử cuối
    footer_html = page.evaluate('document.body.innerHTML')
    with open("pv_html.txt", "w", encoding="utf-8") as f:
        f.write(footer_html)
        
    browser.close()
