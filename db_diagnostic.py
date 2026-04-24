#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('patient_portal.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print('\n=== DATABASE DIAGNOSTIC ===\n')

# Check all users
print('1. ALL USERS:')
users = c.execute('SELECT id, email, fullname, role, phc_id FROM users ORDER BY id').fetchall()
if users:
    for u in users:
        print(f'   ID: {u["id"]}, Email: {u["email"]}, Name: {u["fullname"]}, Role: {u["role"]}, PHC_ID: {u["phc_id"]}')
else:
    print('   No users found')

# Check patients specifically
print('\n2. PATIENTS:')
patients = c.execute('SELECT id, email, fullname, phc_id FROM users WHERE role = "patient"').fetchall()
print(f'   Total patients: {len(patients)}')
for p in patients:
    print(f'   ID: {p["id"]}, Email: {p["email"]}, Name: {p["fullname"]}, PHC_ID: {p["phc_id"]}')

# Check patient_logs
print('\n3. PATIENT_LOGS:')
logs_count = c.execute('SELECT COUNT(*) as cnt FROM patient_logs').fetchone()
print(f'   Total patient_logs entries: {logs_count["cnt"]}')
logs = c.execute('SELECT id, user_id, phc_id, symptoms FROM patient_logs ORDER BY id DESC LIMIT 10').fetchall()
for log in logs:
    print(f'   ID: {log["id"]}, User_ID: {log["user_id"]}, PHC_ID: {log["phc_id"]}, Symptoms: {log["symptoms"][:30] if log["symptoms"] else ""}...')

# Check PHC facilities
print('\n4. PHC FACILITIES:')
phcs = c.execute('SELECT id, name FROM phc_facilities').fetchall()
if phcs:
    for phc in phcs:
        print(f'   ID: {phc["id"]}, Name: {phc["name"]}')
else:
    print('   No PHC facilities found')

# Check PHC nurses
print('\n5. PHC NURSES:')
nurses = c.execute('SELECT id, email, fullname, phc_id FROM users WHERE role = "phc_nurse"').fetchall()
if nurses:
    for n in nurses:
        print(f'   ID: {n["id"]}, Email: {n["email"]}, Name: {n["fullname"]}, PHC_ID: {n["phc_id"]}')
else:
    print('   No PHC nurses found')

# Check the problematic query
if nurses:
    nurse = nurses[0]
    print(f'\n6. TESTING PHC NURSE QUERY (PHC Nurse ID: {nurse["id"]}, PHC_ID: {nurse["phc_id"]}):')
    test_query = """
        SELECT
            u.id,
            u.email,
            u.fullname,
            u.phone,
            COUNT(DISTINCT a.id) as total_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
        FROM users u
        LEFT JOIN appointments a ON u.id = a.patient_id
        LEFT JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
        WHERE u.role = 'patient' AND pl.phc_id = ?
        GROUP BY u.id
        ORDER BY u.fullname ASC
    """
    results = c.execute(test_query, (nurse["phc_id"], nurse["phc_id"])).fetchall()
    print(f'   Results count (BUGGY QUERY): {len(results)}')

    # Test the CORRECT query
    print(f'\n7. TESTING CORRECTED QUERY (using u.phc_id instead of pl.phc_id):')
    test_query_fixed = """
        SELECT
            u.id,
            u.email,
            u.fullname,
            u.phone,
            COUNT(DISTINCT a.id) as total_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
        FROM users u
        LEFT JOIN appointments a ON u.id = a.patient_id
        WHERE u.role = 'patient' AND u.phc_id = ?
        GROUP BY u.id
        ORDER BY u.fullname ASC
    """
    results_fixed = c.execute(test_query_fixed, (nurse["phc_id"],)).fetchall()
    print(f'   Results count (FIXED QUERY): {len(results_fixed)}')
    for r in results_fixed:
        print(f'     - {r["fullname"]} (ID: {r["id"]})')

conn.close()
print('\n')
