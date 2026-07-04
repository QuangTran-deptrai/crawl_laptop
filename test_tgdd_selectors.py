from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.thegioididong.com/laptop')
    time.sleep(3)
    
    links1 = page.query_selector_all('li.item a.main-contain')
    print("Links found with 'li.item a.main-contain':", len(links1))
    
    links2 = page.query_selector_all('ul.listproduct li.item a')
    print("Links found with 'ul.listproduct li.item a':", len(links2))
    
    links3 = page.query_selector_all('li[data-id] > a')
    print("Links found with 'li[data-id] > a':", len(links3))
    
    browser.close()
