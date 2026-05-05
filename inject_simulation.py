import sqlite3
import os

db_path = 'triage.db'
if not os.path.exists(db_path):
    print("Database not found")
else:
    conn = sqlite3.connect(db_path)
    # Chennai Simulation
    conn.execute("INSERT OR IGNORE INTO ambulances (ambulance_number, district, status, location_lat, location_lon) VALUES ('TN-01-AMB-2024', 'Chennai', 'available', 13.0827, 80.2707)")
    conn.execute("INSERT OR IGNORE INTO ambulances (ambulance_number, district, status, location_lat, location_lon) VALUES ('TN-01-EMR-9999', 'Chennai', 'on_mission', 13.0475, 80.2322)")
    
    # Trichy Simulation (in case district is Trichy)
    conn.execute("INSERT OR IGNORE INTO ambulances (ambulance_number, district, status, location_lat, location_lon) VALUES ('TN-45-AMB-108', 'Trichy', 'available', 10.7905, 78.7047)")
    conn.execute("INSERT OR IGNORE INTO ambulances (ambulance_number, district, status, location_lat, location_lon) VALUES ('TN-45-FAST-01', 'Trichy', 'on_mission', 10.8210, 78.6811)")
    
    conn.commit()
    conn.close()
    print("Simulation Fleet Injected Successfully")
