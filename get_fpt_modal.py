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
        
        # Click "Xem tất cả thông số"
        page.evaluate('''() => {
            let btns = document.querySelectorAll('button, a, span, div');
            for (let btn of btns) {
                if (btn.innerText && btn.innerText.includes("Xem tất cả thông số")) {
                    btn.click();
                    break;
                }
            }
        }''')
        time.sleep(2)
        
        with open("fpt_specs_modal.html", "w", encoding="utf-8") as f:
            # We want to find the modal or popup
            modal = page.evaluate('''() => {
                let m = document.querySelector('.ReactModalPortal, [class*="modal"], [class*="popup"], .relative.z-50');
                return m ? m.outerHTML : document.body.innerHTML;
            }''')
            f.write(modal)
            
        browser.close()

if __name__ == "__main__":
    get_html()
