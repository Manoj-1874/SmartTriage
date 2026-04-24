import sqlite3

conn = sqlite3.connect('triage.db')

print("=== DOCTOR CREDENTIALS ===")
docs = conn.execute("SELECT id, email FROM users WHERE role='doctor' LIMIT 3").fetchall()
for d in docs:
    print(f"Doctor ID {d[0]}: {d[1]}")

print("\n=== PHC NURSE CREDENTIALS ===")
nurses = conn.execute("SELECT id, email FROM users WHERE role='phc_nurse' LIMIT 2").fetchall()
for n in nurses:
    print(f"Nurse ID {n[0]}: {n[1]}")

print("\n=== PATIENT CREDENTIALS ===")
patients = conn.execute("SELECT id, email FROM users WHERE role='patient' LIMIT 2").fetchall()
for p in patients:
    print(f"Patient ID {p[0]}: {p[1]}")

print("\n=== DDHS ADMIN CREDENTIALS ===")
admins = conn.execute("SELECT id, email FROM users WHERE role='ddhs_admin' LIMIT 2").fetchall()
for a in admins:
    print(f"Admin ID {a[0]}: {a[1]}")
