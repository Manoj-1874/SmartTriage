from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('triage.db')
cur = conn.cursor()

# Generate hash for password "test123"
hashed_pwd = generate_password_hash('test123')

# Update Henry's password
cur.execute('UPDATE users SET password_hash = ? WHERE email = "henry@gmail.com"', (hashed_pwd,))
conn.commit()

# Verify
user = cur.execute('SELECT id, email, password_hash FROM users WHERE email = "henry@gmail.com"').fetchone()
print(f"Updated user: {user[1]}")
print(f"New password hash starts with: {user[2][:20]}...")

conn.close()
print("✓ Henry's password reset to 'test123'")
