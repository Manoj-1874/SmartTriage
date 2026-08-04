import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('triage.db')
cursor = conn.cursor()

email = 'branch3_pharmacist@phc.in'
password = generate_password_hash('password123')
phc_id = 163 # Govt PHC Karur - Branch 3

cursor.execute("DELETE FROM users WHERE email=?", (email,))
cursor.execute('''
    INSERT INTO users (email, password_hash, fullname, role, phc_id, is_approved)
    VALUES (?, ?, ?, ?, ?, ?)
''', (email, password, 'Kavya (Branch 3)', 'pharmacist', phc_id, 1))

conn.commit()
print("Added target pharmacist account: branch3_pharmacist@phc.in / password123")
conn.close()
