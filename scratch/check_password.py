import sqlite3
from werkzeug.security import check_password_hash

def check_pass():
    conn = sqlite3.connect('triage.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT email, password_hash FROM users WHERE email='dr.karurgh@prioritymed.local'")
    user = cursor.fetchone()
    if user:
        is_valid = check_password_hash(user['password_hash'], 'test123')
        print(f"Password 'test123' for {user['email']} is: {is_valid}")
        
        is_valid_default = check_password_hash(user['password_hash'], 'password')
        print(f"Password 'password' for {user['email']} is: {is_valid_default}")
    conn.close()

if __name__ == '__main__':
    check_pass()
