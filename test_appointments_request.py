import requests
import json

# Make a request to the appointments page using a session with cookies
session = requests.Session()

# Get a session from the running server
response = session.get('http://localhost:5000/appointments')

print(f"Status: {response.status_code}")

# Look for the JavaScript appointments data in the HTML
if 'const appointments' in response.text:
    # Find the line with appointments data
    import re
    match = re.search(r'const appointments = (.+?);', response.text)
    if match:
        json_str = match.group(1).replace("&#x27;", "'").strip()
        print(f"\nFound appointments JavaScript:")
        print(json_str[:500])  # Print first 500 chars
else:
    print("No 'const appointments' found in HTML")

# Check if we're logged in
if 'sign out' in response.text.lower() or 'logout' in response.text.lower():
    print("\n✓ Logged in successfully")
else:
    print("\n✗ Not logged in - got redirected to login")
    print(f"Response URL: {response.url}")
