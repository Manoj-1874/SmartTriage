import requests
url = 'https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/MAIN/descriptions'
params = {'term': 'Morquio Syndrome'}
r = requests.get(url, params=params)
print(f'Status: {r.status_code}')
print(f'Content: {r.text[:200]}')
