import sqlite3
from datetime import datetime

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
print(f"Auditing attendance for today ({datetime.now().date()})...")

rows = conn.execute("SELECT * FROM staff_attendance").fetchall()
print(f"Total attendance records in DB: {len(rows)}")

today_rows = conn.execute("""
    SELECT sa.*, u.fullname, u.role 
    FROM staff_attendance sa 
    JOIN users u ON sa.user_id = u.id 
    WHERE date(sa.check_in_time) = date('now', 'localtime')
""").fetchall()

print(f"Records found for today: {len(today_rows)}")
for r in today_rows:
    print(r)

conn.close()
