import re
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()
routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", text)
print("All Routes:")
for r in routes:
    print(r)
