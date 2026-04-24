#!/usr/bin/env python3
"""Quick database verification script"""
import sqlite3
import os
import time

db_path = 'patient_portal.db'

# Wait a moment for app to create DB
time.sleep(2)

if not os.path.exists(db_path):
    print("❌ Database file does not exist yet")
    exit(1)

db_size = os.path.getsize(db_path)
print(f"✅ Database file exists - Size: {db_size} bytes")

if db_size == 0:
    print("❌ Database file is still empty (0 bytes)")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = c.fetchall()

    print(f"\n✅ Found {len(tables)} tables:")
    for table in tables:
        c.execute(f"PRAGMA table_info({table[0]})")
        columns = c.fetchall()
        print(f"   - {table[0]} ({len(columns)} columns)")

        if table[0] == 'users':
            for col in columns:
                print(f"     • {col[1]} ({col[2]})")
                if col[1] == 'phc_id':
                    print("       ✅ phc_id column present!")

    conn.close()
    print("\n✅ Database initialized successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
