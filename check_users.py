import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get all users
print("=== ALL USERS ===")
users = c.execute('SELECT id, email, role FROM users').fetchall()
for user in users:
    print(f"ID: {user['id']}, Email: {user['email']}, Role: {user['role']}")

# Get DDHS admins specifically
print("\n=== DDHS ADMINS ===")
admins = c.execute('SELECT id, email, role FROM users WHERE role = "ddhs_admin"').fetchall()
for admin in admins:
    print(f"ID: {admin['id']}, Email: {admin['email']}, Role: {admin['role']}")

conn.close()
