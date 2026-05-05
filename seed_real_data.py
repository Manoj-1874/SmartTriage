import sqlite3
import os
from datetime import datetime, timedelta

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

def seed():
    print("Seeding real-world linked data (Deep Link Edition)...")
    
    # Get a valid PHC ID (Vellode is usually 1)
    phc_id = 1
    
    # 1. CREATE PATIENTS
    patients = [
        ('Kavitha M.', 'kavitha@demo.com', 'Chennai', '9988776601'),
        ('Arjun Kumar', 'arjun@demo.com', 'Chennai', '9988776602'),
        ('Ravi S.', 'ravi@demo.com', 'Chennai', '9988776603')
    ]
    
    p_ids = {}
    for name, email, dist, phone in patients:
        c.execute("INSERT OR IGNORE INTO users (fullname, email, password_hash, role, district, phone, phc_id, is_approved) VALUES (?, ?, 'pbkdf2:sha256:260000$demo$demo', 'patient', ?, ?, ?, 1)", 
                  (name, email, dist, phone, phc_id))
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        p_ids[name] = c.fetchone()[0]

    # 2. CREATE VHN FIELD ENTRY
    c.execute("DELETE FROM vhn_field_entries WHERE patient_name = 'Kavitha M.'")
    c.execute("""
        INSERT INTO vhn_field_entries (vhn_id, patient_name, village, risk_score, vitals_summary)
        VALUES (10, 'Kavitha M.', 'Village Alpha', 9.0, 'BP: 170/110, HR: 105, Critical Pregnancy Case')
    """)

    # 3. CREATE NURSE TRIAGE LOG
    c.execute("DELETE FROM patient_logs WHERE user_id = ?", (p_ids['Arjun Kumar'],))
    c.execute("""
        INSERT INTO patient_logs (user_id, phc_id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, respiration_rate, spo2, dual_brain_risk, recommended_specialist, risk_score, news2_score, phc_department, district)
        VALUES (?, ?, 35, 'Male', 'Persistent High Fever, Fatigue', 110, 70, 105, 102.5, 22, 94, 'HIGH', 'General Physician', 7.5, 5, 'Emergency', 'Chennai')
    """, (p_ids['Arjun Kumar'], phc_id))

    # 4. CREATE APPOINTMENT (Deep Link)
    doctor = c.execute("SELECT id, fullname FROM users WHERE role='doctor' LIMIT 1").fetchone()
    if doctor:
        c.execute("DELETE FROM appointments WHERE patient_id = ?", (p_ids['Arjun Kumar'],))
        c.execute("""
            INSERT INTO appointments (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date, appointment_time, status, notes, phc_id)
            VALUES (?, ?, ?, ?, 'General Medicine', DATE('now'), '10:30 AM', 'Pending', 'Follow up on high-risk fever triage', ?)
        """, (p_ids['Arjun Kumar'], 'Arjun Kumar', doctor[0], doctor[1], phc_id))

    conn.commit()
    print("Database seeding completed. All roles are now logically linked.")

if __name__ == "__main__":
    seed()
    conn.close()
