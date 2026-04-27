from app import app, get_db_connection, User, ddhs_admin_resources
from flask_login import login_user
from flask import url_for

with app.test_request_context():
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE role = 'ddhs_admin'").fetchone()
    if not user_row:
        print("No admin found")
        exit(1)
    
    u = User(
        id=user_row['id'],
        email=user_row['email'],
        fullname=user_row['fullname'],
        role=user_row['role'],
        phone=user_row['phone'],
        phc_id=user_row['phc_id'],
        district=user_row['district']
    )
    login_user(u)
    
    try:
        ddhs_admin_resources()
        print("SUCCESS")
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
