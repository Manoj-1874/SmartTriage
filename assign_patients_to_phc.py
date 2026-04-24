import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Check patient data
print("=== PATIENTS IN DATABASE ===")
patients = conn.execute('SELECT id, email, location, phc_id FROM users WHERE role = ?', ('patient',)).fetchall()
for p in patients[:5]:
    print(f"ID: {p['id']}, Email: {p['email']}, Location: {p['location']}, PHC: {p['phc_id']}")

# Directly assign Henry (user_id 58) to PHC Central
print("\n=== ASSIGNING PATIENTS TO PHCS ===")
conn.execute('UPDATE users SET phc_id = ? WHERE id = ? AND role = ?', (1, 58, 'patient'))
conn.execute('UPDATE patient_logs SET phc_id = ? WHERE user_id = ?', (1, 58))

# Assign other patients to various PHCs for distribution
other_patients = conn.execute('SELECT id FROM users WHERE role = ? AND id != ?', ('patient', 58)).fetchall()
phc_assignment = [2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6, 1]

for i, patient in enumerate(other_patients):
    phc_id = phc_assignment[i % len(phc_assignment)]
    conn.execute('UPDATE users SET phc_id = ? WHERE id = ?', (phc_id, patient['id']))
    conn.execute('UPDATE patient_logs SET phc_id = ? WHERE user_id = ?', (phc_id, patient['id']))
    print(f"✓ Assigned Patient ID {patient['id']} to PHC {phc_id}")

conn.commit()

# Verify
print("\n=== VERIFICATION ===")
for phc_id in range(1, 7):
    count = conn.execute('SELECT COUNT(*) FROM patient_logs WHERE phc_id = ?', (phc_id,)).fetchone()[0]
    phc_names = ['', 'PHC Central', 'PHC North', 'PHC South', 'PHC East', 'PHC West', 'PHC Rural']
    print(f"{phc_names[phc_id]}: {count} patient logs")

total = conn.execute('SELECT COUNT(*) FROM patient_logs WHERE phc_id IS NOT NULL').fetchone()[0]
print(f"\nTotal assigned: {total}")
