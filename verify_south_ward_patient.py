import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

result = conn.execute('SELECT id, email, fullname, location, phc_id, role FROM users WHERE email=?', ('southpatient@test.com',)).fetchone()

if result:
    print("✅ Patient Created Successfully!")
    print(f"ID: {result['id']}")
    print(f"Email: {result['email']}")
    print(f"Full Name: {result['fullname']}")
    print(f"Location: {result['location']}")
    print(f"PHC ID: {result['phc_id']} (Expected: 3 for 'South Ward')")
    print(f"Role: {result['role']}")

    if result['phc_id'] == 3:
        print("\n✅ SUCCESS: Location-based PHC assignment works correctly!")
    else:
        print(f"\n❌ ERROR: Expected PHC 3, got PHC {result['phc_id']}")
else:
    print("❌ Patient not found in database")

conn.close()
