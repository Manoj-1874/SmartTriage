import sqlite3
from werkzeug.security import generate_password_hash
import uuid

conn = sqlite3.connect('triage.db')
cursor = conn.cursor()

# Create test patient if not exists
test_email = 'test_patient@example.com'
test_password = 'Test123!@'
hashed_password = generate_password_hash(test_password)

# Check if already exists
cursor.execute('SELECT id FROM users WHERE email = ?', (test_email,))
if cursor.fetchone():
    print(f'Test user {test_email} already exists')
else:
    # Insert test user
    user_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO users (id, email, password_hash, name, role, phone, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 1)
    ''', (user_id, test_email, hashed_password, 'Test Patient', 'patient', '9876543210'))
    conn.commit()
    print(f'Created test user: {test_email} / {test_password}')

conn.close()
