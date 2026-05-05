import sqlite3
import os

db_path = 'triage.db'
conn = sqlite3.connect(db_path)

print("Adding Domain Specialists for high-stakes demo...")

# 1. OBGYN for the Kavitha pregnancy case
conn.execute("""
    INSERT OR IGNORE INTO users (fullname, email, password_hash, role, specialization, phc_id, district, is_approved) 
    VALUES ('Dr. Priyadarshini', 'priya.obgyn@demo.com', 'pbkdf2:sha256:260000$demo$demo', 'doctor', 'Obstetrics and Gynecology', 1, 'Chennai', 1)
""")

# 2. Pediatrician for village-level fever outbreaks
conn.execute("""
    INSERT OR IGNORE INTO users (fullname, email, password_hash, role, specialization, phc_id, district, is_approved) 
    VALUES ('Dr. Selvam', 'selvam.peds@demo.com', 'pbkdf2:sha256:260000$demo$demo', 'doctor', 'Pediatrics', 1, 'Chennai', 1)
""")

conn.commit()
conn.close()
print("Domain Specialists Added Successfully")
