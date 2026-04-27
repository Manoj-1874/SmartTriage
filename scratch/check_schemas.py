import sqlite3
conn = sqlite3.connect('e:\\Nilal_thiruvila\\SmartTriage_Dashboard\\triage.db')
cursor = conn.cursor()

tables = ['users', 'phc_facilities', 'ambulances', 'staff_attendance']
for table in tables:
    print(f"\nTable: {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        print(row)
conn.close()
