"""
Get valid test credentials for role verification
"""

import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Get first user from each role
roles = ['patient', 'doctor', 'phc_nurse', 'ddhs_admin']

print("=" * 80)
print("VALID TEST CREDENTIALS FOR ROLE-BASED ACCESS VERIFICATION")
print("=" * 80)

for role in roles:
    user = conn.execute(
        'SELECT email FROM users WHERE role=? LIMIT 1',
        (role,)
    ).fetchone()

    if user:
        print(f"\n{role.upper()}:")
        print(f"  Email: {user['email']}")
        print(f"  Password: (check with user registration)")

# Get recently created users with locations (for location-based signup testing)
recent_users = conn.execute('''
    SELECT email, role, location FROM users
    WHERE location IS NOT NULL AND location != ""
    ORDER BY id DESC LIMIT 5
''').fetchall()

print("\n" + "=" * 80)
print("RECENTLY CREATED USERS (WITH LOCATIONS)")
print("=" * 80)

for user in recent_users:
    print(f"\nEmail: {user['email']}")
    print(f"  Role: {user['role']}")
    print(f"  Location: {user['location']}")
    print(f"  Password: (from creation - e.g., {user['role'].capitalize()}123!@#{user['role'].capitalize()})")

conn.close()
