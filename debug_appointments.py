import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Query for patient with id 58
patient_id = 58
rows = cur.execute('''
    SELECT a.*, u.fullname as patient_fullname, u.phone as patient_phone
    FROM appointments a
    LEFT JOIN users u ON a.patient_id = u.id
    WHERE a.patient_id = ?
    ORDER BY a.appointment_date ASC, a.appointment_time ASC
''', (patient_id,)).fetchall()

print(f'Query result for patient_id={patient_id}:')
print(f'Total rows: {len(rows)}')
for r in rows:
    print(dict(r))

# Also check who user 58 is
user_row = cur.execute('SELECT * FROM users WHERE id = ?', (58,)).fetchone()
print(f'\nUser 58: {dict(user_row) if user_row else "NOT FOUND"}')

# Check current logged in user context
conn.close()
