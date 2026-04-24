import sys
sys.path.insert(0, '/e/Nilal_thiruvila/SmartTriage_Dashboard')

from app import app, current_user
from flask_login import UserMixin
from database import User

# Create a test client
client = app.test_client()

# First, let's test without authentication to see what happens
with app.app_context():
    # Get the user from database directly
    from utils.database import get_db_connection
    conn = get_db_connection()
    user_row = conn.execute('SELECT * FROM users WHERE id = 58').fetchone()
    conn.close()

    if user_row:
        print(f"Found user: {dict(user_row)}")
        # Note: We can't easily test with login_required in this context
        # But we can test the query directly

    # Test the appointments query directly
    conn = get_db_connection()
    appointments_list = conn.execute('''
        SELECT a.*, u.fullname as patient_fullname, u.phone as patient_phone
        FROM appointments a
        LEFT JOIN users u ON a.patient_id = u.id
        WHERE a.patient_id = 58
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
    ''', (58,)).fetchall()

    appointments_list = [dict(row) for row in appointments_list]
    print(f"\nDirect query result: {len(appointments_list)} appointments")
    for apt in appointments_list:
        print(f"  - {apt['id']}: {apt['patient_name']} -> {apt['doctor_name']} ({apt['status']})")

    conn.close()
