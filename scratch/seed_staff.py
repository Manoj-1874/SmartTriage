import sqlite3
import random
import hashlib

conn = sqlite3.connect('triage.db')
c = conn.cursor()

def hash_password(password):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

default_pwd = hash_password('password123')

# Get all known districts in the database
districts_query = c.execute("SELECT DISTINCT district FROM users WHERE district IS NOT NULL AND district != ''").fetchall()
db_districts = [row[0] for row in districts_query]

# Add some fallback ones just in case
all_districts = list(set(db_districts + ['Karur']))

phc_count = 0
doc_count = 0
nurse_count = 0
specializations = ['General Medicine', 'Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Gynecology']

for dist in all_districts:
    # Check existing PHCs in this district
    existing_phcs = c.execute("SELECT id FROM phc_facilities WHERE district = ?", (dist,)).fetchall()
    phcs_needed = max(0, 10 - len(existing_phcs))
    new_phc_ids = [row[0] for row in existing_phcs]
    
    for i in range(phcs_needed):
        phc_name = f"Govt PHC {dist} - Branch {i+1+len(existing_phcs)}"
        c.execute("""
            INSERT INTO phc_facilities (name, location, district, contact, status)
            VALUES (?, ?, ?, ?, 'ACTIVE')
        """, (phc_name, f"{dist} Block {i+1+len(existing_phcs)}", dist, f"044-2{random.randint(100000, 999999)}"))
        new_phc_ids.append(c.lastrowid)
        phc_count += 1
        
    # Check existing staff
    existing_docs = c.execute("SELECT id FROM users WHERE role = 'doctor' AND district = ?", (dist,)).fetchall()
    existing_nurses = c.execute("SELECT id FROM users WHERE role = 'phc_nurse' AND district = ?", (dist,)).fetchall()
    
    docs_needed = max(0, 10 - len(existing_docs))
    nurses_needed = max(0, 10 - len(existing_nurses))
    
    for i in range(docs_needed):
        doc_name = f"Dr. {random.choice(['Arun', 'Raj', 'Priya', 'Kavya', 'Ramesh', 'Suresh', 'Anita', 'Sunil'])} {random.choice(['Kumar', 'Singh', 'Reddy', 'Verma', 'Sharma', 'Nair'])} {i}"
        email = f"doc_{dist.replace(' ', '').lower()}_{i}_{random.randint(100,999)}@gov.in"
        phc_id = random.choice(new_phc_ids) if new_phc_ids else None
        
        c.execute("""
            INSERT INTO users (email, password_hash, fullname, role, phc_id, district, specialization, experience, is_approved)
            VALUES (?, ?, ?, 'doctor', ?, ?, ?, ?, 1)
        """, (email, default_pwd, doc_name, phc_id, dist, random.choice(specializations), random.randint(3, 25)))
        doc_count += 1
        
    for i in range(nurses_needed):
        nurse_name = f"Nurse {random.choice(['Malar', 'Shanthi', 'Geetha', 'Lakshmi', 'Rani'])} {i}"
        email = f"nurse_{dist.replace(' ', '').lower()}_{i}_{random.randint(100,999)}@gov.in"
        phc_id = random.choice(new_phc_ids) if new_phc_ids else None
        
        c.execute("""
            INSERT INTO users (email, password_hash, fullname, role, phc_id, district, is_approved)
            VALUES (?, ?, ?, 'phc_nurse', ?, ?, 1)
        """, (email, default_pwd, nurse_name, phc_id, dist))
        nurse_count += 1

conn.commit()
conn.close()

print(f"Inserted {phc_count} PHCs, {doc_count} Doctors, {nurse_count} Nurses across {len(all_districts)} districts.")
