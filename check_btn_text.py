from bs4 import BeautifulSoup
import re

html = open('fpt_detail.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

with open('fpt_btn_text.txt', 'w', encoding='utf-8') as f:
    for e in soup.find_all(['button', 'a', 'span']):
        text = e.text.strip()
        if re.search('cấu hình|thông số|kỹ thuật|chi tiết', text, re.I):
            f.write(f"<{e.name}>: {text}\n")
