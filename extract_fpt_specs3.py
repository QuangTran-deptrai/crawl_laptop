import re

def extract_fpt_specs(html):
    specs = {}
    
    # We look for "displayName":"CPU","description":"Ryzen 7" or similar
    # The JSON string in Next.js might be escaped as \\" or unescaped "
    
    # Let's clean the html from backslashes to make parsing easier
    clean_html = html.replace('\\"', '"').replace('\\\\', '\\')
    
    # Find all productAttributeHighlight or productAttribute items
    matches = re.findall(r'"displayName":"([^"]+)","description":"([^"]+)"', clean_html)
    
    for name, value in matches:
        if name not in specs: # Keep first occurrence
            specs[name] = value
            
    return specs

if __name__ == "__main__":
    html = open('fpt_detail.html', encoding='utf-8').read()
    specs = extract_fpt_specs(html)
    for k, v in specs.items():
        print(f"{k}: {v}")
