"""
Reset passwords for test users to known values for verification testing
"""

import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('triage.db')

# Define test credentials
test_credentials = {
    'henry@gmail.com': 'password123',
    'rajesh.cardio@smarttriage.com': 'password123',
    'fendy.phc_nurse@gmail.com': 'password123',
    'gopi.ddhsadmin@gmail.com': 'password123',
}

print("Resetting passwords for test users:")
print("=" * 60)

for email, password in test_credentials.items():
    # Get user first
    user = conn.execute(
        'SELECT id, role FROM users WHERE email = ?',
        (email,)
    ).fetchone()

    if user:
        hashed_pwd = generate_password_hash(password)
        conn.execute(
            'UPDATE users SET password = ? WHERE email = ?',
            (hashed_pwd, email)
        )
        conn.commit()
        print(f"✓ {email} ({user[1]}) -> password: {password}")
    else:
        print(f"✗ {email} - User not found")

print("=" * 60)
print("\nTest Credentials for Role-Based Verification:")
print("=" * 60)
for email, password in test_credentials.items():
    print(f"{email} : {password}")

conn.close()
