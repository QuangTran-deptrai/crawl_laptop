import requests

url = 'https://api.cellphones.com.vn/v2/graphql/query'
headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

query = """
    query GetProductsByCateId{
        products(
            filter: {
                static: {
                    categories: ["380"],
                    province_id: 30,
                    stock: { from: 0 },
                    company_stock_id: [46, 56, 152, 4920]
                },
                dynamic: {}
            },
            page: %d,
            size: 100,
            sort: [{view: desc}]
        )
        { general{ url_path } }
    }
"""

seen = set()
page = 1
while True:
    r = requests.post(url, json={'query': query % page}, headers=headers, timeout=15)
    data = r.json()
    prods = data.get('data', {}).get('products', [])
    if not prods: break
    for p in prods:
        seen.add(p.get('general', {}).get('url_path'))
    page += 1

print(f'TOTAL: {len(seen)}')
