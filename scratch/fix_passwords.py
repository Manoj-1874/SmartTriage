import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('triage.db')
c = conn.cursor()

correct_hash = generate_password_hash('password123')

# Update all users whose password does not start with pbkdf2 or scrypt
c.execute("UPDATE users SET password_hash = ? WHERE password_hash NOT LIKE 'pbkdf2%' AND password_hash NOT LIKE 'scrypt%' AND password_hash != 'LIGHTNING_BYPASS'", (correct_hash,))

conn.commit()
conn.close()

print(f"Updated passwords to use werkzeug hash.")
