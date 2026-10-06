"""Playwright test to capture XHR post data"""
from patchright.sync_api import sync_playwright
import time
import json

captured = []

def on_request(request):
    if request.resource_type in ["xhr", "fetch"]:
        url = request.url
        if "v2/graphql/query" in url:
            pd = request.post_data
            if pd:
                captured.append(pd)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    page.on("request", on_request)
    
    page.goto("https://cellphones.com.vn/laptop.html", wait_until="networkidle")
    time.sleep(2)
    
    try:
        btn = page.locator('.btn-show-more, .cps-block-content_btn-showmore')
        if btn.count() > 0:
            btn.first.click()
            time.sleep(2)
    except:
        pass
    
    browser.close()

if captured:
    with open('captured_post_data.json', 'w', encoding='utf-8') as f:
        f.write(captured[0])
    print(f"Saved payload, length: {len(captured[0])}")
else:
    print("No payload captured")
