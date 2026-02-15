import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random

DB_PATH = 'triage.db'

def add_sample_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("🔄 Adding sample data to SmartTriage Dashboard...")
    
    # Step 1: Create sample users (patients and doctors)
    sample_patients = [
        ('john.smith@email.com', 'John Smith', '555-0101'),
        ('sarah.johnson@email.com', 'Sarah Johnson', '555-0102'),
        ('michael.brown@email.com', 'Michael Brown', '555-0103'),
        ('emily.davis@email.com', 'Emily Davis', '555-0104'),
        ('david.wilson@email.com', 'David Wilson', '555-0105'),
        ('lisa.martinez@email.com', 'Lisa Martinez', '555-0106'),
        ('james.anderson@email.com', 'James Anderson', '555-0107'),
        ('maria.garcia@email.com', 'Maria Garcia', '555-0108'),
    ]
    
    sample_doctors = [
        ('dr.thompson@hospital.com', 'Dr. Sarah Thompson', '555-1001', 'Cardiology', 'MD-12345', 15),
        ('dr.chen@hospital.com', 'Dr. Michael Chen', '555-1002', 'Neurology', 'MD-12346', 12),
        ('dr.patel@hospital.com', 'Dr. Priya Patel', '555-1003', 'Emergency Medicine', 'MD-12347', 10),
        ('dr.johnson@hospital.com', 'Dr. Robert Johnson', '555-1004', 'Internal Medicine', 'MD-12348', 20),
        ('dr.williams@hospital.com', 'Dr. Amanda Williams', '555-1005', 'Pediatrics', 'MD-12349', 8),
    ]
    
    patient_ids = []
    doctor_ids = []
    
    # Insert patients
    print("\n👥 Adding sample patients...")
    default_password = generate_password_hash('password123')
    
    for email, name, phone in sample_patients:
        try:
            c.execute('''INSERT INTO users (email, password_hash, fullname, role, phone)
                        VALUES (?, ?, ?, ?, ?)''',
                     (email, default_password, name, 'patient', phone))
            patient_ids.append(c.lastrowid)
            print(f"   ✅ Added patient: {name}")
        except sqlite3.IntegrityError:
            # User already exists, get their ID
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            result = c.fetchone()
            if result:
                patient_ids.append(result[0])
                print(f"   ℹ️  Patient already exists: {name}")
    
    # Insert doctors
    print("\n👨‍⚕️ Adding sample doctors...")
    for email, name, phone, specialization, license, experience in sample_doctors:
        try:
            c.execute('''INSERT INTO users (email, password_hash, fullname, role, phone, 
                        specialization, license, experience)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (email, default_password, name, 'doctor', phone, 
                      specialization, license, experience))
            doctor_ids.append(c.lastrowid)
            print(f"   ✅ Added doctor: {name} - {specialization}")
        except sqlite3.IntegrityError:
            # User already exists, get their ID
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            result = c.fetchone()
            if result:
                doctor_ids.append(result[0])
                print(f"   ℹ️  Doctor already exists: {name}")
    
    conn.commit()
    
    # Step 2: Create sample appointments with various statuses and dates
    print("\n📅 Adding sample appointments...")
    
    statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled']
    times = ['09:00 AM', '10:00 AM', '11:00 AM', '02:00 PM', '03:00 PM', '04:00 PM']
    
    symptoms_list = [
        'Routine checkup',
        'Chest pain and shortness of breath',
        'Severe headache and dizziness',
        'High blood pressure follow-up',
        'Fever and cough for 3 days',
        'Abdominal pain',
        'Annual physical examination',
        'Diabetes management',
        'Back pain',
        'Medication review',
    ]
    
    appointments_data = []
    
    # Create appointments for the past 30 days and next 30 days
    for i in range(40):
        # Random patient and doctor
        if not patient_ids or not doctor_ids:
            print("❌ No patients or doctors available!")
            break
            
        patient_idx = random.randint(0, len(patient_ids) - 1)
        doctor_idx = random.randint(0, len(doctor_ids) - 1)
        
        patient_id = patient_ids[patient_idx]
        doctor_id = doctor_ids[doctor_idx]
        
        # Get patient and doctor names
        c.execute('SELECT fullname FROM users WHERE id = ?', (patient_id,))
        patient_name = c.fetchone()[0]
        
        c.execute('SELECT fullname, specialization FROM users WHERE id = ?', (doctor_id,))
        doctor_data = c.fetchone()
        doctor_name = doctor_data[0]
        department = doctor_data[1]
        
        # Random date between -30 and +30 days from today
        days_offset = random.randint(-30, 30)
        appointment_date = (datetime.now() + timedelta(days=days_offset)).strftime('%Y-%m-%d')
        
        # Random time
        appointment_time = random.choice(times)
        
        # Status based on date
        if days_offset < -5:
            # Past appointments are mostly Completed or Cancelled
            status = random.choice(['Completed', 'Completed', 'Completed', 'Cancelled'])
        elif days_offset < 0:
            # Recent past appointments
            status = random.choice(['Completed', 'Confirmed', 'Cancelled'])
        elif days_offset <= 7:
            # Near future appointments
            status = random.choice(['Confirmed', 'Confirmed', 'Pending'])
        else:
            # Far future appointments
            status = random.choice(['Pending', 'Confirmed'])
        
        symptoms = random.choice(symptoms_list)
        
        notes = ''
        if status == 'Completed':
            notes = 'Examination completed. Patient stable.'
        elif status == 'Cancelled':
            notes = 'Patient requested cancellation.'
        elif status == 'Confirmed':
            notes = 'Appointment confirmed via phone.'
        
        appointments_data.append((
            patient_id, patient_name, doctor_id, doctor_name, department,
            appointment_date, appointment_time, status, symptoms, notes
        ))
    
    # Insert appointments
    for apt_data in appointments_data:
        c.execute('''INSERT INTO appointments 
                    (patient_id, patient_name, doctor_id, doctor_name, department,
                     appointment_date, appointment_time, status, symptoms, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', apt_data)
        print(f"   ✅ Added: {apt_data[1]} → {apt_data[3]} on {apt_data[5]} ({apt_data[7]})")
    
    conn.commit()
    
    # Step 3: Add some patient logs for health reports
    print("\n📊 Adding sample patient health logs...")
    
    conditions = ['None', 'Diabetes', 'Hypertension', 'Asthma', 'Heart Disease']
    symptoms_health = [
        'Routine checkup - no symptoms',
        'Mild fever and headache',
        'Chest discomfort',
        'Shortness of breath',
        'Fatigue and dizziness',
    ]
    
    for i in range(20):
        if not patient_ids:
            break
            
        patient_id = random.choice(patient_ids)
        age = random.randint(18, 75)
        gender = random.choice(['Male', 'Female'])
        sys_bp = random.randint(110, 160)
        dia_bp = random.randint(70, 100)
        hr = random.randint(60, 100)
        temp = round(random.uniform(97.5, 99.5), 1)
        history = random.choice(conditions)
        symptom = random.choice(symptoms_health)
        
        # Determine risk based on vitals
        if sys_bp > 140 or hr > 90 or temp > 99.0:
            xgb_risk = 'HIGH'
            dual_brain_risk = 'HIGH'
            routing = 'Emergency Department'
        elif sys_bp > 130 or hr > 80:
            xgb_risk = 'MEDIUM'
            dual_brain_risk = 'MEDIUM'
            routing = 'Urgent Care'
        else:
            xgb_risk = 'LOW'
            dual_brain_risk = 'LOW'
            routing = 'General Ward'
        
        # Random timestamp in last 60 days
        days_ago = random.randint(0, 60)
        timestamp = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('''INSERT INTO patient_logs 
                    (user_id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, 
                     history, xgb_risk, dual_brain_risk, routing, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (patient_id, age, gender, symptom, sys_bp, dia_bp, hr, temp,
                  history, xgb_risk, dual_brain_risk, routing, timestamp))
    
    conn.commit()
    print(f"   ✅ Added 20 patient health logs")
    
    # Display statistics
    print("\n" + "="*60)
    print("📈 DATABASE STATISTICS")
    print("="*60)
    
    c.execute("SELECT COUNT(*) FROM users WHERE role='patient'")
    patient_count = c.fetchone()[0]
    print(f"👥 Total Patients: {patient_count}")
    
    c.execute("SELECT COUNT(*) FROM users WHERE role='doctor'")
    doctor_count = c.fetchone()[0]
    print(f"👨‍⚕️ Total Doctors: {doctor_count}")
    
    c.execute("SELECT COUNT(*) FROM appointments")
    appointment_count = c.fetchone()[0]
    print(f"📅 Total Appointments: {appointment_count}")
    
    c.execute("SELECT status, COUNT(*) FROM appointments GROUP BY status")
    status_breakdown = c.fetchall()
    print(f"\n📊 Appointment Status Distribution:")
    for status, count in status_breakdown:
        print(f"   {status}: {count}")
    
    c.execute("SELECT COUNT(*) FROM patient_logs")
    log_count = c.fetchone()[0]
    print(f"\n📋 Total Patient Logs: {log_count}")
    
    conn.close()
    
    print("\n✅ Sample data added successfully!")
    print("\n🔐 Login credentials for all users:")
    print("   Password: password123")
    print("\n   Sample Patients:")
    for email, name, _ in sample_patients[:3]:
        print(f"   📧 {email} - {name}")
    print("\n   Sample Doctors:")
    for email, name, _, spec, _, _ in sample_doctors[:3]:
        print(f"   📧 {email} - {name} ({spec})")

if __name__ == '__main__':
    add_sample_data()
