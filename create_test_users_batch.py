"""
Batch Create Test Users with Location-Based PHC Assignment
Tests complete location keyword mapping and role-specific logic
"""

import sqlite3
import hashlib
from datetime import datetime

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Test data: Create patients with all location keywords
test_patients = [
    ("North Ward Patient", "+91-9876543210", "north@test.com", "North Ward", "North123!@#North"),
    ("East Sub-district Patient", "+91-9765432101", "east@test.com", "East Sub-district", "East123!@#East"),
    ("West Ward Patient", "+91-9654321012", "west@test.com", "West Ward", "West123!@#West"),
    ("Rural Area Patient", "+91-9543210123", "rural@test.com", "Rural Area", "Rural123!@#Rural"),
    ("Central District Patient", "+91-9432101234", "central@test.com", "Central District", "Central123!@#Central"),
    ("City Center Patient", "+91-9321012345", "citycenter@test.com", "City Center", "CityCenter123!@#"),
]

# Test data: Create healthcare professionals with locations
test_professionals = [
    ("doctor", "Dr. Rajesh Kumar", "+91-8876543210", "rajesh.doctor@test.com", "North Ward", "Dr.Rajesh123!@#"),
    ("phc_nurse", "Nurse Priya Sharma", "+91-8765432101", "priya.nurse@test.com", "South Ward", "Priya.Nurse123!@#"),
    ("phc_nurse", "Nurse Amit Verma", "+91-8654321012", "amit.nurse@test.com", "East Sub-district", "Amit.Nurse123!@#"),
]

print("=" * 100)
print("CREATING TEST USERS WITH LOCATION-BASED PHC ASSIGNMENT")
print("=" * 100)

created_count = 0
skipped_count = 0

# Create patients
print("\n[PATIENTS]")
print("-" * 100)
for name, phone, email, location, password in test_patients:
    # Check if user already exists
    existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        print(f"⏭️  SKIP: {email} (already exists)")
        skipped_count += 1
        continue

    # Insert patient
    password_hash = hash_password(password)
    conn.execute('''
        INSERT INTO users
        (email, password_hash, fullname, role, phone, location, email_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (email, password_hash, name, 'patient', phone, location, True))

    print(f"✅ CREATED: {email:<25} | Location: {location:<20} | Role: patient")
    created_count += 1

# Create professionals
print("\n[HEALTHCARE PROFESSIONALS]")
print("-" * 100)
for role, name, phone, email, location, password in test_professionals:
    # Check if user already exists
    existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        print(f"⏭️  SKIP: {email} (already exists)")
        skipped_count += 1
        continue

    # Insert professional
    password_hash = hash_password(password)
    conn.execute('''
        INSERT INTO users
        (email, password_hash, fullname, role, phone, location, email_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (email, password_hash, name, role, phone, location, True))

    print(f"✅ CREATED: {email:<25} | Location: {location:<20} | Role: {role}")
    created_count += 1

conn.commit()

print("\n" + "=" * 100)
print(f"SUMMARY: Created {created_count} test users | Skipped {skipped_count} (already exist)")
print("=" * 100)

conn.close()
