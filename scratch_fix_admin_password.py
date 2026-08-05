import sqlite3
from werkzeug.security import generate_password_hash

def fix_karur_admin_password():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    
    # Correctly hash the password
    new_hash = generate_password_hash('password')
    
    cursor.execute('''
        UPDATE users SET password_hash = ? WHERE phone = '9876543333'
    ''', (new_hash,))
    
    conn.commit()
    conn.close()
    print("Karur DDHS Admin password reset to 'password' successfully.")

if __name__ == '__main__':
    fix_karur_admin_password()
