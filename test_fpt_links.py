import time
from patchright.sync_api import sync_playwright

SEARCH_URL = "https://fptshop.com.vn/may-tinh-xach-tay"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(SEARCH_URL, wait_until="domcontentloaded")
    time.sleep(3)
    
    print("Clicking Xem them...")
    while True:
        page.evaluate("window.scrollBy(0, 1000);")
        time.sleep(1)
        page.evaluate("window.scrollBy(0, 1000);")
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
        if not clicked:
            break
        time.sleep(2)
        
    # Cuon them xuong cuoi trang
    for _ in range(10):
        page.evaluate("window.scrollBy(0, 1000);")
        time.sleep(0.5)

    print("Extracting links...")
    # Find all anchor tags that look like products. Product links usually have a lot of hyphens and no special paths like /tin-tuc/
    hrefs = page.evaluate('''() => {
        let links = [];
        document.querySelectorAll('a').forEach(a => {
            let href = a.getAttribute('href');
            if(href && href.length > 20 && href.includes('-')) {
                links.push(href);
            }
        });
        return links;
    }''')
    browser.close()
    
    unique_hrefs = set(hrefs)
    
    # Filter links that are actually laptops
    laptop_links = []
    for h in unique_hrefs:
        # Exclude obvious non-products
        if '/tin-tuc/' in h or '/ho-tro/' in h or '/khuyen-mai/' in h or '/thu-cu-doi-moi' in h:
            continue
        # Only keep links that contain at least 3 hyphens (product slugs)
        if h.count('-') >= 3:
            laptop_links.append(h)
            
    with open("fpt_test_links.txt", "w", encoding="utf-8") as f:
        for link in sorted(laptop_links):
            f.write(link + "\n")
    print(f"Total potential product links: {len(laptop_links)}")
