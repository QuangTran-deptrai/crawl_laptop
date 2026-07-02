import time
from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def crawl_specs():
    specs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto("https://fptshop.com.vn/may-tinh-xach-tay/lenovo-gaming-loq-15arp10e-ryzen-7-170-83s000dcvn")
        
        time.sleep(3)
        page.evaluate("window.scrollBy(0, 500);")
        time.sleep(2)
        
        try:
            cookie_btn = page.locator('button:has-text("Chấp nhận")').first
            if cookie_btn.is_visible(timeout=1000):
                cookie_btn.click()
                time.sleep(1)
        except:
            pass
            
        try:
            btn = page.locator('button:has-text("Xem tất cả thông số"), a:has-text("Xem tất cả thông số")').first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(2)
        except Exception as e:
            pass
            
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        with open('fpt_specs_modal_dump.txt', 'w', encoding='utf-8') as f:
            elements = soup.find_all(string=lambda text: text and "Dung lượng RAM" in text)
            for e in elements:
                if e.parent.name == 'script': continue
                f.write(f"Found RAM in tag: {e.parent.name}\n")
                # Write the whole parent block to inspect structure
                f.write(e.parent.parent.parent.parent.prettify())
                f.write("\n==========================\n")
            
        browser.close()

if __name__ == "__main__":
    crawl_specs()
