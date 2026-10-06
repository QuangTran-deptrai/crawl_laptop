"""Script kiểm tra số lượng sản phẩm thực tế từ API CellphoneS và Sitemap TGDĐ"""
import requests
import json
import re
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. KIỂM TRA CELLPHONES API
# ============================================================
print("=" * 60)
print("  KIỂM TRA CELLPHONES API")
print("=" * 60)

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

all_products = []
seen_ids = set()
page = 1

while True:
    payload = {
        'query': '''
            query GetProductsByCateId{
                products(
                        filter: {
                            static: {
                                categories: ["380"],
                                province_id: 30,
                                stock: { from: 0 }
                            },
                            dynamic: {}
                        },
                        page: %d,
                        size: 50,
                        sort: [{view: desc}]
                    )
                {
                    general{
                        product_id
                        name
                        url_path
                    }
                    filterable{
                        price
                        special_price
                    }
                }
            }
        ''' % page
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        data = r.json()
        prods = data.get('data', {}).get('products', [])
    except Exception as e:
        print(f"  Lỗi tại page {page}: {e}")
        break
    
    if not prods:
        print(f"  Page {page}: 0 products -> DỪNG")
        break
    
    new_count = 0
    for p in prods:
        pid = p.get('general', {}).get('url_path', '')
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            all_products.append(p)
            new_count += 1
    
    print(f"  Page {page}: {len(prods)} returned, {new_count} new (total unique: {len(all_products)})")
    
    if new_count == 0:
        print(f"  -> Không có sản phẩm mới, DỪNG")
        break
    
    page += 1

print(f"\n>>> CELLPHONES: Tổng cộng {len(all_products)} sản phẩm unique sau {page} trang")
print(f">>> Vấn đề: API trả về {page-1} trang x ~50 sản phẩm")

# Kiểm tra trùng lặp
all_url_paths = []
for p in all_products:
    all_url_paths.append(p.get('general', {}).get('url_path', ''))

print(f">>> Số url_path unique: {len(set(all_url_paths))}")
print(f">>> Số url_path total: {len(all_url_paths)}")

# Kiểm tra xem có sản phẩm nào không phải laptop không
non_laptop = []
for p in all_products:
    name = p.get('general', {}).get('name', '').lower()
    if 'laptop' not in name and 'macbook' not in name:
        non_laptop.append(p.get('general', {}).get('name', ''))

if non_laptop:
    print(f"\n>>> CÓ {len(non_laptop)} sản phẩm KHÔNG PHẢI LAPTOP:")
    for n in non_laptop[:20]:
        print(f"    - {n}")
    if len(non_laptop) > 20:
        print(f"    ... và {len(non_laptop) - 20} sản phẩm khác")

# ============================================================
# 2. KIỂM TRA TGDĐ SITEMAP 
# ============================================================
print("\n" + "=" * 60)
print("  KIỂM TRA TGDĐ SITEMAP")
print("=" * 60)

SITEMAP_INDEX_URL = "https://www.thegioididong.com/newsitemap/sitemap-product"
NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
headers_tgdd = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

now = datetime.now()
cutoff = now - relativedelta(months=3)
cutoff_year = cutoff.year
cutoff_month = cutoff.month

print(f"  >> Cutoff: tháng {cutoff_month}/{cutoff_year}")

try:
    resp = httpx.get(SITEMAP_INDEX_URL, headers=headers_tgdd, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    
    # Đếm tổng sub-sitemap
    all_subs = root.findall("ns:sitemap", NS)
    print(f"  >> Tổng số sub-sitemap: {len(all_subs)}")
    
    # Lọc theo 3 tháng
    filtered_subs = []
    for sitemap_el in all_subs:
        loc = sitemap_el.findtext("ns:loc", default="", namespaces=NS)
        if not loc:
            continue
        match = re.search(r'sitemap-product-(\d{4})-(\d{1,2})', loc)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            if (year > cutoff_year) or (year == cutoff_year and month >= cutoff_month):
                filtered_subs.append(loc)
    
    print(f"  >> Sub-sitemap trong 3 tháng gần nhất: {len(filtered_subs)}")
    
    # Đếm link laptop từ các sub-sitemap
    total_laptop_links = 0
    total_all_links = 0
    laptop_links_set = set()
    
    for idx, sub_url in enumerate(filtered_subs, 1):
        try:
            resp = httpx.get(sub_url, headers=headers_tgdd, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            sub_root = ET.fromstring(resp.content)
            
            all_urls_in_sub = sub_root.findall("ns:url", NS)
            laptop_count = 0
            non_laptop_examples = []
            
            for url_el in all_urls_in_sub:
                loc = url_el.findtext("ns:loc", default="", namespaces=NS)
                total_all_links += 1
                if loc and "/laptop/" in loc.lower():
                    laptop_links_set.add(loc)
                    laptop_count += 1
            
            total_laptop_links += laptop_count
            print(f"  [{idx}/{len(filtered_subs)}] {sub_url}")
            print(f"      Total URLs: {len(all_urls_in_sub)}, Laptop URLs: {laptop_count}")
            
        except Exception as e:
            print(f"  [{idx}/{len(filtered_subs)}] Lỗi: {e}")
    
    print(f"\n>>> TGDĐ: Tổng link laptop (có thể trùng): {total_laptop_links}")
    print(f">>> TGDĐ: Tổng link laptop UNIQUE: {len(laptop_links_set)}")
    print(f">>> TGDĐ: Tổng tất cả link sản phẩm: {total_all_links}")
    
    # Kiểm tra xem có link nào không phải laptop thực sự không
    suspicious = []
    for link in list(laptop_links_set)[:10]:
        print(f"    Ví dụ link: {link}")
        
except Exception as e:
    print(f"  Lỗi khi kiểm tra TGDĐ: {e}")
