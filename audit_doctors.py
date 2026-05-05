import sqlite3
import os

db_path = 'triage.db'
if not os.path.exists(db_path):
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    # Get doctors and their PHC names
    query = """
        SELECT u.fullname, u.specialization, f.name as phc_name 
        FROM users u
        LEFT JOIN phc_facilities f ON u.phc_id = f.id
        WHERE u.role = 'doctor'
    """
    doctors = conn.execute(query).fetchall()
    print(f"Total Doctors in System: {len(doctors)}")
    for d in doctors:
        spec = d[1] if d[1] else "General Physician (MBBS)"
        print(f"Doctor: {d[0]} | Specialization: {spec} | Location: {d[2]}")
    conn.close()
