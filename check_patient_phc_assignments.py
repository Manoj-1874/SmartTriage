import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

patients = conn.execute('SELECT id, email, fullname, location, phc_id FROM users WHERE role="patient" ORDER BY id DESC LIMIT 10;').fetchall()

print("Last 10 Patient Registrations:")
print("=" * 100)
print(f"{'ID':<5} | {'Email':<30} | {'Full Name':<25} | {'Location':<20} | {'PHC ID':<5}")
print("-" * 100)

for p in patients:
    email = p['email'] if p['email'] else 'N/A'
    name = p['fullname'] if p['fullname'] else 'N/A'
    loc = p['location'] if p['location'] else 'N/A'
    phc = p['phc_id'] if p['phc_id'] else 'None'
    print(f"{p['id']:<5} | {email:<30} | {name:<25} | {loc:<20} | {phc:<5}")

conn.close()
