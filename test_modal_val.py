from bs4 import BeautifulSoup
import re
soup = BeautifulSoup(open('fpt_specs_modal.html', encoding='utf-8').read(), 'html.parser')
res = [e.parent.parent.parent.prettify() for e in soup.find_all(string=re.compile('16 GB'))]
with open('fpt_modal_val_out.txt', 'w', encoding='utf-8') as f:
    f.write("\n=======================\n".join(res[:3]))
