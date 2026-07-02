import time
from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def test_tgdd_price_active():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.thegioididong.com/laptop#c=44&p=37699,311863,311890&o=13&pi=1", wait_until="domcontentloaded")
        time.sleep(3)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        first_product = soup.select_one('li.item a.main-contain')
        if not first_product:
            print("No product found")
            return
            
        url = "https://www.thegioididong.com" + first_product.get('href')
        print("Visiting", url)
        
        page.goto(url)
        time.sleep(3)
        
        html_detail = page.content()
        soup_detail = BeautifulSoup(html_detail, 'html.parser')
        
        price_tags = soup_detail.find_all(class_=lambda c: c and 'price' in c.lower())
        
        with open('tgdd_price_debug2.txt', 'w', encoding='utf-8') as f:
            for tag in price_tags:
                f.write(f"Class: {tag.get('class')} | Text: {tag.get_text(strip=True)}\n")
                
        browser.close()

if __name__ == "__main__":
    test_tgdd_price_active()
