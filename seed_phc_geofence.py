import sqlite3

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Seeding PHCs with realistic coordinates in Trichy area
phc_coords = [
    (1, '10.7905', '78.7047'), # PHC Central
    (2, '10.8200', '78.6900'), # PHC North
    (3, '10.7600', '78.7200'), # PHC South
    (4, '10.7800', '78.7500'), # PHC East
    (5, '10.7700', '78.6700'), # PHC West
    (6, '10.8500', '78.6500'), # PHC Rural
    (7, '10.7300', '78.6800')  # PHC T.Nagar
]

print("Seeding PHC Geofence Anchors...")
for pid, lat, lon in phc_coords:
    c.execute("UPDATE phc_facilities SET lat = ?, lon = ? WHERE id = ?", (lat, lon, pid))

conn.commit()
conn.close()
print("Geofence anchors seeded successfully.")
