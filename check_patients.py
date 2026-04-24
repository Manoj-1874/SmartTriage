import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# List all tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f'Tables in database: {[t[0] for t in tables]}')

# Get first PHC facility if table exists
if any(t[0] == 'phc_facilities' for t in tables):
    phc = conn.execute('SELECT id FROM phc_facilities LIMIT 1').fetchone()
    print(f'First PHC ID: {phc[0] if phc else None}')
else:
    print('phc_facilities table does not exist!')

# Get PHC nurse info
nurse = conn.execute('SELECT id, email, fullname, role, phc_id FROM users WHERE role="phc_nurse" LIMIT 1').fetchone()
if nurse:
    print(f'\nPHC Nurse: {nurse[2]} (ID: {nurse[0]}, PHC: {nurse[4]})')

# Get recent patients
patients = conn.execute('SELECT id, email, fullname, role, phc_id FROM users WHERE role="patient" ORDER BY id DESC LIMIT 5').fetchall()
print(f'\nRecent Patients ({len(patients)}):')
for p in patients:
    print(f'  ID: {p[0]}, Email: {p[1]}, Name: {p[2]}, Role: {p[3]}, PHC: {p[4]}')

# Get patient assessment records
assessments = conn.execute('SELECT user_id, phc_id FROM patient_logs ORDER BY id DESC LIMIT 5').fetchall()
print(f'\nRecent Assessment Records ({len(assessments)}):')
for a in assessments:
    print(f'  User ID: {a[0]}, PHC: {a[1]}')

conn.close()
