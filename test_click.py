import time
from patchright.sync_api import sync_playwright

def test_click():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://fptshop.com.vn/may-tinh-xach-tay/lenovo-gaming-loq-15arp10e-ryzen-7-170-83s000dcvn")
        time.sleep(3)
        page.evaluate("window.scrollBy(0, 800);")
        time.sleep(1)
        
        # Take a screenshot before click
        page.screenshot(path="fpt_before_click.png")
        
        # Click "Xem tất cả thông số"
        page.evaluate('''() => {
            let btns = document.querySelectorAll('button, a, span, div');
            for (let btn of btns) {
                if (btn.innerText && (btn.innerText.includes("Xem tất cả thông số") || btn.innerText.includes("Thông số kỹ thuật"))) {
                    btn.click();
                    break;
                }
            }
        }''')
        
        time.sleep(3)
        
        # Take a screenshot after click
        page.screenshot(path="fpt_after_click.png")
        
        browser.close()

if __name__ == "__main__":
    test_click()
