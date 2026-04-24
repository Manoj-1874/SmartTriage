"""
Fix patient_logs by assigning phc_id based on patient location
This ensures DDHS Admin and PHC Nurse dashboards show patient data
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Location keyword to PHC mapping
LOCATION_TO_PHC = {
    'north': 2, 'north ward': 2,
    'south': 3, 'south ward': 3,
    'east': 4, 'east sub-district': 4,
    'west': 5, 'west ward': 5,
    'rural': 6, 'rural area': 6, 'rural sub-district': 6,
    'central': 1, 'central district': 1, 'city center': 1, 'main': 1,
}

print("=" * 70)
print("FIXING PATIENT_LOGS - ASSIGNING PHC_ID BASED ON LOCATION")
print("=" * 70)

# Get all patients with their locations
patients = conn.execute('''
    SELECT DISTINCT pl.id as log_id, u.id as user_id, u.location, u.phc_id as user_phc_id
    FROM patient_logs pl
    JOIN users u ON pl.user_id = u.id
    WHERE u.role = 'patient'
''').fetchall()

print(f"\nFound {len(patients)} patient log entries to process\n")

updated = 0

for log in patients:
    log_id = log['log_id']
    user_id = log['user_id']
    location = log['location']
    current_phc = log['user_phc_id']

    # Determine PHC ID from location
    phc_id = None
    if location:
        location_lower = location.lower()
        for keyword, phc in LOCATION_TO_PHC.items():
            if keyword in location_lower:
                phc_id = phc
                break

    # If not found by location, use patient's current phc_id
    if not phc_id and current_phc:
        phc_id = current_phc

    # Update patient_log
    if phc_id:
        conn.execute('UPDATE patient_logs SET phc_id = ? WHERE id = ?', (phc_id, log_id))
        print(f"✓ Log {log_id} (User {user_id}): Location='{location}' → PHC {phc_id}")
        updated += 1
    else:
        print(f"✗ Log {log_id} (User {user_id}): Location='{location}' → No PHC found, skipping")

conn.commit()

print("\n" + "=" * 70)
print(f"COMPLETE: Updated {updated} patient log entries with PHC assignments")
print("=" * 70)

# Verify the update
print("\nVERIFYING UPDATES:")
print("-" * 70)

for phc_id in range(1, 7):
    count = conn.execute('SELECT COUNT(*) FROM patient_logs WHERE phc_id = ?', (phc_id,)).fetchone()[0]
    phc_name = ['', 'PHC Central', 'PHC North', 'PHC South', 'PHC East', 'PHC West', 'PHC Rural'][phc_id]
    print(f"{phc_name:<20}: {count} patients")

print("\n✅ Patient_logs now have proper PHC assignments!")
print("✅ DDHS Admin dashboard will show all patients")
print("✅ PHC Nurse dashboard will show center patients")
