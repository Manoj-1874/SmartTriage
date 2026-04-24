import sqlite3

conn = sqlite3.connect('triage.db')

print("=== DATA VERIFICATION ===\n")

# Count patients
patients = conn.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0]
print(f"Total patients: {patients}")

# Count doctors
doctors = conn.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0]
print(f"Total doctors: {doctors}")

# Count nurses
nurses = conn.execute("SELECT COUNT(*) FROM users WHERE role='phc_nurse'").fetchone()[0]
print(f"Total PHC nurses: {nurses}")

# Count admins
admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='ddhs_admin'").fetchone()[0]
print(f"Total DDHS admins: {admins}")

# Total staff
staff = doctors + nurses + admins
print(f"Total staff (doctors + nurses + admins): {staff}")

# Count health centers (distinct phc_id from doctors and nurses)
centers = conn.execute("SELECT COUNT(DISTINCT phc_id) FROM users WHERE role IN ('doctor', 'phc_nurse') AND phc_id IS NOT NULL").fetchone()[0]
print(f"Health centers (distinct phc_id from staff): {centers}")

# Count ambulances
ambulances = conn.execute("SELECT COUNT(*) FROM ambulances WHERE status='available'").fetchone()[0]
print(f"Available ambulances: {ambulances}")

print(f"\n=== SUMMARY ===")
print(f"Should show:")
print(f"  Total Patients: {patients}")
print(f"  Health Centers: {centers}")
print(f"  Total Staff: {staff}")
print(f"  Active Ambulances: {ambulances}")

conn.close()
