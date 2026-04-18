#!/usr/bin/env python3
import sqlite3, os, sys
from werkzeug.security import generate_password_hash
from datetime import datetime

DB_PATH = 'triage.db'

TEST_PASSWORD = 'test123'
PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)

DDHS_ADMIN = {'email': 'admin@ddhs.gov', 'fullname': 'Dr. Rajesh Kumar', 'role': 'ddhs_admin', 'phone': '+91-9876543210'}

PATIENTS = [
    {'email': 'patient1@example.com', 'fullname': 'Ramesh Sharma', 'phone': '+91-8765432101'},
    {'email': 'patient2@example.com', 'fullname': 'Priya Desai', 'phone': '+91-8765432102'},
    {'email': 'patient3@example.com', 'fullname': 'Arjun Patel', 'phone': '+91-8765432103'},
    {'email': 'patient4@example.com', 'fullname': 'Sneha Gupta', 'phone': '+91-8765432104'},
    {'email': 'patient5@example.com', 'fullname': 'Vikram Singh', 'phone': '+91-8765432105'},
]

DOCTORS = [
    {'email': 'doctor1@hospital.com', 'fullname': 'Arun Kumar', 'phone': '+91-9111111101', 'specialization': 'Cardiology', 'license': 'LIC/2020/0001', 'experience': '15', 'phc_id': 1},
    {'email': 'doctor2@hospital.com', 'fullname': 'Meera Verma', 'phone': '+91-9111111102', 'specialization': 'Pediatrics', 'license': 'LIC/2021/0002', 'experience': '12', 'phc_id': 2},
    {'email': 'doctor3@hospital.com', 'fullname': 'Suresh Patel', 'phone': '+91-9111111103', 'specialization': 'Orthopedics', 'license': 'LIC/2019/0003', 'experience': '18', 'phc_id': 3},
    {'email': 'doctor4@hospital.com', 'fullname': 'Anjali Sharma', 'phone': '+91-9111111104', 'specialization': 'Dermatology', 'license': 'LIC/2022/0004', 'experience': '10', 'phc_id': 4},
    {'email': 'doctor5@hospital.com', 'fullname': 'Vivek Singh', 'phone': '+91-9111111105', 'specialization': 'General Medicine', 'license': 'LIC/2020/0005', 'experience': '14', 'phc_id': 5},
]

PHC_NURSES = [
    {'email': 'nurse1@phc.gov', 'fullname': 'Priya Nair', 'phone': '+91-9222222201', 'specialization': 'General Nursing', 'license': 'NUR/2020/0001', 'experience': '8', 'phc_id': 1},
    {'email': 'nurse2@phc.gov', 'fullname': 'Pooja Reddy', 'phone': '+91-9222222202', 'specialization': 'Maternal Health', 'license': 'NUR/2021/0002', 'experience': '6', 'phc_id': 2},
    {'email': 'nurse3@phc.gov', 'fullname': 'Lakshmi Iyer', 'phone': '+91-9222222203', 'specialization': 'Community Health', 'license': 'NUR/2019/0003', 'experience': '10', 'phc_id': 3},
]

def insert_user(conn, user_data):
    cursor = conn.cursor()
    try:
        if user_data['role'] in ('doctor', 'phc_nurse'):
            cursor.execute('INSERT INTO users (email, password_hash, fullname, role, phc_id, phone, specialization, license, experience, email_verified, verification_token, verification_expires) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (user_data['email'], PASSWORD_HASH, user_data['fullname'], user_data['role'], user_data.get('phc_id'), user_data.get('phone'), user_data.get('specialization'), user_data.get('license'), user_data.get('experience'), 1, 'test_' + user_data['email'], datetime.utcnow().isoformat()))
        else:
            cursor.execute('INSERT INTO users (email, password_hash, fullname, role, phc_id, phone, email_verified, verification_token, verification_expires) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (user_data['email'], PASSWORD_HASH, user_data['fullname'], user_data['role'], user_data.get('phc_id'), user_data.get('phone'), 1, 'test_' + user_data['email'], datetime.utcnow().isoformat()))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print("SKIP: {} exists".format(user_data['email']))
        return None

def setup():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("\n" + "="*70)
    print("SMARTTRIAGE TEST DATA SETUP")
    print("="*70)

    print("\nDDHS Admin...")
    admin_id = insert_user(conn, DDHS_ADMIN)
    print("OK" if admin_id else "SKIP")

    print("\nPatients (5)...")
    patient_ids = []
    for i, p in enumerate(PATIENTS, 1):
        p['role'] = 'patient'
        pid = insert_user(conn, p)
        if pid:
            patient_ids.append(pid)
            print("OK - {} (ID: {})".format(p['fullname'], pid))

    print("\nDoctors (5)...")
    doctor_ids = []
    for i, d in enumerate(DOCTORS, 1):
        d['role'] = 'doctor'
        did = insert_user(conn, d)
        if did:
            doctor_ids.append(did)
            print("OK - {} ({}) at PHC {} (ID: {})".format(d['fullname'], d['specialization'], d.get('phc_id'), did))

    print("\nPHC Nurses (3)...")
    nurse_ids = []
    for i, n in enumerate(PHC_NURSES, 1):
        n['role'] = 'phc_nurse'
        nid = insert_user(conn, n)
        if nid:
            nurse_ids.append(nid)
            print("OK - {} at PHC {} (ID: {})".format(n['fullname'], n.get('phc_id'), nid))

    conn.close()

    # Write credentials
    with open('TEST_CREDENTIALS.txt', 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("SMARTTRIAGE TEST CREDENTIALS\n")
        f.write("="*70 + "\n")
        f.write("Password: {}\n\n".format(TEST_PASSWORD))

        f.write("DDHS ADMIN\n")
        f.write("Email: {}\n".format(DDHS_ADMIN['email']))
        f.write("Password: {}\n".format(TEST_PASSWORD))
        f.write("ID: {}\n".format(admin_id))
        f.write("URL: http://localhost:5000/ddhs-admin/dashboard\n\n")

        f.write("PATIENTS\n")
        for i, p in enumerate(PATIENTS):
            f.write("Patient {} - {} / {} (ID: {})\n".format(i+1, p['email'], TEST_PASSWORD, patient_ids[i] if i < len(patient_ids) else 'N/A'))

        f.write("\nDOCTORS\n")
        for i, d in enumerate(DOCTORS):
            f.write("Doctor {} - {} / {} ({}) at PHC ID {} (ID: {})\n".format(
                i+1, d['email'], TEST_PASSWORD, d['specialization'], d['phc_id'], doctor_ids[i] if i < len(doctor_ids) else 'N/A'))

        f.write("\nPHC NURSES\n")
        for i, n in enumerate(PHC_NURSES):
            f.write("Nurse {} - {} / {} at PHC ID {} (ID: {})\n".format(
                i+1, n['email'], TEST_PASSWORD, n['phc_id'], nurse_ids[i] if i < len(nurse_ids) else 'N/A'))

        f.write("\n" + "="*70 + "\n")
        f.write("PHC CENTERS\n")
        f.write("PHC 1: PHC Central\n")
        f.write("PHC 2: PHC North\n")
        f.write("PHC 3: PHC South\n")
        f.write("PHC 4: PHC East\n")
        f.write("PHC 5: PHC West\n")
        f.write("PHC 6: PHC Rural\n")

    print("\n" + "="*70)
    print("SUCCESS - Test data created!")
    print("Credentials saved to: TEST_CREDENTIALS.txt")
    print("="*70 + "\n")

if __name__ == '__main__':
    setup()
