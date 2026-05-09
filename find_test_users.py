import sqlite3

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get some users for testing
users = c.execute("SELECT email, role, fullname FROM users WHERE role IN ('phc_nurse', 'ddhs_admin', 'pharmacist') LIMIT 10").fetchall()
print("Test Users Found:")
for u in users:
    print(f"Email: {u[0]} | Role: {u[1]} | Name: {u[2]}")

conn.close()
