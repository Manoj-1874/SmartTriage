import requests

def test_wikipedia(disease_name):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{disease_name.replace(' ', '_')}"
        headers = {
            'User-Agent': 'SmartTriageBot/1.0 (https://smarttriage.phc; admin@smarttriage.phc) requests/2.25.1',
            'Accept': 'application/json'
        }
        print(f"Testing URL: {url}")
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found: {data.get('title')}")
            print(f"Extract snippet: {data.get('extract', '')[:100]}...")
            return True
        else:
            print(f"Failed with status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_wikipedia("Idiopathic pulmonary arterial hypertension")
    test_wikipedia("Stroke")
