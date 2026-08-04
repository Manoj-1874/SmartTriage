import sqlite3

conn = sqlite3.connect('triage.db')
c = conn.cursor()
schema = c.execute("SELECT sql FROM sqlite_master WHERE name='notifications'").fetchone()
if schema:
    print(schema[0])
else:
    print("Table 'notifications' does not exist.")
conn.close()
