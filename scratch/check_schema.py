import sqlite3
conn = sqlite3.connect('triage.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(patient_logs)")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
