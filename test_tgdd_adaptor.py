from playwright.sync_api import sync_playwright
import time
from scrapling.parser import Adaptor

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.thegioididong.com/laptop')
    time.sleep(3)
    
    html_content = page.content()
    search_page = Adaptor(html_content, url='https://www.thegioididong.com/laptop')
    
    product_blocks = search_page.css('li.item a.main-contain')
    print("Links found with Adaptor:", len(product_blocks))
    
    browser.close()
