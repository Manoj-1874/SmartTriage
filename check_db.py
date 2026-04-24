#!/usr/bin/env python3
import sqlite3
import os

db_file = 'patient_portal.db'
print(f'Database file exists: {os.path.exists(db_file)}')

if os.path.exists(db_file):
    print(f'Database file size: {os.path.getsize(db_file)} bytes')

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Get all tables
    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f'Tables in database: {len(tables)}')
    for t in tables:
        print(f'  - {t[0]}')

    conn.close()
else:
    print('Database file does NOT exist - will be created on app start')
