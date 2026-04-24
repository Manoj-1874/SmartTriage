import sqlite3

conn = sqlite3.connect('triage.db')
c = conn.cursor()

# Check users table schema
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
print('Users table columns:')
for col in columns:
    print(f'  {col[1]:25s} {col[2]:15s}')

# Check if location column exists
location_exists = any(col[1] == 'location' for col in columns)
print(f'\nLocation column exists: {location_exists}')

conn.close()
