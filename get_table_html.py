import time
from patchright.sync_api import sync_playwright

def get_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://fptshop.com.vn/may-tinh-xach-tay/lenovo-gaming-loq-15arp10e-ryzen-7-170-83s000dcvn", wait_until="domcontentloaded")
        time.sleep(3)
        page.evaluate("window.scrollBy(0, 1000);")
        time.sleep(1)
        page.evaluate("window.scrollBy(0, 1000);")
        time.sleep(2)
        
        # Click button Xem cấu hình chi tiết
        page.evaluate('''() => {
            let btns = document.querySelectorAll('button, a, span');
            for (let btn of btns) {
                let text = btn.innerText.toLowerCase();
                if (text.includes("cấu hình chi tiết") || text.includes("xem tất cả thông số") || text.includes("xem thêm cấu hình")) {
                    btn.click();
                    break;
                }
            }
        }''')
        time.sleep(3)
        
        # Extract tables or divs containing specs
        specs_html = page.evaluate('''() => {
            // Find a table or a div that looks like specs
            let tables = document.querySelectorAll('table');
            if (tables.length > 0) return tables[0].outerHTML;
            
            // Or look for modal containing technical specs
            let modal = document.querySelector('.modal-body, .technical-content, [class*="spec"]');
            return modal ? modal.outerHTML : document.body.innerHTML.substring(0, 5000);
        }''')
        
        with open("fpt_specs_dom.html", "w", encoding="utf-8") as f:
            f.write(specs_html)
            
        browser.close()

if __name__ == "__main__":
    get_html()
