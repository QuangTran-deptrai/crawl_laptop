from scrapling.fetchers import StealthyFetcher

SEARCH_URL = "https://gearvn.com/search?q=laptop%20gaming%20rtx%203050"

print("=== Mở trình duyệt để kiểm tra ===")
fetcher = StealthyFetcher()
page = fetcher.fetch(SEARCH_URL, headless=False, wait_selector='.proloop-name', timeout=30000)

# Kiểm tra số block
blocks = page.css('.proloop-block')
print(f"Tổng .proloop-block: {len(blocks)}")

# Kiểm tra block nào có tên sản phẩm thật (không phải skeleton)
real_blocks = []
for b in blocks:
    name = b.css('.proloop-name a::text').get(default="").strip()
    sku = b.attrib.get('data-product-sku', '').strip()
    if name:
        real_blocks.append((name, sku))

print(f"Block có tên sản phẩm thật: {len(real_blocks)}")
for i, (name, sku) in enumerate(real_blocks[:10]):
    print(f"  [{i+1}] {name} | SKU: {sku}")

# Kiểm tra có block nào chứa 3050
matched = [(n, s) for n, s in real_blocks if "3050" in n.upper() or "3050" in s.upper()]
print(f"\nBlock chứa '3050': {len(matched)}")
for i, (name, sku) in enumerate(matched[:10]):
    print(f"  [{i+1}] {name} | SKU: {sku}")
