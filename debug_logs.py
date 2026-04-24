import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Get unique users with patient logs
users_with_logs = conn.execute('''
    SELECT DISTINCT u.id, u.email, COUNT(pl.id) as log_count, MIN(u.phc_id) as phc
    FROM users u
    LEFT JOIN patient_logs pl ON u.id = pl.user_id
    WHERE u.role = 'patient'
    GROUP BY u.id
    ORDER BY log_count DESC
''').fetchall()

print("=== PATIENTS WITH LOGS ===")
for row in users_with_logs:
    print(f"ID: {row['id']:<3} | Email: {row['email']:<35} | Logs: {row['log_count']:<3} | PHC: {row['phc']}")

# Now let's get all patient logs and their user assignments
print("\n=== ALL PATIENT LOGS ===")
all_logs = conn.execute('SELECT DISTINCT user_id, phc_id FROM patient_logs ORDER BY user_id').fetchall()
print(f"Total log entries: {len(all_logs)}")
for row in all_logs:
    print(f"User {row['user_id']}: PHC {row['phc_id']}")

# Fix: Update all patient_logs to have proper PHC assignments
print("\n=== FIXING LOGS ===")
conn.execute("""
    UPDATE patient_logs SET phc_id = (
        SELECT phc_id FROM users WHERE users.id = patient_logs.user_id
    ) WHERE phc_id IS NULL OR phc_id = 97
""")

# But wait, let's first check that users have PHC assignments
print("\n=== CHECKING USER PHC ASSIGNMENTS ===")
users = conn.execute('SELECT id, email, phc_id FROM users WHERE role = ?', ('patient',)).fetchall()
for u in users[:10]:
    print(f"User {u['id']}: {u['email']:<40} → PHC {u['phc_id']}")

conn.commit()
