import sqlite3
import os
db_path = os.path.join('E:\\Nilal_thiruvila\\SmartTriage_Dashboard', 'triage.db')
conn = sqlite3.connect(db_path)
conn.execute("UPDATE users SET role = 'ambulance_driver' WHERE role = 'ambulance'")
conn.commit()
conn.close()
print('Updated driver roles')
