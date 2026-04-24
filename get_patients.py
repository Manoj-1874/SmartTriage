import sqlite3

conn = sqlite3.connect('triage.db')
cursor = conn.cursor()
cursor.execute('SELECT email, password_hash, role FROM users WHERE role="patient" LIMIT 5')
for row in cursor.fetchall():
    print(f'Email: {row[0]}, Role: {row[2]}')
conn.close()
