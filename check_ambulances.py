import sqlite3

conn = sqlite3.connect('triage.db')

# Check ambulances schema
print("=== AMBULANCES TABLE SCHEMA ===")
cols = conn.execute("PRAGMA table_info(ambulances)").fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Check ambulances count
print("\n=== AMBULANCES ===")
all_ambulances = conn.execute("SELECT COUNT(*) FROM ambulances").fetchone()[0]
available = conn.execute("SELECT COUNT(*) FROM ambulances WHERE status = 'available'").fetchone()[0]
print(f"Total ambulances: {all_ambulances}")
print(f"Available: {available}")

# If none, create some sample ambulances
if all_ambulances == 0:
    print("\nCreating sample ambulances...")
    for i in range(1, 7):
        conn.execute("""
            INSERT INTO ambulances (ambulance_number, vehicle_type, status, phc_id, capacity)
            VALUES (?, ?, ?, ?, ?)
        """, (f'AMB-{i:03d}', 'Standard', 'available', i, 4))
    conn.commit()
    print("✓ Created 6 ambulances")

# Verify
available_now = conn.execute("SELECT COUNT(*) FROM ambulances WHERE status = 'available'").fetchone()[0]
print(f"\nNow available: {available_now}")

conn.close()
