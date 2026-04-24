"""
Assign PHC IDs to Test Users Based on Location Keywords
Uses the same keyword mapping as find_nearest_phc()
"""

import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Keyword mapping - same as in app.py find_nearest_phc()
keyword_mapping = {
    'north': 2, 'south': 3, 'east': 4, 'west': 5, 'rural': 6,
    'central': 1, 'city center': 1, 'main': 1,
}

# Get users needing PHC assignment
users = conn.execute('''
    SELECT id, email, location FROM users
    WHERE location IS NOT NULL AND (phc_id IS NULL OR phc_id = 0)
''').fetchall()

print("=" * 100)
print("ASSIGNING PHC IDs BASED ON LOCATION KEYWORDS")
print("=" * 100)

assigned_count = 0

for user in users:
    user_id = user['id']
    email = user['email']
    location = user['location']

    # Find matching PHC
    assigned_phc = None
    location_lower = location.lower()

    for keyword, phc_id in keyword_mapping.items():
        if keyword in location_lower:
            assigned_phc = phc_id
            print(f"✅ {email:<30} | Location: {location:<25} | Assigned PHC: {phc_id}")
            break

    if assigned_phc is None:
        # Default to PHC 1 (Central)
        assigned_phc = 1
        print(f"⚙️  {email:<30} | Location: {location:<25} | Assigned PHC: 1 (default)")

    # Update user's PHC
    conn.execute('UPDATE users SET phc_id=? WHERE id=?', (assigned_phc, user_id))
    assigned_count += 1

conn.commit()

print("\n" + "=" * 100)
print(f"COMPLETED: Assigned PHC IDs to {assigned_count} users")
print("=" * 100)

conn.close()
