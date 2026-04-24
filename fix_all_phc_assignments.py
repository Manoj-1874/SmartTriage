import sqlite3
from datetime import datetime

conn = sqlite3.connect('triage.db')

print("=== FIXING DATA ISSUES ===\n")

# 1. Assign all patients to a PHC if not already assigned
print("1. Assigning patients to PHCs...")
patients = conn.execute("SELECT id FROM users WHERE role='patient'").fetchall()
phc_ids = [1, 2, 3, 4, 5, 6]  # Our 6 PHC centers

for idx, (patient_id,) in enumerate(patients):
    phc_id = phc_ids[idx % len(phc_ids)]
    conn.execute("UPDATE users SET phc_id = ? WHERE id = ?", (phc_id, patient_id))
    print(f"  ✓ Patient {patient_id} → PHC {phc_id}")

print(f"\n✓ Assigned {len(patients)} patients to PHCs\n")

# 2. Assign all patient_logs to have correct phc_id based on the patient's assigned PHC
print("2. Updating patient_logs with PHC IDs...")
logs = conn.execute("""
    SELECT pl.id, pl.user_id, u.phc_id
    FROM patient_logs pl
    JOIN users u ON u.id = pl.user_id
""").fetchall()

for log_id, user_id, phc_id in logs:
    if phc_id:
        conn.execute("UPDATE patient_logs SET phc_id = ? WHERE id = ?", (phc_id, log_id))

print(f"✓ Updated {len(logs)} patient_logs with PHC IDs\n")

# 3. Verify all doctors are assigned to PHCs
print("3. Verifying doctor assignments...")
doctors = conn.execute("SELECT id, phc_id FROM users WHERE role='doctor'").fetchall()
unassigned = sum(1 for _, phc_id in doctors if phc_id is None)
if unassigned > 0:
    for idx, (doctor_id, _) in enumerate(doctors):
        if _ is None:
            phc_id = phc_ids[idx % len(phc_ids)]
            conn.execute("UPDATE users SET phc_id = ? WHERE id = ?", (phc_id, doctor_id))
            print(f"  ✓ Doctor {doctor_id} → PHC {phc_id}")
else:
    print("  ✓ All doctors already assigned\n")

# 4. Verify nurse assignments
print("4. Verifying nurse assignments...")
nurses = conn.execute("SELECT id, phc_id FROM users WHERE role='phc_nurse'").fetchall()
unassigned = sum(1 for _, phc_id in nurses if phc_id is None)
if unassigned > 0:
    for idx, (nurse_id, _) in enumerate(nurses):
        if _ is None:
            phc_id = phc_ids[idx % len(phc_ids)]
            conn.execute("UPDATE users SET phc_id = ? WHERE id = ?", (phc_id, nurse_id))
            print(f"  ✓ Nurse {nurse_id} → PHC {phc_id}")
else:
    print("  ✓ All nurses already assigned\n")

conn.commit()

# Verify results
print("\n=== VERIFICATION ===\n")

# Check patients by PHC
print("Patients by PHC:")
for phc_id in phc_ids:
    count = conn.execute("SELECT COUNT(*) FROM users WHERE role='patient' AND phc_id=?", (phc_id,)).fetchone()[0]
    print(f"  PHC {phc_id}: {count} patients")

# Check patient_logs by PHC
print("\nPatient Logs by PHC:")
for phc_id in phc_ids:
    count = conn.execute("SELECT COUNT(*) FROM patient_logs WHERE phc_id=?", (phc_id,)).fetchone()[0]
    print(f"  PHC {phc_id}: {count} logs")

# Check doctors by PHC
print("\nDoctors by PHC:")
for phc_id in phc_ids:
    count = conn.execute("SELECT COUNT(*) FROM users WHERE role='doctor' AND phc_id=?", (phc_id,)).fetchone()[0]
    print(f"  PHC {phc_id}: {count} doctors")

# Check nurses by PHC
print("\nNurses by PHC:")
for phc_id in phc_ids:
    count = conn.execute("SELECT COUNT(*) FROM users WHERE role='phc_nurse' AND phc_id=?", (phc_id,)).fetchone()[0]
    print(f"  PHC {phc_id}: {count} nurses")

conn.close()
print("\n✅ All data assignments complete!")
