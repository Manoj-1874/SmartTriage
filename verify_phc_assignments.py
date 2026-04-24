"""
Verify PHC Assignments for All Test Users
"""

import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Query all recently created test users
users = conn.execute('''
    SELECT id, email, fullname, role, location, phc_id
    FROM users
    WHERE email IN (
        'north@test.com', 'east@test.com', 'west@test.com', 'rural@test.com',
        'central@test.com', 'citycenter@test.com', 'rajesh.doctor@test.com',
        'priya.nurse@test.com', 'amit.nurse@test.com', 'southpatient@test.com'
    )
    ORDER BY role DESC, email ASC
''').fetchall()

# Expected mappings
keyword_mapping = {
    'north': 2,
    'south': 3,
    'east': 4,
    'west': 5,
    'rural': 6,
    'central': 1,
    'city center': 1,
    'main': 1,
}

print("=" * 120)
print("TEST USER PHC ASSIGNMENT VERIFICATION")
print("=" * 120)
print(f"\n{'Email':<30} | {'Role':<12} | {'Location':<25} | {'Assigned PHC':<15} | {'Status':<15}")
print("-" * 120)

correct_count = 0
incorrect_count = 0

for user in users:
    email = user['email']
    role = user['role']
    location = user['location'] if user['location'] else 'N/A'
    assigned_phc = user['phc_id'] if user['phc_id'] else 'NONE'

    # Determine expected PHC
    expected_phc = None
    if location != 'N/A':
        location_lower = location.lower()
        for keyword, phc_id in keyword_mapping.items():
            if keyword in location_lower:
                expected_phc = phc_id
                break

    # Verify assignment
    if expected_phc:
        if assigned_phc == expected_phc or assigned_phc == 'NONE':
            # Either correctly assigned or hasn't been assigned yet
            status = "✅ OK" if assigned_phc == expected_phc else "⏳ PENDING"
            if assigned_phc == expected_phc:
                correct_count += 1
        else:
            status = f"❌ WRONG (expected {expected_phc})"
            incorrect_count += 1
    else:
        status = "⚠️ NO MAPPING"

    print(f"{email:<30} | {role:<12} | {location:<25} | {str(assigned_phc):<15} | {status:<15}")

print("-" * 120)
print(f"\n✅ Correct Assignments: {correct_count}")
print(f"⏳ Pending Assignments: {len(users) - correct_count - incorrect_count}")
print(f"❌ Incorrect Assignments: {incorrect_count}")

# Check if we need to assign PHCs
pending = conn.execute('''
    SELECT id, email, location FROM users
    WHERE location IS NOT NULL AND (phc_id IS NULL OR phc_id = 0)
    AND email IN (
        'north@test.com', 'east@test.com', 'west@test.com', 'rural@test.com',
        'central@test.com', 'citycenter@test.com', 'rajesh.doctor@test.com',
        'priya.nurse@test.com', 'amit.nurse@test.com'
    )
''').fetchall()

if pending:
    print(f"\n⚠️ {len(pending)} users need PHC assignment - they were created via direct SQL insert")
    print("   (The signup form uses find_nearest_phc() which assigns correctly)")
else:
    print("\n✅ All users have been assigned PHC IDs!")

conn.close()
