import requests
urls = [
    'https://browser.ihtsdotools.org/snowstorm/snomed-ct/descriptions',
    'https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/descriptions',
    'https://browser.ihtsdotools.org/snowstorm/snomed-ct/v3/descriptions',
    'https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct/descriptions',
    'https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct/MAIN/descriptions'
]
for u in urls:
    try:
        r = requests.get(u, params={'term': 'Morquio Syndrome'}, timeout=3)
        print(f'{u} -> {r.status_code}')
    except:
        print(f'{u} -> TIMEOUT/ERROR')
