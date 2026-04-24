import sys
sys.path.insert(0, '/e/Nilal_thiruvila/SmartTriage_Dashboard')

from utils.database import get_db_connection

# Test what database Flask is using
conn = get_db_connection()
cur = conn.cursor()

# Query appointments
rows = cur.execute('SELECT COUNT(*) as count FROM appointments').fetchone()
print(f'Flask db connection - Total appointments: {rows["count"]}')

# List all appointments
rows = cur.execute('SELECT id, patient_id, doctor_id, status, appointment_date FROM appointments').fetchall()
print(f'\nAll {len(rows)} appointments:')
for r in rows:
    print(f'  ID {r["id"]}: patient {r["patient_id"]} -> doctor {r["doctor_id"]}, status={r["status"]}, date={r["appointment_date"]}')

conn.close()
