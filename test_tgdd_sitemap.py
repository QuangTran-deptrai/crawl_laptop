import httpx
import xml.etree.ElementTree as ET
import time
import re

SITEMAP_INDEX_URL = "https://www.thegioididong.com/newsitemap/sitemap-product"
NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
headers = {"User-Agent": "Mozilla/5.0"}

print("Fetching sitemap index...")
resp = httpx.get(SITEMAP_INDEX_URL, headers=headers, timeout=60, follow_redirects=True)
root = ET.fromstring(resp.content)

sub_sitemaps = []
for sitemap_el in root.findall("ns:sitemap", NS):
    loc = sitemap_el.findtext("ns:loc", default="", namespaces=NS)
    if loc:
        sub_sitemaps.append(loc)

print(f"Total sub-sitemaps: {len(sub_sitemaps)}")

# Lọc chỉ những sub-sitemap có khả năng chứa laptop
# TGDD sitemaps are typically grouped by year/month.
# A laptop could be added 1 or 2 years ago and still active.
laptop_links = set()
count_subs = 0

# Limit to last 24 months (2 years)
sub_sitemaps = sub_sitemaps[-24:]

for sub_url in sub_sitemaps:
    try:
        r = httpx.get(sub_url, headers=headers, timeout=30)
        sub_root = ET.fromstring(r.content)
        for url_el in sub_root.findall("ns:url", NS):
            loc = url_el.findtext("ns:loc", default="", namespaces=NS)
            if loc and "/laptop/" in loc.lower():
                laptop_links.add(loc)
        count_subs += 1
        print(f"Processed {count_subs}/{len(sub_sitemaps)}: {len(laptop_links)} laptop links so far")
    except Exception as e:
        print("Error", sub_url, e)

print(f"Total unique laptop links in last 24 months: {len(laptop_links)}")
