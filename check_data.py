import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Check DDHS Admin
admin = conn.execute('SELECT id, phc_id, role FROM users WHERE email = ?', ('gopi.ddhsadmin@gmail.com',)).fetchone()
print('=== DDHS ADMIN ===')
print(f'ID: {admin["id"]}, PHC_ID: {admin["phc_id"]}, Role: {admin["role"]}')

# Check patient logs
print('\n=== PATIENT_LOGS SAMPLE ===')
logs = conn.execute('SELECT id, user_id, phc_id, dual_brain_risk FROM patient_logs LIMIT 5').fetchall()
for row in logs:
    print(dict(row))

# Check total patients
print('\n=== TOTAL PATIENTS ===')
patients = conn.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('patient',)).fetchone()[0]
print(f'Total patients: {patients}')

# Check nurse's phc_id
print('\n=== PHC NURSE ===')
nurse = conn.execute('SELECT id, phc_id, role FROM users WHERE email = ?', ('fendy.phc_nurse@gmail.com',)).fetchone()
print(f'ID: {nurse["id"]}, PHC_ID: {nurse["phc_id"]}, Role: {nurse["role"]}')

# Check patient logs for that phc
print('\n=== PATIENT_LOGS FOR PHC 97 ===')
phc97_logs = conn.execute('SELECT COUNT(*) FROM patient_logs WHERE phc_id = ?', (97,)).fetchone()[0]
print(f'Patient logs for PHC 97: {phc97_logs}')
