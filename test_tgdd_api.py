import requests
from patchright.sync_api import sync_playwright
import time
import json

captured = []

def on_request(request):
    if request.resource_type in ["xhr", "fetch"]:
        url = request.url
        if "thegioididong.com" in url:
            captured.append(url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    page.on("request", on_request)
    
    print("Loading TGDD...")
    page.goto("https://www.thegioididong.com/laptop", wait_until="domcontentloaded")
    time.sleep(3)
    
    try:
        # cuộn xuống để hiện nút xem thêm
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        btn = page.locator('.view-more, .btn-viewmore, .view-more a, .view-ele a')
        if btn.count() > 0:
            print("Clicking Xem them TGDD...")
            btn.first.click()
            time.sleep(3)
        else:
            print("Khong tim thay nut xem them")
    except Exception as e:
        print("Loi click", e)
    
    browser.close()

print("Captured TGDD URLs:")
for u in captured:
    print(u)
