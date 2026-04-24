import requests
branches = ['SNOMEDCT-US', 'MAIN', 'SNOMEDCT-US/MAIN', 'SNOMEDCT-US/2026-03-01']
for b in branches:
    url = f'https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/{b}/descriptions'
    r = requests.get(url, params={'term': 'Morquio Syndrome'})
    print(f'Branch {b}: {r.status_code}')
