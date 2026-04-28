import requests

def test_snomed(disease_name):
    SNOMED_APIS = ["https://browser.ihtsdotools.org/snowstorm/snomed-ct", "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"]
    LATEST_BRANCHES = ["MAIN", "SNOMEDCT-US"]
    params = {'term': disease_name, 'activeFilter': 'true', 'limit': 1}
    headers = {'User-Agent': 'SmartTriage/2.5', 'Accept': 'application/json'}
    
    for server in SNOMED_APIS:
        for branch in LATEST_BRANCHES:
            try:
                url = f"{server.rstrip('/')}/browser/{branch}/descriptions"
                print(f"Testing SNOMED URL: {url}")
                resp = requests.get(url, params=params, headers=headers, timeout=5)
                print(f"Status Code: {resp.status_code}")
                if resp.status_code == 200:
                    items = resp.json().get('items', [])
                    if items:
                        print(f"Match found: {items[0].get('term')}")
                        return True
                    else:
                        print("No items found in branch " + branch)
                else:
                    print(f"Failed on {server} / {branch}")
            except Exception as e:
                print(f"Error on {server} / {branch}: {e}")
    return False

if __name__ == "__main__":
    test_snomed("Idiopathic pulmonary arterial hypertension")
