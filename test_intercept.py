"""Dung Playwright bat chinh xac API request ma web CellphoneS gui"""
from patchright.sync_api import sync_playwright
import json
import time

captured_requests = []

def handle_request(request):
    if 'graphql' in request.url.lower() or 'api.cellphones' in request.url.lower():
        try:
            post_data = request.post_data
            if post_data and 'products' in post_data.lower():
                captured_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'post_data': post_data[:2000]
                })
        except:
            pass

def handle_response(response):
    if 'graphql' in response.url.lower() or 'api.cellphones' in response.url.lower():
        try:
            body = response.text()
            if 'products' in body.lower() and len(body) > 100:
                # Parse to check structure
                data = json.loads(body)
                if 'data' in data and 'products' in (data.get('data') or {}):
                    prods = data['data']['products']
                    print(f"  [RESPONSE] {response.url[:80]} -> {len(prods)} products")
        except:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    # Bat request
    page.on("request", handle_request)
    page.on("response", handle_response)
    
    print("=== LOADING CELLPHONES LAPTOP PAGE ===")
    page.goto("https://cellphones.com.vn/laptop.html", wait_until="networkidle")
    time.sleep(3)
    
    # Tim so luong san pham tren trang
    try:
        # Tim text "xxx san pham"
        count_text = page.evaluate('''() => {
            // Tim tat ca text node co chua "san pham" hoac "sản phẩm"
            let results = [];
            let walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                let text = walker.currentNode.textContent.trim();
                if (text.match(/\\d+\\s*(sản phẩm|san pham|sp)/i)) {
                    results.push(text);
                }
            }
            // Tim ca trong element co class lien quan
            document.querySelectorAll('[class*="count"], [class*="total"], [class*="result"]').forEach(el => {
                results.push(el.className + ': ' + el.innerText.trim().substring(0, 100));
            });
            return results;
        }''')
        print(f"\nText chua 'san pham': {count_text}")
    except Exception as e:
        print(f"Loi tim text: {e}")
    
    # Tim nut "Xem them" va text cua no
    try:
        xem_them = page.evaluate('''() => {
            let btns = [];
            document.querySelectorAll('button, a, div').forEach(el => {
                let text = el.innerText.trim();
                if (text.match(/xem thêm|xem them|load more/i) && text.length < 100) {
                    btns.push({text: text, class: el.className.substring(0, 50)});
                }
            });
            return btns;
        }''')
        print(f"\nNut 'Xem them': {xem_them}")
    except Exception as e:
        print(f"Loi tim button: {e}")
    
    # In ra cac captured requests
    print(f"\n=== CAPTURED {len(captured_requests)} API REQUESTS ===")
    for i, req in enumerate(captured_requests):
        print(f"\n--- Request {i+1} ---")
        print(f"URL: {req['url']}")
        print(f"Method: {req['method']}")
        if req['post_data']:
            try:
                pd = json.loads(req['post_data'])
                # Pretty print query
                if 'query' in pd:
                    print(f"Query: {pd['query'][:500]}")
                if 'variables' in pd:
                    print(f"Variables: {json.dumps(pd['variables'], indent=2)[:500]}")
            except:
                print(f"Post data: {req['post_data'][:500]}")
    
    # Click "Xem them" neu co de bat them request
    try:
        btn = page.locator('button:has-text("Xem thêm"), a:has-text("Xem thêm")')
        if btn.count() > 0:
            print("\n=== CLICK XEM THEM ===")
            btn.first.click()
            time.sleep(3)
            print(f"Captured {len(captured_requests)} requests after click")
            for i, req in enumerate(captured_requests[-2:]):
                print(f"\n--- New Request ---")
                print(f"URL: {req['url']}")
                if req['post_data']:
                    try:
                        pd = json.loads(req['post_data'])
                        if 'query' in pd:
                            print(f"Query: {pd['query'][:500]}")
                    except:
                        print(f"Post data: {req['post_data'][:500]}")
    except Exception as e:
        print(f"Loi click xem them: {e}")
    
    browser.close()

print("\n=== DONE ===")
