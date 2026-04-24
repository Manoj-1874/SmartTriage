#!/usr/bin/env python3
"""Create sample health records for patient"""

import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get the patient user (Henry)
patient = c.execute("SELECT id FROM users WHERE email LIKE '%patient%' LIMIT 1").fetchone()
if not patient:
    # Try to find user named Henry
    patient = c.execute("SELECT id FROM users WHERE name = 'Henry' LIMIT 1").fetchone()

if patient:
    patient_id = patient['id']
    print(f"Found patient with ID: {patient_id}")

    # Create 10 sample health records
    base_date = datetime.now() - timedelta(days=90)

    for i in range(10):
        timestamp = base_date + timedelta(days=i*9)
        sys_bp = random.randint(120, 140)
        dia_bp = random.randint(75, 90)
        hr = random.randint(60, 80)
        temp = round(random.uniform(98.0, 99.5), 1)
        risk_level = random.choice(['LOW', 'MEDIUM', 'HIGH'])
        symptom = random.choice(['Fever', 'Cough', 'Headache', 'Fatigue', 'Normal'])

        c.execute('''
            INSERT INTO patient_logs
            (user_id, timestamp, sys_bp, dia_bp, hr, temp, dual_brain_risk, symptoms, age, gender, phc_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, timestamp.isoformat(), sys_bp, dia_bp, hr, temp, risk_level, symptom, 44, 'M', 1))
