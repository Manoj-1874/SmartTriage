import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Find doctor
docs = conn.execute("SELECT email, fullname FROM users WHERE role='doctor' AND fullname LIKE '%Ramesh Sharma 1%'").fetchall()
for doc in docs:
    print(dict(doc))
conn.close()
