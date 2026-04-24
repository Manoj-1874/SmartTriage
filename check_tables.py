import sqlite3

conn = sqlite3.connect('patient_portal.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in c.fetchall()]
print("Tables in database:", tables)
print("Messages table exists:", 'messages' in tables)

if 'messages' in tables:
    c.execute("PRAGMA table_info(messages)")
    columns = c.fetchall()
    print("\nMessages table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

conn.close()
