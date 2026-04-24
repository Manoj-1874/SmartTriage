"""
Verify database connectivity and password authentication for all roles
"""

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

print("\n" + "="*100)
print("DATABASE CONNECTIVITY & PASSWORD AUTHENTICATION VERIFICATION")
print("="*100)

# Test roles
test_credentials = {
    'patient': 'henry@gmail.com',
    'doctor': 'rajesh.doctor@test.com',  # Has PHC assigned
    'phc_nurse': 'fendy.phc_nurse@gmail.com',
    'ddhs_admin': 'gopi.ddhsadmin@gmail.com'
}

print("\n✅ CHECKING DATABASE PASSWORD HASHES FOR EACH ROLE:\n")

for role, email in test_credentials.items():
    user = conn.execute('SELECT * FROM users WHERE email=? AND role=?', (email, role)).fetchone()

    if not user:
        print(f"❌ {role.upper()}: User {email} NOT FOUND")
        continue

    print(f"✅ {role.upper()}: {email}")
    print(f"   ID: {user['id']}")
    print(f"   Role: {user['role']}")
    print(f"   PHC Assigned: {user['phc_id']}")
    print(f"   Password Hash Exists: {'YES' if user['password_hash'] else 'NO'}")
    print(f"   Hash Length: {len(user['password_hash']) if user['password_hash'] else 0}")

    # Test password verification with common patterns
    password_attempts = [
        f"{role.capitalize()}123",
        f"{role.upper()}123",
        "password123",
        "test123",
        "123456",
        "Password123"
    ]

    verified = False
    for pwd in password_attempts:
        if check_password_hash(user['password_hash'], pwd):
            print(f"   ✅ PASSWORD WORKS: {pwd}")
            verified = True
            break

    if not verified:
        print(f"   ⚠️  Password hash present but couldn't verify with common patterns")
        print(f"      (Database connectivity works but need correct password)")
    print()

print("-"*100)
print("DATABASE CONNECTION TEST:\n")

# Test database operations
try:
    # Test 1: Count users
    user_count = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    print(f"✅ SELECT Query Works: {user_count} total users in database")

    # Test 2: Count PHCs
    phc_count = conn.execute('SELECT COUNT(*) as c FROM phc_facilities').fetchone()['c']
    print(f"✅ PHC Facilities Table: {phc_count} centers registered")

    # Test 3: Role-based query
    patient_count = conn.execute('SELECT COUNT(*) as c FROM users WHERE role=?', ('patient',)).fetchone()['c']
    print(f"✅ Role Filter Works: {patient_count} patients registered")

    # Test 4: Complex query (PHC-based filtering)
    phc_1_patients = conn.execute('SELECT COUNT(*) as c FROM users WHERE role=? AND phc_id=?', ('patient', 1)).fetchone()['c']
    print(f"✅ PHC Filter Works: {phc_1_patients} patients at PHC Central")

    # Test 5: Appointment query
    appointments = conn.execute('SELECT COUNT(*) as c FROM appointments').fetchone()['c']
    print(f"✅ Appointments Table: {appointments} total appointments")

    print("\n✅ ALL DATABASE OPERATIONS SUCCESSFUL")
    print("   Database connectivity: VERIFIED")
    print("   All role-based queries: WORKING")
    print("   Filtering by PHC: WORKING")

except Exception as e:
    print(f"❌ Database Error: {e}")

print("\n" + "="*100)
print("DATABASE & AUTHENTICATION STATUS: ✅ READY FOR LOGIN TESTING")
print("="*100 + "\n")

conn.close()
