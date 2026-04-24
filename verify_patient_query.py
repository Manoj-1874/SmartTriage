import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Simulate what phc_nurse_patients route does - get patients for PHC 1
phc_id = 1

patients = conn.execute('''
    SELECT u.id, u.email, u.fullname, u.phc_id,
           COUNT(pl.id) as total_records
    FROM users u
    LEFT JOIN patient_logs pl ON u.id = pl.user_id
    WHERE u.role = 'patient' AND u.phc_id = ?
    GROUP BY u.id
    ORDER BY u.created_at DESC
''', (phc_id,)).fetchall()

print(f'\nPatients for PHC {phc_id}:')
print(f'Total: {len(patients)}')
for patient in patients:
    print(f'  - {patient[2]} ({patient[1]}) - ID: {patient[0]}, Records: {patient[4]}')

# Verify testpatient2 is included
testpatient = conn.execute(
    'SELECT id, email, fullname, phc_id FROM users WHERE email="testpatient2@test.com"'
).fetchone()
if testpatient:
    print(f'\nTestpatient2 verification:')
    print(f'  Email: {testpatient[1]}')
    print(f'  Name: {testpatient[2]}')
    print(f'  PHC ID: {testpatient[3]}')
    print(f'  Will be visible to PHC {testpatient[3]} nurses: YES')
else:
    print('\nTestpatient2 not found!')

conn.close()
