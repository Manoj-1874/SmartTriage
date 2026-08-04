import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Check newest patient
patient = conn.execute("SELECT fullname, district, phc_id FROM users WHERE role = 'patient' ORDER BY id DESC LIMIT 1").fetchone()
print("Newest Patient:", dict(patient) if patient else None)

# Check districts in DB
districts = conn.execute("SELECT DISTINCT district FROM users WHERE district IS NOT NULL AND district != ''").fetchall()
print("All Districts in DB:", [d['district'] for d in districts])
