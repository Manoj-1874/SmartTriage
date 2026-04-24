"""
Fix test user passwords - set to password123 for all test accounts
"""

import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('triage.db')

# Test users needing password reset
test_users = [
    'henry@gmail.com',                    # Patient
    'rajesh.cardio@smarttriage.com',      # Doctor
    'fendy.phc_nurse@gmail.com',          # PHC Nurse
    'gopi.ddhsadmin@gmail.com',           # DDHS Admin
]

password = 'password123'
password_hash = generate_password_hash(password)

print("Fixing test user passwords...")
print("=" * 60)

for email in test_users:
    user = conn.execute('SELECT id, role FROM users WHERE email = ?', (email,)).fetchone()

    if user:
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
        conn.commit()
        print(f"✓ {email:<35} | Role: {user[1]:<15} | Password: {password}")
    else:
        print(f"✗ {email:<35} - User not found")

print("=" * 60)
print("\n✅ All test passwords updated to: password123")
