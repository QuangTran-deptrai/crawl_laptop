import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('https://phongvu.vn/c/laptop')
    time.sleep(5)
    
    last_count = 0
    no_change = 0
    for i in range(50):
        # Scroll exactly one screen height
        page.evaluate('window.scrollBy(0, window.innerHeight);')
        time.sleep(2)
        
        current_count = page.evaluate('document.querySelectorAll("a[href*=\'-s\']").length')
        if current_count > last_count:
            print(f'Scroll {i}: {current_count} items')
            last_count = current_count
            no_change = 0
        else:
            no_change += 1
            if no_change > 5:
                print('No more new items after 5 scrolls.')
                
                # Check if there is ANY button to click!
                btn = page.locator('button, div').filter(has_text='Xem thêm').locator('visible=true').first
                if btn.count() > 0:
                    try:
                        print('Found button:', btn.inner_text().split('\\n')[0])
                        btn.click(force=True)
                        time.sleep(3)
                        no_change = 0
                    except:
                        break
                else:
                    break
    
    links = page.evaluate('''() => {
        return Array.from(document.querySelectorAll("a[href*='-s']")).map(a => a.getAttribute('href'))
    }''')
    valid = [l for l in links if l and '-' in l.split('/')[-1] and len(l.split('/')[-1]) > 20]
    print(f'Total DOM links: {len(links)}')
    print(f'Total valid unique laptops: {len(set(valid))}')
    browser.close()
