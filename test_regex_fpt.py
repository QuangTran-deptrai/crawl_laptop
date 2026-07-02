import re
import json

html = open('fpt_detail.html', encoding='utf-8').read()
# We need to find the productAttribute JSON array. In Next.js stringified JSON, the double quotes might be escaped as \" or unescaped.
# Let's search for something like "productAttribute":[{
m = re.search(r'\\"productAttribute\\":(\[.*?\]),\\"productAttributeHighlight\\"', html)
if m:
    print("Found escaped!")
    data = json.loads(m.group(1).replace('\\"', '"').replace('\\\\', '\\'))
    for item in data[:2]:
        print(item['displayName'])
else:
    m2 = re.search(r'"productAttribute":(\[.*?\]),"productAttributeHighlight"', html)
    if m2:
        print("Found unescaped!")
        try:
            # Clean up the Next.js escaped strings before parsing
            # In __next_f, strings often look like: ["foo", "bar"]
            # But the JSON itself is inside a string literal.
            s = m2.group(1)
            # Remove the wrapping Next.js escapes if any
            s = s.replace('\\"', '"')
            data = json.loads(s)
            print("Successfully parsed!")
            for item in data[:2]:
                print(item.get('displayName'))
        except Exception as e:
            print("Error parsing JSON:", e)
            print(m2.group(1)[:200])
    else:
        print("Not found")

