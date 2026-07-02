from patchright.sync_api import sync_playwright
import time

def test_price():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://www.thegioididong.com/laptop/lenovo-loq-15iax9e-i5-83lk0079vn')
        time.sleep(3)
        try:
            print("box-price:", page.evaluate('document.querySelector(".box-price").innerText'))
        except Exception as e:
            print(e)
            
        try:
            print("bs_price strong:", page.evaluate('document.querySelector(".bs_price strong").innerText'))
        except:
            pass
            
        try:
            print("text-price:", page.evaluate('document.querySelector(".text-price").innerText'))
        except:
            pass
            
        browser.close()

if __name__ == '__main__':
    test_price()
