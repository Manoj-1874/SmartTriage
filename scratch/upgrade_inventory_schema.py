import sqlite3
import os

db_path = 'triage.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        # 1. Add Expiry Column
        try:
            conn.execute("ALTER TABLE inventory ADD COLUMN expiry_date TEXT DEFAULT '2026-12-31';")
            print("Column expiry_date added successfully.")
        except:
            print("expiry_date already exists.")

        # 2. Add Batch ID Column
        try:
            conn.execute("ALTER TABLE inventory ADD COLUMN batch_id TEXT DEFAULT 'TN-MSC-001';")
            print("Column batch_id added successfully.")
        except:
            print("batch_id already exists.")
            
        print("Inventory table upgraded successfully.")
    except Exception as e:
        print(f"Error during upgrade: {e}")
    conn.commit()
    conn.close()
else:
    print(f"Database {db_path} not found.")
