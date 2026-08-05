import sqlite3
import hashlib

def create_karur_admin():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    
    # Get a dummy password hash from an existing user
    cursor.execute("SELECT password_hash FROM users WHERE phone = '9876543210' LIMIT 1")
    pass_hash_row = cursor.fetchone()
    if pass_hash_row:
        pass_hash = pass_hash_row[0]
    else:
        # Fallback hash for "password"
        pass_hash = hashlib.sha256('password'.encode()).hexdigest()
    
    # Check if a user with phone 9876543333 already exists
    cursor.execute("SELECT id FROM users WHERE phone = '9876543333'")
    existing_user = cursor.fetchone()
    
    if existing_user:
        cursor.execute('''
            UPDATE users SET district = 'Karur', role = 'ddhs_admin', email = 'karur_admin@smarttriage.gov'
            WHERE phone = '9876543333'
        ''')
        print("Updated existing user 9876543333 to Karur DDHS Admin.")
    else:
        cursor.execute('''
            INSERT INTO users (email, password_hash, fullname, role, phc_id, district, created_at, phone, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, 1)
        ''', ('karur_admin@smarttriage.gov', pass_hash, 'Karur DDHS Admin', 'ddhs_admin', None, 'Karur', '9876543333'))
        print("Created Karur DDHS Admin successfully! Email: karur_admin@smarttriage.gov, Phone: 9876543333")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_karur_admin()
