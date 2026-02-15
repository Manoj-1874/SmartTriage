import sqlite3

# Connect to database
conn = sqlite3.connect('triage.db')
cursor = conn.cursor()

# Email to delete
email_to_delete = 'administrator@gmail.com'

# First, check if the account exists
cursor.execute("SELECT id, email, fullname, role FROM users WHERE email=?", (email_to_delete,))
user = cursor.fetchone()

if user:
    print(f"Found account:")
    print(f"  ID: {user[0]}")
    print(f"  Email: {user[1]}")
    print(f"  Name: {user[2]}")
    print(f"  Role: {user[3]}")
    print()
    
    # Delete the account
    cursor.execute("DELETE FROM users WHERE email=?", (email_to_delete,))
    conn.commit()
    
    print(f"✅ Account deleted successfully!")
    print(f"Deleted {cursor.rowcount} account(s)")
else:
    print(f"❌ No account found with email: {email_to_delete}")

conn.close()
