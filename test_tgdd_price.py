import time
from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def test_tgdd_price():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.thegioididong.com/laptop/asus-tuf-gaming-f15-fx506hf-i5-hn014w")
        time.sleep(3)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # In ra các thẻ có class liên quan đến giá
        price_tags = soup.find_all(class_=lambda c: c and 'price' in c.lower())
        with open('tgdd_price_debug.txt', 'w', encoding='utf-8') as f:
            for tag in price_tags:
                f.write(f"Class: {tag.get('class')} | Text: {tag.get_text(strip=True)}\n")
        
        browser.close()

if __name__ == "__main__":
    test_tgdd_price()
