import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all view-section divs
view_divs = re.findall(r'<div\s+id="view-([^"]+)"', content)
print("Found view IDs:")
print(view_divs)
