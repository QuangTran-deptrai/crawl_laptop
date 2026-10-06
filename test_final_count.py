"""Kiem tra chinh xac so luong san pham web CellphoneS hien thi
Web CellphoneS su dung cung API nhung co them tham so 'is_display_out_of_stock'
"""
import requests
import json

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

# Test voi cac bien the filter khac nhau ma web co the dung
tests = [
    ("stock >= 1 (con hang)", '''
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
                size: 20,
                sort: [{view: desc}]
            )
            {
                general{ product_id name }
                filterable{ stock }
            }
        }
    '''),
    ("stock >= 0 (bao gom het hang)", '''
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
                page: 1,
                size: 20,
                sort: [{view: desc}]
            )
            {
                general{ product_id name }
                filterable{ stock }
            }
        }
    '''),
    ("khong co stock filter", '''
        query GetProductsByCateId{
            products(
                filter: {
                    static: {
                        categories: ["380"],
                        province_id: 30
                    },
                    dynamic: {}
                },
                page: 1,
                size: 20,
                sort: [{view: desc}]
            )
            {
                general{ product_id name }
                filterable{ stock }
            }
        }
    '''),
]

for name, query in tests:
    payload = {'query': query}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    stocks = [p.get('filterable', {}).get('stock', 'N/A') for p in prods]
    print(f"\n=== {name} ===")
    print(f"  Products returned: {len(prods)}")
    print(f"  Stock values: {stocks}")
    for p in prods[:5]:
        n = p.get('general', {}).get('name', '')[:70]
        s = p.get('filterable', {}).get('stock', 'N/A')
        print(f"    [{s}] {n}")

# Dem nhanh tong so cho stock >= 1
print("\n\n=== DEM TONG SO TRANG CHO STOCK >= 1 ===")
page = 1
total = 0
while True:
    payload = {'query': '''
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
                size: 100,
                sort: [{view: desc}]
            )
            {
                general{ product_id name }
            }
        }
    ''' % page}
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    if not prods:
        break
    total += len(prods)
    print(f"  Page {page}: {len(prods)} products (running total: {total})")
    page += 1

print(f"\n>>> TONG SO SAN PHAM CON HANG (stock >= 1): {total}")
print(f">>> Day la so ma web hien thi (vi web chi hien thi san pham con ban)")
