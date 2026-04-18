import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create a test DDHS admin user
email = 'test.ddhs@admin.com'
password_hash = generate_password_hash('Test@123456')

try:
    # Check if user exists
    existing = c.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        # Update existing user
        c.execute('''
            UPDATE users
            SET password_hash = ?, role = 'ddhs_admin'
            WHERE email = ?
        ''', (password_hash, email))
        print(f"✅ Updated existing user: {email}")
    else:
        # Insert new user
        c.execute('''
            INSERT INTO users (email, password_hash, fullname, role, phone, email_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, password_hash, 'Test DDHS Admin', 'ddhs_admin', '9999999999', 1))
        print(f"✅ Created new DDHS admin user: {email}")
        print(f"   Password: Test@123456")

    conn.commit()
    print("\n✅ Test account ready. Login with:")
    print(f"   Email: {email}")
    print(f"   Password: Test@123456")
    print(f"   Role: DDHS Admin")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
