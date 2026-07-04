import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    no_change_count = 0
    last_count = 0
    for _ in range(30):
        page.evaluate('window.scrollBy(0, window.innerHeight);')
        time.sleep(1)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
        time.sleep(3)
        c = page.evaluate('document.querySelectorAll("a[href*=\\\"-s\\\"]").length')
        print(f"Items: {c}")
        if c == last_count:
            no_change_count += 1
            if no_change_count >= 3:
                break
        else:
            no_change_count = 0
        last_count = c
        
    browser.close()
