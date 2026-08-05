import sqlite3

def find_karur_doctor():
    conn = sqlite3.connect('triage.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if there is any doctor with district='Karur' or associated PHC has district='Karur'
    cursor.execute("""
        SELECT u.id, u.email, u.fullname, u.role, p.district as phc_district, u.district as u_district 
        FROM users u 
        LEFT JOIN phc_facilities p ON u.phc_id = p.id 
        WHERE u.role = 'doctor' 
        AND (u.district = 'Karur' OR p.district = 'Karur' OR p.district LIKE '%Karur%')
        LIMIT 5;
    """)
    
    doctors = cursor.fetchall()
    
    if doctors:
        for doc in doctors:
            print(f"Doctor Found: Email={doc['email']}, Name={doc['fullname']}, PHC District={doc['phc_district']}, User District={doc['u_district']}")
    else:
        print("No Karur doctor found. Searching for any doctor with 'Karur' in their name...")
        cursor.execute("SELECT email, fullname FROM users WHERE role='doctor' AND fullname LIKE '%Karur%';")
        doc_by_name = cursor.fetchall()
        for doc in doc_by_name:
            print(f"Name Match: {doc['fullname']} ({doc['email']})")
            
        print("Here are 3 random doctors:")
        cursor.execute("SELECT email, fullname, district FROM users WHERE role='doctor' LIMIT 3;")
        for doc in cursor.fetchall():
            print(f"- {doc['fullname']} ({doc['email']}) - District: {doc['district']}")

    conn.close()

if __name__ == '__main__':
    find_karur_doctor()
