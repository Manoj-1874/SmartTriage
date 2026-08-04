import sqlite3
import os

db_path = 'triage.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE patient_logs ADD COLUMN is_dispensed INTEGER DEFAULT 0;")
        print("Column is_dispensed added successfully to triage.db.")
    except Exception as e:
        print(f"Error or already exists: {e}")
    conn.commit()
    conn.close()
else:
    print(f"Database {db_path} not found.")
