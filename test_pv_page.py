import time
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    all_links = set()
    for i in range(1, 6):
        page.goto(f'https://phongvu.vn/c/laptop?page={i}')
        time.sleep(3)
        page.evaluate('window.scrollBy(0, 1000);')
        time.sleep(2)
        
        links = page.evaluate('''() => {
            return Array.from(document.querySelectorAll("a[href*='-s']")).map(a => a.getAttribute('href'))
        }''')
        
        valid_links = [l for l in links if l and '-' in l.split('/')[-1] and len(l.split('/')[-1]) > 20]
        
        all_links.update(valid_links)
        print(f'Page {i}: found {len(valid_links)} valid links. Total unique now: {len(all_links)}')
        
    browser.close()
