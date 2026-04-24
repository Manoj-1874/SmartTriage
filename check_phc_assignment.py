import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Get all PHC nurses and their assigned PHCs
nurses = conn.execute('SELECT id, email, fullname, phc_id FROM users WHERE role="phc_nurse" ORDER BY phc_id').fetchall()
print('\nPHC Nurses:')
for nurse in nurses:
    phc_name = conn.execute('SELECT name FROM phc_facilities WHERE id=?', (nurse[3],)).fetchone() if nurse[3] else None
    phc_display = f'{phc_name[0]} (ID: {nurse[3]})' if phc_name else 'Unassigned'
    print(f'  {nurse[1]} - PHC: {phc_display}')

# Check how many patients per PHC
print('\nPatients per PHC:')
phcs = conn.execute('SELECT DISTINCT phc_id FROM users WHERE role="patient" ORDER BY phc_id').fetchall()
for phc in phcs:
    count = conn.execute('SELECT COUNT(*) FROM users WHERE role="patient" AND phc_id=?', (phc[0],)).fetchone()[0]
    phc_name = conn.execute('SELECT name FROM phc_facilities WHERE id=?', (phc[0],)).fetchone()
    phc_display = f'{phc_name[0]} (ID: {phc[0]})' if phc_name else f'ID: {phc[0]}'
    print(f'  {phc_display}: {count} patients')

conn.close()
