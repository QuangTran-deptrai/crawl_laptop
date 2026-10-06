"""Tim filter chinh xac cho 665 san pham"""
import requests

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

def count_all(query_template, label):
    seen = set()
    page = 1
    while True:
        payload = {'query': query_template % page}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            data = r.json()
            prods = data.get('data', {}).get('products', [])
            if prods is None:
                prods = []
        except:
            break
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
        page += 1
    print(f"  {label}: {len(seen)} san pham")
    return len(seen)

# Lay 1 trang de xem gia tri status
print("=== KIEM TRA GIA TRI STATUS ===")
payload = {'query': '''
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
            general{ product_id name url_path attributes }
            filterable{ stock }
        }
    }
'''}
r = requests.post(url, json=payload, headers=headers, timeout=15)
data = r.json()
prods = data.get('data', {}).get('products', [])

status_values = set()
for p in prods:
    attrs = p.get('general', {}).get('attributes', {}) or {}
    status = attrs.get('status', 'N/A')
    stock = p.get('filterable', {}).get('stock', 0)
    name = p.get('general', {}).get('name', '')[:50]
    status_values.add(str(status))
    print(f"  status={status}, stock={stock}: {name}")

print(f"\nCac gia tri status: {status_values}")

# Lay trang san pham het hang de xem status cua chung
print("\n=== STATUS CUA SAN PHAM HET HANG ===")
payload = {'query': '''
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
            page: 1,
            size: 20,
            sort: [{view: desc}]
        )
        {
            general{ product_id name attributes }
            filterable{ stock }
        }
    }
'''}
r = requests.post(url, json=payload, headers=headers, timeout=15)
data = r.json()
prods = data.get('data', {}).get('products', []) or []

status_counts = {}
for p in prods:
    attrs = p.get('general', {}).get('attributes', {}) or {}
    status = attrs.get('status', 'N/A')
    stock = p.get('filterable', {}).get('stock', 0)
    name = p.get('general', {}).get('name', '')[:50]
    status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    print(f"  status={status}, stock={stock}: {name}")

print(f"\nStatus counts trong het hang: {status_counts}")

# Thu dem voi dynamic filter status
print("\n=== DEM VOI DYNAMIC STATUS FILTER ===")

# status = 1 (enabled/active)
q_status1 = '''
    query GetProductsByCateId{
        products(
            filter: {
                static: {
                    categories: ["380"],
                    province_id: 30,
                    stock: { from: 0 }
                },
                dynamic: {
                    status: ["1"]
                }
            },
            page: %d,
            size: 100,
            sort: [{view: desc}]
        )
        {
            general{ product_id url_path }
        }
    }
'''
count_all(q_status1, "stock>=0, status=1")

# status = 1 va stock >= 1
q_status1_stock1 = '''
    query GetProductsByCateId{
        products(
            filter: {
                static: {
                    categories: ["380"],
                    province_id: 30,
                    stock: { from: 1 }
                },
                dynamic: {
                    status: ["1"]
                }
            },
            page: %d,
            size: 100,
            sort: [{view: desc}]
        )
        {
            general{ product_id url_path }
        }
    }
'''
count_all(q_status1_stock1, "stock>=1, status=1")

# Thu khong co stock filter, co status = 1
q_nostock_status1 = '''
    query GetProductsByCateId{
        products(
            filter: {
                static: {
                    categories: ["380"],
                    province_id: 30
                },
                dynamic: {
                    status: ["1"]
                }
            },
            page: %d,
            size: 100,
            sort: [{view: desc}]
        )
        {
            general{ product_id url_path }
        }
    }
'''
count_all(q_nostock_status1, "no stock, status=1")

# Thu voi cac category filter khac
# category 869 (Laptop chinh khong bao gom PC)
q_cat869 = '''
    query GetProductsByCateId{
        products(
            filter: {
                static: {
                    categories: ["869"],
                    province_id: 30,
                    stock: { from: 0 }
                },
                dynamic: {}
            },
            page: %d,
            size: 100,
            sort: [{view: desc}]
        )
        {
            general{ product_id url_path }
        }
    }
'''
count_all(q_cat869, "category 869, stock>=0")

# Tong ket
print("\n=== TARGET: 665 san pham ===")
