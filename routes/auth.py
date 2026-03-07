"""
Authentication Blueprint
Handles user registration, login, and logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from utils.database import get_db_connection
from utils.validation import UserValidator, ValidationError
from config import get_config

config = get_config()

# Import User class
import sys
sys.path.append('..')
from app import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Basic validation
        try:
            email = UserValidator.validate_email(email)
        except ValidationError as e:
            return render_template('login.html', error=e.message)

        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ? AND role = ?', (email, role)).fetchone()
        conn.close()

        if user_data is None:
            return render_template('login.html', error='Invalid email, password, or role')

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(
                id=user_data['id'],
                email=user_data['email'],
                fullname=user_data['fullname'],
                role=user_data['role'],
                phone=user_data['phone'],
                specialization=user_data['specialization'],
                license=user_data['license'],
                experience=user_data['experience']
            )
            login_user(user, remember=request.form.get('remember'))

            # Redirect based on role
            if user.role == 'doctor':
                return redirect(url_for('dashboard.doctor_dashboard'))
            else:
                return redirect(url_for('dashboard.patient_dashboard'))
        else:
            return render_template('login.html', error='Invalid email, password, or role')

    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if current_user.is_authenticated:
       pass  # Allow signup even if logged in

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        phone = request.form.get('phone')

        # Doctor-specific fields
        specialization = request.form.get('specialization')
        license = request.form.get('license')
        experience = request.form.get('experience')

        # Validate inputs
        try:
            fullname = UserValidator.validate_fullname(fullname)
            email = UserValidator.validate_email(email)
            password = UserValidator.validate_password(password, config.PASSWORD_MIN_LENGTH)
        except ValidationError as e:
            return render_template('signup.html', error=e.message)

        # Check if email already exists
        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE email = ? AND role = ?', (email, role)).fetchone()

        if existing:
            conn.close()
            return render_template('signup.html', error='Email already registered for this role')

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires = datetime.now() + timedelta(hours=24)

        # Hash password and insert user
        password_hash = generate_password_hash(password)

        try:
            conn.execute('''
                INSERT INTO users (email, password_hash, fullname, role, phone,
                                 specialization, license, experience,
                                 verification_token, verification_expires)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, fullname, role, phone,
                  specialization, license, experience,
                  verification_token, verification_expires))
            conn.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.close()
            return render_template('signup.html', error=f'Registration failed: {str(e)}')
        finally:
            conn.close()

    return render_template('signup.html')


@auth_bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user email address"""
    conn = get_db_connection()

    user_data = conn.execute('''
        SELECT * FROM users
        WHERE verification_token = ?
        AND verification_expires > ?
        AND email_verified = 0
    ''', (token, datetime.now())).fetchone()

    if user_data:
        conn.execute('''
            UPDATE users
            SET email_verified = 1, verification_token = NULL
            WHERE id = ?
        ''', (user_data['id'],))
        conn.commit()
        conn.close()

        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    else:
        conn.close()
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('auth.signup'))
