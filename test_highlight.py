import re
import json

html = open('fpt_detail.html', encoding='utf-8').read()

# Need to find the unescaped Next.js JSON array or parse it after replacing \'
m2 = re.search(r'"productAttributeHighlight":(\[.*?\]),"(productInfo|variants|relatedProducts|category|brand)"', html)
if m2:
    s = m2.group(1)
    s = s.replace('\\"', '"').replace('\\\\', '\\')
    
    # Try parsing
    try:
        data = json.loads(s)
        for item in data:
            print(f"{item.get('displayName')}: {item.get('description')}")
    except Exception as e:
        print("Error parsing:", e)
        print(s[:500])
else:
    print("Not found highlight")

