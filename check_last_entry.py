"""
Quick script to check the last patient log entry
"""
import sqlite3

# Connect to database
conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row  # This enables column access by name
cursor = conn.cursor()

# Get the last entry
cursor.execute('SELECT * FROM patient_logs ORDER BY id DESC LIMIT 1')
row = cursor.fetchone()

if row:
    print("\n" + "="*70)
    print("LAST PATIENT LOG ENTRY")
    print("="*70)

    for key in row.keys():
        print(f"{key:20s}: {row[key]}")

    print("="*70 + "\n")
else:
    print("No entries found in database")

conn.close()
