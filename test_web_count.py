"""Kiem tra web CellphoneS hien thi bao nhieu san pham"""
import requests

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

# Khong dung stock filter (giong web)
payload = {
    'query': '''
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
                size: 50,
                sort: [{view: desc}]
            )
            {
                general{ product_id name }
                filterable{ price stock }
            }
        }
    '''
}
r = requests.post(url, json=payload, headers=headers, timeout=15)
data = r.json()
prods = data.get('data', {}).get('products', [])
print(f"No stock filter: page 1 has {len(prods)} products")
for p in prods[:5]:
    name = p.get('general',{}).get('name','')
    stock = p.get('filterable',{}).get('stock', 'N/A')
    print(f"  stock={stock} | {name[:60]}")

# Dem tat ca pages KHONG co stock filter
seen = set()
page = 1
while True:
    payload['query'] = '''
        query GetProductsByCateId{
            products(
                filter: {
                    static: {
                        categories: ["380"],
                        province_id: 30
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
    page += 1

print(f"\nKHONG co stock filter: {len(seen)} san pham ({page-1} pages)")
print(f"CO stock >= 0: da biet la 3536")
print(f"CO stock >= 1: da biet la 392")
print(f"\n=> Neu bo stock filter thi API tra ve {len(seen)} san pham")
print(f"=> Day chinh la so luong tren web (web khong filter stock)")
