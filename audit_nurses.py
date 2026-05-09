import sqlite3
import os

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
print("Auditing Nurse assignments...")
nurses = conn.execute("SELECT id, fullname, phc_id FROM users WHERE role='phc_nurse'").fetchall()
for n in nurses:
    print(f"ID: {n[0]} | Name: {n[1]} | PHC ID: {n[2]}")
conn.close()
