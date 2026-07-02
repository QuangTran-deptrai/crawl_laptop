import re

html = open('fpt_detail.html', encoding='utf-8').read()
m = re.search(r'.{0,100}cpuTechnology.{0,100}', html, re.I)
with open('fpt_cpu_out.txt', 'w', encoding='utf-8') as f:
    f.write(m.group(0) if m else 'Not found')
