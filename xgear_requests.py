import requests
import json
import math
import time
import argparse
from datetime import datetime, timezone, timedelta
import pandas as pd

def calculate_discount(current_price, original_price, scraped_discount=""):
    try:
        import re
        if 'liên hệ' in str(current_price).lower() or 'liên hệ' in str(original_price).lower():
            return ""
        c = int(re.sub(r'[^\d]', '', str(current_price)))
        o = int(re.sub(r'[^\d]', '', str(original_price)))
        if o > c and o > 0 and c > 0:
            percent = round((o - c) / o * 100)
            if percent <= 70:
                return f"-{percent}%"
    except Exception:
        pass
        
    if scraped_discount and str(scraped_discount).strip():
        d = str(scraped_discount).strip()
        if d.endswith('%') and not d.startswith('-'):
            d = f"-{d}"
        return d
        
    return ""

def fetch_page(page):
    """Fetch 1 trang tu API cua XGear"""
    url = f'https://xgear.net/collections/laptop/products.json?limit=50&page={page}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('products', [])
    except Exception as e:
        print(f"    [X] Loi tai trang {page}: {e}")
    return []

def get_all_laptop_products():
    """Lay toan bo danh muc Laptop tu XGear"""
    print("[*] Dang kiem tra san pham Laptop tren XGear...")
    
    all_products = []
    seen_ids = set()
    page = 1
    
    while True:
        print(f"    - Dang tai trang {page}...")
        prods = fetch_page(page)
        
        if not prods or len(prods) == 0:
            break
            
        new_count = 0
        for p in prods:
            pid = p.get('id')
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_products.append(p)
                new_count += 1
                
        if new_count == 0:
            break
            
        page += 1
        
    print(f"[*] Tim thay tong cong {len(all_products)} san pham ({page-1} trang).")
    return all_products

def extract_config_from_tags(tags):
    """Parse config tu tags cua XGear (Shopify API)"""
    cpu = ram = storage = vga = screen = ""
    if isinstance(tags, str):
        tag_list = [t.strip() for t in tags.split(',')]
    elif isinstance(tags, list):
        tag_list = tags
    else:
        return cpu, ram, storage, vga, screen

    for tag in tag_list:
        tag_str = str(tag).strip()
        tag_lower = tag_str.lower()
        if tag_lower.startswith('chip_'):
            cpu = tag_str.split('_', 1)[1]
        elif tag_lower.startswith('cpu_') and not cpu:
            cpu = tag_str.split('_', 1)[1]
        elif tag_lower.startswith('ram_'):
            ram = tag_str.split('_', 1)[1]
        elif tag_lower.startswith('ssd_'):
            storage = tag_str.split('_', 1)[1]
        elif tag_lower.startswith('vga_'):
            vga = tag_str.split('_', 1)[1]
        elif tag_lower.startswith('screen_'):
            screen = tag_str.split('_', 1)[1]
    return cpu, ram, storage, vga, screen

def parse_item(item):
    name = item.get("title", "N/A")
    variants = item.get("variants", [])
    if variants and len(variants) > 0:
        price = variants[0].get("price", 0)
        price_before = variants[0].get("compare_at_price", 0)
    else:
        price, price_before = 0, 0
        
    try:
        price = float(price) if price else 0
        price_before = float(price_before) if price_before else 0
    except:
        price, price_before = 0, 0

    handle = item.get("handle", "")
    link = f"https://xgear.net/products/{handle}" if handle else "N/A"
    
    updated_at = item.get("updated_at", "N/A")
    brand = item.get("vendor", "")
    
    discount = "0%"
    if price_before > price and price_before > 0:
        discount = f"{round((1 - price/price_before) * 100)}%"

    cpu, ram, storage, vga, screen = extract_config_from_tags(item.get('tags', ''))

    specs_dict = {
        "Thương hiệu": brand,
        "CPU": cpu,
        "RAM": ram,
        "Ổ cứng": storage,
        "VGA": vga,
        "Màn hình": screen
    }
    specs_string = " | ".join([f"{k}: {v}" for k, v in specs_dict.items() if v])

    crawl_time = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    try:
        current_price_str = f"{int(price):,}đ".replace(",", ".") if price > 0 else ""
        original_price_str = f"{int(price_before):,}đ".replace(",", ".") if price_before > 0 else ""
    except:
        current_price_str = ""
        original_price_str = ""

    return {
        "Tên Sản Phẩm": name,
        "Giá Hiện Tại": current_price_str,
        "Giá Gốc": original_price_str,
        "Giảm Giá": calculate_discount(current_price_str, original_price_str, discount),
        "Khuyến Mãi": "",
        "Quà Tặng / Ghi Chú": "",
        "Cấu Hình Chi Tiết": specs_string,
        "Link Sản Phẩm": link,
        "Ngày Cập Nhật (Sitemap)": updated_at,
        "Ngày Giờ Crawl": crawl_time
    }

def crawl_xgear_to_excel(chunk=1, total_chunks=1, get_links_only=False):
    timestamp = int(time.time())
    EXCEL_FILE = f"laptop_xgear_chunk_{chunk}_{timestamp}.xlsx"
    
    all_products = get_all_laptop_products()
    
    if get_links_only:
        LINKS_FILE = "xgear_links.txt"
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            for p in all_products:
                handle = p.get("handle", "")
                if handle:
                    f.write(f"https://xgear.net/products/{handle}\n")
        print(f"--> Đã lưu links ra file {LINKS_FILE}")
        return

    # Sort to ensure consistent order
    all_products = sorted(all_products, key=lambda x: x.get('handle', ''))
    
    chunk_size = math.ceil(len(all_products) / total_chunks)
    start_idx = (chunk - 1) * chunk_size
    end_idx = start_idx + chunk_size
    chunk_products = all_products[start_idx:end_idx]
    
    print(f"--> [SHARDING] Mảnh {chunk}/{total_chunks}: Cào {len(chunk_products)} sản phẩm (từ {start_idx} đến {end_idx-1})")

    parsed_products = [parse_item(p) for p in chunk_products]
    
    if parsed_products:
        df = pd.DataFrame(parsed_products)
        df.to_excel(EXCEL_FILE, index=False)
        print(f"\n[SAVED] {EXCEL_FILE}")
    else:
        print("\nKhong co du lieu nao de luu.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunk', type=int, default=1)
    parser.add_argument('--total-chunks', type=int, default=1)
    parser.add_argument('--get-links-only', action='store_true')
    args = parser.parse_args()
    
    print("="*60)
    print("  XGEAR - CRAWL ALL LAPTOP")
    print("="*60)
    
    crawl_xgear_to_excel(chunk=args.chunk, total_chunks=args.total_chunks, get_links_only=args.get_links_only)
