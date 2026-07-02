import time
from patchright.sync_api import sync_playwright

url = 'https://fptshop.com.vn/may-tinh-xach-tay'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    time.sleep(3)
    
    count = 0
    while True:
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(1)
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(1)
        
        clicked = page.evaluate('''() => {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                let text = btn.innerText.toLowerCase();
                if (text.includes("xem thêm") && (text.includes("kết quả") || text.includes("sản phẩm"))) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if clicked:
            count += 1
            time.sleep(2)
        else:
            break
            
    for _ in range(5):
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(1)

    cards = page.evaluate('''() => {
        return document.querySelectorAll('div.grid-cols-2 > div').length;
    }''')
    
    links = page.evaluate('''() => {
        let ls = [];
        document.querySelectorAll('a[href^="/may-tinh-xach-tay/"], a[href^="/laptop"]').forEach(a => {
            ls.push(a.getAttribute('href').split('?')[0]); // ignore query params
        });
        return ls;
    }''')
    
    unique_links = list(set(links))
    
    print('Total grid items rendered:', cards)
    print('Total raw links found:', len(links))
    print('Total UNIQUE links found (ignoring query parameters):', len(unique_links))
    browser.close()
