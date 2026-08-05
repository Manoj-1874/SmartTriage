import sqlite3

def print_schema(table_name):
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"Table: {table_name}")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    conn.close()

for t in ['appointments', 'patient_logs', 'users']:
    print_schema(t)
