import time
from patchright.sync_api import sync_playwright

def get_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://fptshop.com.vn/may-tinh-xach-tay/lenovo-gaming-loq-15arp10e-ryzen-7-170-83s000dcvn")
        time.sleep(3)
        page.evaluate("window.scrollBy(0, 1000);")
        time.sleep(1)
        with open("fpt_detail.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        browser.close()

if __name__ == "__main__":
    get_html()
