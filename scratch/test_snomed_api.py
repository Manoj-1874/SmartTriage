import requests
url = 'https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/MAIN/descriptions'
params = {
    'term': 'Morquio Syndrome',
    'active': 'true',
    'conceptActive': 'true',
    'limit': 5,
    'lang': 'en',
    'searchMode': 'PARTIAL_MATCHING'
}
headers = {'Accept': 'application/json'}
r = requests.get(url, params=params, headers=headers)
print(f'Status: {r.status_code}')
print(f'Count: {len(r.json().get("items", []))}')
if r.json().get("items"):
    print(f'First Hit: {r.json()["items"][0]["term"]}')
