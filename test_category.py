"""Kiem tra category 380 cua CellphoneS va thu cac filter khac"""
import requests

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

# Test 1: Lay trang 1 voi stock >= 1 (con hang)
print("=== TEST 1: stock from 1 (con hang) ===")
payload = {
    'query': '''
        query GetProductsByCateId{
            products(
                filter: {
                    static: {
                        categories: ["380"],
                        province_id: 30,
                        stock: { from: 1 }
                    },
                    dynamic: {}
                },
                page: 1,
                size: 50,
                sort: [{view: desc}]
            )
            {
                general{ product_id name url_path }
                filterable{ price special_price stock }
            }
        }
    '''
}
r = requests.post(url, json=payload, headers=headers, timeout=15)
data = r.json()
prods = data.get('data', {}).get('products', [])
print(f"  Page 1 (stock>=1): {len(prods)} products")

# Dem tat ca trang voi stock >= 1
total_stock1 = 0
seen = set()
page = 1
while True:
    payload['query'] = '''
        query GetProductsByCateId{
            products(
                filter: {
                    static: {
                        categories: ["380"],
                        province_id: 30,
                        stock: { from: 1 }
                    },
                    dynamic: {}
                },
                page: %d,
                size: 50,
                sort: [{view: desc}]
            )
            {
                general{ product_id name url_path }
            }
        }
    ''' % page
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    if not prods:
        break
    new = 0
    for p in prods:
        uid = p.get('general', {}).get('url_path', '')
        if uid and uid not in seen:
            seen.add(uid)
            new += 1
    if new == 0:
        break
    print(f"  Page {page}: {len(prods)} returned, {new} new (total: {len(seen)})")
    page += 1

print(f"\n>>> stock >= 1 (CON HANG): {len(seen)} san pham")

# Test 2: Dem stock = 0 (het hang)
seen0 = set()
page = 1
while True:
    payload['query'] = '''
        query GetProductsByCateId{
            products(
                filter: {
                    static: {
                        categories: ["380"],
                        province_id: 30,
                        stock: { from: 0, to: 0 }
                    },
                    dynamic: {}
                },
                page: %d,
                size: 50,
                sort: [{view: desc}]
            )
            {
                general{ product_id name url_path }
            }
        }
    ''' % page
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    if not prods:
        break
    new = 0
    for p in prods:
        uid = p.get('general', {}).get('url_path', '')
        if uid and uid not in seen0:
            seen0.add(uid)
            new += 1
    if new == 0:
        break
    page += 1

print(f">>> stock = 0 (HET HANG): {len(seen0)} san pham")
print(f">>> TONG: {len(seen) + len(seen0)} (con hang + het hang)")

# Test 3: Kiem tra nhanh cac ten san pham khong phai laptop
print("\n=== PHAN TICH SAN PHAM KHONG PHAI LAPTOP ===")
non_laptop_keywords = ['mac mini', 'imac', 'mac studio', 'studio display', 'surface pro', 'may tinh de ban']
all_seen = set()
page = 1
non_laptop_list = []
laptop_list = []

while True:
    payload['query'] = '''
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
                general{ product_id name url_path }
            }
        }
    ''' % page
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    if not prods:
        break
    new = 0
    for p in prods:
        uid = p.get('general', {}).get('url_path', '')
        name = p.get('general', {}).get('name', '')
        if uid and uid not in all_seen:
            all_seen.add(uid)
            new += 1
            name_lower = name.lower()
            if 'laptop' not in name_lower and 'macbook' not in name_lower:
                non_laptop_list.append(name)
            else:
                laptop_list.append(name)
    if new == 0:
        break
    page += 1

print(f"  Co ten 'laptop' hoac 'macbook': {len(laptop_list)}")
print(f"  KHONG co ten 'laptop'/'macbook': {len(non_laptop_list)}")
print(f"  => Ty le khong phai laptop: {len(non_laptop_list)}/{len(all_seen)} = {len(non_laptop_list)/len(all_seen)*100:.1f}%")

# Phan loai non-laptop
categories = {}
for name in non_laptop_list:
    nl = name.lower()
    if 'mac mini' in nl:
        cat = 'Mac mini'
    elif 'imac' in nl:
        cat = 'iMac'
    elif 'mac studio' in nl:
        cat = 'Mac Studio'
    elif 'studio display' in nl or 'pro display' in nl:
        cat = 'Display/Man hinh'
    elif 'surface pro' in nl or 'surface go' in nl:
        cat = 'Surface Pro/Go (tablet)'
    elif 'mac pro' in nl:
        cat = 'Mac Pro'
    else:
        cat = 'Khac'
    categories[cat] = categories.get(cat, 0) + 1

print("\n  Phan loai san pham KHONG phai laptop:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"    {cat}: {count}")
