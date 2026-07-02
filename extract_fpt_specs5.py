import re
import json

def extract_fpt_specs_from_json(html):
    specs = {}
    clean_html = html.replace('\\"', '"').replace('\\\\', '\\')
    
    # Matching {"id":828,"propertyName":"ram","displayName":"Dung lượng RAM","isCompare":true,"icon":null,"unit":null,"value":"16 GB (1 thanh 16 GB)"}
    matches = re.findall(r'\{[^{]*?"displayName":"([^"]+)"[^{]*?"value":"([^"]+)"[^{]*?\}', clean_html)
    
    for name, value in matches:
        if name not in specs: 
            specs[name] = value
            
    return specs

if __name__ == "__main__":
    html = open('fpt_detail.html', encoding='utf-8').read()
    specs = extract_fpt_specs_from_json(html)
    with open('fpt_specs_parsed.txt', 'w', encoding='utf-8') as f:
        for k, v in specs.items():
            f.write(f"{k}: {v}\n")
