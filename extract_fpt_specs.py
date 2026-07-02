from bs4 import BeautifulSoup
import re

html = open('fpt_detail.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

with open('fpt_specs_out.txt', 'w', encoding='utf-8') as f:
    els = soup.find_all(string=re.compile('Thông số kỹ thuật|Cấu hình', re.I))
    for e in els:
        f.write(f"--- Parent of {e.strip()} ---\n")
        f.write(str(e.parent) + "\n")
        
    f.write("\n\n--- Tìm ID hoặc class chứa technical/spec ---\n")
    for el in soup.find_all(class_=re.compile('spec|tech|table', re.I)):
        f.write(f"Class: {el.get('class')}\n")
