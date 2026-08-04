import sqlite3
conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Check admin district
admin = conn.execute("SELECT id, fullname, role, district FROM users WHERE id = 2").fetchone()
print("Admin:", dict(admin))

# Check doctors' districts
doctors = [dict(r) for r in conn.execute("SELECT id, fullname, district FROM users WHERE role = 'doctor' LIMIT 10").fetchall()]
print("Doctors' Districts:", doctors)

# Check PHCs' districts
phcs = [dict(r) for r in conn.execute("SELECT id, name, district FROM phc_facilities LIMIT 10").fetchall()]
print("PHCs' Districts:", phcs)
