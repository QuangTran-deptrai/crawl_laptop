import re

def extract_fpt_specs(html):
    specs = {}
    
    # We clean up backslashes used for JSON escaping inside strings
    clean_html = html.replace('\\"', '"').replace('\\\\', '\\')
    
    # We look for "displayName":"CPU", ..., "value":"Ryzen 7 7435HS"
    matches = re.findall(r'"displayName":"([^"]+)".*?"value":"([^"]+)"', clean_html)
    
    for name, value in matches:
        if name not in specs: # Keep first occurrence
            specs[name] = value
            
    return specs

if __name__ == "__main__":
    html = open('fpt_detail.html', encoding='utf-8').read()
    specs = extract_fpt_specs(html)
    for k, v in specs.items():
        print(f"{k}: {v}")
