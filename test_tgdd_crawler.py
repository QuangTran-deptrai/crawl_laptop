import time
from patchright.sync_api import sync_playwright

def test_fetch_links():
    links = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("Loading TGDD Laptop Category...")
        page.goto("https://www.thegioididong.com/laptop", wait_until="networkidle")
        time.sleep(3)
        
        # Close popups
        page.evaluate("document.querySelectorAll('.popup-login-mdm, .popup__login__overlay').forEach(e => e.style.display = 'none')")
        
        # Keep clicking load more until it disappears
        clicks = 0
        while True:
            try:
                # Find the view more button. On TGDD it's usually an anchor tag inside a div with class .view-more or similar
                # "Xem thêm 390 Laptop"
                btn = page.locator('a:has-text("Xem thêm"), div:has-text("Xem thêm")')
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.scroll_into_view_if_needed()
                    btn.first.click()
                    clicks += 1
                    print(f"Clicked load more {clicks} times...")
                    time.sleep(3)
                else:
                    print("No more load more button visible.")
                    break
            except Exception as e:
                print("Error clicking:", e)
                break
                
        # Collect all product links
        print("Extracting links...")
        locators = page.locator('ul.listproduct li.item a.main-contain')
        for i in range(locators.count()):
            href = locators.nth(i).get_attribute('href')
            if href and ('/laptop/' in href or '/may-tinh-xach-tay/' in href):
                links.add("https://www.thegioididong.com" + href if not href.startswith('http') else href)
                
        browser.close()
        
    print(f"Total links found: {len(links)}")
    return links

if __name__ == "__main__":
    test_fetch_links()
