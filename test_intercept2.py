"""Playwright test to capture all XHRs"""
from patchright.sync_api import sync_playwright
import time
import json

captured = []

def on_response(response):
    if response.request.resource_type in ["xhr", "fetch"]:
        url = response.url
        if "cellphones.com.vn" in url:
            captured.append(url)
            print(f"Captured: {url}")
            try:
                body = response.text()
                if 'totalProduct' in body or 'products' in body:
                    print(f"  --> FOUND DATA IN {url}")
                    with open('captured_response.json', 'w', encoding='utf-8') as f:
                        f.write(body)
            except:
                pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    page.on("response", on_response)
    
    print("Loading page...")
    page.goto("https://cellphones.com.vn/laptop.html", wait_until="networkidle")
    time.sleep(3)
    
    try:
        btn = page.locator('.btn-show-more, .cps-block-content_btn-showmore')
        if btn.count() > 0:
            print("Clicking Xem them...")
            btn.first.click()
            time.sleep(3)
    except Exception as e:
        print("Loi click", e)
    
    browser.close()
