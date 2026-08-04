import os
import sys
from werkzeug.security import generate_password_hash

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import db_manager

def populate_specialists():
    specialists = [
        {"email": "cardio@smarttriage.phc", "fullname": "Dr. Arun Kumar", "specialization": "Cardiologist", "role": "Doctor", "experience": "12 years"},
        {"email": "neuro@smarttriage.phc", "fullname": "Dr. Lakshmi", "specialization": "Neurologist", "role": "Doctor", "experience": "10 years"},
        {"email": "pulmo@smarttriage.phc", "fullname": "Dr. Siva Rama", "specialization": "Pulmonologist", "role": "Doctor", "experience": "15 years"},
        {"email": "onco@smarttriage.phc", "fullname": "Dr. Priya", "specialization": "Oncologist", "role": "Doctor", "experience": "8 years"},
        {"email": "ortho@smarttriage.phc", "fullname": "Dr. Ramesh", "specialization": "Orthopedic Surgeon", "role": "Doctor", "experience": "20 years"},
        {"email": "derm@smarttriage.phc", "fullname": "Dr. Ayesha", "specialization": "Dermatologist", "role": "Doctor", "experience": "5 years"},
        {"email": "gastro@smarttriage.phc", "fullname": "Dr. Murugan", "specialization": "Gastroenterologist", "role": "Doctor", "experience": "11 years"},
        {"email": "nephro@smarttriage.phc", "fullname": "Dr. Srinivasan", "specialization": "Nephrologist", "role": "Doctor", "experience": "18 years"},
        {"email": "obgyn@smarttriage.phc", "fullname": "Dr. Meena", "specialization": "OB/GYN Specialist", "role": "Doctor", "experience": "14 years"},
        {"email": "optho@smarttriage.phc", "fullname": "Dr. Kavitha", "specialization": "Ophthalmologist", "role": "Doctor", "experience": "9 years"},
        {"email": "pedia@smarttriage.phc", "fullname": "Dr. Vignesh", "specialization": "Pediatrician", "role": "Doctor", "experience": "7 years"},
        {"email": "endo@smarttriage.phc", "fullname": "Dr. Rajesh", "specialization": "Endocrinologist", "role": "Doctor", "experience": "13 years"},
        {"email": "infectious@smarttriage.phc", "fullname": "Dr. Sanjay", "specialization": "Infectious Disease Specialist", "role": "Doctor", "experience": "16 years"},
        {"email": "hema@smarttriage.phc", "fullname": "Dr. Nithya", "specialization": "Hematologist", "role": "Doctor", "experience": "6 years"}
    ]
    
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get a default PHC id for them
        cursor.execute("SELECT id FROM phc_facilities LIMIT 1")
        row = cursor.fetchone()
        phc_id = row['id'] if row else 1
        
        added_count = 0
        for spec in specialists:
            # Check if exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (spec['email'],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (email, password_hash, fullname, role, phc_id, specialization, experience, email_verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    spec['email'],
                    generate_password_hash('doctor123'),
                    spec['fullname'],
                    spec['role'],
                    phc_id,
                    spec['specialization'],
                    spec['experience']
                ))
                added_count += 1
                print(f"Added {spec['specialization']}: {spec['fullname']}")
            else:
                print(f"{spec['specialization']} already exists.")
                
        print(f"Successfully added {added_count} specialist doctors to the database.")

if __name__ == "__main__":
    populate_specialists()
