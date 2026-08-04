import sqlite3
import os
from werkzeug.security import generate_password_hash

tn_districts = [
    'Chennai', 'Coimbatore', 'Madurai', 'Trichy', 'Salem',
    'Tirunelveli', 'Tiruppur', 'Ranipet', 'Vellore', 'Erode',
    'Thoothukudi', 'Dindigul', 'Thanjavur', 'Kanchipuram',
    'Chengalpattu', 'Karur'
]

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triage.db')
print(f"Connecting to {db_path}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Clear existing ambulances and drivers to prevent duplicates
conn.execute("DELETE FROM ambulances")
conn.execute("DELETE FROM users WHERE role = 'ambulance'")

amb_types = ['Basic Life Support (BLS)', 'Advanced Life Support (ALS)', 'Neonatal Ambulance', 'Basic Life Support (BLS)', 'Advanced Life Support (ALS)']
statuses = ['available', 'available', 'available', 'available', 'in_transit']
locations = ['Central Station', 'North Station', 'South Station', 'East Station', 'West Station']

# Generate password hash once to save time
password_hash = generate_password_hash('password123')

for d_idx, dist in enumerate(tn_districts):
    for i in range(5):
        # Create driver
        driver_email = f'driver_{dist.lower()}_{i}@smarttriage.in'
        driver_name = f'Driver {i+1} ({dist})'
        phone = f'+91-98765{d_idx:02d}{i:03d}'
        
        conn.execute('''
            INSERT INTO users (email, password_hash, fullname, role, phone, created_at, district)
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        ''', (driver_email, password_hash, driver_name, 'ambulance_driver', phone, dist))
        
        driver_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Create ambulance
        veh_no = f'TN-{d_idx:02d}-AT-{1000 + i}'
        conn.execute('''
            INSERT INTO ambulances (ambulance_number, status, vehicle_type, location, current_driver_id, district, driver_name, driver_contact, created_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (veh_no, statuses[i], amb_types[i], locations[i], driver_id, dist, driver_name, phone))

conn.commit()
conn.close()
print("Successfully seeded 5 ambulances and drivers for all 16 districts.")
