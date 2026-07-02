import time
from patchright.sync_api import sync_playwright
from scrapling.parser import Adaptor

COLLECTION_URLS = [
    "https://gearvn.com/collections/laptop-gaming-gia-tu-20-den-25-trieu",
    "https://gearvn.com/collections/laptop-gaming-ban-chay",
    "https://gearvn.com/collections/laptop-gaming-gia-tu-25-den-35-trieu",
    "https://gearvn.com/collections/laptop-gaming-tren-35-trieu",
]
BASE_URL = "https://gearvn.com"

def close_popup(page):
    js_close = '''() => {
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.querySelectorAll('.modal').forEach(m => {
            m.style.display = 'none';
            m.classList.remove('show', 'in');
        });
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    }'''
    try:
        page.evaluate(js_close)
    except:
        pass

# Thu thap link tu tung trang
page_products = {}  # {url: [(name, link), ...]}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for col_url in COLLECTION_URLS:
        short_name = col_url.split("/")[-1]
        print(f"\nDang quet: {short_name}")
        
        page.goto(col_url, wait_until="domcontentloaded")
        time.sleep(3)
        close_popup(page)
        
        # Bam "Xem them" cho den het
        while True:
            try:
                btn = page.locator('#load_more, #load_more_search')
                if btn.count() == 0 or not btn.first.is_visible():
                    break
                btn.first.scroll_into_view_if_needed()
                time.sleep(0.5)
                btn.first.click()
                time.sleep(3)
            except:
                break
        
        time.sleep(1)
        html = page.content()
        parsed = Adaptor(html, url=col_url)
        blocks = parsed.css('.proloop-block')
        
        products = []
        for block in blocks:
            name = block.css('.proloop-name a::text').get(default="").strip()
            if not name or not name.lower().startswith("laptop"):
                continue
            href = block.css('.proloop-name a::attr(href)').get(default="")
            if href:
                full = BASE_URL + href if href.startswith('/') else href
                products.append((name, full))
        
        page_products[short_name] = products
        print(f"  -> {len(products)} laptop")
    
    browser.close()

# Phan tich trung
print("\n" + "="*80)
print("PHAN TICH TRUNG LAP")
print("="*80)

# Tao map: link -> [ten trang chua no]
link_to_pages = {}
link_to_name = {}
for page_name, products in page_products.items():
    for name, link in products:
        if link not in link_to_pages:
            link_to_pages[link] = []
            link_to_name[link] = name
        link_to_pages[link].append(page_name)

# Tim cac link xuat hien > 1 trang
duplicates = {link: pages for link, pages in link_to_pages.items() if len(pages) > 1}

print(f"\nTong so link duy nhat: {len(link_to_pages)}")
print(f"So link bi trung (xuat hien > 1 trang): {len(duplicates)}")

if duplicates:
    print(f"\n{'='*80}")
    print("DANH SACH SAN PHAM TRUNG:")
    print(f"{'='*80}")
    for i, (link, pages) in enumerate(duplicates.items(), 1):
        name = link_to_name[link]
        print(f"\n{i}. {name}")
        print(f"   Link: {link}")
        print(f"   Xuat hien tai: {', '.join(pages)}")

# Thong ke tung trang
print(f"\n{'='*80}")
print("THONG KE TUNG TRANG:")
print(f"{'='*80}")
for page_name, products in page_products.items():
    links = [link for _, link in products]
    unique_to_page = [link for link in links if len(link_to_pages[link]) == 1]
    shared = [link for link in links if len(link_to_pages[link]) > 1]
    print(f"\n{page_name}: {len(products)} san pham ({len(unique_to_page)} rieng, {len(shared)} trung)")
