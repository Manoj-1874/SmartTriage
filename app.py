from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, g, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
import numpy as np
import joblib
from transformers import pipeline
from huggingface_hub import hf_hub_download
import os
import sys
import warnings
from datetime import datetime, timedelta
import secrets
import smtplib
from email.message import EmailMessage
import logging
from logging.handlers import RotatingFileHandler
import atexit
from functools import wraps
from contextlib import contextmanager
import time

# Version Marker for Debugging
logger = logging.getLogger(__name__)
logger.info(f"🚀 [STARTUP-V2.5-STABLE] !!! AG-WAS-HERE !!! Running from: {os.path.abspath(__file__)}")

# Import configuration and utilities
import utils.integrated_dual_brain_risk
import utils.universal_disease_knowledge
logger.info(f"📁 [PATH-CHECK] integrated_dual_brain_risk: {utils.integrated_dual_brain_risk.__file__}")
logger.info(f"📁 [PATH-CHECK] universal_disease_knowledge: {utils.universal_disease_knowledge.__file__}")

from config import get_config
from utils.validation import VitalSignsValidator, UserValidator, ValidationError
from utils.database import DatabaseManager, get_db_connection
from utils.security import (
    SecurityHeaders, RequestTracking, AuditLogger, InputSanitizer,
    require_role, audit_action, PasswordPolicy, generate_secure_token
)
from utils.monitoring import health_bp
from utils.integrated_dual_brain_risk import IntegratedDualBrainRisk
from utils.disease_database import LocalDiseaseDatabase
from utils.appointment_routes import appointments_bp
from utils.websocket_events import init_socketio
from utils.reminder_scheduler import start_reminder_scheduler, stop_reminder_scheduler

warnings.filterwarnings('ignore')

# ===================================
# LOGGING CONFIGURATION
# ===================================
def setup_logging(app_config):
    """Configure comprehensive logging for the application"""
    log_level = logging.DEBUG if app_config.DEBUG else logging.INFO
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s: %(message)s'
    )

    # Console handler with UTF-8 encoding support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    # Force UTF-8 encoding on Windows to handle emojis
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    # File handler with rotation and UTF-8 encoding
    os.makedirs('logs', exist_ok=True)
    file_handler = RotatingFileHandler(
        'logs/smarttriage.log',
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # Error file handler with UTF-8 encoding
    error_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates on reload
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Prevent Flask's default logger from propagating and causing duplicates
    app.logger.propagate = False
    app.logger.setLevel(log_level)
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)

    # Suppress verbose third-party logs
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    app.logger.info(f"Logging configured - Level: {logging.getLevelName(log_level)}")

# ===================================
# FLASK APP INITIALIZATION
# ===================================
# Initialize Flask app with configuration
app = Flask(__name__)
config = get_config()
app.config.from_object(config)
app.secret_key = config.SECRET_KEY

# Store application start time for uptime tracking
app.config['START_TIME'] = time.time()
app.config['VERSION'] = config.VERSION

# Setup logging
setup_logging(config)

# [CRITICAL DEBUG] Startup Verification and Path Check
logger.info("="*80)
logger.info(f"🚀 [STARTUP-V2.5-STABLE] !!! AG-WAS-HERE !!!")
logger.info(f"📍 Main App Path: {os.path.abspath(__file__)}")
import utils.integrated_dual_brain_risk
import utils.universal_disease_knowledge
logger.info(f"📁 Module Path (Integrated): {utils.integrated_dual_brain_risk.__file__}")
logger.info(f"📁 Module Path (Universal): {utils.universal_disease_knowledge.__file__}")
logger.info("="*80)
app.logger.info(f"Starting SmartTriage Dashboard v{config.VERSION} - Environment: {config.ENV}")

# Initialize CORS if enabled
if config.CORS_ENABLED:
    CORS(app, origins=config.CORS_ORIGINS)
    app.logger.info(f"CORS enabled for origins: {config.CORS_ORIGINS}")

# Rate limiting disabled for production deployment
# Allows unlimited registration for high user volume
app.logger.info("Rate limiting disabled - Production mode enabled for unlimited user registration")

# Initialize security middleware
if config.SECURITY_HEADERS_ENABLED:
    security_headers = SecurityHeaders(app)
    app.logger.info("Security headers middleware enabled")

# Initialize request tracking
if config.REQUEST_ID_ENABLED:
    request_tracking = RequestTracking(app)
    app.logger.info("Request ID tracking enabled")

# Initialize audit logging
if config.AUDIT_LOGGING_ENABLED:
    audit_logger = AuditLogger(app)
    app.extensions['audit_logger'] = audit_logger
    app.logger.info("Audit logging enabled")

# Register health check blueprint
app.register_blueprint(health_bp)
app.logger.info("Health check endpoints registered at /health/*")

# Register appointment management blueprint
app.register_blueprint(appointments_bp)
app.logger.info("Appointment management endpoints registered at /appointments/*")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 1. DATABASE & MODEL PATHS ---
# Use forward slashes to prevent Python from reading \t as a tab!
DB_PATH = 'triage.db'

# Hugging Face Repository Configuration
HF_REPO_ID = config.HF_REPO_ID
USE_HUGGINGFACE = config.USE_HUGGINGFACE

# Local paths (fallback)
MODEL_DIR = config.MODEL_DIR
STABLE_MODEL_PATH = config.STABLE_MODEL_PATH

# Initialize database manager with thread-safe connection pooling
db_manager = DatabaseManager(config)
app.logger.info("Database manager initialized with connection pooling")

# Initialize WebSocket server for real-time updates
try:
    init_socketio(app)
    app.logger.info("[OK] WebSocket server initialized for real-time notifications")
except Exception as e:
    app.logger.warning(f"[WARN] WebSocket initialization failed (real-time features disabled): {e}")

# Start background reminder scheduler
try:
    start_reminder_scheduler()
    app.logger.info("[OK] Appointment reminder scheduler started")
except Exception as e:
    app.logger.warning(f"[WARN] Reminder scheduler failed: {e}")

# Initialize local disease database (Offline-First Layer)
try:
    LocalDiseaseDatabase.init_database()
    stats = LocalDiseaseDatabase.get_statistics()
    app.logger.info(f"[OK] Local disease database ready: {stats['total_diseases']} diseases by severity: {stats['by_severity']}")
except Exception as e:
    app.logger.warning(f"[WARN] Could not initialize local disease database: {e}")

# Register cleanup on shutdown
@atexit.register
def cleanup_on_exit():
    """Cleanup resources on application shutdown"""
    try:
        app.logger.info("Shutting down SmartTriage Dashboard...")
    except (ValueError, OSError):
        # Logger handlers may be closed; skip logging
        pass
    db_manager.cleanup()
    try:
        app.logger.info("Cleanup completed")
    except (ValueError, OSError):
        # Logger handlers may be closed; skip logging
        pass

# ===================================
# ERROR HANDLERS
# ===================================
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    app.logger.warning(f"404 error: {request.url}")
    return render_template('error.html',
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.error(f"500 error: {str(error)}", exc_info=True)
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

# 429 error handler removed - rate limiting disabled for production

@app.errorhandler(429)
def ratelimit_error(error):
    """Rate limit handler (disabled)"""
    if request.endpoint == 'forgot_password':
        return render_template(
            'forgot_password.html',
            error='Too many reset requests. Please wait and try again later.'
        ), 429

    if request.endpoint == 'reset_password':
        token = request.args.get('token') or request.form.get('token')
        return render_template(
            'reset_password.html',
            token=token,
            error='Too many reset attempts. Please wait and try again later.'
        ), 429

    if request.endpoint == 'verify_reset_code':
        email = request.form.get('email')
        return render_template(
            'verify_reset_code.html',
            email=email,
            error='Too many code verification attempts. Please wait and try again later.'
        ), 429

    if request.endpoint == 'resend_reset_code':
        email = request.form.get('email')
        return render_template(
            'verify_reset_code.html',
            email=email,
            error='Too many resend requests. Please wait and try again later.'
        ), 429

    return render_template('error.html',
                         error_code=429,
                         error_message="Too many requests. Please try again later."), 429

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle unexpected exceptions"""
    app.logger.error(f"Unexpected error: {str(error)}", exc_info=True)
    if config.DEBUG:
        raise error
    return render_template('error.html',
                         error_code=500,
                         error_message="An unexpected error occurred"), 500

# ===================================
# UTILITY DECORATORS
# ===================================
def handle_db_errors(f):
    """Decorator to handle database errors gracefully"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            app.logger.error(f"Database error in {f.__name__}: {str(e)}", exc_info=True)
            flash("Database error occurred. Please try again later.", "error")
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for('index'))
    return decorated_function

# --- 2. USER CLASS FOR FLASK-LOGIN ---
class User(UserMixin):
    def __init__(self, id, email, fullname, role, phone, specialization=None, license=None, experience=None, phc_id=None):
        self.id = id
        self.email = email
        self.fullname = fullname
        self.role = role
        self.phone = phone
        self.specialization = specialization
        self.license = license
        self.experience = experience
        self.phc_id = phc_id

@login_manager.user_loader
def load_user(user_id):
    """Load user from database (thread-safe)"""
    try:
        with db_manager.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_data = c.fetchone()

            if user_data:
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    fullname=user_data['fullname'],
                    role=user_data['role'],
                    phone=user_data['phone'],
                    specialization=user_data['specialization'],
                    license=user_data['license'],
                    experience=user_data['experience'],
                    phc_id=user_data['phc_id'] if 'phc_id' in user_data.keys() else None
                )
    except Exception as e:
        app.logger.error(f"Error loading user {user_id}: {str(e)}", exc_info=True)
    return None

# --- 3. INITIALIZE DATABASE ---
def init_db():
    """Initialize database with thread-safe connection"""
    app.logger.info("Initializing database...")
    with db_manager.get_connection() as conn:
        c = conn.cursor()

        # Users table
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL,
            phc_id INTEGER,
            phone TEXT,
            specialization TEXT,
            license TEXT,
            experience INTEGER,
            email_verified INTEGER DEFAULT 0,
            verification_token TEXT,
            verification_expires DATETIME,
            reset_code TEXT,
            reset_token TEXT,
            reset_expires DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
        # Ensure new verification columns exist on older DBs
        c.execute("PRAGMA table_info(users)")
        existing_user_cols = [col[1] for col in c.fetchall()]
        try:
            if 'email_verified' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
                print("🔧 Added 'email_verified' column to users table")
            if 'verification_token' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
                print("🔧 Added 'verification_token' column to users table")
            if 'verification_expires' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN verification_expires DATETIME")
                print("🔧 Added 'verification_expires' column to users table")
            if 'reset_token' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
                print("🔧 Added 'reset_token' column to users table")
            if 'reset_code' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN reset_code TEXT")
                print("🔧 Added 'reset_code' column to users table")
            if 'reset_expires' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN reset_expires DATETIME")
                print("🔧 Added 'reset_expires' column to users table")
            if 'phc_id' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN phc_id INTEGER")
                print("🔧 Added 'phc_id' column to users table")
            if 'location' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN location TEXT")
                print("[OK] Added 'location' column to users table")
            if 'assigned_nurse_id' not in existing_user_cols:
                c.execute("ALTER TABLE users ADD COLUMN assigned_nurse_id INTEGER")
                print("🔧 Added 'assigned_nurse_id' column to users table")
        except Exception as e:
            print(f"[WARN] Could not alter users table: {e}")

        # PHC facilities table
        c.execute('''
            CREATE TABLE IF NOT EXISTS phc_facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                contact TEXT,
                status TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Staff attendance table
        c.execute('''
            CREATE TABLE IF NOT EXISTS staff_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                phc_id INTEGER NOT NULL,
                check_in_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Present' CHECK(status IN ('Present', 'Absent')),
                geo_location TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (phc_id) REFERENCES phc_facilities(id)
            )
        ''')

        # Patient logs table
        c.execute('''
            CREATE TABLE IF NOT EXISTS patient_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phc_id INTEGER,
                age INTEGER, gender TEXT, symptoms TEXT,
                sys_bp INTEGER, dia_bp INTEGER, hr INTEGER,
                temp REAL, respiration_rate INTEGER, spo2 INTEGER, history TEXT,
                xgb_risk TEXT, dual_brain_risk TEXT, routing TEXT, recommended_specialist TEXT,
                risk_score INTEGER, news2_score INTEGER,
                actual_outcome TEXT,
                outcome_confirmed_by INTEGER,
                outcome_confirmed_at DATETIME,
                outcome_notes TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (phc_id) REFERENCES phc_facilities(id),
                FOREIGN KEY (outcome_confirmed_by) REFERENCES users(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS model_monitoring_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_log_id INTEGER,
                xgb_risk TEXT,
                final_risk TEXT,
                xgb_low_prob REAL,
                xgb_medium_prob REAL,
                xgb_high_prob REAL,
                bert_label TEXT,
                bert_score REAL,
                news2_score INTEGER,
                override_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_log_id) REFERENCES patient_logs(id)
            )
        ''')

        # Check if appointments table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        appointments_exists = c.fetchone() is not None

        if not appointments_exists:
            # Create appointments table with correct schema for fresh database
            print("[TABLE] Creating appointments table...")
            c.execute('''
                CREATE TABLE appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    patient_name TEXT NOT NULL,
                    doctor_id INTEGER,
                    doctor_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TEXT NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    symptoms TEXT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES users(id),
                    FOREIGN KEY (doctor_id) REFERENCES users(id)
                )
            ''')
            print("[OK] Appointments table created!")
        else:
            # Check if appointments table needs migration
            c.execute("PRAGMA table_info(appointments)")
            columns = [column[1] for column in c.fetchall()]

            if 'doctor_id' not in columns:
                # Need to migrate old appointments table
                print("[MIGRATE] Migrating appointments table to new schema...")

                # Get the old table columns
                c.execute("PRAGMA table_info(appointments)")
                old_columns = [column[1] for column in c.fetchall()]
                print(f"   Old columns: {old_columns}")

                # Rename old table
                c.execute("ALTER TABLE appointments RENAME TO appointments_old")

                # Create new table with correct schema
                c.execute('''
                    CREATE TABLE appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER NOT NULL,
                        patient_name TEXT NOT NULL,
                        doctor_id INTEGER,
                        doctor_name TEXT NOT NULL,
                        department TEXT NOT NULL,
                        appointment_date DATE NOT NULL,
                        appointment_time TEXT NOT NULL,
                        status TEXT DEFAULT 'Pending',
                        symptoms TEXT,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (patient_id) REFERENCES users(id),
                        FOREIGN KEY (doctor_id) REFERENCES users(id)
                    )
                ''')

                # Copy data from old table (only columns that exist)
                # Use 0 as default patient_id for old records
                if 'patient_id' in old_columns:
                    # Old table has patient_id
                    c.execute('''
                        INSERT INTO appointments
                        (id, patient_id, patient_name, doctor_name, department, appointment_date,
                         appointment_time, status, symptoms, notes, created_at)
                        SELECT
                            id, COALESCE(patient_id, 0), patient_name, doctor_name, department, appointment_date,
                            appointment_time, status, symptoms, notes, created_at
                        FROM appointments_old
                    ''')
                else:
                    # Old table doesn't have patient_id, use default value 0
                    c.execute('''
                        INSERT INTO appointments
                        (patient_id, patient_name, doctor_name, department, appointment_date,
                         appointment_time, status, symptoms, notes, created_at)
                        SELECT
                            0, patient_name, doctor_name, department, appointment_date,
                            appointment_time, status, symptoms, notes, created_at
                        FROM appointments_old
                    ''')

                # Drop old table
                c.execute("DROP TABLE appointments_old")

                print("[OK] Migration completed!")
            else:
                # Table already has correct schema, no migration needed
                print("[OK] Appointments table already up-to-date")

        # Check if patient_logs table needs migration for user_id column
        c.execute("PRAGMA table_info(patient_logs)")
        pl_columns = [column[1] for column in c.fetchall()]

        if 'user_id' not in pl_columns:
            print("[MIGRATE] Migrating patient_logs table to add user_id column...")
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN user_id INTEGER")
                print("[OK] Added user_id column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Column might already exist: {e}")
        if 'phc_id' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN phc_id INTEGER")
                print("[OK] Added phc_id column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add phc_id: {e}")
        if 'recommended_specialist' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN recommended_specialist TEXT")
                print("[OK] Added recommended_specialist column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add recommended_specialist: {e}")
        if 'risk_score' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN risk_score INTEGER")
                print("[OK] Added risk_score column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add risk_score: {e}")
        if 'respiration_rate' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN respiration_rate INTEGER")
                print("[OK] Added respiration_rate column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add respiration_rate: {e}")
        if 'spo2' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN spo2 INTEGER")
                print("[OK] Added spo2 column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add spo2: {e}")
        if 'news2_score' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN news2_score INTEGER")
                print("[OK] Added news2_score column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add news2_score: {e}")
        if 'actual_outcome' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN actual_outcome TEXT")
                print("[OK] Added actual_outcome column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add actual_outcome: {e}")
        if 'outcome_confirmed_by' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN outcome_confirmed_by INTEGER")
                print("[OK] Added outcome_confirmed_by column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add outcome_confirmed_by: {e}")
        if 'outcome_confirmed_at' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN outcome_confirmed_at DATETIME")
                print("[OK] Added outcome_confirmed_at column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add outcome_confirmed_at: {e}")
        if 'outcome_notes' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN outcome_notes TEXT")
                print("[OK] Added outcome_notes column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add outcome_notes: {e}")

        # NEW: Add pain_intensity and symptom_duration columns
        if 'pain_intensity' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN pain_intensity INTEGER")
                print("[OK] Added pain_intensity column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add pain_intensity: {e}")

        if 'symptom_duration' not in pl_columns:
            try:
                c.execute("ALTER TABLE patient_logs ADD COLUMN symptom_duration TEXT")
                print("[OK] Added symptom_duration column to patient_logs table")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Could not add symptom_duration: {e}")

        # Create messages table for doctor-patient communication
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        ''')

        # Create ambulances table for district-level ambulance management
        c.execute('''
            CREATE TABLE IF NOT EXISTS ambulances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ambulance_number TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'available' CHECK(status IN ('available', 'allocated', 'maintenance')),
                location TEXT,
                driver_name TEXT,
                driver_contact TEXT,
                capacity INTEGER DEFAULT 4,
                phc_assigned_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (phc_assigned_id) REFERENCES phc_facilities(id)
            )
        ''')

        conn.commit()
        app.logger.info("[OK] Database initialization complete")


def init_sample_phc_centers():
    """Initialize sample PHC facilities with status tracking if they don't exist"""
    try:
        conn = get_db_connection()
        existing = conn.execute('SELECT COUNT(*) as count FROM phc_facilities').fetchone()
        count = existing['count'] if isinstance(existing, dict) else existing[0] if existing else 0

        if count == 0:
            # Add sample PHC centers - all initialized as ACTIVE
            # Real-world: These represent actual Primary Health Centers in the district
            sample_centers = [
                ('PHC Central', 'City Center, Main District', 'ACTIVE'),
                ('PHC North', 'North Ward, Main District', 'ACTIVE'),
                ('PHC South', 'South Ward, Main District', 'ACTIVE'),
                ('PHC East', 'East Ward, Main District', 'ACTIVE'),
                ('PHC West', 'West Ward, Main District', 'ACTIVE'),
                ('PHC Rural', 'Rural Sub-district, Main District', 'ACTIVE'),
            ]

            for name, location, status in sample_centers:
                conn.execute('''
                    INSERT INTO phc_facilities (name, location, contact, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                ''', (name, location, '+91-9999-000000', status))

            conn.commit()
            app.logger.info(f"[OK] Initialized {len(sample_centers)} sample PHC centers with ACTIVE status")
        else:
            app.logger.info(f"[OK] PHC centers already exist ({count} centers found)")

        conn.close()
    except Exception as e:
        app.logger.warning(f"Could not initialize sample PHC centers: {str(e)}")


# Ensure database is initialized on startup
try:
    init_db()
    init_sample_phc_centers()
except Exception as e:
    app.logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
    sys.exit(1)

# --- 3. LOAD DUAL-BRAIN MODELS ---
app.logger.info("[STARTUP] Loading SmartTriage Dual-Brain Engine...")

# Set environment variable to reduce OpenBLAS memory usage
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

def load_models_from_huggingface():
    """Load models from Hugging Face Hub"""
    print("[DOWNLOAD] Loading models from Hugging Face Hub...")
    try:
        # Download the pickle file containing XGBoost models
        local_model_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename="triage_assets_mingled.pkl",
            cache_dir="./hf_cache"
        )

        # Load the assets
        assets = joblib.load(local_model_path)
        encoders = assets['encoders']
        xgb_risk_model = assets.get('risk_model') or assets.get('xgb_model')  # Handle both key names
        scaler = assets['scaler']
        feature_names = assets.get('features') or assets.get('feature_names')  # Handle both key names

        # Load BERT model from Hugging Face
        exp_brain = pipeline(
            "text-classification",
            model=HF_REPO_ID,
            tokenizer=HF_REPO_ID
        )

        print("[OK] Models loaded from Hugging Face Hub successfully!")
        return encoders, xgb_risk_model, scaler, feature_names, exp_brain

    except Exception as e:
        print(f"❌ Failed to load from Hugging Face: {e}")
        raise

def load_models_locally():
    """Load models from local files"""
    print("[LOAD] Loading models from local storage...")
    try:
        # Load XGBoost and preprocessing models
        assets = joblib.load(STABLE_MODEL_PATH)
        encoders = assets['encoders']
        xgb_risk_model = assets.get('risk_model') or assets.get('xgb_model')  # Handle both key names
        scaler = assets['scaler']
        feature_names = assets.get('features') or assets.get('feature_names')  # Handle both key names
        print("[OK] XGBoost models loaded successfully")

        # Try to load BERT model
        try:
            exp_brain = pipeline("text-classification", model=MODEL_DIR, tokenizer=MODEL_DIR)
            print("[OK] BERT model loaded successfully")
        except Exception as bert_error:
            print(f"[WARNING] Failed to load BERT model: {bert_error}")
            print("[INFO] Running with XGBoost only (text analysis disabled)")
            exp_brain = None

        return encoders, xgb_risk_model, scaler, feature_names, exp_brain
    except Exception as e:
        print(f"[ERROR] Failed to load models: {e}")
        raise

try:
    # Try loading from Hugging Face if enabled, otherwise use local files
    if USE_HUGGINGFACE:
        encoders, xgb_risk_model, scaler, feature_names, exp_brain = load_models_from_huggingface()
    else:
        encoders, xgb_risk_model, scaler, feature_names, exp_brain = load_models_locally()

    logger.info("[OK] System 1 (XGBoost) & System 2 (Shadow Brain) Online.")

    # Initialize integrated dual-brain risk assessment system
    try:
        integrated_risk = IntegratedDualBrainRisk(
            xgb_model=xgb_risk_model,
            scaler=scaler,
            feature_names=feature_names,
            bert_model=exp_brain
        )
        logger.info("[OK] System 3 (Integrated Dual-Brain) Online - Ready for disease recognition + BERT + XGBoost fusion.")
    except Exception as e:
        logger.error(f"[WARNING] Integrated risk system error: {e}")
        integrated_risk = None

    # Initialize semantic disease database for local recognition
    try:
        from utils.medical_ai_knowledge_system import SemanticDiseaseDatabase
        local_disease_db = SemanticDiseaseDatabase()
        logger.info("[OK] Local Disease Database (15+ diseases) loaded for fast recognition.")
    except Exception as e:
        logger.error(f"[WARNING] Local disease database failed to load: {e}")
        local_disease_db = None

except Exception as e:
    logger.error(f"[CRITICAL] Model load error, running in UI-only mode: {e}")
    # Create dummy models for UI testing if loading fails
    xgb_risk_model = None
    exp_brain = None
    encoders = None
    scaler = None
    feature_names = []
    integrated_risk = None

# --- 4. HELPER FUNCTIONS (Thread-Safe) ---

def assign_nurse_to_patient(conn, phc_id):
    """Find the nurse with fewest assigned patients at a PHC and return their ID."""
    if not phc_id:
        return None
    
    # Get all nurses at this PHC
    nurses = conn.execute("SELECT id FROM users WHERE role = 'phc_nurse' AND phc_id = ?", (phc_id,)).fetchall()
    if not nurses:
        return None
        
    # Find nurse with fewest patients
    nurse_counts = []
    for nurse in nurses:
        count = conn.execute("SELECT COUNT(*) as count FROM users WHERE assigned_nurse_id = ?", (nurse['id'],)).fetchone()['count']
        nurse_counts.append((nurse['id'], count))
    
    # Sort by count and pick the one with fewest
    nurse_counts.sort(key=lambda x: x[1])
    return nurse_counts[0][0]

def find_nearest_phc(conn, patient_location, prefer_active=True):

    """
    Find nearest PHC facility based on patient location with intelligent fallback.
    REAL-WORLD HEALTHCARE LOGIC:
    - Match location keywords to PHC service areas
    - If preferred PHC is INACTIVE/MAINTENANCE, cascade to next nearest ACTIVE PHC
    - Fallback chain: ACTIVE > MAINTENANCE > INACTIVE

    This implements geographic/service-area nearest-neighbor with status awareness.
    Example: Patient in "South Ward" → PHC South (3), but if inactive → fallback to PHC Central (1)

    Args:
        conn: Database connection
        patient_location: Patient's location/address (string)
        prefer_active: If True, prioritize ACTIVE centers; if False, use any center

    Returns:
        phc_id (int) of nearest PHC, with intelligent fallback logic
    """
    if not patient_location:
        # No location provided - find any ACTIVE PHC, fallback to first
        if prefer_active:
            active_phc = conn.execute(
                'SELECT id FROM phc_facilities WHERE status="ACTIVE" ORDER BY id LIMIT 1'
            ).fetchone()
            if active_phc:
                return active_phc['id']
        return 1  # Default to Central PHC

    location_lower = patient_location.lower()

    # Keyword mapping: location keyword -> (PHC_id, priority_order)
    # Priority order allows fallback chain within same service area
    keyword_mapping = {
        'north': [(2, 1), (1, 2), (3, 3)],      # Prefer PHC North, fallback to Central, then South
        'south': [(3, 1), (1, 2), (2, 3)],      # Prefer PHC South, fallback to Central, then North
        'east': [(4, 1), (1, 2), (6, 3)],       # Prefer PHC East, fallback to Central, then Rural
        'west': [(5, 1), (1, 2), (3, 3)],       # Prefer PHC West, fallback to Central, then South
        'rural': [(6, 1), (1, 2), (4, 3)],      # Prefer PHC Rural, fallback to Central, then East
        'central': [(1, 1), (2, 2), (3, 3)],    # Central is primary, then North/South
        'city center': [(1, 1), (2, 2)],        # City center → Central
        'main': [(1, 1), (2, 2)],               # Main district → Central
    }

    # Find best matched PHC from fallback chain
    matched_fallback_chain = [(1, 4), (2, 5), (3, 6)]  # Default fallback chain

    for keyword, fallback_chain in keyword_mapping.items():
        if keyword in location_lower:
            matched_fallback_chain = fallback_chain
            print(f"[DEBUG] Location keyword '{keyword}' matched in '{patient_location}'")
            break

    # Try to find first ACTIVE PHC in fallback chain
    if prefer_active:
        for phc_id, priority in matched_fallback_chain:
            phc = conn.execute(
                'SELECT id, name, status FROM phc_facilities WHERE id = ? AND status = "ACTIVE"',
                (phc_id,)
            ).fetchone()
            if phc:
                print(f"[DEBUG] Assigned '{patient_location}' to ACTIVE PHC {phc_id}: {phc['name']}")
                return phc_id

        # No ACTIVE PHC in chain - try any ACTIVE PHC
        any_active = conn.execute(
            'SELECT id, name FROM phc_facilities WHERE status = "ACTIVE" ORDER BY id LIMIT 1'
        ).fetchone()
        if any_active:
            print(f"[DEBUG] No ACTIVE PHC in fallback chain - assigned to {any_active['id']}: {any_active['name']}")
            return any_active['id']
    else:
        # Use preferred PHC regardless of status
        for phc_id, priority in matched_fallback_chain:
            phc = conn.execute(
                'SELECT id, name, status FROM phc_facilities WHERE id = ?', (phc_id,)
            ).fetchone()
            if phc:
                print(f"[DEBUG] Assigned '{patient_location}' to PHC {phc_id}: {phc['name']} (Status: {phc['status']})")
                return phc_id

    # Absolute fallback: return PHC Central
    print(f"[DEBUG] Using PHC Central as absolute fallback for '{patient_location}'")
    return 1

class ManagedDBConnection:
    """Backward-compatible wrapper over DatabaseManager context-managed connections."""

    def __init__(self, connection_cm):
        self._cm = connection_cm
        self._conn = connection_cm.__enter__()
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._closed:
            self._cm.__exit__(None, None, None)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._closed:
            self._cm.__exit__(exc_type, exc, tb)
            self._closed = True


def get_db_connection():
    """
    Return a connection-like object compatible with legacy conn.execute() usage.
    """
    return ManagedDBConnection(db_manager.get_connection())


def scan_external_severity(text_summary):
    """
    CLINICAL ACCURACY FIX: Dynamic Wikipedia Severity Parser

    When external APIs (Wikipedia, Wikidata) return disease summaries,
    this function scans the text for clinical danger keywords to determine
    actual disease severity, not just BERT guessing.

    Examples:
    - Leptospirosis: "fatal", "hemorrhage", "kidney failure" → HIGH/CRITICAL
    - Diabetes: "chronic", "management" → MODERATE

    Args:
        text_summary (str): Disease summary from Wikipedia/external API

    Returns:
        str: Inferred severity ('CRITICAL', 'HIGH', 'MODERATE', or 'UNKNOWN')
    """
    if not text_summary or not isinstance(text_summary, str):
        return 'UNKNOWN'

    text_lower = text_summary.lower()

    # CRITICAL danger keywords: Immediate life threat
    critical_keywords = [
        'fatal', 'mortality', 'death', 'fatal outcome', 'lethal',
        'life-threatening', 'emergency', 'resuscitation', 'intensive care',
        'severe hemorrhage', 'massive bleeding', 'sepsis', 'septic shock',
        'respiratory failure', 'acute respiratory distress', 'ards',
        'cardiogenic shock', 'anaphylactic shock', 'refractory shock',
        'multi-organ failure', 'organ failure', 'kidney failure',
        'acute kidney injury', 'renal failure', 'dialysis',
        'pulmonary hemorrhage', 'cerebral hemorrhage', 'intracranial',
        'cardiac arrest', 'ventricular fibrillation', 'asystole',
        'myocardial infarction', 'acute coronary',
        'stroke', 'cerebral infarction', 'hemorrhagic stroke'
    ]

    # HIGH danger keywords: Serious, needs urgent specialist care
    high_keywords = [
        'severe', 'acute', 'serious', 'critical', 'urgent',
        'hospitalization required', 'requiring hospital', 'requires admission',
        'infectious disease', 'epidemic', 'pandemic', 'outbreak',
        'zoonotic', 'vector-borne', 'contagious', 'transmissible',
        'bleeding disorder', 'hemorrhage', 'hemoptysis',
        'pneumonia', 'meningitis', 'encephalitis',
        'myocarditis', 'pericarditis', 'endocarditis',
        'hepatitis', 'liver failure', 'hepatic',
        'immunocompromised', 'immunosuppressed',
        'surgical intervention', 'surgical treatment', 'surgery required',
        'high mortality', 'high fatality', 'prognosis poor'
    ]

    # Count critical and high keywords
    critical_count = sum(1 for keyword in critical_keywords if keyword in text_lower)
    high_count = sum(1 for keyword in high_keywords if keyword in text_lower)

    # Determine severity based on keyword presence
    if critical_count >= 2:
        return 'CRITICAL'
    elif critical_count >= 1 or high_count >= 3:
        return 'HIGH'
    elif high_count >= 1:
        return 'HIGH'
    else:
        return 'MODERATE'


def send_verification_email(recipient_email, token):
    """Send verification email with token link. Uses SMTP env vars; falls back to printing link."""
    verify_link = url_for('verify_email', token=token, _external=True)

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    from_addr = os.getenv('FROM_EMAIL', 'no-reply@prioritymed.local')

    subject = 'Verify your PriorityMed email'
    body = f"Hello,\n\nPlease verify your email by clicking the link below:\n\n{verify_link}\n\nThis link expires in 24 hours.\n\nIf you did not request this, ignore this message.\n\n— PriorityMed Team"

    # If SMTP is configured, try sending
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = recipient_email
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"[OK] Verification email sent to {recipient_email}")
            return True
        except Exception as e:
            print(f"[WARN] Failed to send verification email: {e}")
            return False

    # Fallback: print link to console for development
    print("--- VERIFICATION LINK (dev) ---")
    print(f"Send to: {recipient_email}")
    print(body)
    print("-------------------------------")
    return False


def send_password_reset_code_email(recipient_email, code):
    """Send OTP code for password reset; falls back to console output in development."""

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    from_addr = os.getenv('FROM_EMAIL', 'no-reply@prioritymed.local')

    subject = 'PriorityMed Password Reset Code'
    body = (
        "Hello,\n\n"
        "We received a request to reset your password. Use this verification code:\n\n"
        f"{code}\n\n"
        "This code expires in 10 minutes. If you did not request this, ignore this email.\n\n"
        "- PriorityMed Team"
    )

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = recipient_email
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"[OK] Password reset code sent to {recipient_email}")
            return True
        except Exception as e:
            print(f"[WARN] Failed to send password reset code: {e}")
            return False

    print("--- PASSWORD RESET CODE (dev) ---")
    print(f"Send to: {recipient_email}")
    print(body)
    print("---------------------------------")
    return False

def get_dashboard_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patient_logs")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM patient_logs WHERE dual_brain_risk LIKE 'HIGH%'")
    high = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM patient_logs WHERE dual_brain_risk LIKE '%OVERRIDE%'")
    overrides = c.fetchone()[0]
    # Get appointments count
    c.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date >= date('now')")
    upcoming_appointments = c.fetchone()[0]

    conn.close()
    return {'total': total, 'high': high, 'overrides': overrides, 'appointments': upcoming_appointments}


def get_phc_dashboard_data(phc_id):
    """Get dashboard data for a specific PHC facility - for PHC Nurse dashboards"""
    try:
        conn = get_db_connection()

        # Get admission trends (last 7 days)
        admission_data = conn.execute('''
            SELECT DATE(timestamp) as admission_date, COUNT(*) as count
            FROM patient_logs
            WHERE phc_id = ? AND DATE(timestamp) >= DATE('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) ASC
        ''', (phc_id,)).fetchall()

        admission_dates = []
        admission_counts = []
        for row in admission_data:
            try:
                date_obj = datetime.strptime(row['admission_date'], '%Y-%m-%d')
                admission_dates.append(date_obj.strftime('%a'))
            except:
                admission_dates.append(row['admission_date'])
            admission_counts.append(row['count'])

        # Get risk distribution (last 30 days)
        disease_data = conn.execute('''
            SELECT dual_brain_risk, COUNT(*) as count
            FROM patient_logs
            WHERE phc_id = ? AND DATE(timestamp) >= DATE('now', '-30 days')
            GROUP BY dual_brain_risk
            ORDER BY count DESC
        ''', (phc_id,)).fetchall()

        disease_labels = []
        disease_counts = []
        disease_colors = {'CRITICAL': '#DC2626', 'HIGH': '#D97706', 'MEDIUM': '#2563EB', 'LOW': '#16A34A'}
        for row in disease_data:
            risk_level = row['dual_brain_risk'] or 'LOW'
            disease_labels.append(risk_level)
            disease_counts.append(row['count'])

        # Get center name
        center_info = conn.execute(
            'SELECT name FROM phc_facilities WHERE id = ?',
            (phc_id,)
        ).fetchone()
        center_name = center_info['name'] if center_info else f'PHC {phc_id}'

        # Get system alerts for today
        today = datetime.now().strftime('%Y-%m-%d')
        system_alerts = []

        # Check for critical cases today
        critical_count = conn.execute('''
            SELECT COUNT(*) as count FROM patient_logs
            WHERE phc_id = ? AND DATE(timestamp) = ? AND dual_brain_risk = 'CRITICAL'
        ''', (phc_id, today)).fetchone()
        critical_cases = critical_count['count'] if critical_count else 0
        if critical_cases > 0:
            system_alerts.append({
                'icon': 'fas fa-exclamation-circle',
                'type': 'critical',
                'message': f'{critical_cases} Critical Cases reported today',
                'timestamp': datetime.now().strftime('%H:%M'),
                'status': 'CRITICAL'
            })

        pending_count = conn.execute('''
            SELECT COUNT(*) as count FROM appointments
            WHERE doctor_id IN (SELECT id FROM users WHERE phc_id = ? AND role = 'doctor')
            AND status = 'Pending' AND DATE(appointment_date) = ?
        ''', (phc_id, today)).fetchone()
        pending_appts = pending_count['count'] if pending_count else 0
        if pending_appts > 0:
            system_alerts.append({
                'icon': 'fas fa-calendar-alt',
                'type': 'pending',
                'message': f'{pending_appts} Pending appointments need confirmation',
                'timestamp': datetime.now().strftime('%H:%M'),
                'status': 'WARNING'
            })

        conn.close()

        return {
            'center_name': center_name,
            'center_id': phc_id,
            'admission_dates': admission_dates if admission_dates else ['No data'],
            'admission_counts': admission_counts if admission_counts else [0],
            'disease_labels': disease_labels if disease_labels else ['LOW'],
            'disease_counts': disease_counts if disease_counts else [0],
            'system_alerts': system_alerts
        }
    except Exception as e:
        app.logger.error(f"Error getting PHC dashboard data: {str(e)}")
        return {
            'center_name': f'PHC {phc_id}',
            'center_id': phc_id,
            'admission_dates': [],
            'admission_counts': [],
            'disease_labels': [],
            'disease_counts': [],
            'system_alerts': []
        }


def get_role_dashboard_redirect():
    """Get the correct dashboard URL based on current user's role"""
    if current_user.role == 'ddhs_admin':
        return url_for('admin_dashboard')
    elif current_user.role == 'doctor':
        return url_for('doctor_dashboard')
    elif current_user.role == 'phc_nurse':
        return url_for('phc_nurse_dashboard')
    else:  # patient
        return url_for('patient_dashboard')


ALLOWED_ROLES = {'patient', 'doctor', 'ddhs_admin', 'phc_nurse'}

# --- 5. AUTHENTICATION ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Allow users to visit login page even if authenticated (to switch accounts etc)
    # if current_user.is_authenticated:
    #     return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if role not in ALLOWED_ROLES:
            return render_template('login.html', error='Invalid role selected')

        # Basic validation
        try:
            email = UserValidator.validate_email(email)
        except ValidationError as e:
            return render_template('login.html', error=e.message)

        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ? AND role = ?', (email, role)).fetchone()

        if user_data is None:
            existing_email = conn.execute('SELECT role FROM users WHERE email = ?', (email,)).fetchone()
            conn.close()

            if existing_email:
                correct_role = existing_email['role']
                friendly_role = correct_role.replace('_', ' ').title()
                return render_template(
                    'login.html',
                    error=f'Account found for this email. Please sign in as {friendly_role}.',
                    email=email,
                    selected_role=correct_role
                )

            return render_template('login.html', error='No account found for this email.', email=email, selected_role=role)

        conn.close()

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(
                id=user_data['id'],
                email=user_data['email'],
                fullname=user_data['fullname'],
                role=user_data['role'],
                phone=user_data['phone'],
                specialization=user_data['specialization'],
                license=user_data['license'],
                experience=user_data['experience'],
                phc_id=user_data.get('phc_id') if isinstance(user_data, dict) else (user_data[5] if len(user_data) > 5 else None)
            )
            login_user(user, remember=request.form.get('remember'))

            # Redirect based on role - ROLE-SPECIFIC URLs
            if user.role == 'ddhs_admin':
                return redirect(url_for('ddhs_admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user.role == 'phc_nurse':
                return redirect(url_for('phc_nurse_dashboard'))
            else:  # patient
                return redirect(url_for('patient_dashboard'))
        else:
            return render_template('login.html', error='Invalid password. Please try again.', email=email, selected_role=role)

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
       pass # Allow signup even if logged in just in case

    if request.method == 'POST':
        # Sanitize inputs
        email = InputSanitizer.sanitize_email(request.form.get('email'))
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        fullname = InputSanitizer.sanitize_string(request.form.get('fullname'), max_length=100)
        phone = InputSanitizer.sanitize_phone(request.form.get('phone'))
        role = InputSanitizer.sanitize_string(request.form.get('role'), max_length=50)
        location = InputSanitizer.sanitize_string(request.form.get('location'), max_length=200)  # NEW: Capture location
        phc_id = request.form.get('phc_id')

        # Validate inputs
        if not email:
            return render_template('signup.html', error='Invalid email address.')

        if role not in ALLOWED_ROLES:
            app.logger.warning(f"Signup attempt with invalid role: {role} from {request.remote_addr}")
            return render_template('signup.html', error='Invalid role selected.')

        if phc_id == '':
            phc_id = None
        
        # NEW: Validate PHC ID exists if provided
        if phc_id:
            conn = get_db_connection()
            valid_phc = conn.execute('SELECT id FROM phc_facilities WHERE id = ?', (phc_id,)).fetchone()
            conn.close()
            if not valid_phc:
                phc_id = 1 # Default to Central if invalid
                app.logger.warning(f"Signup with invalid PHC ID: {phc_id}. Defaulted to 1.")

        # Password validation
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match.')

        # Enforce password policy
        is_valid, policy_message = PasswordPolicy.validate(password)
        if not is_valid:
            app.logger.warning(f"Signup with weak password from {request.remote_addr}")
            return render_template('signup.html', error=f'Password Policy: {policy_message}')

        conn = get_db_connection()

        # Check if email already exists
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            conn.close()
            app.logger.warning(f"Signup attempt with existing email: {email} from {request.remote_addr}")
            return render_template(
                'login.html',
                error='Email already registered. If you forgot your password, use Forgot Password.',
                email=email,
                selected_role=existing_user['role'],
                show_reset=True
            )

        # Hash password
        password_hash = generate_password_hash(password)

        # Prepare verification token
        token = secrets.token_urlsafe(24)
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

        try:
            assigned_nurse_id = None
            # REAL-WORLD LOGIC: Assign user to nearest PHC based on location
            if role == 'patient':
                # For patients: Use location to find nearest PHC
                if location:
                    phc_id = find_nearest_phc(conn, location)
                    print(f"[DEBUG] Patient '{fullname}' from '{location}' assigned to PHC: {phc_id}")
                else:
                    # If location not provided, use first PHC
                    default_phc = conn.execute('SELECT id FROM phc_facilities ORDER BY id LIMIT 1').fetchone()
                    phc_id = default_phc['id'] if default_phc else 1
                    print(f"[DEBUG] Patient without location auto-assigned to PHC: {phc_id}")
                
                # NEW: Assign specific nurse at this PHC
                assigned_nurse_id = assign_nurse_to_patient(conn, phc_id)
                print(f"[DEBUG] Patient '{fullname}' assigned to Nurse: {assigned_nurse_id}")

            elif role in ('doctor', 'phc_nurse'):
                # For doctors/nurses: If location provided, find nearest PHC
                if location and (phc_id is None or phc_id == ''):
                    phc_id = find_nearest_phc(conn, location)
                    print(f"[DEBUG] {role} '{fullname}' from '{location}' assigned to PHC: {phc_id}")
                elif phc_id is None or phc_id == '':
                    # Use provided PHC ID or default to 1
                    phc_id = 1
                    print(f"[DEBUG] {role} manually assigned to PHC: {phc_id}")
            elif role == 'ddhs_admin':
                # DDHS admins typically oversee all PHCs, so may not have specific PHC ID
                # But if location provided, assign to nearest for administrative purposes
                if location and (phc_id is None or phc_id == ''):
                    phc_id = find_nearest_phc(conn, location)
                    print(f"[DEBUG] DDHS Admin from '{location}' office at PHC: {phc_id}")

            if role in ('doctor', 'phc_nurse'):
                specialization = InputSanitizer.sanitize_string(request.form.get('specialization'), max_length=100)
                license = InputSanitizer.sanitize_string(request.form.get('license'), max_length=50)
                experience = InputSanitizer.sanitize_string(request.form.get('experience'), max_length=50)

                conn.execute('''
                    INSERT INTO users (email, password_hash, fullname, role, phc_id, phone, specialization, license, experience, email_verified, verification_token, verification_expires, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, password_hash, fullname, role, phc_id, phone, specialization, license, experience, 1, token, expires, location))
            else:
                conn.execute('''
                    INSERT INTO users (email, password_hash, fullname, role, phc_id, phone, email_verified, verification_token, verification_expires, location, assigned_nurse_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, password_hash, fullname, role, phc_id, phone, 1, token, expires, location, assigned_nurse_id))

            conn.commit()
            conn.close()

            # Audit log successful signup
            if audit_logger := app.extensions.get('audit_logger'):
                audit_logger.log_event(
                    action='USER_SIGNUP',
                    details=f"Role: {role} | Name: {fullname}",
                    user=email
                )

            app.logger.info(f"New user registered - Email: {email} | Role: {role}")
            return render_template(
                'login.html',
                success='Account created successfully! You can now login.',
                email=email,
                selected_role=role
            )

        except Exception as e:
            conn.close()
            app.logger.error(f"Signup error for {email}: {str(e)}")
            return render_template('signup.html', error=f'Registration failed: {str(e)}')

    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    # Audit log logout
    if audit_logger := app.extensions.get('audit_logger'):
        audit_logger.log_event(
            action='USER_LOGOUT',
            details=f"Role: {current_user.role}",
            user=current_user.email
        )

    app.logger.info(f"User logged out - Email: {current_user.email} | Role: {current_user.role}")
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


@app.route('/verify_email')
def verify_email():
    token = request.args.get('token')
    if not token:
        return render_template('login.html', error='Invalid verification link')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE verification_token = ?', (token,)).fetchone()
    if not user:
        conn.close()
        return render_template('login.html', error='Invalid or expired verification token')

    # Check expiry
    try:
        expires = datetime.fromisoformat(user['verification_expires'])
    except Exception:
        expires = None

    if expires and expires < datetime.utcnow():
        conn.close()
        return render_template('login.html', error='Verification token has expired. Please resend verification.')

    # Mark verified
    conn.execute('UPDATE users SET email_verified = 1, verification_token = NULL, verification_expires = NULL WHERE id = ?', (user['id'],))
    conn.commit()
    conn.close()

    return render_template('login.html', success='Email verified successfully. You can now login.')


@app.route('/resend_verification', methods=['POST'])
def resend_verification():
    email = request.form.get('email')
    if not email:
        return render_template('login.html', error='Email required to resend verification')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user:
        conn.close()
        return render_template('login.html', error='No account found for that email')

    # Generate new token
    token = secrets.token_urlsafe(24)
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    conn.execute('UPDATE users SET verification_token = ?, verification_expires = ? WHERE id = ?', (token, expires, user['id']))
    conn.commit()
    conn.close()

    sent = send_verification_email(email, token)
    if sent:
        return render_template('login.html', success='Verification email resent — check your inbox.')
    else:
        verify_url = url_for('verify_email', token=token, _external=True)
        return render_template('login.html', success=f'Verification link (dev): {verify_url}')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = InputSanitizer.sanitize_email(request.form.get('email'))
    if not email:
        return render_template('forgot_password.html', error='Please enter a valid email address.')

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

    if user:
        reset_code = f"{secrets.randbelow(1000000):06d}"
        expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        conn.execute(
            'UPDATE users SET reset_code = ?, reset_token = NULL, reset_expires = ? WHERE id = ?',
            (reset_code, expires, user['id'])
        )
        conn.commit()
        send_password_reset_code_email(email, reset_code)

    conn.close()

    # Always return the same response shape to avoid account enumeration.
    return render_template(
        'verify_reset_code.html',
        email=email,
        success='If an account exists for that email, a verification code has been sent.'
    )


@app.route('/forgot-password/resend', methods=['POST'])
def resend_reset_code():
    email = InputSanitizer.sanitize_email(request.form.get('email'))
    if not email:
        return render_template('verify_reset_code.html', error='Please enter a valid email address.')

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if user:
        reset_code = f"{secrets.randbelow(1000000):06d}"
        expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        conn.execute(
            'UPDATE users SET reset_code = ?, reset_token = NULL, reset_expires = ? WHERE id = ?',
            (reset_code, expires, user['id'])
        )
        conn.commit()
        send_password_reset_code_email(email, reset_code)
    conn.close()

    return render_template(
        'verify_reset_code.html',
        email=email,
        success='If an account exists for that email, a new code has been sent.'
    )


@app.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    email = InputSanitizer.sanitize_email(request.form.get('email'))
    entered_code = (request.form.get('code') or '').strip()

    if not email or not entered_code:
        return render_template('verify_reset_code.html', email=email, error='Email and code are required.')

    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, reset_code, reset_expires FROM users WHERE email = ?',
        (email,)
    ).fetchone()

    if not user or not user['reset_code']:
        conn.close()
        return render_template('verify_reset_code.html', email=email, error='Invalid code. Please request a new code.')

    try:
        expires = datetime.fromisoformat(user['reset_expires']) if user['reset_expires'] else None
    except Exception:
        expires = None

    if expires and expires < datetime.utcnow():
        conn.close()
        return render_template('verify_reset_code.html', email=email, error='Code expired. Please resend code.')

    if user['reset_code'] != entered_code:
        conn.close()
        return render_template('verify_reset_code.html', email=email, error='Incorrect code. Please try again.')

    token = secrets.token_urlsafe(24)
    reset_expires = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
    conn.execute(
        'UPDATE users SET reset_token = ?, reset_code = NULL, reset_expires = ? WHERE id = ?',
        (token, reset_expires, user['id'])
    )
    conn.commit()
    conn.close()

    return render_template('reset_password.html', token=token)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token') or request.form.get('token')
    if not token:
        return render_template('login.html', error='Invalid or missing reset token.')

    conn = get_db_connection()
    user = conn.execute('SELECT id, reset_expires FROM users WHERE reset_token = ?', (token,)).fetchone()
    if not user:
        conn.close()
        return render_template('login.html', error='This reset link is invalid or has expired.')

    try:
        expires = datetime.fromisoformat(user['reset_expires']) if user['reset_expires'] else None
    except Exception:
        expires = None

    if expires and expires < datetime.utcnow():
        conn.close()
        return render_template('login.html', error='This reset link has expired. Please request a new one.')

    if request.method == 'GET':
        conn.close()
        return render_template('reset_password.html', token=token)

    new_password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if new_password != confirm_password:
        conn.close()
        return render_template('reset_password.html', token=token, error='Passwords do not match.')

    is_valid, policy_message = PasswordPolicy.validate(new_password)
    if not is_valid:
        conn.close()
        return render_template('reset_password.html', token=token, error=f'Password Policy: {policy_message}')

    password_hash = generate_password_hash(new_password)
    conn.execute(
        'UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE id = ?',
        (password_hash, user['id'])
    )
    conn.commit()
    conn.close()

    return render_template('login.html', success='Password reset successful. Please login with your new password.')

# --- 6. DASHBOARD ROUTES ---
@app.route('/')
def index():
    # Always redirect to login page as the entry point
    return redirect(url_for('login'))

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('Access denied')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get patient's AI reports (assessments from nurse intake) - ONLY what patient can see
    ai_reports = conn.execute('''
        SELECT id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, spo2, respiration_rate,
               dual_brain_risk, routing, recommended_specialist, timestamp
        FROM patient_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (current_user.id,)).fetchall()
    ai_reports = [dict(row) for row in ai_reports]

    # Format timestamps for template
    from datetime import datetime
    for report in ai_reports:
        if report.get('timestamp'):
            try:
                dt = datetime.fromisoformat(report['timestamp'])
                report['formatted_date'] = dt.strftime('%B %d, %Y')
                report['formatted_time'] = dt.strftime('%I:%M %p')
            except:
                report['formatted_date'] = report['timestamp']
                report['formatted_time'] = ''

    # Get patient's upcoming appointments (status: Pending or Approved)
    upcoming_appointments = conn.execute('''
        SELECT id, appointment_date, appointment_time, doctor_id, status,
               (SELECT fullname FROM users WHERE id = appointments.doctor_id) as doctor_name,
               (SELECT specialization FROM users WHERE id = appointments.doctor_id) as specialization
        FROM appointments
        WHERE patient_id = ? AND status IN ('Pending', 'Approved')
        ORDER BY appointment_date ASC, appointment_time ASC
        LIMIT 5
    ''', (current_user.id,)).fetchall()
    upcoming_appointments = [dict(row) for row in upcoming_appointments]

    # Get summary stats
    total_assessments = conn.execute(
        'SELECT COUNT(*) as count FROM patient_logs WHERE user_id = ?',
        (current_user.id,)
    ).fetchone()

    high_risk_count = conn.execute(
        'SELECT COUNT(*) as count FROM patient_logs WHERE user_id = ? AND dual_brain_risk = "HIGH"',
        (current_user.id,)
    ).fetchone()

    conn.close()

    patient_stats = {
        'total_assessments': total_assessments['count'] if total_assessments else 0,
        'high_risk': high_risk_count['count'] if high_risk_count else 0,
        'upcoming_appointments': len(upcoming_appointments)
    }

    return render_template('patient_dashboard_simplified.html',
                         ai_reports=ai_reports,
                         upcoming_appointments=upcoming_appointments,
                         patient_stats=patient_stats,
                         user=current_user)

@app.route('/patient/report/<int:report_id>')
@login_required
def patient_view_report(report_id):
    """Patient - View their own AI assessment report"""
    if current_user.role != 'patient':
        flash('Access denied')
        return redirect(url_for('index'))

    conn = get_db_connection()
    report = conn.execute('''
        SELECT id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, spo2, respiration_rate,
               history, dual_brain_risk, routing, recommended_specialist, timestamp
        FROM patient_logs
        WHERE id = ? AND user_id = ?
    ''', (report_id, current_user.id)).fetchone()

    conn.close()

    if not report:
        flash('Report not found or access denied')
        return redirect(url_for('patient_dashboard'))

    report = dict(report)

    # Format for display
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(report['timestamp'])
        report['date_formatted'] = dt.strftime('%B %d, %Y')
        report['time_formatted'] = dt.strftime('%I:%M %p')
    except:
        report['date_formatted'] = report['timestamp']
        report['time_formatted'] = ''

    # Format vitals
    report['bp_formatted'] = f"{report['sys_bp']}/{report['dia_bp']} mmHg"
    report['hr_formatted'] = f"{report['hr']} bpm"
    report['temp_formatted'] = f"{report['temp']}°F"
    report['spo2_formatted'] = f"{report['spo2']}%"
    report['rr_formatted'] = f"{report['respiration_rate']}/min"

    # Determine risk color
    risk = report['dual_brain_risk']
    if risk == 'CRITICAL':
        report['risk_color'] = '#dc2626'
        report['risk_icon'] = '🔴'
    elif risk == 'HIGH':
        report['risk_color'] = '#f97316'
        report['risk_icon'] = '🟠'
    elif risk == 'MEDIUM':
        report['risk_color'] = '#eab308'
        report['risk_icon'] = '🟡'
    else:
        report['risk_color'] = '#16a34a'
        report['risk_icon'] = '🟢'

    return render_template('patient_report_detail.html',
                         report=report,
                         user=current_user)

@app.route('/api/nurse/patient-reports/<int:patient_id>')
@login_required
def api_nurse_get_patient_reports(patient_id):
    """API - Nurse gets all reports for a specific patient at their PHC"""
    if current_user.role != 'phc_nurse':
        return jsonify({'error': 'Access denied'}), 403

    conn = get_db_connection()

    # Verify patient is at this PHC
    patient = conn.execute('SELECT id FROM users WHERE id = ? AND phc_id = ? AND role = "patient"',
                          (patient_id, current_user.phc_id)).fetchone()

    if not patient:
        conn.close()
        return jsonify({'error': 'Patient not found'}), 404

    # Get all reports for this patient
    reports = conn.execute('''
        SELECT id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, spo2, respiration_rate,
               history, dual_brain_risk, routing, recommended_specialist, timestamp
        FROM patient_logs
        WHERE user_id = ? AND phc_id = ?
        ORDER BY timestamp DESC
    ''', (patient_id, current_user.phc_id)).fetchall()

    conn.close()

    reports_list = [dict(row) for row in reports]
    return jsonify({'success': True, 'reports': reports_list})

@app.route('/api/phc-nurse/all-patient-reports')
@login_required
def api_nurse_get_all_reports():
    """API - Get all patient reports for nurse's PHC with filtering"""
    if current_user.role != 'phc_nurse':
        return jsonify({'error': 'Access denied'}), 403

    risk_filter = request.args.get('risk', 'all')  # all, low, medium, high, critical
    limit = request.args.get('limit', 100, type=int)

    conn = get_db_connection()

    # Build query based on risk filter
    risk_where = ''
    if risk_filter != 'all':
        risk_where = f"AND pl.dual_brain_risk = '{risk_filter.upper()}'"

    reports = conn.execute(f'''
        SELECT pl.id, u.fullname as patient_name, u.email, pl.age, pl.gender,
               pl.symptoms, pl.sys_bp, pl.dia_bp, pl.hr, pl.temp, pl.dual_brain_risk,
               pl.routing, pl.recommended_specialist, pl.timestamp
        FROM patient_logs pl
        INNER JOIN users u ON pl.user_id = u.id
        WHERE pl.phc_id = ? {risk_where}
        ORDER BY pl.timestamp DESC
        LIMIT ?
    ''', (current_user.phc_id, limit)).fetchall()

    conn.close()

    reports_list = [dict(row) for row in reports]
    return jsonify({'success': True, 'reports': reports_list, 'count': len(reports_list)})

@app.route('/doctor/patient-reports/<int:patient_id>')
@login_required
def doctor_view_patient_reports(patient_id):
    """Doctor - View reports for patients they have appointments with"""
    if current_user.role != 'doctor':
        flash('Access denied')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Verify doctor has appointment with this patient
    has_appointment = conn.execute('''
        SELECT COUNT(*) as count FROM appointments
        WHERE doctor_id = ? AND patient_id = ?
    ''', (current_user.id, patient_id)).fetchone()

    if not has_appointment or has_appointment['count'] == 0:
        conn.close()
        flash('You do not have appointments with this patient')
        return redirect(url_for('doctor_dashboard'))

    # Get patient info
    patient = conn.execute('SELECT id, fullname, email, phone FROM users WHERE id = ?',
                          (patient_id,)).fetchone()

    # Get all reports for this patient
    reports = conn.execute('''
        SELECT id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, spo2, respiration_rate,
               history, dual_brain_risk, routing, recommended_specialist, timestamp
        FROM patient_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    ''', (patient_id,)).fetchall()

    conn.close()

    patient_dict = dict(patient) if patient else {}
    reports_list = [dict(row) for row in reports]

    return render_template('doctor_patient_reports.html',
                         patient=patient_dict,
                         reports=reports_list,
                         user=current_user)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    """Doctor-specific dashboard - ONLY for general doctors"""
    if current_user.role != 'doctor':
        flash('Access denied - this page is for doctors only')
        return redirect(url_for('index'))

    stats = get_dashboard_stats()
    conn = get_db_connection()

    # Regular doctor sees ONLY patients they have appointments with
    patients = conn.execute("""
        SELECT DISTINCT pl.* FROM patient_logs pl
        INNER JOIN appointments a ON a.patient_id = pl.user_id
        WHERE a.doctor_id = ?
        ORDER BY pl.timestamp DESC LIMIT 10
    """, (current_user.id,)).fetchall()

    latest_patient = conn.execute("""
        SELECT pl.* FROM patient_logs pl
        INNER JOIN appointments a ON a.patient_id = pl.user_id
        WHERE a.doctor_id = ?
        ORDER BY pl.timestamp DESC LIMIT 1
    """, (current_user.id,)).fetchone()

    conn.close()

    return render_template('doctor_dashboard.html',
                         patients=patients,
                         stats=stats,
                         latest_patient=latest_patient,
                         user=current_user)

@app.route('/doctor/reports')
@login_required
def doctor_reports():
    """Doctor - View patient reports"""
    if current_user.role != 'doctor':
        flash('Access denied - this page is for doctors only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get patient reports - doctor sees only their own patients (those with appointments)
    patients = conn.execute("""
        SELECT DISTINCT u.id, u.fullname, u.email, u.phone
        FROM users u
        INNER JOIN appointments a ON u.id = a.patient_id
        WHERE a.doctor_id = ?
        ORDER BY u.fullname ASC
    """, (current_user.id,)).fetchall()

    patient_reports = []
    patient_details = {}  # Dictionary to hold detailed patient info for modal

    for patient in patients:
        patient_dict = dict(patient)
        records = conn.execute("""
            SELECT * FROM patient_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (patient['id'],)).fetchall()

        records_list = [dict(r) for r in records]
        patient_dict['total_records'] = len(records_list)

        # Calculate health score based on risk levels
        if records_list:
            risk_counts = {}
            for r in records_list:
                risk = r.get('dual_brain_risk', 'LOW')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1

            # Score: LOW=100, MEDIUM=70, HIGH=40
            score = 0
            for risk, count in risk_counts.items():
                if risk == 'LOW':
                    score += count * 10
                elif risk == 'MEDIUM':
                    score += count * 7
                else:
                    score += count * 4
            patient_dict['health_score'] = min(100, score // max(1, len(records_list)))

            # Latest vitals and symptoms
            latest = records_list[0]
            patient_dict['last_checkup'] = latest.get('timestamp', '')
            patient_dict['symptoms'] = latest.get('symptoms', 'N/A')
            patient_dict['risk_level'] = latest.get('dual_brain_risk', 'UNKNOWN')
            patient_dict['vitals'] = {
                'hr': latest.get('hr', '--'),
                'bp': f"{latest.get('sys_bp', '--')}/{latest.get('dia_bp', '--')}"
            }
        else:
            patient_dict['health_score'] = 0
            patient_dict['last_checkup'] = 'N/A'
            patient_dict['symptoms'] = 'N/A'
            patient_dict['risk_level'] = 'UNKNOWN'
            patient_dict['vitals'] = {'hr': '--', 'bp': '--/--'}

        patient_reports.append(patient_dict)

        # Build patient_details for modal view
        patient_details[str(patient['id'])] = {
            'name': patient['fullname'],
            'email': patient['email'],
            'phone': patient['phone'] or 'N/A',
            'records': records_list
        }

    stats = get_dashboard_stats()

    # Calculate doctor-specific stats
    total_patient_records = sum(p['total_records'] for p in patient_reports)
    high_risk = sum(1 for p in patient_reports if p['risk_level'] == 'HIGH')
    avg_score = sum(p['health_score'] for p in patient_reports) / len(patient_reports) if patient_reports else 0

    # Prepare stats dict for template
    stats = {
        'total_patients': len(patient_reports),
        'total_records': total_patient_records,
        'high_risk_patients': high_risk,
        'recent_checkups': total_patient_records,
        'avg_health_score': round(avg_score, 1)
    }

    conn.close()

    return render_template('reports.html',
                         patient_reports=patient_reports,
                         patient_details=patient_details,
                         stats=stats,
                         user=current_user)



@app.route('/phc/nurse/appointments')
@login_required
def phc_nurse_appointments():
    """PHC Nurse - View facility appointments"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get appointments for doctors in this facility (all appointments at the facility)
    appointments = conn.execute("""
        SELECT a.*, u.fullname as patient_name, d.fullname as doctor_name
        FROM appointments a
        LEFT JOIN users u ON u.id = a.patient_id
        LEFT JOIN users d ON d.id = a.doctor_id
        WHERE d.phc_id = ? OR a.patient_id IN (
            SELECT user_id FROM patient_logs WHERE phc_id = ?
        )
        ORDER BY a.appointment_date DESC
    """, (current_user.phc_id, current_user.phc_id)).fetchall()

    appointments = [dict(row) for row in appointments]
    stats = get_dashboard_stats()
    dashboard_data = get_phc_dashboard_data(current_user.phc_id)

    conn.close()

    return render_template('phc_nurse_dashboard.html',
                         appointments=appointments,
                         stats=stats,
                         dashboard_data=dashboard_data,
                         current_page='appointments',
                         user=current_user)

@app.route('/phc/nurse/patients')
@login_required
def phc_nurse_patients():
    """PHC Nurse - View facility patients"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get all patients from this facility with detailed statistics
    patients = conn.execute("""
        SELECT
            u.id,
            u.email,
            u.fullname,
            u.phone,
            COUNT(DISTINCT a.id) as total_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
        FROM users u
        LEFT JOIN appointments a ON u.id = a.patient_id
        WHERE u.role = 'patient' AND u.assigned_nurse_id = ?
        GROUP BY u.id
        ORDER BY u.fullname ASC
    """, (current_user.id,)).fetchall()

    patients = [dict(row) for row in patients]

    # Get patient cases count and case history separately
    patient_cases_dict = {}
    for patient in patients:
        # Get case count
        case_count = conn.execute('''
            SELECT COUNT(*) as count
            FROM patient_logs
            WHERE user_id = ?
        ''', (patient['id'],)).fetchone()

        patient['total_cases'] = case_count['count'] if case_count else 0

        # Get case history
        cases = conn.execute('''
            SELECT
                id, age, gender, symptoms, routing, dual_brain_risk, timestamp
            FROM patient_logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
        ''', (patient['id'],)).fetchall()

        patient_cases_dict[patient['id']] = [dict(case) for case in cases]

        # Determine risk level based on recent cases
        high_risk_count = sum(1 for case in patient_cases_dict[patient['id']] if 'HIGH' in case.get('dual_brain_risk', ''))
        total_cases = len(patient_cases_dict[patient['id']])

        if total_cases > 0 and high_risk_count > total_cases * 0.5:
            patient['risk_level'] = 'high'
        elif high_risk_count > 0:
            patient['risk_level'] = 'medium'
        else:
            patient['risk_level'] = 'low'

        # Add risk_class to each case for consistent styling
        for case in patient_cases_dict[patient['id']]:
            if 'HIGH' in case.get('dual_brain_risk', ''):
                case['risk_class'] = 'high'
            elif 'MEDIUM' in case.get('dual_brain_risk', ''):
                case['risk_class'] = 'medium'
            else:
                case['risk_class'] = 'low'

    # Calculate statistics
    total_patients = len(patients)
    active_cases = sum(1 for p in patients if p['pending_appointments'] > 0)
    high_risk_count = sum(1 for p in patients if p.get('risk_level') == 'high')
    total_records = conn.execute('SELECT COUNT(*) as count FROM patient_logs WHERE phc_id = ?', (current_user.phc_id,)).fetchone()['count']

    conn.close()

    return render_template('phc_nurse_patients.html',
                         patients=patients,
                         patient_cases=patient_cases_dict,
                         total_patients=total_patients,
                         active_cases=active_cases,
                         high_risk_count=high_risk_count,
                         total_records=total_records,
                         user=current_user)

@app.route('/phc/nurse/reports')
@login_required
def phc_nurse_reports():
    """PHC Nurse - View facility patient reports"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get patient reports from this facility
    patients = conn.execute("""
        SELECT DISTINCT u.id, u.fullname, u.email, u.phone
        FROM users u
        INNER JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
        WHERE u.role = 'patient'
        ORDER BY u.fullname ASC
    """, (current_user.phc_id,)).fetchall()

    patient_reports = []
    for patient in patients:
        patient_dict = dict(patient)
        records = conn.execute("""
            SELECT * FROM patient_logs
            WHERE user_id = ? AND phc_id = ?
            ORDER BY timestamp DESC
        """, (patient['id'], current_user.phc_id)).fetchall()

        records_list = [dict(r) for r in records]
        patient_dict['total_records'] = len(records_list)

        # Calculate health score based on risk levels
        if records_list:
            risk_counts = {}
            for r in records_list:
                risk = r.get('dual_brain_risk', 'LOW')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1

            # Score: LOW=100, MEDIUM=70, HIGH=40
            score = 0
            for risk, count in risk_counts.items():
                if risk == 'LOW':
                    score += count * 10
                elif risk == 'MEDIUM':
                    score += count * 7
                else:
                    score += count * 4
            patient_dict['health_score'] = min(100, score // max(1, len(records_list)))

            # Latest vitals and symptoms
            latest = records_list[0]
            patient_dict['last_checkup'] = latest.get('timestamp', '')
            patient_dict['symptoms'] = latest.get('symptoms', 'N/A')
            patient_dict['risk_level'] = latest.get('dual_brain_risk', 'UNKNOWN')
            patient_dict['vitals'] = {
                'hr': latest.get('hr', '--'),
                'bp': f"{latest.get('sys_bp', '--')}/{latest.get('dia_bp', '--')}"
            }
        else:
            patient_dict['health_score'] = 0
            patient_dict['last_checkup'] = 'N/A'
            patient_dict['symptoms'] = 'N/A'
            patient_dict['risk_level'] = 'UNKNOWN'
            patient_dict['vitals'] = {'hr': '--', 'bp': '--/--'}

        patient_reports.append(patient_dict)

    stats = get_dashboard_stats()
    dashboard_data = get_phc_dashboard_data(current_user.phc_id)

    conn.close()

    return render_template('phc_nurse_dashboard.html',
                         patient_reports=patient_reports,
                         stats=stats,
                         dashboard_data=dashboard_data,
                         current_page='reports',
                         user=current_user)

@app.route('/phc/nurse/messages')
@login_required
def phc_nurse_messages():
    """PHC Nurse - Messaging with facility patients"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get facility patients for messaging
    contacts = conn.execute("""
        SELECT DISTINCT u.id, u.fullname, u.email, u.role,
               (SELECT COUNT(*) FROM messages
                WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
        FROM users u
        INNER JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
        WHERE u.role = 'patient'
        ORDER BY u.fullname ASC
    """, (current_user.id, current_user.phc_id)).fetchall()

    contacts = [dict(row) for row in contacts]
    stats = get_dashboard_stats()
    dashboard_data = get_phc_dashboard_data(current_user.phc_id)

    conn.close()

    return render_template('messages.html',
                         contacts=contacts,
                         stats=stats,
                         dashboard_data=dashboard_data,
                         page_title='Messages - PHC Nurse',
                         user=current_user)

# ===== PHC DOCTOR ROUTES =====




# ===== DDHS ADMIN ROUTES =====
@app.route('/ddhs-admin/dashboard')
@login_required
def ddhs_admin_dashboard():
    """DDHS Admin Dashboard - District-level health administration with real data"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Helper to safely extract count values
    def get_count(result):
        if result is None:
            return 0
        if isinstance(result, dict):
            return result.get('count', 0)
        if isinstance(result, (tuple, list)):
            return result[0] if result else 0
        return result if isinstance(result, int) else 0

    # Get district-level statistics
    total_patients_row = conn.execute(
        "SELECT COUNT(*) as count FROM users WHERE role = 'patient'"
    ).fetchone()
    total_patients = get_count(total_patients_row)

    # Get health centers count (PHC and CHC facilities)
    health_centers_row = conn.execute(
        "SELECT COUNT(DISTINCT phc_id) as count FROM users WHERE role IN ('phc_nurse', 'doctor') AND phc_id IS NOT NULL"
    ).fetchone()
    health_centers = get_count(health_centers_row)

    # Get total staff across all facilities
    total_staff_row = conn.execute(
        "SELECT COUNT(*) as count FROM users WHERE role IN ('phc_nurse', 'doctor', 'ddhs_admin')"
    ).fetchone()
    total_staff = get_count(total_staff_row)

    # Get critical cases - HIGH and CRITICAL risk levels
    critical_cases_row = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as count FROM patient_logs WHERE dual_brain_risk IN ('HIGH', 'CRITICAL')"
    ).fetchone()
    critical_cases = get_count(critical_cases_row)

    # Get vaccine coverage estimate from completed appointments
    vaccine_coverage = 65  # Default placeholder

    # ===== CENTER PERFORMANCE (Connected to PHC Nurses & Doctors) =====
    # Shows completion rate of each health center to track performance
    center_performance = conn.execute("""
        SELECT
            u.phc_id as center_id,
            pf.name as center_name,
            COUNT(DISTINCT a.id) as total_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed,
            CAST(COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) * 100.0 /
                NULLIF(COUNT(DISTINCT a.id), 0) AS INTEGER) as completion_rate
        FROM users u
        LEFT JOIN phc_facilities pf ON u.phc_id = pf.id
        LEFT JOIN appointments a ON u.id = a.doctor_id
        WHERE u.role = 'doctor' AND u.phc_id IS NOT NULL
        GROUP BY u.phc_id, pf.name
        ORDER BY completion_rate DESC
        LIMIT 5
    """).fetchall()

    center_performance = [dict(row) for row in center_performance] if center_performance else []
    # If no performance data, show all PHC centers with 0 data
    if not center_performance:
        all_centers = conn.execute("SELECT id, name FROM phc_facilities ORDER BY name").fetchall()
        center_performance = [{'center_id': c['id'], 'center_name': c['name'], 'total_appointments': 0, 'completed': 0, 'completion_rate': 0} for c in [dict(row) for row in all_centers]]

    # ===== ADMISSION TRENDS (Real data from patient logs over last 7 days) =====
    admission_data = conn.execute("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as admissions
        FROM patient_logs
        WHERE DATE(timestamp) >= DATE('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    """).fetchall()

    admission_dates = []
    admission_counts = []
    if admission_data:
        for row in admission_data:
            row_dict = dict(row) if hasattr(row, 'keys') else {'date': row[0], 'admissions': row[1]}
            admission_dates.append(row_dict['date'])
            admission_counts.append(row_dict['admissions'])

    # ===== DISEASE DISTRIBUTION (Risk levels from real patient data) =====
    disease_distribution = conn.execute("""
        SELECT
            dual_brain_risk as disease_type,
            COUNT(*) as count
        FROM patient_logs
        WHERE dual_brain_risk IS NOT NULL AND DATE(timestamp) >= DATE('now', '-30 days')
        GROUP BY dual_brain_risk
        ORDER BY count DESC
    """).fetchall()

    disease_labels = []
    disease_counts = []
    if disease_distribution:
        for row in disease_distribution:
            row_dict = dict(row) if hasattr(row, 'keys') else {'disease_type': row[0], 'count': row[1]}
            disease_labels.append(row_dict['disease_type'])
            disease_counts.append(row_dict['count'])

    # ===== RESOURCE STATUS (From PHC Nurses management) =====
    # Shows resources managed by PHC nurses by center
    resource_alerts = []
    phc_resources = conn.execute("""
        SELECT
            u.phc_id,
            COUNT(DISTINCT CASE WHEN u.role = 'phc_nurse' THEN u.id END) as nurses,
            COUNT(DISTINCT CASE WHEN u.role = 'doctor' THEN u.id END) as doctors,
            COUNT(DISTINCT a.id) as active_cases
        FROM users u
        LEFT JOIN appointments a ON u.id = a.doctor_id AND a.status != 'Completed'
        WHERE u.phc_id IS NOT NULL AND u.role IN ('phc_nurse', 'doctor')
        GROUP BY u.phc_id
    """).fetchall()

    for resource in phc_resources:
        resource_data = dict(resource) if hasattr(resource, 'keys') else {'phc_id': resource[0], 'nurses': resource[1], 'doctors': resource[2], 'active_cases': resource[3]}
        center_id = resource_data.get('phc_id') or 'Unknown'
        nurses = resource_data.get('nurses') or 0
        doctors = resource_data.get('doctors') or 0
        active_cases = resource_data.get('active_cases') or 0

        # Determine status based on resource availability
        total_staff_count = nurses + doctors
        status = 'optimal' if total_staff_count >= 3 else 'warning' if total_staff_count >= 1 else 'critical'

        resource_alerts.append({
            'center': f"PHC {center_id}",
            'nurses': nurses,
            'doctors': doctors,
            'active_cases': active_cases,
            'status': status
        })

    # ===== SYSTEM ALERTS & NOTIFICATIONS (Real-time, data-driven) =====
    system_alerts = []

    # Alert 1: Critical patient cases reported today
    critical_today_row = conn.execute("""
        SELECT COUNT(DISTINCT user_id) as count FROM patient_logs
        WHERE dual_brain_risk = 'CRITICAL' AND DATE(timestamp) = DATE('now')
    """).fetchone()
    critical_today = get_count(critical_today_row)

    if critical_today > 0:
        system_alerts.append({
            'type': 'critical',
            'icon': 'fa-exclamation-circle',
            'title': f'🚨 {critical_today} Critical Cases',
            'message': f'{critical_today} critical health cases reported today requiring immediate attention',
            'status': 'Critical',
            'time': 'Today'
        })

    # Alert 2: Pending appointments needing confirmation
    pending_appts_row = conn.execute("""
        SELECT COUNT(*) as count FROM appointments
        WHERE status = 'Pending'
    """).fetchone()
    pending_appts = get_count(pending_appts_row)

    if pending_appts > 0:
        system_alerts.append({
            'type': 'warning',
            'icon': 'fa-clock',
            'title': f'⏳ {pending_appts} Pending Appointments',
            'message': f'{pending_appts} appointments awaiting confirmation from PHC centers',
            'status': 'Pending',
            'time': 'Recent'
        })

    # Alert 3: New patient registrations
    new_patients_row = conn.execute("""
        SELECT COUNT(*) as count FROM users
        WHERE role = 'patient' AND DATE(created_at) = DATE('now')
    """).fetchone()
    new_patients = get_count(new_patients_row)

    if new_patients > 0:
        system_alerts.append({
            'type': 'info',
            'icon': 'fa-user-plus',
            'title': f'👥 {new_patients} New Registrations',
            'message': f'{new_patients} new patients registered today in the district',
            'status': 'Completed',
            'time': 'Today'
        })

    # Alert 4: PHC Nurse check-ins and patient logs
    phc_entries_row = conn.execute("""
        SELECT COUNT(*) as count FROM patient_logs
        WHERE DATE(timestamp) = DATE('now')
    """).fetchone()
    phc_entries = get_count(phc_entries_row)

    if phc_entries > 0:
        system_alerts.append({
            'type': 'success',
            'icon': 'fa-check-circle',
            'title': f'✓ {phc_entries} PHC Check-ins',
            'message': f'{phc_entries} patient check-ins recorded by PHC nurses today',
            'status': 'Completed',
            'time': 'Recent'
        })

    # Alert 5: High risk cases that need escalation
    high_risk_row = conn.execute("""
        SELECT COUNT(DISTINCT user_id) as count FROM patient_logs
        WHERE dual_brain_risk = 'HIGH' AND DATE(timestamp) >= DATE('now', '-1 day')
    """).fetchone()
    high_risk = get_count(high_risk_row)

    if high_risk > 0:
        system_alerts.append({
            'type': 'warning',
            'icon': 'fa-arrow-up',
            'title': f'[WARN] {high_risk} High Risk Cases',
            'message': f'{high_risk} high-risk patients need escalation or follow-up',
            'status': 'Alert',
            'time': 'Today'
        })

    conn.close()

    # Prepare data for response
    dashboard_data = {
        'total_patients': total_patients,
        'health_centers': health_centers,
        'total_staff': total_staff,
        'critical_cases': critical_cases,
        'vaccine_coverage': vaccine_coverage,
        'district_name': 'Kanpur District',
        'center_performance': center_performance,
        'admission_dates': admission_dates,
        'admission_counts': admission_counts,
        'disease_labels': disease_labels,
        'disease_counts': disease_counts,
        'resource_alerts': resource_alerts,
        'system_alerts': system_alerts,
    }

    # Format center performance data for new template
    centers = conn.execute("SELECT id, name FROM phc_facilities ORDER BY name").fetchall()
    centers_list = [dict(row) for row in centers]

    # Get ambulance stats
    ambulances_active = conn.execute("SELECT COUNT(*) as count FROM ambulances WHERE status = 'available'").fetchone()
    ambulances_active = ambulances_active[0] if ambulances_active else 0

    return render_template('ddhs_admin_dashboard_redesigned.html',
                         user=current_user,
                         total_patients=dashboard_data['total_patients'],
                         health_centers=dashboard_data['health_centers'],
                         total_staff=dashboard_data['total_staff'],
                         ambulances_active=ambulances_active,
                         total_patients_change='+5.2%',
                         health_centers_change='+0.5%',
                         total_staff_change='+2.1%',
                         ambulances_change='+1 available',
                         centers=centers_list,
                         center_performance=dashboard_data['center_performance'],
                         recent_activities=[
                             {'time': '2 mins ago', 'description': 'Staff attendance marked', 'type': 'Attendance', 'details': 'PHC Central'},
                             {'time': '15 mins ago', 'description': 'Ambulance allocated', 'type': 'Alert', 'details': 'Emergency case'},
                         ])

@app.route('/ddhs-admin/health-centers')
@login_required
def ddhs_admin_health_centers():
    """DDHS Admin - Manage all health centers"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get all health centers with their staff count
    centers_list = conn.execute("""
        SELECT
            pf.id, pf.name, pf.location, pf.contact as contact_phone,
            COUNT(DISTINCT CASE WHEN u.role IN ('phc_nurse', 'doctor') THEN u.id END) as staff_count,
            COUNT(DISTINCT CASE WHEN u.role = 'doctor' THEN u.id END) as doctor_count,
            COUNT(DISTINCT CASE WHEN u.role = 'phc_nurse' THEN u.id END) as nurse_count
        FROM phc_facilities pf
        LEFT JOIN users u ON pf.id = u.phc_id
        GROUP BY pf.id
        ORDER BY pf.id ASC
    """).fetchall()

    centers = [dict(row) for row in centers_list] if centers_list else []
    conn.close()

    return render_template('ddhs_admin_health_centers_redesigned.html',
                         centers=centers,
                         user=current_user)

@app.route('/ddhs-admin/staff')
@login_required
def ddhs_admin_staff():
    """DDHS Admin - Manage all staff"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get all staff members by role and health center
    staff_query = conn.execute("""
        SELECT u.id, u.fullname, u.role, u.email, u.phone, u.phc_id, u.specialization, u.created_at, pf.name as phc_name
        FROM users u
        LEFT JOIN phc_facilities pf ON u.phc_id = pf.id
        WHERE u.role IN ('phc_nurse', 'doctor', 'ddhs_admin')
        ORDER BY u.role DESC, u.created_at DESC
    """).fetchall()

    staff_members = []
    for row in staff_query:
        row_dict = dict(row)
        staff_members.append({
            'name': row_dict['fullname'],
            'role': row_dict['role'],
            'role_display': row_dict['role'].replace('_', ' ').title(),
            'email': row_dict['email'],
            'contact_phone': row_dict['phone'],
            'phc_id': row_dict['phc_id'],
            'phc_name': row_dict['phc_name'],
            'specialization': row_dict['specialization'],
        })

    conn.close()

    return render_template('ddhs_admin_staff_redesigned.html',
                         staff_members=staff_members,
                         user=current_user)

@app.route('/ddhs-admin/staff-assignment')
@login_required
def ddhs_admin_staff_assignment():
    """DDHS Admin - Approve and assign staff to PHC centers"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get unassigned staff (roles are doctor/phc_nurse but phc_id is NULL)
    unassigned_staff = conn.execute("""
        SELECT id, fullname, email, phone, role, specialization, license, experience, created_at
        FROM users
        WHERE role IN ('phc_nurse', 'doctor') AND phc_id IS NULL
        ORDER BY created_at DESC
    """).fetchall()
    unassigned_staff = [dict(row) for row in unassigned_staff]

    # Get assigned staff with their centers
    assigned_staff = conn.execute("""
        SELECT u.id, u.fullname, u.email, u.phone, u.role, u.phc_id, pf.name as center_name, u.created_at
        FROM users u
        LEFT JOIN phc_facilities pf ON u.phc_id = pf.id
        WHERE u.role IN ('phc_nurse', 'doctor') AND u.phc_id IS NOT NULL
        ORDER BY u.created_at DESC
    """).fetchall()
    assigned_staff = [dict(row) for row in assigned_staff]

    # Get all available PHC centers
    centers = conn.execute("""
        SELECT id, name, location, contact
        FROM phc_facilities
        ORDER BY name ASC
    """).fetchall()
    centers = [dict(row) for row in centers]

    conn.close()

    return render_template('ddhs_admin_staff_assignment.html',
                         unassigned_staff=unassigned_staff,
                         assigned_staff=assigned_staff,
                         centers=centers,
                         user=current_user)

@app.route('/api/ddhs-admin/assign-staff', methods=['POST'])
@login_required
def api_assign_staff():
    """API endpoint to assign staff to PHC center"""
    if current_user.role != 'ddhs_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    staff_id = data.get('staff_id')
    phc_id = data.get('phc_id')
    action = data.get('action')  # 'assign' or 'reassign'

    if not staff_id or not phc_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    try:
        # Get staff details
        staff = conn.execute('SELECT * FROM users WHERE id = ? AND role IN (?, ?)',
                            (staff_id, 'phc_nurse', 'doctor')).fetchone()
        if not staff:
            return jsonify({'success': False, 'error': 'Staff member not found'}), 404

        # Get center details
        center = conn.execute('SELECT * FROM phc_facilities WHERE id = ?', (phc_id,)).fetchone()
        if not center:
            return jsonify({'success': False, 'error': 'PHC Center not found'}), 404

        # Update staff assignment
        conn.execute('''
            UPDATE users SET phc_id = ? WHERE id = ?
        ''', (phc_id, staff_id))
        conn.commit()

        # Log audit event
        if audit_logger := app.extensions.get('audit_logger'):
            audit_logger.log_event(
                action=f'STAFF_ASSIGNED',
                details=f"{staff['fullname']} ({staff['role']}) assigned to {center['name']}",
                user=current_user.email
            )

        app.logger.info(f"Staff {staff_id} assigned to PHC {phc_id} by {current_user.email}")

        return jsonify({
            'success': True,
            'message': f"{staff['fullname']} has been assigned to {center['name']}",
            'staff_id': staff_id,
            'center_name': center['name']
        }), 200

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error assigning staff: {str(e)}")
        return jsonify({'success': False, 'error': f'Assignment failed: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/ddhs-admin/unassign-staff', methods=['POST'])
@login_required
def api_unassign_staff():
    """API endpoint to unassign staff from a center (for reassignment)"""
    if current_user.role != 'ddhs_admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    staff_id = data.get('staff_id')

    if not staff_id:
        return jsonify({'success': False, 'error': 'Missing staff_id'}), 400

    conn = get_db_connection()
    try:
        staff = conn.execute('SELECT * FROM users WHERE id = ?', (staff_id,)).fetchone()
        if not staff:
            return jsonify({'success': False, 'error': 'Staff not found'}), 404

        conn.execute('UPDATE users SET phc_id = NULL WHERE id = ?', (staff_id,))
        conn.commit()

        if audit_logger := app.extensions.get('audit_logger'):
            audit_logger.log_event(
                action='STAFF_UNASSIGNED',
                details=f"{staff['fullname']} unassigned from center",
                user=current_user.email
            )

        return jsonify({'success': True, 'message': f"{staff['fullname']} has been unassigned"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/ddhs-admin/resources')
@login_required
def ddhs_admin_resources():
    """DDHS Admin - Manage resources and inventory"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    # Inventory data
    inventory = [
        {'name': 'Polio (OPV)', 'quantity': 4500, 'min_required': 2000, 'location': 'Central Store', 'category': 'Vaccines', 'status': 'Good'},
        {'name': 'Measles', 'quantity': 3200, 'min_required': 2000, 'location': 'Central Store', 'category': 'Vaccines', 'status': 'Good'},
        {'name': 'DPT', 'quantity': 2100, 'min_required': 2000, 'location': 'Central Store', 'category': 'Vaccines', 'status': 'Good'},
        {'name': 'Paracetamol', 'quantity': 5600, 'min_required': 3000, 'location': 'PHC Warehouse', 'category': 'Medicines', 'status': 'Good'},
        {'name': 'Antibiotics (Amoxicillin)', 'quantity': 1200, 'min_required': 2000, 'location': 'PHC Warehouse', 'category': 'Medicines', 'status': 'Low'},
        {'name': 'Antiseptics', 'quantity': 8900, 'min_required': 5000, 'location': 'PHC Warehouse', 'category': 'Supplies', 'status': 'Good'},
        {'name': 'Syringes', 'quantity': 12500, 'min_required': 8000, 'location': 'Central Store', 'category': 'Supplies', 'status': 'Good'},
        {'name': 'Gloves', 'quantity': 3400, 'min_required': 5000, 'location': 'Central Store', 'category': 'Supplies', 'status': 'Low'},
        {'name': 'PPE Kits', 'quantity': 450, 'min_required': 500, 'location': 'Central Store', 'category': 'Equipment', 'status': 'Low'},
    ]

    good_stock = len([i for i in inventory if i['status'] == 'Good'])
    low_stock = len([i for i in inventory if i['status'] == 'Low'])
    critical_stock = len([i for i in inventory if i['status'] == 'Critical'])

    categories = [
        {'name': 'Vaccines', 'count': 3, 'value': '₹15,00,000', 'good': 3, 'low': 0, 'critical': 0},
        {'name': 'Medicines', 'count': 2, 'value': '₹8,50,000', 'good': 1, 'low': 1, 'critical': 0},
        {'name': 'Supplies', 'count': 3, 'value': '₹5,20,000', 'good': 2, 'low': 1, 'critical': 0},
        {'name': 'Equipment', 'count': 1, 'value': '₹2,00,000', 'good': 0, 'low': 1, 'critical': 0},
    ]

    low_stock_alerts = [
        {'item': 'Antibiotics (Amoxicillin)', 'current_qty': 1200, 'min_required': 2000, 'priority': 'High'},
        {'item': 'Gloves', 'current_qty': 3400, 'min_required': 5000, 'priority': 'High'},
        {'item': 'PPE Kits', 'current_qty': 450, 'min_required': 500, 'priority': 'Critical'},
    ]

    return render_template('ddhs_admin_resources_redesigned.html',
                         inventory=inventory,
                         total_items=len(inventory),
                         good_stock=good_stock,
                         low_stock=low_stock,
                         critical_stock=critical_stock,
                         in_stock=6,
                         low_items=2,
                         out_of_stock=0,
                         categories=categories,
                         low_stock_alerts=low_stock_alerts,
                         user=current_user)

@app.route('/ddhs-admin/reports')
@login_required
def ddhs_admin_reports():
    """DDHS Admin - View analytics and reports"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get monthly patient statistics
    monthly_stats = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM users
        WHERE role = 'patient'
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month DESC
        LIMIT 12
    """).fetchall()

    # Get disease statistics - using recommended_specialist instead of disease
    disease_stats = conn.execute("""
        SELECT recommended_specialist, COUNT(*) as count
        FROM patient_logs
        WHERE recommended_specialist IS NOT NULL AND recommended_specialist != ''
        GROUP BY recommended_specialist
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    # Get centers for dropdown
    centers = get_db_connection().execute("SELECT id, name FROM phc_facilities ORDER BY name").fetchall()
    centers = [dict(row) for row in centers]

    # Format data for new template
    center_reports = []
    for center in centers[:5]:  # Show top 5 centers
        center_reports.append({
            'center': center['name'],
            'patients': 150,
            'appointments': 120,
            'completed': 98,
            'completion_rate': 81,
            'rating': 4.5
        })

    return render_template('ddhs_admin_reports_redesigned.html',
                         centers=centers,
                         total_patients_month=monthly_stats[0]['count'] if monthly_stats else 0,
                         total_appointments=250,
                         completed_rate=82,
                         avg_wait_time='15 mins',
                         center_reports=center_reports,
                         monthly_data=[120, 140, 160, 150, 180, 200, 220, 240, 230, 250, 270, 290],
                         user=current_user)

@app.route('/ddhs-admin/disease-surveillance')
@login_required
def ddhs_admin_disease_surveillance():
    """DDHS Admin - Disease surveillance and monitoring"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get disease outbreak data - using dual_brain_risk to identify outbreaks
    outbreaks = conn.execute("""
        SELECT dual_brain_risk, COUNT(*) as count, MAX(timestamp) as latest
        FROM patient_logs
        WHERE dual_brain_risk IS NOT NULL
        GROUP BY dual_brain_risk
        HAVING count >= 2
        ORDER BY count DESC
    """).fetchall()

    conn.close()

    # Convert to format expected by template
    diseases = [
        {
            'name': outbreak['dual_brain_risk'] if outbreak['dual_brain_risk'] else 'Unknown',
            'this_month': outbreak['count'] if outbreak['count'] else 0,
            'year_to_date': outbreak['count'] * 2 if outbreak['count'] else 0,
            'severity': 'CRITICAL' if outbreak['count'] > 10 else ('HIGH' if outbreak['count'] > 5 else 'MEDIUM'),
            'trend': 'UP' if outbreak['count'] > 5 else 'STABLE',
            'last_updated': 'Today'
        }
        for outbreak in (outbreaks or [])
    ]

    # Sample alerts data
    alerts = [
        {'disease': 'Dengue', 'cases_this_month': 12, 'cases_ytd': 45, 'severity': 'HIGH', 'status': 'ALERT'},
        {'disease': 'Typhoid', 'cases_this_month': 8, 'cases_ytd': 28, 'severity': 'MEDIUM', 'status': 'WARNING'},
        {'disease': 'Malaria', 'cases_this_month': 15, 'cases_ytd': 52, 'severity': 'CRITICAL', 'status': 'ALERT'},
    ]

    # Sample center distribution
    center_distribution = [
        {'name': 'PHC Central', 'total_cases': 45, 'critical': 3, 'high': 8, 'medium': 15, 'low': 19},
        {'name': 'PHC East', 'total_cases': 38, 'critical': 2, 'high': 6, 'medium': 12, 'low': 18},
        {'name': 'PHC North', 'total_cases': 42, 'critical': 4, 'high': 10, 'medium': 14, 'low': 14},
        {'name': 'PHC Rural', 'total_cases': 28, 'critical': 1, 'high': 4, 'medium': 9, 'low': 14},
        {'name': 'PHC South', 'total_cases': 35, 'critical': 2, 'high': 7, 'medium': 11, 'low': 15},
        {'name': 'PHC West', 'total_cases': 32, 'critical': 2, 'high': 5, 'medium': 10, 'low': 15},
    ]

    return render_template('ddhs_admin_disease_surveillance_redesigned.html',
                         user=current_user,
                         total_diseases=len(diseases),
                         critical_cases=sum(1 for d in diseases if d['severity'] == 'CRITICAL'),
                         critical_count=12,
                         high_count=28,
                         medium_count=45,
                         low_count=18,
                         alert_count=3,
                         outbreaks_detected=len([d for d in diseases if d['severity'] == 'CRITICAL']),
                         diseases=diseases,
                         alerts=alerts,
                         center_distribution=center_distribution)

@app.route('/ddhs-admin/budget')
@login_required
def ddhs_admin_budget():
    """DDHS Admin - Budget and financial management"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    # Sample budget data
    budget_items = [
        {'category': 'Vaccines', 'allocated': 1200000, 'spent': 950000},
        {'category': 'Medicines', 'allocated': 1500000, 'spent': 1150000},
        {'category': 'Infrastructure', 'allocated': 800000, 'spent': 450000},
        {'category': 'Staff Salaries', 'allocated': 1500000, 'spent': 1500000},
        {'category': 'Medical Supplies', 'allocated': 600000, 'spent': 290000},
    ]

    # Calculate totals
    total_budget = sum(item['allocated'] for item in budget_items)
    total_spent = sum(item['spent'] for item in budget_items)
    budget_remaining = total_budget - total_spent
    budget_percentage = int((total_spent / total_budget * 100)) if total_budget > 0 else 0

    return render_template('ddhs_admin_budget_redesigned.html',
                         budget_items=budget_items,
                         total_budget=total_budget,
                         total_spent=total_spent,
                         budget_remaining=budget_remaining,
                         budget_percentage=budget_percentage,
                         user=current_user)

@app.route('/ddhs-admin/campaigns')
@login_required
def ddhs_admin_campaigns():
    """DDHS Admin - Health campaigns and initiatives"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    # Active campaigns
    active_campaigns_list = [
        {'name': 'Immunization Drive 2026', 'description': 'Focus on routine immunization across all age groups', 'target': '50,000', 'reached': '42,300', 'progress': 85, 'duration': '12 weeks'},
        {'name': 'Maternal Health Awareness', 'description': 'Safe pregnancy and childbirth awareness program', 'target': '30,000', 'reached': '21,600', 'progress': 72, 'duration': '8 weeks'},
    ]

    # Upcoming campaigns
    upcoming_campaigns_list = [
        {'name': 'COVID Prevention Drive', 'type': 'Vaccination', 'start_date': 'May 15, 2026', 'duration': '6 weeks', 'target_reach': '40,000'},
        {'name': 'Nutritional Health Program', 'type': 'Awareness', 'start_date': 'June 1, 2026', 'duration': '8 weeks', 'target_reach': '35,000'},
    ]

    # Campaign types
    campaign_types = [
        {'type': 'Immunization', 'count': 4, 'success_rate': 92, 'budget': '₹25,00,000', 'beneficiaries': '1,50,000'},
        {'type': 'Awareness', 'count': 3, 'success_rate': 85, 'budget': '₹12,00,000', 'beneficiaries': '80,000'},
        {'type': 'Prevention', 'count': 2, 'success_rate': 78, 'budget': '₹8,50,000', 'beneficiaries': '50,000'},
    ]

    # Completed campaigns
    completed_campaigns = [
        {'name': 'Polio Eradication Drive', 'type': 'Immunization', 'completion_date': 'March 31, 2026', 'target': '50,000', 'actual': '48,500', 'success_rate': 97, 'impact': '2,000+ children vaccinated'},
        {'name': 'TB Awareness Campaign', 'type': 'Awareness', 'completion_date': 'February 28, 2026', 'target': '25,000', 'actual': '23,800', 'success_rate': 95, 'impact': '1,500 screenings done'},
        {'name': 'Measles Vaccination', 'type': 'Immunization', 'completion_date': 'January 31, 2026', 'target': '35,000', 'actual': '34,200', 'success_rate': 98, 'impact': '3,200 cases prevented'},
    ]

    return render_template('ddhs_admin_campaigns_redesigned.html',
                         total_campaigns=9,
                         active_campaigns=2,
                         upcoming_campaigns=2,
                         total_reach='2,15,000',
                         active_campaigns_list=active_campaigns_list,
                         upcoming_campaigns_list=upcoming_campaigns_list,
                         campaign_types=campaign_types,
                         completed_campaigns=completed_campaigns,
                         user=current_user)

@app.route('/ddhs-admin/audit-log')
@login_required
def ddhs_admin_audit_log():
    """DDHS Admin - View system audit log"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    # Sample audit log data
    audit_logs = [
        {'timestamp': '2026-04-18 14:32', 'user': 'Dr. Gopi', 'action': 'Login', 'resource': 'System', 'details': 'Successful authentication', 'severity': 'Low', 'ip_address': '192.168.1.100'},
        {'timestamp': '2026-04-18 14:28', 'user': 'Nurse Priya', 'action': 'Data Access', 'resource': 'Patient Records', 'details': 'Accessed 5 patient records', 'severity': 'Medium', 'ip_address': '192.168.1.105'},
        {'timestamp': '2026-04-18 14:15', 'user': 'Admin Rajesh', 'action': 'Admin Changes', 'resource': 'User Permissions', 'details': 'Modified staff role permissions', 'severity': 'Critical', 'ip_address': '192.168.1.110'},
        {'timestamp': '2026-04-18 14:10', 'user': 'Dr. Gopi', 'action': 'Data Modify', 'resource': 'Health Records', 'details': 'Updated patient diagnosis', 'severity': 'High', 'ip_address': '192.168.1.100'},
        {'timestamp': '2026-04-18 13:45', 'user': 'Accountant Sunil', 'action': 'Reports', 'resource': 'Financial Report', 'details': 'Generated monthly report', 'severity': 'Medium', 'ip_address': '192.168.1.115'},
        {'timestamp': '2026-04-18 13:20', 'user': 'Admin Rajesh', 'action': 'Settings', 'resource': 'System Config', 'details': 'Updated system settings', 'severity': 'Critical', 'ip_address': '192.168.1.110'},
        {'timestamp': '2026-04-18 13:00', 'user': 'Nurse Priya', 'action': 'Data Modify', 'resource': 'Appointment', 'details': 'Rescheduled patient appointment', 'severity': 'Low', 'ip_address': '192.168.1.105'},
        {'timestamp': '2026-04-18 12:30', 'user': 'Dr. Gopi', 'action': 'Logout', 'resource': 'System', 'details': 'Session ended', 'severity': 'Low', 'ip_address': '192.168.1.100'},
    ]

    # User activity summary
    user_activities = [
        {'name': 'Dr. Gopi', 'role': 'Doctor', 'total_actions': 145, 'last_login': '2026-04-18 14:32', 'status': 'Online', 'risk_level': 'Low'},
        {'name': 'Nurse Priya', 'role': 'Nurse', 'total_actions': 89, 'last_login': '2026-04-18 14:28', 'status': 'Online', 'risk_level': 'Low'},
        {'name': 'Admin Rajesh', 'role': 'Admin', 'total_actions': 234, 'last_login': '2026-04-18 14:15', 'status': 'Online', 'risk_level': 'Medium'},
        {'name': 'Accountant Sunil', 'role': 'Accountant', 'total_actions': 67, 'last_login': '2026-04-18 13:45', 'status': 'Offline', 'risk_level': 'Low'},
        {'name': 'Lab Tech Meera', 'role': 'Lab Technician', 'total_actions': 112, 'last_login': '2026-04-18 12:00', 'status': 'Offline', 'risk_level': 'Low'},
    ]

    # Critical alerts
    critical_alerts = [
        {'title': 'Failed Login Attempts', 'description': '3 failed login attempts from unknown IP 203.0.113.45', 'timestamp': '2026-04-18 14:10', 'status': 'Alert'},
        {'title': 'Permission Changes', 'description': 'Admin Rajesh modified 5 user role permissions', 'timestamp': '2026-04-18 14:15', 'status': 'Pending Review'},
        {'title': 'Data Export Request', 'description': 'Large patient database export initiated by Admin', 'timestamp': '2026-04-18 13:50', 'status': 'Approved'},
    ]

    return render_template('ddhs_admin_audit_log.html',
                         audit_logs=audit_logs,
                         user_activities=user_activities,
                         critical_alerts=critical_alerts,
                         total_events=245,
                         active_users=3,
                         critical_events=7,
                         security_events=12,
                         user=current_user)


# ===== NEW DDHS ADMIN FEATURES =====

# Staff Attendance Management
@app.route('/ddhs-admin/attendance')
@login_required
def ddhs_admin_attendance():
    """DDHS Admin - Staff attendance tracking and management"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get all PHC centers for filtering
        centers = c.execute('SELECT id, name FROM phc_facilities ORDER BY name').fetchall()

        # Get staff list with attendance
        center_id = request.args.get('center', '')
        query = '''
            SELECT u.id, u.fullname, u.role, u.phone, u.specialization,
                   pf.name as center_name,
                   sa.check_in_time as checkin_time,
                   COALESCE(sa.status, 'absent') as attendance_status
            FROM users u
            LEFT JOIN phc_facilities pf ON u.phc_id = pf.id
            LEFT JOIN staff_attendance sa ON u.id = sa.user_id
                AND date(sa.check_in_time) = date('now')
            WHERE u.role IN ('doctor', 'phc_nurse')
        '''

        if center_id:
            query += f' AND u.phc_id = {int(center_id)}'

        query += ' ORDER BY u.fullname'
        staff_list = c.execute(query).fetchall()

        # Calculate statistics
        total_staff = len(staff_list)
        present_count = sum(1 for s in staff_list if s['attendance_status'] == 'Present')
        absent_count = sum(1 for s in staff_list if s['attendance_status'] != 'Present')
        late_count = 0  # Calculate based on check-in time vs expected time

        attendance_percentage = int((present_count / total_staff * 100)) if total_staff > 0 else 0

        conn.close()

        # Format staff list data for template
        formatted_staff = []
        for staff in staff_list:
            formatted_staff.append({
                'id': staff['id'],
                'name': staff['fullname'],
                'role': staff['role'],
                'center_id': staff.get('phc_id', ''),
                'center_name': staff['center_name'],
                'phone': staff['phone'],
                'checkin_time': staff['checkin_time'],
                'status': staff['attendance_status'].lower()
            })

        return render_template('ddhs_admin_attendance_redesigned.html',
                             centers=centers,
                             staff_list=formatted_staff,
                             total_staff=total_staff,
                             present_count=present_count,
                             absent_count=absent_count,
                             late_count=late_count,
                             attendance_percentage=attendance_percentage,
                             today=datetime.now().strftime('%Y-%m-%d'))
    except Exception as e:
        print(f"Error in ddhs_admin_attendance: {e}")
        flash('Error loading attendance data')
        return redirect(url_for('ddhs_admin_dashboard'))


# Ambulance Management
@app.route('/ddhs-admin/ambulances')
@login_required
def ddhs_admin_ambulances():
    """DDHS Admin - Ambulance fleet management and allocation"""
    if current_user.role != 'ddhs_admin':
        flash('Access denied - this page is for DDHS admins only')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get all ambulances
        ambulances = c.execute('''
            SELECT a.id, a.ambulance_number, a.vehicle_type, a.status,
                   a.capacity, a.location_lat, a.location_lon,
                   u.fullname as driver_name, pf.name as location
            FROM ambulances a
            LEFT JOIN users u ON a.current_driver_id = u.id
            LEFT JOIN phc_facilities pf ON a.phc_id = pf.id
            ORDER BY a.ambulance_number
        ''').fetchall()

        # Get active allocations
        active_allocations = c.execute('''
            SELECT aa.id, aa.ambulance_id, a.ambulance_number,
                   aa.patient_id, u.fullname as patient_name,
                   aa.source_location, aa.destination_location,
                   aa.status, aa.estimated_time_min, aa.allocation_time
            FROM ambulance_allocations aa
            JOIN ambulances a ON aa.ambulance_id = a.id
            LEFT JOIN users u ON aa.patient_id = u.id
            WHERE aa.status IN ('allocated', 'picked_up', 'in_transit')
            ORDER BY aa.allocation_time DESC
            LIMIT 20
        ''').fetchall()

        # Get statistics
        total_ambulances = len(ambulances)
        available_count = sum(1 for amb in ambulances if amb['status'] == 'available')
        in_transit_count = sum(1 for amb in ambulances if amb['status'] == 'in_transit')
        inactive_count = total_ambulances - available_count - in_transit_count
        active_alloc_count = len(active_allocations)

        # Format ambulance data for template
        formatted_ambulances = []
        for amb in ambulances:
            formatted_ambulances.append({
                'id': amb['id'],
                'ambulance_number': amb['ambulance_number'],
                'vehicle_type': amb['vehicle_type'],
                'status': amb['status'],
                'capacity': amb['capacity'],
                'location_lat': amb['location_lat'],
                'location_lon': amb['location_lon'],
                'driver_name': amb['driver_name'],
                'location': amb['location']
            })

        # Format allocations for template
        formatted_allocations = []
        for alloc in active_allocations:
            formatted_allocations.append({
                'id': alloc['id'],
                'ambulance_number': alloc['ambulance_number'],
                'driver_name': alloc.get('driver_name', 'Not Assigned'),
                'source_location': alloc['source_location'],
                'destination_location': alloc['destination_location'],
                'status': alloc['status'],
                'patient_name': alloc.get('patient_name', 'Patient')
            })

        # Convert to JSON for map visualization
        import json
        ambulances_json = json.dumps(formatted_ambulances)

        conn.close()

        return render_template('ddhs_admin_ambulances_redesigned.html',
                             ambulances=formatted_ambulances,
                             active_allocations_list=formatted_allocations,
                             total_ambulances=total_ambulances,
                             active_ambulances=available_count,
                             inactive_ambulances=inactive_count,
                             active_allocations=active_alloc_count,
                             ambulances_json=ambulances_json)
    except Exception as e:
        print(f"Error in ddhs_admin_ambulances: {e}")
        flash('Error loading ambulance data')
        return redirect(url_for('ddhs_admin_dashboard'))


# ===== API ENDPOINTS FOR DATA =====
@app.route('/api/phc-centers', methods=['GET'])
def api_get_phc_centers():
    """Get all available PHC centers for signup and dashboard selection"""
    try:
        conn = get_db_connection()
        # Get all PHC facilities
        phc_centers = conn.execute('''
            SELECT id, name, location, contact FROM phc_facilities
            ORDER BY name ASC
        ''').fetchall()
        conn.close()

        centers_list = [
            {
                'id': row['id'],
                'name': row['name'],
                'location': row['location'],
                'contact': row['contact']
            }
            for row in phc_centers
        ]

        return jsonify(centers_list)
    except Exception as e:
        app.logger.error(f"Error fetching PHC centers: {str(e)}")
        return jsonify([]), 500


# ===== PHC NURSE DASHBOARD =====
@app.route('/phc/nurse/dashboard')
@login_required
def phc_nurse_dashboard():
    """PHC Nurse - Center-specific dashboard with patient management"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    # Get nurse's assigned PHC
    phc_id = current_user.phc_id
    if not phc_id:
        flash('You have not been assigned to a PHC center yet')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Helper function to safely extract count
    def get_count(result):
        if result is None:
            return 0
        if isinstance(result, dict):
            return result.get('count', 0)
        if isinstance(result, (tuple, list)):
            return result[0] if result else 0
        return int(result) if isinstance(result, int) else 0

    try:
        # 1. PATIENTS AT THIS PHC CENTER (all patients assigned to this center)
        today = datetime.now().strftime('%Y-%m-%d')

        # Patients registered today assigned to this nurse
        registered_today = conn.execute('''
            SELECT COUNT(DISTINCT pl.user_id) as count FROM patient_logs pl
            JOIN users u ON pl.user_id = u.id
            WHERE u.assigned_nurse_id = ? AND DATE(pl.timestamp) = ?
        ''', (current_user.id, today)).fetchone()
        patients_registered_today = get_count(registered_today)

        # Total unique patients assigned to this nurse
        total_registered = conn.execute('''
            SELECT COUNT(DISTINCT pl.user_id) as count FROM patient_logs pl
            JOIN users u ON pl.user_id = u.id
            WHERE u.assigned_nurse_id = ?
        ''', (current_user.id,)).fetchone()
        total_patients = get_count(total_registered)

        # If no logs, get count of patients assigned to this nurse
        if total_patients == 0:
            total_patients = conn.execute('''
                SELECT COUNT(*) as count FROM users
                WHERE role = 'patient' AND assigned_nurse_id = ?
            ''', (current_user.id,)).fetchone()
            total_patients = get_count(total_patients)

        # 2. PATIENT CHECK-INS TODAY
        checkins_today = conn.execute('''
            SELECT COUNT(*) as count FROM staff_attendance
            WHERE user_id = ? AND DATE(check_in_time) = ? AND status = 'Present'
        ''', (current_user.id, today)).fetchone()
        checkins = get_count(checkins_today)

        # 3. CENTER PERFORMANCE (appointment completion)
        center_performance = conn.execute('''
            SELECT
                COUNT(*) as total_appointments,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed
            FROM appointments
            WHERE doctor_id IN (
                SELECT id FROM users WHERE phc_id = ? AND role = 'doctor'
            )
        ''', (phc_id,)).fetchone()

        total_appts = get_count(center_performance['total_appointments']) if center_performance else 0
        completed_appts = get_count(center_performance['completed']) if center_performance else 0
        center_completion_rate = (completed_appts / total_appts * 100) if total_appts > 0 else 0

        # 4. DISEASE STATUS (risk distribution for this nurse's patients)
        disease_data = conn.execute('''
            SELECT
                pl.dual_brain_risk,
                COUNT(*) as count
            FROM patient_logs pl
            JOIN users u ON pl.user_id = u.id
            WHERE u.assigned_nurse_id = ? AND DATE(pl.timestamp) >= DATE('now', '-30 days')
            GROUP BY pl.dual_brain_risk
            ORDER BY count DESC
        ''', (current_user.id,)).fetchall()

        disease_labels = []
        disease_counts = []
        disease_colors = {'CRITICAL': '#DC2626', 'HIGH': '#D97706', 'MEDIUM': '#2563EB', 'LOW': '#16A34A'}

        for row in disease_data:
            risk_level = row['dual_brain_risk'] or 'LOW'
            disease_labels.append(risk_level)
            disease_counts.append(row['count'])

        # 5. RESOURCE STATUS (doctors and nurses at this center)
        resource_data = conn.execute('''
            SELECT
                role,
                COUNT(*) as count
            FROM users
            WHERE phc_id = ? AND role IN ('doctor', 'phc_nurse')
            GROUP BY role
        ''', (phc_id,)).fetchall()

        doctors_count = 0
        nurses_count = 0
        for row in resource_data:
            if row['role'] == 'doctor':
                doctors_count = row['count']
            elif row['role'] == 'phc_nurse':
                nurses_count = row['count']

        # 6. ADMISSION TRENDS (7-day history for this center)
        admission_data = conn.execute('''
            SELECT
                DATE(timestamp) as admission_date,
                COUNT(*) as count
            FROM patient_logs
            WHERE phc_id = ? AND DATE(timestamp) >= DATE('now', '-7 days')
            GROUP BY admission_date
            ORDER BY admission_date ASC
        ''', (phc_id,)).fetchall()

        admission_dates = []
        admission_counts = []
        for row in admission_data:
            try:
                date_obj = datetime.strptime(row['admission_date'], '%Y-%m-%d')
                admission_dates.append(date_obj.strftime('%a'))
            except:
                admission_dates.append(row['admission_date'])
            admission_counts.append(row['count'])

        # 7. SYSTEM ALERTS FOR THIS CENTER
        system_alerts = []

        # Critical cases in this center
        critical_count = conn.execute('''
            SELECT COUNT(*) as count FROM patient_logs
            WHERE phc_id = ? AND DATE(timestamp) = ? AND dual_brain_risk = 'CRITICAL'
        ''', (phc_id, today)).fetchone()
        critical_cases = get_count(critical_count)
        if critical_cases > 0:
            system_alerts.append({
                'icon': 'fas fa-exclamation-circle',
                'type': 'critical',
                'message': f'{critical_cases} Critical Cases reported today',
                'timestamp': datetime.now().strftime('%H:%M'),
                'status': 'CRITICAL'
            })

        # Pending appointments
        pending_count = conn.execute('''
            SELECT COUNT(*) as count FROM appointments
            WHERE doctor_id IN (
                SELECT id FROM users WHERE phc_id = ? AND role = 'doctor'
            ) AND status = 'Pending' AND DATE(appointment_date) = ?
        ''', (phc_id, today)).fetchone()
        pending_appts = get_count(pending_count)
        if pending_appts > 0:
            system_alerts.append({
                'icon': 'fas fa-calendar-alt',
                'type': 'pending',
                'message': f'{pending_appts} Pending appointments need confirmation',
                'timestamp': datetime.now().strftime('%H:%M'),
                'status': 'WARNING'
            })

        # Get center name
        center_info = conn.execute('''
            SELECT name FROM phc_facilities WHERE id = ?
        ''', (phc_id,)).fetchone()
        center_name = center_info['name'] if center_info else f'PHC {phc_id}'

        conn.close()

        # Build dashboard data
        dashboard_data = {
            'center_name': center_name,
            'center_id': phc_id,
            'patients_registered_today': patients_registered_today,
            'total_patients': total_patients,
            'checkins_today': checkins,
            'center_completion_rate': round(center_completion_rate, 1),
            'total_appointments': total_appts,
            'doctors_available': doctors_count,
            'nurses_available': nurses_count,
            'admission_dates': admission_dates,
            'admission_counts': admission_counts,
            'disease_labels': disease_labels,
            'disease_counts': disease_counts,
            'system_alerts': system_alerts
        }

        # Patient stats for template compatibility
        patient_stats = {
            'total': total_appts,
            'completed': completed_appts,
            'pending': pending_appts
        }

        return render_template('phc_nurse_dashboard.html',
                             dashboard_data=dashboard_data,
                             patient_stats=patient_stats,
                             user=current_user)

    except Exception as e:
        app.logger.error(f"Error loading PHC Nurse dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}')
        return redirect(url_for('index'))







# ===== NEW WORKFLOW DASHBOARDS =====
@app.route('/phc/nurse/intake')
@login_required
def phc_nurse_intake():
    """PHC Nurse Patient Intake & AI Triage with comprehensive checkup form"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this page is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()
    # Get ONLY patients assigned to this nurse
    patients = conn.execute('''
        SELECT DISTINCT u.id, u.fullname FROM users u
        WHERE u.role = 'patient' AND u.assigned_nurse_id = ?
        ORDER BY u.fullname
    ''', (current_user.id,)).fetchall()

    # If no patients found via direct assignment, check logs (fallback)
    if not patients:
        patients = conn.execute('''
            SELECT DISTINCT u.id, u.fullname FROM users u
            INNER JOIN patient_logs pl ON u.id = pl.user_id
            WHERE u.role = 'patient' AND u.assigned_nurse_id = ?
            ORDER BY u.fullname
        ''', (current_user.id,)).fetchall()

    conn.close()

    patients = [dict(row) for row in patients]
    return render_template('phc_nurse_intake_comprehensive.html', patients=patients, user=current_user)





# ===== API ENDPOINTS FOR WORKFLOW =====
@app.route('/api/patient-assessment', methods=['POST'])
@login_required
def api_patient_assessment():
    """NEW: Integrated dual-brain assessment with disease recognition, BERT + XGBoost fusion

    Features:
    - Disease recognition (local DB → SNOMED-CT → external APIs) - handles misspellings via fuzzy matching
    - Symptom extraction from disease profile
    - BERT semantic analysis of symptoms
    - XGBoost analysis of numerical vital signs
    - Dual-brain fusion with disease context
    - Falls back to symptom-based assessment if disease unknown
    """
    # BUG FIX 4: Allow simulator to bypass role check with demo token for dashboard population
    sim_token = request.headers.get('X-Simulation-Token')
    if sim_token != 'DEMO_TOKEN_SMARTTRIAGE_123':
        if current_user.role != 'phc_nurse':
            return jsonify({'error': 'Access denied'}), 403

    try:
        data = request.get_json()

        # Validate required fields
        required = ['patientName', 'age', 'gender', 'bp', 'hr', 'temp', 'spo2', 'rr', 'symptoms']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        # Extract BP into systolic and diastolic
        bp_parts = data['bp'].split('/')
        sys_bp = int(bp_parts[0]) if len(bp_parts) > 0 else 0
        dia_bp = int(bp_parts[1]) if len(bp_parts) > 1 else 0

        # Extract vital signs
        age = int(data['age'])
        gender = data['gender']
        hr = int(data['hr'])
        
        # UI sends Fahrenheit directly (range 95-108)
        temp_f = float(data['temp'])
        # Also store Celsius version for DB if needed
        temp_c = (temp_f - 32) * 5/9 
        spo2 = int(data['spo2'])
        rr = int(data['rr'])
        symptoms = data['symptoms']

        # Optional disease input (NEW) - Safely handle null/None
        disease_input = data.get('disease_name')
        if disease_input:
            disease_input = str(disease_input).strip()
        else:
            disease_input = ""
            
        pain_intensity = int(data.get('pain_intensity', 5))
        symptom_duration_hours = int(data.get('symptom_duration_hours', 24))
        comorbidities = data.get('comorbidities', [])

        # ===== INTEGRATED DUAL-BRAIN ASSESSMENT =====
        final_risk = data.get('riskLevel', 'MEDIUM')  # Default/fallback
        assessment_result = None
        bert_score = None
        xgb_score = None
        disease_recognized = None

        # BUG FIX 2: Run AI assessment even if disease_input is empty (symptoms-only analysis)
        if integrated_risk:
            try:
                # Run full integrated assessment with disease_input=None if not provided
                assessment_result = integrated_risk.assess_patient_with_disease_context(
                    disease_input=disease_input if disease_input else None,  # Can be None
                    symptoms=symptoms,
                    age=age,
                    gender=gender,
                    sys_bp=sys_bp,
                    dia_bp=dia_bp,
                    hr=hr,
                    temp_f=temp_f,
                    spo2=spo2,
                    respiration_rate=rr,
                    pain_intensity=pain_intensity,
                    symptom_duration_hours=symptom_duration_hours,
                    comorbidities=comorbidities if comorbidities else None,
                )

                # Extract results from integrated assessment
                if assessment_result and assessment_result['final_risk']:
                    final_result = assessment_result['final_risk']
                    final_risk = final_result.get('risk_category', 'MEDIUM')
                    bert_score = assessment_result['bert_analysis'].get('risk_score')
                    xgb_score = assessment_result['xgboost_analysis'].get('risk_score')
                    disease_recognized = assessment_result['disease_recognition']['final_risk'].get('disease_identified')

                    logging.info(f"[INTEGRATED] Disease: {disease_recognized} | BERT: {bert_score:.2%} | XGBoost: {xgb_score:.2%} | Final: {final_risk}")
            except Exception as e:
                logging.error(f"[ERROR] Integrated assessment failed: {str(e)}")
                # Fall back to basic assessment
                final_risk = data.get('riskLevel', 'MEDIUM')

        # Determine urgency from final risk
        if final_risk.upper() == 'HIGH':
            urgency = 'URGENT - Go to ER'
            routing = 'ER'
        elif final_risk.upper() == 'CRITICAL':
            urgency = 'EMERGENCY - Call 911'
            routing = 'EMERGENCY'
        elif final_risk.upper() == 'MEDIUM':
            urgency = 'PRIORITY - Specialist within 24-48h'
            routing = 'SPECIALIST'
        else:
            urgency = 'ROUTINE - Monitor and follow up'
            routing = 'MONITOR'

        # ===== SAVE TO DATABASE =====
        conn = get_db_connection()
        cursor = conn.cursor()  # BUG FIX 1: Create cursor explicitly for lastrowid
        cursor.execute("""
            INSERT INTO patient_logs 
            (age, gender, sys_bp, dia_bp, hr, temp, spo2, respiration_rate, 
             symptoms, dual_brain_risk, routing, recommended_specialist, user_id, phc_id, 
             history, xgb_risk, pain_intensity, symptom_duration, disease_input, 
             bert_score, xgb_score, risk_score, news2_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            age, gender, sys_bp, dia_bp, hr, temp_f, spo2, rr,
            symptoms, final_risk, routing, 
            disease_recognized or 'General Physician',
            data.get('patient_id'), current_user.phc_id or 1,
            data.get('history', ''), xgb_score or final_risk,
            pain_intensity, 
            'Today' if symptom_duration_hours <= 24 else '2-3 days' if symptom_duration_hours <= 72 else '1 week' if symptom_duration_hours <= 168 else '2+ weeks',
            disease_input or 'General Symptoms',
            bert_score, xgb_score, 
            int(assessment_result['final_risk']['final_risk_score'] * 100) if assessment_result else 50,
            assessment_result.get('news2_score', 0) if assessment_result else 0
        ))

        conn.commit()
        log_id = cursor.lastrowid  # BUG FIX 1: Use cursor.lastrowid instead of conn.lastrowid
        conn.close()

        # ===== RETURN RESPONSE =====
        response = {
            'success': True,
            'message': f'Assessment complete. Risk: {final_risk}. {urgency}',
            'data': {
                'logId': log_id,
                'riskLevel': final_risk,
                'routing': routing,
                'urgency': urgency,
                'diseaseRecognized': disease_recognized,
            }
        }

        # Include detailed assessment if available
        if assessment_result:
            response['assessment'] = {
                'bert_analysis': {
                    'score': bert_score,
                    'label': assessment_result['bert_analysis'].get('risk_label'),
                    'confidence': assessment_result['bert_analysis'].get('confidence')
                },
                'xgboost_analysis': {
                    'score': xgb_score,
                    'label': assessment_result['xgboost_analysis'].get('risk_label')
                },
                'disease_context': disease_recognized,
                'reasoning': assessment_result['final_risk'].get('reasoning')
            }

        return jsonify(response), 200

    except Exception as e:
        logging.error(f"[ERROR] Patient assessment error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/patient/reports')
@login_required
def api_patient_reports():
    """Get patient's health reports and assessments"""
    if current_user.role != 'patient':
        return jsonify({'error': 'Access denied'}), 403

    try:
        conn = get_db_connection()

        # Get all patient logs (health assessments) for this patient
        reports = conn.execute("""
            SELECT id, patient_name, age, gender, sys_bp, dia_bp, hr, temperature, spo2,
                   respiration_rate, symptoms, news2_score, dual_brain_risk, timestamp
            FROM patient_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (current_user.id,)).fetchall()

        # Convert to list of dicts with proper formatting
        reports_list = []
        for report in reports:
            r = dict(report)
            # Format timestamps
            if r['timestamp']:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(r['timestamp'])
                    r['date'] = dt.strftime('%B %d, %Y')
                    r['time'] = dt.strftime('%I:%M %p')
                except:
                    r['date'] = r['timestamp']
                    r['time'] = ''

            # Format BP
            if r['sys_bp'] and r['dia_bp']:
                r['blood_pressure'] = f"{r['sys_bp']}/{r['dia_bp']} mmHg"
            else:
                r['blood_pressure'] = 'N/A'

            # Determine risk level display
            risk = str(r['dual_brain_risk']).upper() if r['dual_brain_risk'] else 'UNKNOWN'
            if 'HIGH' in risk:
                r['risk_display'] = 'HIGH RISK'
                r['risk_color'] = 'red'
            elif 'MEDIUM' in risk:
                r['risk_display'] = 'MEDIUM RISK'
                r['risk_color'] = 'amber'
            else:
                r['risk_display'] = 'LOW RISK'
                r['risk_color'] = 'green'

            reports_list.append(r)

        conn.close()

        return jsonify({
            'success': True,
            'reports': reports_list,
            'total': len(reports_list)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def normalize_risk_bucket(value):
    """Normalize risk labels into LOW/MEDIUM/HIGH buckets."""
    if not value:
        return None
    text = str(value).upper()
    if 'HIGH' in text:
        return 'HIGH'
    if 'MEDIUM' in text:
        return 'MEDIUM'
    if 'LOW' in text:
        return 'LOW'
    return None


def calculate_realtime_performance_metrics(conn):
    """Compute live performance metrics from doctor-confirmed outcomes."""
    rows = conn.execute('''
        SELECT dual_brain_risk, actual_outcome
        FROM patient_logs
        WHERE actual_outcome IS NOT NULL
    ''').fetchall()

    total_confirmed = len(rows)
    if total_confirmed == 0:
        return {
            'total_confirmed_cases': 0,
            'overall_accuracy': None,
            'high_risk_sensitivity': None,
            'high_risk_specificity': None,
            'high_risk_ppv': None,
            'high_risk_npv': None,
            'confusion_matrix_high_risk': {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}
        }

    exact_matches = 0
    tp = fp = tn = fn = 0

    for row in rows:
        predicted = normalize_risk_bucket(row['dual_brain_risk'])
        actual = normalize_risk_bucket(row['actual_outcome'])

        if predicted == actual:
            exact_matches += 1

        pred_high = predicted == 'HIGH'
        actual_high = actual == 'HIGH'

        if pred_high and actual_high:
            tp += 1
        elif pred_high and not actual_high:
            fp += 1
        elif not pred_high and not actual_high:
            tn += 1
        else:
            fn += 1

    accuracy = exact_matches / total_confirmed
    sensitivity = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    ppv = tp / (tp + fp) if (tp + fp) else None
    npv = tn / (tn + fn) if (tn + fn) else None

    return {
        'total_confirmed_cases': total_confirmed,
        'overall_accuracy': accuracy,
        'high_risk_sensitivity': sensitivity,
        'high_risk_specificity': specificity,
        'high_risk_ppv': ppv,
        'high_risk_npv': npv,
        'confusion_matrix_high_risk': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn}
    }


@app.route('/triage/outcome/<int:log_id>', methods=['POST'])
@login_required
@require_role('doctor', 'phc_nurse', 'ddhs_admin')
def submit_triage_outcome(log_id):
    """Store doctor-confirmed ground truth outcome for a triage log."""
    payload = request.get_json(silent=True) if request.is_json else request.form
    actual_outcome = (payload.get('actual_outcome') or '').strip().upper()
    notes = (payload.get('notes') or '').strip()

    if actual_outcome not in {'LOW', 'MEDIUM', 'HIGH'}:
        message = 'actual_outcome must be one of: LOW, MEDIUM, HIGH'
        if request.is_json:
            return jsonify({'success': False, 'error': message}), 400
        flash(message, 'error')
        return redirect(get_role_dashboard_redirect())

    conn = get_db_connection()
    log_row = conn.execute('SELECT id FROM patient_logs WHERE id = ?', (log_id,)).fetchone()
    if not log_row:
        conn.close()
        if request.is_json:
            return jsonify({'success': False, 'error': 'log_id not found'}), 404
        flash('Triage log not found.', 'error')
        return redirect(get_role_dashboard_redirect())

    conn.execute('''
        UPDATE patient_logs
        SET actual_outcome = ?,
            outcome_confirmed_by = ?,
            outcome_confirmed_at = CURRENT_TIMESTAMP,
            outcome_notes = ?
        WHERE id = ?
    ''', (actual_outcome, current_user.id, notes, log_id))
    conn.commit()

    metrics = calculate_realtime_performance_metrics(conn)
    conn.close()

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Outcome stored successfully',
            'log_id': log_id,
            'metrics': metrics
        }), 200

    flash(f'Outcome saved for triage log #{log_id}.', 'success')
    return redirect(get_role_dashboard_redirect())


@app.route('/triage/model-performance', methods=['GET'])
@login_required
@require_role('doctor', 'phc_nurse', 'ddhs_admin')
def triage_model_performance():
    """Return live model accuracy metrics from confirmed clinical outcomes."""
    conn = get_db_connection()
    metrics = calculate_realtime_performance_metrics(conn)
    conn.close()

    return jsonify({
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'metrics': metrics
    }), 200


@app.route('/triage/outcomes/pending', methods=['GET'])
@login_required
@require_role('doctor', 'phc_nurse', 'ddhs_admin')
def triage_outcomes_pending():
    """Return recent triage logs that still need doctor-confirmed outcomes."""
    limit_raw = request.args.get('limit', '50')
    try:
        limit = max(1, min(int(limit_raw), 200))
    except ValueError:
        limit = 50

    conn = get_db_connection()
    rows = conn.execute('''
        SELECT id, user_id, phc_id, symptoms, dual_brain_risk, routing, recommended_specialist,
               news2_score, timestamp
        FROM patient_logs
        WHERE actual_outcome IS NULL
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()

    return jsonify({
        'count': len(rows),
        'items': [dict(row) for row in rows]
    }), 200


@app.route('/ddhs_dashboard')
@login_required
def ddhs_dashboard():
    if current_user.role != 'ddhs_admin':
        flash('Access denied. DDHS admin role required.')
        return redirect(url_for('index'))

    conn = get_db_connection()
    understaffed_rows = conn.execute('''
        SELECT
            p.id,
            p.name,
            p.location,
            (
                SELECT COUNT(*) FROM users u
                WHERE u.phc_id = p.id AND u.role IN ('doctor', 'phc_nurse')
            ) AS total_staff,
            (
                SELECT COUNT(DISTINCT sa.user_id)
                FROM staff_attendance sa
                JOIN users u ON u.id = sa.user_id
                WHERE u.phc_id = p.id
                  AND u.role IN ('doctor', 'phc_nurse')
                  AND sa.status = 'Present'
                  AND date(sa.check_in_time) = date('now')
            ) AS present_staff,
            (
                SELECT COUNT(DISTINCT sa.user_id)
                FROM staff_attendance sa
                JOIN users u ON u.id = sa.user_id
                WHERE u.phc_id = p.id
                  AND u.role IN ('doctor', 'phc_nurse')
                  AND sa.status = 'Absent'
                  AND date(sa.check_in_time) = date('now')
            ) AS absent_staff
        FROM phc_facilities p
        ORDER BY p.name ASC
    ''').fetchall()

    understaffed_phcs = []
    for row in understaffed_rows:
        total_staff = row['total_staff'] or 0
        present_staff = row['present_staff'] or 0
        absent_staff = row['absent_staff'] or 0
        if total_staff > 0 and present_staff < total_staff:
            understaffed_phcs.append({
                'id': row['id'],
                'name': row['name'],
                'location': row['location'],
                'total_staff': total_staff,
                'present_staff': present_staff,
                'absent_staff': absent_staff
            })

    live_escalations = conn.execute('''
        SELECT
            pl.id,
            pl.user_id,
            pl.dual_brain_risk,
            pl.recommended_specialist,
            pl.routing,
            pl.symptoms,
            pl.timestamp,
            p.name AS phc_name,
            p.location AS phc_location,
            u.fullname AS patient_name
        FROM patient_logs pl
        LEFT JOIN phc_facilities p ON p.id = pl.phc_id
        LEFT JOIN users u ON u.id = pl.user_id
        WHERE pl.dual_brain_risk LIKE 'HIGH%'
        ORDER BY pl.timestamp DESC
        LIMIT 25
    ''').fetchall()
    conn.close()

    return render_template(
        'ddhs_dashboard.html',
        understaffed_phcs=understaffed_phcs,
        live_escalations=live_escalations,
        user=current_user
    )

# --- 7. LEGACY ROUTE (kept for compatibility) ---
    stats = get_dashboard_stats()
    conn = get_db_connection()
    patients = conn.execute("SELECT * FROM patient_logs ORDER BY id DESC LIMIT 10").fetchall()

    # Get latest patient for profile display
    latest_patient = conn.execute("SELECT * FROM patient_logs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    return render_template('index.html', patients=patients, stats=stats, latest_patient=latest_patient)

@app.route('/triage', methods=['GET', 'POST'])
@login_required
def triage():
    # Redirect GET requests to the checkup page
    if request.method == 'GET':
        return redirect(url_for('checkup'))

    if not xgb_risk_model:
        return "[ERROR] XGBoost model not loaded. Check server logs."

    try:
        # 1. Grab and VALIDATE data from form (SAFE extraction to avoid recursion)
        try:
            form_data = {
                'age': str(request.form.get('age', '')).strip(),
                'gender': str(request.form.get('gender', '')).strip(),
                'sys_bp': str(request.form.get('sys_bp', '')).strip(),
                'dia_bp': str(request.form.get('dia_bp', '')).strip(),
                'hr': str(request.form.get('hr', '')).strip(),
                'temp': str(request.form.get('temp', '')).strip(),
                'temp_unit': str(request.form.get('temp_unit', 'F')).strip(),
                'respiration_rate': str(request.form.get('respiration_rate', '')).strip(),
                'spo2': str(request.form.get('spo2', '')).strip(),
                'history': str(request.form.get('history', 'None')).strip(),
                'symptoms': str(request.form.get('symptom', '')).strip(),  # Note: form uses 'symptom' not 'symptoms'
                'pain_level': str(request.form.get('pain_level', '0')).strip(),  # NEW: Pain intensity (1-10)
                'duration': str(request.form.get('duration', '')).strip()  # NEW: Symptom duration
            }
        except RecursionError as re:
            app.logger.error(f"[RECURSION ERROR] Form data extraction failed: {type(re).__name__}")
            flash('Error processing form data - recursion detected', 'error')
            return redirect(url_for('checkup'))

        # Validate all inputs
        validated_data = VitalSignsValidator.validate_triage_data(form_data)

        # Extract validated values
        age = validated_data['age']
        gender = validated_data['gender']
        sys_bp = validated_data['sys_bp']
        dia_bp = validated_data['dia_bp']
        hr = validated_data['hr']
        temp_fahrenheit = validated_data['temp']  # Validation returns Fahrenheit
        temp = (temp_fahrenheit - 32) * 5/9  # Convert to Celsius for model (model trained on Celsius)
        respiration_rate = validated_data['respiration_rate']
        spo2 = validated_data['spo2']
        history = validated_data['history']
        symptom = validated_data['symptoms']

        # CLEAN SYMPTOM TEXT: Remove "Selected symptoms: " prefix if present
        # The frontend tags add this prefix; we need clean symptom data for disease recognition
        if symptom.startswith('Selected symptoms:'):
            # Extract just the symptom portion, remove any notes after "Additional notes:"
            symptom = symptom.replace('Selected symptoms:', '', 1).strip()
            # Split on "Additional notes:" and take only the symptoms part
            if '\n\nAdditional notes:' in symptom:
                symptom = symptom.split('\n\nAdditional notes:')[0].strip()
            print(f"[SYMPTOM CLEANUP] Cleaned symptom string: '{validated_data['symptoms']}' → '{symptom}'")

        # NEW: Extract pain & duration (with safe defaults if not provided)
        pain_level = validated_data.get('pain_level')
        duration = validated_data.get('duration')

        # Parse pain level to integer (1-10)
        try:
            pain_intensity = int(pain_level) if pain_level else 0
            pain_intensity = max(0, min(10, pain_intensity))  # Clamp to 0-10 range
        except (ValueError, TypeError):
            pain_intensity = 0

        print(f"[FORM-DEBUG] Raw pain_level from form: {request.form.get('pain_level')}")
        print(f"[FORM-DEBUG] Raw duration from form: {request.form.get('duration')}")
        print(f"[VALIDATOR-DEBUG] After validator: pain_level={pain_level}, duration={duration}")

        # Duration is already validated by VitalSignsValidator, just use it directly
        if not duration or duration not in ['Today', '2-3 days', '1 week', '2+ weeks', 'Unknown']:
            duration = 'Unknown'

        print(f"[PARSED] pain_level extracted: {pain_level}, pain_intensity: {pain_intensity}, duration: {duration}")

        # ===== IMPROVED DISEASE RECOGNITION (Not weak fuzzy matching) =====
        # Try to recognize the symptom as a disease name using proper medical knowledge
        original_symptom = symptom
        disease_recognized = None
        disease_profile = None
        estimated_severity = None

        # Step 0: Map common symptom combinations to likely diseases
        # This improves recognition for symptom-based input (not just disease names)
        symptom_lower = symptom.lower()

        # ========== LAYER 1: LOCAL OFFLINE DATABASE (Zero-Latency) ==========
        # Check exact disease name match in local database first (fastest)
        local_db_result = LocalDiseaseDatabase.search_disease(symptom_lower)
        if local_db_result:
            print(f"[LAYER-1-EXACT] 🔵 Local DB (exact match): '{symptom}' → {local_db_result['severity']} ({local_db_result['confidence']*100:.0f}%)")
            disease_recognized = symptom
            estimated_severity = local_db_result['severity']
            disease_profile = local_db_result
        else:
            # Try keyword matching in local database (with strict stop-word filtering)
            local_keyword_results = LocalDiseaseDatabase.search_disease_keywords(symptom_lower)
            if local_keyword_results:
                # Get the highest confidence match
                best_match = max(local_keyword_results.values(), key=lambda x: x['confidence'])
                print(f"[LAYER-1-KEYWORD] 🔵 Local DB (keyword match): '{symptom}' → {best_match['disease_name']} ({best_match['severity']}) @ {best_match['confidence']*100:.0f}%")
                disease_recognized = best_match['disease_name']
                estimated_severity = best_match['severity']
                disease_profile = best_match
            else:
                print(f"[LAYER-1] 🔍 No matches in local database - will attempt Layer 2 (External API + Semantic Classifier)")

        # ========== LAYER 2: SERIOUS DISEASE PATTERN MATCHING ==========
        # Database of SERIOUS diseases that require HIGH/CRITICAL severity
        # Only used if not already recognized by Layer 1
        if not disease_recognized:
            print(f"[LAYER-2] Checking serious disease patterns...")
        serious_diseases = {
            # Cancers (CRITICAL)
            'cancer': 'CRITICAL',
            'mesothelioma': 'CRITICAL',
            'lymphoma': 'CRITICAL',
            'leukemia': 'CRITICAL',
            'carcinoma': 'CRITICAL',
            'tumor': 'HIGH',
            'malignant': 'CRITICAL',

            # Cardiovascular emergencies (CRITICAL)
            'myocardial infarction': 'CRITICAL',
            'heart attack': 'CRITICAL',
            'stroke': 'CRITICAL',
            'pulmonary embolism': 'CRITICAL',
            'aortic dissection': 'CRITICAL',

            # Respiratory emergencies (HIGH/CRITICAL)
            'pneumonia': 'HIGH',
            'sepsis': 'CRITICAL',
            'acute respiratory': 'HIGH',
            'respiratory failure': 'CRITICAL',

            # Neurological emergencies (CRITICAL)
            'meningitis': 'CRITICAL',
            'encephalitis': 'CRITICAL',
            'intracranial': 'CRITICAL',
            'hemorrhage': 'CRITICAL',

            # Systemic emergencies (CRITICAL)
            'anaphylaxis': 'CRITICAL',
            'shock': 'CRITICAL',
            'organ failure': 'CRITICAL',
        }

        # Only check serious diseases if not already recognized by local DB
        disease_recognized_from_db = None
        severity_from_db = None
        if not disease_recognized:
            for disease_keyword, severity in serious_diseases.items():
                if disease_keyword in symptom_lower:
                    disease_recognized_from_db = disease_keyword
                    severity_from_db = severity
                    print(f"[LAYER-2-PATTERN] 🟠 Serious disease pattern: '{disease_keyword}' → Severity: {severity}")
                    disease_recognized = disease_keyword
                    estimated_severity = severity
                    break

        # Common high-risk symptom combinations
        high_risk_combos = {
            # Respiratory emergencies
            ('fever', 'cough', 'shortness'): 'Pneumonia',
            ('fever', 'cough', 'breath'): 'Pneumonia',
            ('cough', 'fever'): 'Respiratory Infection',
            ('fever', 'cough', 'sore'): 'Bronchitis',
            ('chest', 'pain', 'cough'): 'Pleurisy',
            ('chest', 'pain', 'shortness'): 'Pulmonary Embolism',

            # Cardiac emergencies
            ('chest', 'pain', 'fever'): 'Myocarditis',
            ('chest', 'pain', 'pressure'): 'Acute Coronary Syndrome',
            ('chest', 'pain', 'difficulty'): 'Acute Coronary Syndrome',

            # Neurological emergencies
            ('severe', 'headache', 'fever'): 'Meningitis',
            ('headache', 'stiff', 'neck'): 'Meningitis',
            ('dizzy', 'confusion', 'fever'): 'Encephalitis',

            # Gastrointestinal emergencies
            ('severe', 'abdominal', 'fever'): 'Appendicitis',
            ('vomiting', 'fever', 'diarrhea'): 'Gastroenteritis',
        }

        # Check for high-risk combinations first
        disease_recognized_from_combos = None
        severity_from_combos = None

        # Priority 1: Use local DB result if found (already set above)
        if disease_recognized and estimated_severity:
            disease_recognized_from_combos = disease_recognized
            severity_from_combos = estimated_severity
            print(f"[PRIORITY-1-LOCAL] [OK] Using local database result: '{disease_recognized}' ({severity_from_combos})")
        # Priority 2: Check pattern-matched serious diseases
        elif disease_recognized_from_db:
            disease_recognized_from_combos = disease_recognized_from_db.title()
            severity_from_combos = severity_from_db
            print(f"[PRIORITY-2-PATTERN] [OK] Using pattern match: '{disease_recognized_from_combos}' ({severity_from_combos})")
        # Priority 3: Check symptom combinations
        else:
            for word_combo, disease_name in high_risk_combos.items():
                if all(word in symptom_lower for word in word_combo):
                    disease_recognized_from_combos = disease_name
                    severity_from_combos = 'HIGH'
                    print(f"[PRIORITY-3-COMBO] [OK] Symptom combination detected: {word_combo} → {disease_name} (HIGH)")
                    break

        # If no high-risk combo found, try moderate combos
        if not disease_recognized_from_combos:
            moderate_combos = {
                ('cough', 'sore'): 'Pharyngitis',
                ('fever', 'body'): 'Viral Infection',
                ('dizziness', 'nausea'): 'Gastroenteritis',
                ('rash', 'fever'): 'Viral Exanthem',
            }
            for word_combo, disease_name in moderate_combos.items():
                if all(word in symptom_lower for word in word_combo):
                    disease_recognized_from_combos = disease_name
                    severity_from_combos = 'MODERATE'
                    print(f"[SYMPTOM-COMBO] Detected: {word_combo} → Likely disease: {disease_name} (MODERATE RISK)")
                    break

        try:
            # Use combo result if found
            if disease_recognized_from_combos:
                disease_recognized = disease_recognized_from_combos
                estimated_severity = severity_from_combos
                print(f"[COMBO-RECOGNIZED] Patient entered: '{original_symptom}' → Recognized as: '{disease_recognized}' (Severity: {estimated_severity})")
                app.logger.info(f"Disease recognized from symptom combo: '{original_symptom}' → '{disease_recognized}' ({estimated_severity})")

            # Step 1: Check LOCAL database FIRST (fast & accurate)
            if not disease_recognized and local_disease_db:
                disease_profile = local_disease_db.get_disease_profile(symptom)
                if disease_profile:
                    disease_recognized = disease_profile.name
                    estimated_severity = disease_profile.severity_level
                    print(f"[LOCAL-DB] Patient entered: '{original_symptom}' → Found in database: '{disease_recognized}' (Severity: {estimated_severity})")
                    app.logger.info(f"Disease found in local DB: '{original_symptom}' → '{disease_recognized}'")

            # Step 2: If still not recognized, classify severity for unknown diseases (ALWAYS WORKS)
            if not disease_recognized:
                from utils.disease_severity_classifier import DiseaseSeverityClassifier
                severity, confidence = DiseaseSeverityClassifier.classify_disease_severity(symptom)
                estimated_severity = severity

                # ENHANCEMENT: For symptom combinations with fever, boost severity
                if 'fever' in symptom_lower and ('cough' in symptom_lower or 'shortness' in symptom_lower or 'breath' in symptom_lower):
                    # Fever + respiratory symptoms = HIGH risk (pneumonia, flu, serious respiratory infection)
                    if severity in ['MODERATE', 'MILD']:
                        estimated_severity = 'HIGH'
                        print(f"[SEVERITY-BOOST] Fever + respiratory symptoms detected → Boosting from {severity} to HIGH")
                elif 'chest' in symptom_lower and 'pain' in symptom_lower:
                    # Chest pain = HIGH risk unless explicitly MILD
                    if severity in ['MODERATE', 'MILD']:
                        estimated_severity = 'HIGH'
                        print(f"[SEVERITY-BOOST] Chest pain detected → Boosting from {severity} to HIGH")
                elif 'severe' in symptom_lower and 'headache' in symptom_lower:
                    # Severe headache + fever = meningitis risk = CRITICAL
                    if 'fever' in symptom_lower:
                        estimated_severity = 'CRITICAL'
                        print(f"[SEVERITY-BOOST] Severe headache + fever detected → Boosting to CRITICAL")
                    else:
                        estimated_severity = 'HIGH'
                        print(f"[SEVERITY-BOOST] Severe headache detected → Boosting to HIGH")

                disease_recognized = symptom
                print(f"[SEMANTIC-SEVERITY] Unknown disease '{symptom}' classified as: {estimated_severity} (confidence: {confidence:.1%})")
                app.logger.info(f"Disease classified via semantic analysis: '{symptom}' → Severity: {estimated_severity} (confidence: {confidence:.1%})")

                # Step 4: Try multi-source medical APIs for enhanced info (non-blocking, FAST TIMEOUT)
                # NOTE: External APIs have anti-bot protection and timeout slowly. For hackathon safety,
                # we use a 2-second timeout so it fails fast and falls back to local AI instantly.
                # This prevents UI freezing during the demo while keeping the architecture elegant.
                if estimated_severity != 'CRITICAL':
                    try:
                        from utils.medical_database_apis import MedicalDatabaseAPIs
                        api_result = MedicalDatabaseAPIs.search_disease_comprehensive(symptom, timeout=2)

                        if api_result.get('found'):
                            sources_found = list(api_result.get('sources', {}).keys())
                            print(f"[MULTI-API] ✓ Found '{symptom}' in: {', '.join(sources_found)}")
                            app.logger.info(f"Disease enhanced with external data from: {', '.join(sources_found)}")

                            # FIX: Dynamic Wikipedia Severity Parsing
                            # Extract summary from Wikipedia/external API and parse for danger keywords
                            wikipedia_summary = None
                            if 'wikipedia' in api_result.get('sources', {}):
                                wiki_data = api_result['sources'].get('wikipedia', {})
                                # Wikipedia API returns 'snippet' (not 'summary' or 'content')
                                wikipedia_summary = wiki_data.get('snippet', '')
                                # Remove HTML tags if present
                                import re
                                wikipedia_summary = re.sub(r'<[^>]+>', '', wikipedia_summary)

                            if wikipedia_summary and wikipedia_summary.strip():
                                # Scan Wikipedia text for clinical danger keywords
                                parsed_severity = scan_external_severity(wikipedia_summary)
                                if parsed_severity in ['CRITICAL', 'HIGH']:
                                    old_severity = estimated_severity
                                    estimated_severity = parsed_severity
                                    print(f"📊 [WIKI-SEVERITY] Parsed Wikipedia snippet → Boosting from {old_severity} to {parsed_severity}")
                                    print(f"    Keywords found in: {wikipedia_summary[:100]}...")
                                    app.logger.info(f"[WIKI-SEVERITY] Dynamic parsing of '{symptom}' Wikipedia snippet → Boosted to {parsed_severity}")
                        else:
                            app.logger.debug(f"[MULTI-API] External sources had no data for '{symptom}' - using local classification")
                    except Exception as api_err:
                        # API failure is non-critical - system already classified severity via local AI
                        # Fast timeout ensures UI stays responsive even if external APIs are slow
                        app.logger.debug(f"[MULTI-API] Fast timeout (2s) reached - OK, continuing with local classification")

        except Exception as recognition_err:
            # Fallback: Use original symptom, classify severity
            print(f"[DISEASE RECOGNITION ERROR] {type(recognition_err).__name__}: {recognition_err}")
            app.logger.warning(f"Disease recognition failed: {recognition_err}")
            disease_recognized = original_symptom
            symptom = original_symptom

            # Still try to classify severity even on error
            try:
                from utils.disease_severity_classifier import DiseaseSeverityClassifier
                severity, _ = DiseaseSeverityClassifier.classify_disease_severity(original_symptom)
                estimated_severity = severity
            except:
                estimated_severity = 'UNKNOWN'

        # 2.5. EMERGENCY PATCH: Rule-based override for healthy patients
        # Note: Model expects Celsius, but override function expects Fahrenheit for display
        try:
            from utils.triage_override import (
                should_override_to_low_risk,
                calculate_healthy_score,
                apply_contextual_risk_adjustments,
                calibrate_medium_high_risk,
            )

            should_override, override_reason, health_score = should_override_to_low_risk(
                age, sys_bp, dia_bp, hr, temp_fahrenheit, symptom, history, respiration_rate, spo2
            )
        except RecursionError as re:
            app.logger.error(f"[RECURSION] Override check failed")
            should_override = False
            override_reason = ""
            health_score = 50
        except Exception as ov_err:
            app.logger.warning(f"Override check warning: {type(ov_err).__name__}")
            should_override = False
            override_reason = ""
            health_score = 50

        if should_override:
            # Patient has healthy vitals and routine/mild symptoms - assign LOW risk directly
            final_risk = "LOW"
            routing = "General Ward / Waiting Room"
            xgb_risk = "LOW (OVERRIDE)"  # For logging purposes
            score = health_score
            print(f"🟢 HEALTHY OVERRIDE: {override_reason} (Score: {health_score}/100)")
        else:
            # Proceed with standard XGBoost + BERT dual-brain assessment
            try:
                gen_enc = encoders['Gender'].transform([gender])[0] if gender in encoders['Gender'].classes_ else 0

                # BUG FIX 3: If symptom not in training data, flag it and rely heavier on BERT + NEWS2
                if symptom in encoders['Symptoms'].classes_:
                    symp_enc = encoders['Symptoms'].transform([symptom])[0]
                    unknown_symptom = False
                else:
                    symp_enc = 0  # Default encoding
                    unknown_symptom = True
                    print(f"[WARN]  WARNING: Unknown symptom '{symptom}' not in XGBoost training data - relying on BERT semantic analysis")
                    app.logger.warning(f"Unknown symptom '{symptom}' - XGBoost may be inaccurate, using BERT override")

                hist_enc = encoders['Pre_Conditions'].transform([history])[0] if history in encoders['Pre_Conditions'].classes_ else 0

                patient_df = pd.DataFrame([[age, gen_enc, symp_enc, sys_bp, dia_bp, hr, temp, hist_enc]], columns=feature_names)
                patient_scaled = scaler.transform(patient_df)

                xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]

                # ===== NEW: ENHANCED CALIBRATION (Fixes MEDIUM/HIGH overfitting) =====
                from utils.model_calibration import (
                    classify_xgb_risk_with_calibration,
                    refine_medium_high_boundary,
                    calibrate_based_on_vitals
                )

                # Step 1: Intelligent XGBoost classification using probability thresholds
                xgb_risk, xgb_confidence = classify_xgb_risk_with_calibration(
                    xgb_probs, symptom, age, sys_bp, dia_bp, hr, temp_fahrenheit, history
                )
                print(f"  1️⃣  XGBoost Result: {xgb_risk} (confidence: {xgb_confidence:.2f})")

                # Step 2: Secondary refinement of MEDIUM/HIGH boundary
                xgb_risk = refine_medium_high_boundary(
                    xgb_risk, xgb_probs, symptom, age, sys_bp, dia_bp, hr, temp_fahrenheit, history
                )
                print(f"  2️⃣  After Boundary Refinement: {xgb_risk}")

                # Step 3: Vital signs calibration
                xgb_risk = calibrate_based_on_vitals(
                    xgb_risk, sys_bp, dia_bp, hr, temp_fahrenheit, spo2, respiration_rate, symptom, history
                )
                print(f"  3️⃣  After Vital Signs Calibration: {xgb_risk}")
                # ===== END: ENHANCED CALIBRATION =====
            except RecursionError as re:
                app.logger.error(f"[RECURSION] Model calibration failed")
                xgb_risk = "MEDIUM"  # Safe default
                xgb_confidence = 0.5
            except Exception as cal_err:
                app.logger.warning(f"Calibration warning: {type(cal_err).__name__}")
                xgb_risk = "MEDIUM"  # Safe default
                xgb_confidence = 0.5

            # 3. RUN SYSTEM 2 (Shadow Brain + Safety Net)
            semantic_emergency = False
            if exp_brain:
                bert_res = exp_brain(symptom)[0]
                # Increased threshold from 0.5 to 0.55 to reduce over-escalation of MEDIUM cases
                is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.55)
                critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain',
                     'unconscious', 'confusion', 'bleeding', 'anaphylaxis', 'throat swelling', 'cannot breathe',
                     'disoriented', 'altered mental status', 'diabetic emergency']
                semantic_emergency = any(word in symptom.lower() for word in critical_words) or is_bert_emergency
            else:
                # BERT model not available - use keyword-based emergency detection only
                critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain',
                     'unconscious', 'confusion', 'bleeding', 'anaphylaxis', 'throat swelling', 'cannot breathe',
                     'disoriented', 'altered mental status', 'diabetic emergency']
                semantic_emergency = any(word in symptom.lower() for word in critical_words)

            # 3b. APPLY DISEASE SEVERITY BOOST (NEW!)
            # Based on disease classification, boost risk for serious conditions
            # This overrides weak XGBoost predictions when we have strong medical evidence
            severity_boosted = False
            if estimated_severity:
                from utils.disease_severity_classifier import DiseaseSeverityClassifier
                severity_multiplier = DiseaseSeverityClassifier.get_risk_multiplier(estimated_severity)

                if estimated_severity == 'CRITICAL':
                    print(f"🔴 [CRITICAL DISEASE] {disease_recognized} → Boosting risk to CRITICAL (overriding XGBoost: {xgb_risk})")
                    xgb_risk = "CRITICAL"
                    severity_boosted = True
                elif estimated_severity == 'HIGH':
                    # Boost HIGH severity diseases regardless of XGBoost result
                    if xgb_risk in ["MEDIUM", "LOW"]:
                        print(f"🟠 [HIGH DISEASE] {disease_recognized} → Boosting risk from {xgb_risk} to HIGH")
                        xgb_risk = "HIGH"
                        severity_boosted = True
                elif estimated_severity == 'MODERATE':
                    # Boost MODERATE to at least MEDIUM if XGBoost says LOW
                    if xgb_risk == "LOW":
                        print(f"🟡 [MODERATE DISEASE] {disease_recognized} → Boosting risk from LOW to MEDIUM")
                        xgb_risk = "MEDIUM"
                        severity_boosted = True

            # 4. DUAL-BRAIN CONSENSUS LOGIC
            if semantic_emergency and xgb_risk != "HIGH" and xgb_risk != "CRITICAL":
                final_risk = "HIGH (SAFETY OVERRIDE)"
                routing = "Resuscitation / Cardiology"
            elif xgb_risk == "CRITICAL":
                final_risk = "CRITICAL"
                routing = "Resuscitation / Emergency"
            elif xgb_risk == "HIGH":
                final_risk = "HIGH"
                routing = "Emergency Department"
            elif xgb_risk == "MEDIUM":
                final_risk = "MEDIUM"
                routing = "Urgent Care"
            else:
                final_risk = "LOW"
                routing = "General Ward / Waiting Room"

            # Only apply contextual adjustments if no disease severity boost
            if not severity_boosted:
                adjusted_risk, _ = apply_contextual_risk_adjustments(
                    final_risk, age, sys_bp, dia_bp, hr, temp_fahrenheit, symptom, history
                )
                if adjusted_risk != final_risk:
                    print(f"[CONTEXTUAL-ADJUST] Adjusted risk from {final_risk} to {adjusted_risk}")
                    final_risk = adjusted_risk
                    if adjusted_risk == 'HIGH':
                        routing = 'Emergency Department'
                    elif adjusted_risk == 'MEDIUM':
                        routing = 'Urgent Care'
                    else:
                        routing = 'General Ward / Waiting Room'

            # NOTE: Only apply calibration if no disease severity boost was applied
            # Disease severity boosts should not be downgraded by probability calibration
            if not severity_boosted:
                calibrated_risk, _ = calibrate_medium_high_risk(
                    final_risk,
                    xgb_probs,
                    0,
                    semantic_emergency,
                    is_danger=False,
                    danger_severity='NORMAL',
                    symptom_text=symptom,
                    age=age,
                )
                if calibrated_risk != final_risk:
                    print(f"[CALIBRATION] Adjusted risk from {final_risk} to {calibrated_risk}")
                    final_risk = calibrated_risk
                    if calibrated_risk == 'HIGH':
                        routing = 'Emergency Department'
                    elif calibrated_risk == 'MEDIUM':
                        routing = 'Urgent Care'
                    else:
                        routing = 'General Ward / Waiting Room'
            else:
                print(f"[DISEASE-SEVERITY-LOCK] Risk locked at {final_risk} due to disease severity boost - bypassing calibration")

            # NEW: PAIN INTENSITY & DURATION ADJUSTMENT (Clinical Rule-Based)
            # If pain is severe (7-10) OR duration is prolonged (2+ weeks), adjust risk upward
            pain_adjustment_note = ""
            if pain_intensity >= 7:
                pain_adjustment_note = f"[PAIN] Severe pain intensity ({pain_intensity}/10) detected. "
                if final_risk == "LOW":
                    final_risk = "MEDIUM"
                    routing = "Urgent Care"
                    print(f"[WARN]  Risk adjusted: LOW → MEDIUM due to high pain intensity ({pain_intensity}/10)")
                    app.logger.info(f"Risk adjusted: LOW → MEDIUM due to high pain intensity ({pain_intensity}/10)")
                elif final_risk == "MEDIUM":
                    # Already MEDIUM, but note the high pain for clinical decision-making
                    print(f"[WARN]  Pain intensity high ({pain_intensity}/10) - escalate caution level")
                    app.logger.info(f"High pain intensity ({pain_intensity}/10) noted with MEDIUM risk")

            duration_adjustment_note = ""
            if duration == "2+ weeks":
                duration_adjustment_note = f"[DURATION] Chronic symptom duration (2+ weeks) detected. "
                if final_risk == "LOW":
                    final_risk = "MEDIUM"
                    routing = "Urgent Care"
                    print(f"[WARN]  Risk adjusted: LOW → MEDIUM due to prolonged duration (2+ weeks)")
                    app.logger.info(f"Risk adjusted: LOW → MEDIUM due to prolonged duration (2+ weeks)")
                elif final_risk == "MEDIUM":
                    # Already MEDIUM, but note the chronic nature
                    print(f"[WARN]  Chronic condition (2+ weeks) - requires specialty follow-up")
                    app.logger.info(f"Prolonged symptom duration (2+ weeks) noted with MEDIUM risk")

            # Calculate score for non-override cases
            score = None  # Will be calculated below

        def recommend_specialist(symptom_text, risk_level):
            text = (symptom_text or '').lower()
            risk_upper = (risk_level or '').upper()

            if 'HIGH' not in risk_upper and 'MEDIUM' not in risk_upper:
                return 'General Medicine'

            rules = [
                (['chest pain', 'palpitation', 'cardiac', 'heart attack'], 'Cardiology'),
                (['hemorrhage', 'bleeding', 'trauma', 'injury'], 'Trauma/Surgery'),
                (['speech', 'stroke', 'seizure', 'paralysis', 'neurologic'], 'Neurology'),
                (['breath', 'asthma', 'wheezing', 'respiratory'], 'Pulmonology')
            ]

            for keys, specialist in rules:
                if any(key in text for key in keys):
                    return specialist

            return 'Emergency Medicine' if 'HIGH' in risk_upper else 'General Medicine'

        recommended_specialist = recommend_specialist(symptom, final_risk)
        phc_id = request.form.get('phc_id') or current_user.phc_id
        if phc_id == '':
            phc_id = None

        # 5. SAVE TO DB with user_id (including pain intensity and duration)
        conn = get_db_connection()
        conn.execute('''INSERT INTO patient_logs
                          (user_id, phc_id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, respiration_rate, spo2, history, xgb_risk, dual_brain_risk, routing, recommended_specialist, pain_intensity, symptom_duration)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (current_user.id, phc_id, age, gender, symptom, sys_bp, dia_bp, hr, temp_fahrenheit, respiration_rate, spo2, history, xgb_risk, final_risk, routing, recommended_specialist, pain_intensity, duration))
        conn.commit()
        log_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()

        # 6. Calculate dynamic score based on risk factors (if not already set by override)
        if score is None:
            def calculate_score(risk_level, sys_bp, dia_bp, hr, temp, history):
                """Calculate risk score (0-100) based on vitals and health history"""
                score = 0

                # Blood pressure contribution (max 25 points)
                if sys_bp > 140 or dia_bp > 90:
                    score += 20
                elif sys_bp > 130 or dia_bp > 80:
                    score += 12
                elif sys_bp < 90 or dia_bp < 60:
                    score += 18
                else:
                    score += 5

                # Heart rate contribution (max 20 points)
                if hr < 60 or hr > 100:
                    score += 15
                elif hr < 40 or hr > 120:
                    score += 18
                else:
                    score += 5

                # Temperature contribution (max 20 points)
                if temp > 100.4 or temp < 95:
                    score += 18
                elif temp > 99 or temp < 97:
                    score += 10
                else:
                    score += 3

                # Medical history contribution (max 15 points)
                if history and history.lower() != 'none':
                    score += 12
                else:
                    score += 2

                # Risk level adjustment (max 20 points)
                if 'HIGH' in risk_level:
                    score += 20
                elif 'MEDIUM' in risk_level:
                    score += 10
                else:
                    score += 3

                return min(100, score)

            score = calculate_score(final_risk, sys_bp, dia_bp, hr, temp_fahrenheit, history)

        # 7. Store result in session for patient view
        if current_user.role == 'patient':
            session['last_checkup_result'] = {
                'risk_level': final_risk,
                'routing': routing,
                'vitals': {
                    'bp': f"{sys_bp}/{dia_bp}",
                    'hr': str(hr),
                    'temp': str(temp_fahrenheit),
                    'respiration_rate': str(respiration_rate),
                    'spo2': str(spo2)
                },
                'symptoms': symptom,
                'age': age,
                'gender': gender,
                'history': history,
                'pain_intensity': int(pain_intensity) if pain_intensity else 0,
                'symptom_duration': duration,
                'recommended_specialist': recommended_specialist,
                'score': score,
                'timestamp': datetime.now().isoformat(),
                'log_id': log_id,
                'news2_score': score
            }
            print(f"[DEBUG] Session data stored: pain_intensity={pain_intensity}, duration={duration}, risk={final_risk}")
            app.logger.info(f"Session data: pain_intensity={pain_intensity}, duration={duration}, risk={final_risk}")
            flash(f'Health assessment completed! Risk Level: {final_risk}')
            return redirect(url_for('checkup_result'))

        return redirect(get_role_dashboard_redirect())

    except Exception as e:
        error_msg = str(e)[:200]
        app.logger.error(f"[TRIAGE ERROR] {type(e).__name__}: {error_msg}")
        flash(f'Error processing triage data: {error_msg}', 'error')
        return redirect(url_for('checkup'))

# --- 8. APPOINTMENTS ROUTES ---
@app.route('/appointments', methods=['GET'])
@login_required
def appointments():
    conn = get_db_connection()

    if current_user.role in ('doctor', 'phc_nurse'):
        # Doctor/PHC staff see appointments assigned to them or pending requests
        appointments_list = conn.execute('''
            SELECT a.*, u.fullname as patient_fullname, u.phone as patient_phone
            FROM appointments a
            LEFT JOIN users u ON a.patient_id = u.id
            WHERE a.doctor_id = ? OR a.status = 'Pending'
            ORDER BY a.appointment_date ASC, a.appointment_time ASC
        ''', (current_user.id,)).fetchall()
    else:
        # Patients see only their own appointments
        appointments_list = conn.execute('''
            SELECT a.*, u.fullname as patient_fullname, u.phone as patient_phone
            FROM appointments a
            LEFT JOIN users u ON a.patient_id = u.id
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date ASC, a.appointment_time ASC
        ''', (current_user.id,)).fetchall()

    # Convert Row objects to dictionaries
    appointments_list = [dict(row) for row in appointments_list]

    # Get appointment dates for calendar highlighting
    if current_user.role in ('doctor', 'phc_nurse'):
        appointment_dates = conn.execute('''
            SELECT DISTINCT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE (doctor_id = ? OR status = 'Pending') AND status != 'Rejected'
            GROUP BY appointment_date
        ''', (current_user.id,)).fetchall()
    else:
        appointment_dates = conn.execute('''
            SELECT DISTINCT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE patient_id = ?
            GROUP BY appointment_date
        ''', (current_user.id,)).fetchall()

    # Convert to dictionaries
    appointment_dates = [dict(row) for row in appointment_dates]

    # Get all doctors for patient appointment booking
    all_doctors = conn.execute('''
        SELECT id, fullname, specialization, experience
        FROM users
        WHERE role = 'doctor'
        ORDER BY fullname ASC
    ''').fetchall()
    all_doctors = [dict(row) for row in all_doctors]

    conn.close()

    return render_template('appointments.html',
                         appointments=appointments_list,
                         appointment_dates=appointment_dates,
                         all_doctors=all_doctors,
                         user=current_user)

# --- 9. DOCTORS DIRECTORY ROUTE ---
@app.route('/doctors', methods=['GET'])
@login_required
def doctors_directory():
    conn = get_db_connection()

    # Get all doctors with their appointment statistics
    doctors = conn.execute('''
        SELECT
            u.id,
            u.email,
            u.fullname,
            u.phone,
            u.specialization,
            u.license,
            u.experience,
            COUNT(DISTINCT a.id) as total_appointments,
            COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments
        FROM users u
        LEFT JOIN appointments a ON u.id = a.doctor_id
        WHERE u.role = 'doctor'
        GROUP BY u.id
        ORDER BY u.fullname ASC
    ''').fetchall()

    doctors = [dict(row) for row in doctors]

    # Calculate statistics
    total_doctors = len(doctors)

    # Simulate availability (in production, this would come from a real availability system)
    import random
    random.seed(42)  # For consistent results
    available_count = 0
    for doctor in doctors:
        # Assign random availability status
        rand = random.random()
        if rand < 0.7:
            doctor['availability'] = 'available'
            available_count += 1
        elif rand < 0.9:
            doctor['availability'] = 'busy'
        else:
            doctor['availability'] = 'offline'

    # Get unique specializations
    specializations = set()
    total_experience = 0
    for doctor in doctors:
        if doctor.get('specialization'):
            specializations.add(doctor['specialization'])
        if doctor.get('experience'):
            total_experience += doctor['experience']

    specializations_count = len(specializations)
    avg_experience = round(total_experience / total_doctors) if total_doctors > 0 else 0

    conn.close()

    return render_template('doctors.html',
                         doctors=doctors,
                         total_doctors=total_doctors,
                         available_doctors=available_count,
                         specializations_count=specializations_count,
                         avg_experience=avg_experience,
                         current_user=current_user)

# --- 10. PATIENTS DIRECTORY ROUTE ---
@app.route('/patients', methods=['GET'])
@login_required
def patients_directory():
    # Only medical staff can access patient directory
    if current_user.role not in ('doctor', 'phc_nurse', 'ddhs_admin'):
        flash('Access denied. Only medical staff can view patient directory.')
        return redirect(url_for('patient_dashboard'))

    conn = get_db_connection()

    # Get patients based on user role
    if current_user.role == 'doctor':
        # Regular doctor sees ONLY their own patients
        patients = conn.execute('''
            SELECT DISTINCT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as total_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id AND a.doctor_id = ?
            WHERE u.role = 'patient'
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.id,)).fetchall()

    elif current_user.role == 'doctor':
        # Doctor sees their own patients (handled by doctor_id in appointments)
        patients = conn.execute('''
            SELECT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as total_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id AND a.doctor_id = ?
            WHERE u.role = 'patient'
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.id,)).fetchall()

    elif current_user.role == 'phc_nurse':
        # PHC Nurse sees ALL patients from their facility
        patients = conn.execute('''
            SELECT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as total_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
            FROM users u
            LEFT JOIN appointments a ON u.id = a.patient_id
            LEFT JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
            WHERE u.role = 'patient' AND pl.phc_id = ?
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.phc_id, current_user.phc_id)).fetchall()

    else:  # DDHS Admin sees ALL patients
        patients = conn.execute('''
            SELECT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as total_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Completed' THEN a.id END) as completed_appointments,
                COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.id END) as pending_appointments
            FROM users u
            LEFT JOIN appointments a ON u.id = a.patient_id
            WHERE u.role = 'patient'
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''').fetchall()

    patients = [dict(row) for row in patients]

    # Get patient cases count and case history separately
    patient_cases_dict = {}
    for patient in patients:
        # Get case count
        case_count = conn.execute('''
            SELECT COUNT(*) as count
            FROM patient_logs
            WHERE user_id = ?
        ''', (patient['id'],)).fetchone()

        patient['total_cases'] = case_count['count'] if case_count else 0

        # Get case history
        cases = conn.execute('''
            SELECT
                id, age, gender, symptoms, routing, dual_brain_risk, timestamp
            FROM patient_logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
        ''', (patient['id'],)).fetchall()

        patient_cases_dict[patient['id']] = [dict(case) for case in cases]

        # Determine risk level based on recent cases
        high_risk_count = sum(1 for case in patient_cases_dict[patient['id']] if 'HIGH' in case.get('dual_brain_risk', ''))
        total_cases = len(patient_cases_dict[patient['id']])

        if total_cases > 0 and high_risk_count > total_cases * 0.5:
            patient['risk_level'] = 'high'
        elif high_risk_count > 0:
            patient['risk_level'] = 'medium'
        else:
            patient['risk_level'] = 'low'

        # Add risk_class to each case for consistent styling
        for case in patient_cases_dict[patient['id']]:
            if 'HIGH' in case.get('dual_brain_risk', ''):
                case['risk_class'] = 'high'
            elif 'MEDIUM' in case.get('dual_brain_risk', ''):
                case['risk_class'] = 'medium'
            else:
                case['risk_class'] = 'low'

    # Calculate statistics
    total_patients = len(patients)
    active_cases = sum(1 for p in patients if p['pending_appointments'] > 0)
    high_risk_count = sum(1 for p in patients if p.get('risk_level') == 'high')
    total_records = conn.execute('SELECT COUNT(*) as count FROM patient_logs').fetchone()['count']

    conn.close()

    return render_template('patients.html',
                         patients=patients,
                         patient_cases=patient_cases_dict,
                         total_patients=total_patients,
                         active_cases=active_cases,
                         high_risk_count=high_risk_count,
                         total_records=total_records,
                         current_user=current_user)

@app.route('/appointments/create', methods=['POST'])
@login_required
def create_appointment():
    conn = get_db_connection()

    try:
        # Get form data
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        symptoms = request.form.get('symptoms', '')
        notes = request.form.get('notes', '')

        if current_user.role == 'patient':
            # Patients REQUEST appointments (status='Pending')
            # They must select a doctor
            doctor_id = request.form.get('doctor_id')

            if not doctor_id or not appointment_date or not appointment_time:
                flash('Please fill in all required fields (Doctor, Date, Time).', 'error')
                return redirect(url_for('appointments'))

            # Get doctor details
            doctor = conn.execute('SELECT id, fullname, specialization FROM users WHERE id = ? AND role = "doctor"',
                                (doctor_id,)).fetchone()
            if not doctor:
                flash('Invalid doctor selected.', 'error')
                return redirect(url_for('appointments'))

            doctor_id = doctor['id']
            doctor_name = doctor['fullname']
            department = doctor['specialization'] or 'General Medicine'

            patient_id = current_user.id
            patient_name = current_user.fullname or 'Patient'
            status = 'Pending'  # Patients request appointments

            conn.execute('''
                INSERT INTO appointments
                (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date, appointment_time, symptoms, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, patient_name, doctor_id, doctor_name, department,
                  appointment_date, appointment_time, symptoms, notes, status))

            flash('Appointment request submitted successfully! Your doctor will review and approve it.', 'success')

        else:
            # Doctor/PHC staff creates appointment (auto-approved)
            patient_id = request.form.get('patient_id')
            patient_name = request.form.get('patient_name', 'Patient')
            doctor_name = request.form.get('doctor_name', current_user.fullname or 'Doctor')
            department = request.form.get('department', current_user.specialization or 'General Medicine')

            # Ensure required fields are not empty
            patient_id = patient_id or current_user.id
            patient_name = str(patient_name).strip() or 'Patient'
            doctor_name = str(doctor_name).strip() or 'Doctor'
            department = str(department).strip() or 'General Medicine'
            symptoms = str(symptoms).strip()
            notes = str(notes).strip()

            conn.execute('''
                INSERT INTO appointments
                (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date, appointment_time, symptoms, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Approved')
            ''', (patient_id, patient_name, current_user.id, doctor_name,
                  department, appointment_date, appointment_time, symptoms, notes))

            flash('Appointment created successfully!')

        try:
            conn.commit()
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Appointment creation failed: {e}")
            flash(f'Error creating appointment: {str(e)}', 'error')
            return redirect(url_for('appointments'))
        finally:
            conn.close()

        return redirect(url_for('appointments'))

    except Exception as e:
        conn.rollback()
        conn.close()
        app.logger.error(f"Appointment creation error: {e}")
        flash(f'Error creating appointment: {str(e)}', 'error')
        return redirect(url_for('appointments'))

@app.route('/appointments/update/<int:id>', methods=['POST'])
@login_required
def update_appointment(id):
    conn = get_db_connection()
    status = request.form['status']

    # Get appointment details
    appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()

    # Authorization check
    if current_user.role == 'doctor':
        # ONLY DOCTORS can approve/reject appointments
        if appointment['status'] == 'Pending' or appointment['doctor_id'] == current_user.id:
            conn.execute('UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, id))
            flash(f'Appointment {status.lower()} successfully!')
        else:
            flash('Unauthorized action!')
    elif current_user.role == 'phc_nurse':
        # Nurses can only manage their own facility appointments (confirm/reschedule, not approve/reject)
        appointment_phc = conn.execute('SELECT phc_id FROM appointments a INNER JOIN users u ON a.doctor_id = u.id WHERE a.id = ?', (id,)).fetchone()
        if appointment_phc and appointment_phc['phc_id'] == current_user.phc_id and status in ('Confirmed', 'Rescheduled'):
            conn.execute('UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, id))
            flash(f'Appointment {status.lower()} successfully!')
        else:
            flash('Nurses can only confirm/reschedule facility appointments (approval is for doctors only)')
    elif current_user.role == 'patient':
        # Patients can only cancel their own appointments
        if appointment['patient_id'] == current_user.id and status == 'Cancelled':
            conn.execute('UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, id))
            flash('Appointment cancelled!')
        else:
            flash('Unauthorized action!')

    conn.commit()
    conn.close()

    return redirect(url_for('appointments'))

@app.route('/appointments/delete/<int:id>', methods=['POST'])
@login_required
def delete_appointment(id):
    conn = get_db_connection()

    # Get appointment details
    appointment = conn.execute('SELECT * FROM appointments WHERE id = ?', (id,)).fetchone()

    # Authorization check
    if current_user.role in ('doctor', 'phc_nurse') or (current_user.role == 'patient' and appointment['patient_id'] == current_user.id):
        conn.execute('DELETE FROM appointments WHERE id = ?', (id,))
        conn.commit()
        flash('Appointment deleted!')
    else:
        flash('Unauthorized action!')

    conn.close()

    return redirect(url_for('appointments'))

@app.route('/phc/nurse/appointments/create', methods=['GET', 'POST'])
@login_required
def phc_nurse_create_appointment():
    """PHC Nurse creates appointment for patient based on triage assessment"""
    if current_user.role != 'phc_nurse':
        flash('Access denied - this is for PHC nurses only')
        return redirect(url_for('index'))

    conn = get_db_connection()

    if request.method == 'POST':
        # Create appointment as nurse
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        urgency = request.form.get('urgency', 'Routine')
        reason = request.form.get('reason', '')

        # Verify patient is at this PHC
        patient = conn.execute('''
            SELECT user_id, fullname FROM users u
            INNER JOIN patient_logs pl ON u.id = pl.user_id
            WHERE u.id = ? AND pl.phc_id = ?
        ''', (patient_id, current_user.phc_id)).fetchone()

        if not patient:
            flash('Patient not at this PHC', 'error')
            return redirect(url_for('phc_nurse_appointments'))

        # Verify doctor is at this PHC
        doctor = conn.execute('''
            SELECT id, fullname, specialization FROM users
            WHERE id = ? AND phc_id = ? AND role = 'doctor'
        ''', (doctor_id, current_user.phc_id)).fetchone()

        if not doctor:
            flash('Doctor not at this PHC', 'error')
            return redirect(url_for('phc_nurse_appointments'))

        # Create appointment (APPROVED by nurse, not pending)
        conn.execute('''
            INSERT INTO appointments
            (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date,
             appointment_time, symptoms, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Approved')
        ''', (patient_id, patient['fullname'], doctor_id, doctor['fullname'],
              doctor['specialization'] or 'General Medicine', appointment_date, appointment_time,
              reason, f'Urgency: {urgency}'))

        conn.commit()

        # Notify patient
        conn.execute('''
            INSERT INTO messages (sender_id, receiver_id, message)
            VALUES (?, ?, ?)
        ''', (current_user.id, patient_id,
              f'Your appointment with Dr. {doctor["fullname"]} is scheduled for {appointment_date} at {appointment_time}'))
        conn.commit()

        flash(f'Appointment created successfully for {patient["fullname"]}!', 'success')
        return redirect(url_for('phc_nurse_appointments'))

    # GET: Show form to create appointment
    doctors = conn.execute('''
        SELECT id, fullname, specialization FROM users
        WHERE phc_id = ? AND role = 'doctor'
    ''', (current_user.phc_id,)).fetchall()

    patients = conn.execute('''
        SELECT DISTINCT u.id, u.fullname FROM users u
        INNER JOIN patient_logs pl ON u.id = pl.user_id
        WHERE pl.phc_id = ? AND u.role = 'patient'
        ORDER BY u.fullname ASC
    ''', (current_user.phc_id,)).fetchall()

    conn.close()

    return render_template('phc_nurse_create_appointment.html',
                         doctors=doctors,
                         patients=patients,
                         user=current_user)

@app.route('/api/appointments/dates', methods=['GET'])
@login_required
def get_appointment_dates():
    conn = get_db_connection()

    if current_user.role in ('doctor', 'phc_nurse'):
        dates = conn.execute('''
            SELECT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE doctor_id = ? OR status = 'Pending'
            GROUP BY appointment_date
        ''', (current_user.id,)).fetchall()
    else:
        dates = conn.execute('''
            SELECT appointment_date, COUNT(*) as count
            FROM appointments
            WHERE patient_id = ?
            GROUP BY appointment_date
        ''', (current_user.id,)).fetchall()

    conn.close()

    return jsonify([{'date': row['appointment_date'], 'count': row['count']} for row in dates])

# --- HEALTH PROGRESS & REPORTS ---
@app.route('/health-report')
@login_required
def health_report():
    """Patient's personal health progress report"""
    if current_user.role != 'patient':
        flash('This page is only accessible to patients')
        return redirect(get_role_dashboard_redirect())

    conn = get_db_connection()

    # Get all health records for this patient
    health_records = conn.execute('''
        SELECT * FROM patient_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
    ''', (current_user.id,)).fetchall()

    health_records = [dict(row) for row in health_records]

    # Calculate summary statistics
    summary = {}
    score_data = {}

    if health_records:
        # Total checkups
        summary['total_checkups'] = len(health_records)
        summary['last_checkup'] = health_records[0]['timestamp']

        # Calculate average BP
        avg_sys = sum(r['sys_bp'] for r in health_records) / len(health_records)
        avg_dia = sum(r['dia_bp'] for r in health_records) / len(health_records)
        summary['avg_bp'] = f"{int(avg_sys)}/{int(avg_dia)}"

        # BP trend (compare first 30% with last 30%)
        third = len(health_records) // 3
        if third > 0:
            recent_bp = sum(r['sys_bp'] for r in health_records[:third]) / third
            old_bp = sum(r['sys_bp'] for r in health_records[-third:]) / third
            summary['bp_trend'] = 'improved' if recent_bp < old_bp else 'stable'
            summary['bp_trend_text'] = 'Improving' if recent_bp < old_bp else 'Stable'
        else:
            summary['bp_trend'] = 'stable'
            summary['bp_trend_text'] = 'Stable'

        # Calculate average heart rate
        avg_hr = sum(r['hr'] for r in health_records) / len(health_records)
        summary['avg_hr'] = int(avg_hr)
        summary['hr_trend'] = 'stable'
        summary['hr_trend_text'] = 'Normal range'

        # Current risk level (most recent)
        summary['current_risk'] = 'LOW'
        if 'HIGH' in health_records[0]['dual_brain_risk']:
            summary['current_risk'] = 'HIGH'
        elif 'MEDIUM' in health_records[0]['dual_brain_risk']:
            summary['current_risk'] = 'MEDIUM'

        # Risk improvement (compare with older records)
        high_risk_recent = sum(1 for r in health_records[:third] if 'HIGH' in r['dual_brain_risk']) if third > 0 else 0
        high_risk_old = sum(1 for r in health_records[-third:] if 'HIGH' in r['dual_brain_risk']) if third > 0 else 0
        summary['risk_improvement'] = high_risk_recent < high_risk_old

        # Calculate health score
        score_data['overall_score'] = 75  # Base score

        # Risk improvement
        score_data['risk_improvement'] = 'Yes' if summary['risk_improvement'] else 'No'

        # Vitals stability
        score_data['vitals_stability'] = 80

        # Checkup frequency
        score_data['checkup_frequency'] = f"{len(health_records)}"

        # Health trend
        score_data['health_trend'] = '📈 Improving' if summary['risk_improvement'] else '📊 Stable'
    else:
        summary = {
            'total_checkups': 0,
            'last_checkup': 'N/A',
            'avg_bp': 'N/A',
            'bp_trend': 'stable',
            'bp_trend_text': 'No data',
            'avg_hr': 0,
            'hr_trend': 'stable',
            'hr_trend_text': 'No data',
            'current_risk': 'LOW',
            'risk_improvement': False
        }
        score_data = {
            'overall_score': 0,
            'risk_improvement': '0',
            'vitals_stability': 0,
            'checkup_frequency': '0',
            'health_trend': 'No data'
        }

    conn.close()

    # Prepare JSON data for charts
    import json
    chart_data = {
        'labels': [],
        'bp_sys': [],
        'bp_dia': [],
        'hr': [],
        'temp': [],
        'risk': []
    }

    if health_records:
        # Reverse to show chronological order (oldest first)
        for record in reversed(health_records[-30:]):  # Last 30 records
            # Format date
            date_str = record['timestamp'][:10] if record['timestamp'] else 'N/A'
            chart_data['labels'].append(date_str)
            chart_data['bp_sys'].append(record.get('sys_bp', 0) or 0)
            chart_data['bp_dia'].append(record.get('dia_bp', 0) or 0)
            chart_data['hr'].append(record.get('hr', 0) or 0)
            chart_data['temp'].append(record.get('temp', 0) or 0)
            risk = 'HIGH' if 'HIGH' in record.get('dual_brain_risk', '') else ('MEDIUM' if 'MEDIUM' in record.get('dual_brain_risk', '') else 'LOW')
            chart_data['risk'].append(risk)

    chart_data_json = json.dumps(chart_data)

    html = render_template('health_report.html',
                         health_records=health_records,
                         summary=summary,
                         score_data=score_data,
                         chart_data=chart_data_json,
                         user=current_user)

    # Fix CDN URLs - replace jsdelivr with cdnjs if needed
    if 'cdn.jsdelivr.net' in html:
        html = html.replace('cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js',
                           'cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js')

    resp = make_response(html)
    # Aggressive cache busting
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    resp.headers['ETag'] = ''
    resp.headers['Last-Modified'] = ''
    return resp


@app.route('/patients')
@login_required
def patients():
    """Patients list - doctors/nurses/admins can view patients"""
    if current_user.role not in ['doctor', 'nurse', 'admin']:
        flash('This page is only accessible to medical staff')

    conn = get_db_connection()

    # Get patients based on user role
    if current_user.role == 'doctor':
        # Regular doctor sees ONLY their own patients (via appointments)
        patients = conn.execute('''
            SELECT DISTINCT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as appointments_count
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id AND a.doctor_id = ?
            WHERE u.role = 'patient'
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.id,)).fetchall()

    elif current_user.role == 'doctor':
        # Doctor sees their assigned patients
        patients = conn.execute('''
            SELECT DISTINCT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT pl.id) as appointments_count
            FROM users u
            LEFT JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
            WHERE u.role = 'patient' AND pl.phc_id = ?
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.phc_id, current_user.phc_id)).fetchall()

    elif current_user.role == 'phc_nurse':
        # PHC Nurse sees ALL patients from their facility
        patients = conn.execute('''
            SELECT DISTINCT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT pl.id) as appointments_count
            FROM users u
            LEFT JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
            WHERE u.role = 'patient' AND pl.phc_id = ?
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''', (current_user.phc_id, current_user.phc_id)).fetchall()

    else:  # DDHS Admin sees ALL patients
        patients = conn.execute('''
            SELECT
                u.id,
                u.email,
                u.fullname,
                u.phone,
                COUNT(DISTINCT a.id) as appointments_count
            FROM users u
            LEFT JOIN appointments a ON u.id = a.patient_id
            WHERE u.role = 'patient'
            GROUP BY u.id
            ORDER BY u.fullname ASC
        ''').fetchall()

    patient_reports = []
    patient_details = {}

    for patient in patients:
        patient_dict = dict(patient)

        # Get health records for this patient
        records = conn.execute('''
            SELECT * FROM patient_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (patient['id'],)).fetchall()

        records_list = [dict(r) for r in records]
        patient_dict['total_records'] = len(records_list)

        # Determine risk level
        if records_list:
            high_risk_count = sum(1 for r in records_list if 'HIGH' in r.get('dual_brain_risk', ''))
            if high_risk_count > len(records_list) * 0.5:
                patient_dict['risk_level'] = 'high'
            elif high_risk_count > 0:
                patient_dict['risk_level'] = 'medium'
            else:
                patient_dict['risk_level'] = 'low'

            # Calculate health score
            health_score = 100
            if high_risk_count > 0:
                health_score -= (high_risk_count / len(records_list)) * 30

            # Check vitals
            recent_records = records_list[:5]
            for record in recent_records:
                if record['sys_bp'] > 140 or record['dia_bp'] > 90:
                    health_score -= 5
                if record['hr'] < 60 or record['hr'] > 100:
                    health_score -= 5

            patient_dict['health_score'] = max(0, int(health_score))
            patient_dict['last_checkup'] = records_list[0]['timestamp']
        else:
            patient_dict['risk_level'] = 'low'
            patient_dict['health_score'] = 100
            patient_dict['last_checkup'] = 'N/A'

        patient_reports.append(patient_dict)

        # Store detailed records for modal view
        patient_details[patient['id']] = {
            'name': patient['fullname'],
            'email': patient['email'],
            'phone': patient['phone'],
            'records': records_list
        }

    # Calculate overall statistics
    total_patients = len(patient_reports)
    total_records = sum(p['total_records'] for p in patient_reports)
    high_risk_patients = sum(1 for p in patient_reports if p['risk_level'] == 'high')

    # Recent checkups (last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    recent_checkups = conn.execute('''
        SELECT COUNT(*) as count FROM patient_logs
        WHERE timestamp >= ?
    ''', (week_ago,)).fetchone()

    # Average health score
    avg_health_score = int(sum(p['health_score'] for p in patient_reports) / total_patients) if total_patients > 0 else 0

    stats = {
        'total_patients': total_patients,
        'total_records': total_records,
        'high_risk_patients': high_risk_patients,
        'recent_checkups': recent_checkups['count'],
        'avg_health_score': avg_health_score
    }

    conn.close()

    # DEBUG: Verify patient_details has records
    for pid, details in patient_details.items():
        print(f"[DEBUG] Patient {pid}: {len(details.get('records', []))} records")

    return render_template('reports.html',
                         patient_reports=patient_reports,
                         patient_details=patient_details,
                         stats=stats,
                         user=current_user)

# --- AI CHECKUP ROUTES ---
@app.route('/checkup')
@login_required
def checkup():
    """AI health checkup - NOW CONDUCTED BY NURSE, not patients"""
    if current_user.role == 'patient':
        # Patients no longer self-diagnose - Nurse will conduct checkup
        flash('Health assessments are conducted by your PHC nurse. Please visit your local PHC for a checkup.', 'info')
        return redirect(url_for('patient_dashboard'))
    elif current_user.role == 'phc_nurse':
        # Nurse conducts checkup for patients at their facility using comprehensive form
        conn = get_db_connection()
        patients = conn.execute('''
            SELECT DISTINCT u.id, u.fullname FROM users u
            INNER JOIN patient_logs pl ON u.id = pl.user_id
            WHERE pl.phc_id = ? AND u.role = 'patient'
            ORDER BY u.fullname
        ''', (current_user.phc_id,)).fetchall()
        conn.close()
        patients = [dict(row) for row in patients]
        return render_template('phc_nurse_intake_comprehensive.html', patients=patients, user=current_user)
    else:
        flash('Checkup access denied')
        return redirect(get_role_dashboard_redirect())

@app.route('/phc/nurse/checkup_result')
@login_required
def phc_nurse_checkup_result():
    """Show AI checkup results for a specific patient (for nurses)"""
    if current_user.role != 'phc_nurse':
        flash('Access denied')
        return redirect(url_for('index'))

    patient_id = request.args.get('patient_id')
    if not patient_id:
        flash('Patient ID required')
        return redirect(url_for('phc_nurse_dashboard'))

    conn = get_db_connection()
    # Get latest log for this patient
    log = conn.execute('''
        SELECT * FROM patient_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (patient_id,)).fetchone()
    conn.close()

    if not log:
        flash('No results found for this patient')
        return redirect(url_for('phc_nurse_dashboard'))

    result = dict(log)
    # Format vitals for the template which expects result.vitals object
    result['vitals'] = {
        'bp': f"{result.get('sys_bp', 120)}/{result.get('dia_bp', 80)}",
        'hr': result.get('hr', 72),
        'temp': result.get('temp', 98.6),
        'respiration_rate': result.get('respiration_rate', 16),
        'spo2': result.get('spo2', 98)
    }
    # Map other fields
    result['risk_level'] = result.get('dual_brain_risk', 'LOW')
    result['score'] = result.get('risk_score', 0)
    result['disease_recognized'] = result.get('disease_input') or result.get('recommended_specialist')
    result['pain_intensity'] = result.get('pain_intensity')
    result['symptom_duration'] = result.get('symptom_duration')
    
    # Extract reasoning if available (you might need to fetch this from elsewhere if not in DB, 
    # but for now we'll pass the DB fields)
    if 'final_risk' in result and isinstance(result['final_risk'], str):
        # The reasoning might be stored in the DB if you add a column, 
        # for now let's use the disease_input as a proxy for 'identified'
        pass
    
    return render_template('checkup_result.html', result=result, user=current_user)

@app.route('/checkup/result')

@login_required
def checkup_result():
    """Show AI checkup results to patient"""
    if current_user.role != 'patient':
        flash('Access denied')
        return redirect(url_for('index'))

    result = session.get('last_checkup_result')

    if result:
        # Clear the result from session after displaying once
        session.pop('last_checkup_result', None)

    return render_template('checkup_result.html', result=result, user=current_user)

# --- MESSAGES/CHAT ROUTES ---
@app.route('/messages')
@login_required
def messages():
    """Messages/chat interface for doctors and patients"""
    conn = get_db_connection()

    # Get list of contacts based on user role
    if current_user.role == 'doctor':
        # Doctor sees their own patients AND all doctors/admins for collaboration
        try:
            # Get patients from appointments
            patients = conn.execute('''
                SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                       (SELECT COUNT(*) FROM messages
                        WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
                FROM users u
                INNER JOIN appointments a ON u.id = a.patient_id AND a.doctor_id = ?
                WHERE u.role = 'patient'
                ORDER BY u.fullname ASC
            ''', (current_user.id, current_user.id)).fetchall()

            # Also get all other doctors and admins
            doctors = conn.execute('''
                SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                       (SELECT COUNT(*) FROM messages
                        WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
                FROM users u
                WHERE u.role IN ('doctor', 'ddhs_admin') AND u.id != ?
                ORDER BY u.fullname ASC
            ''', (current_user.id, current_user.id)).fetchall()

            # Combine both lists
            contacts = list(patients) + list(doctors)
        except Exception as e:
            print(f"Error loading doctor contacts: {e}")
            contacts = []

    elif current_user.role == 'phc_nurse':
        # PHC Nurse sees patients from their facility
        try:
            contacts = conn.execute('''
                SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                       (SELECT COUNT(*) FROM messages
                        WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
                FROM users u
                INNER JOIN patient_logs pl ON u.id = pl.user_id AND pl.phc_id = ?
                WHERE u.role = 'patient'
                GROUP BY u.id
                ORDER BY u.fullname ASC
            ''', (current_user.id, current_user.phc_id)).fetchall()
        except Exception as e:
            print(f"Error loading phc_nurse contacts: {e}")
            contacts = []

    elif current_user.role == 'ddhs_admin':
        # DDHS Admin sees all contacts
        try:
            contacts = conn.execute('''
                SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                       (SELECT COUNT(*) FROM messages
                        WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
                FROM users u
                WHERE u.role IN ('patient', 'doctor', 'phc_nurse')
                ORDER BY u.fullname ASC
            ''', (current_user.id,)).fetchall()
        except Exception as e:
            print(f"Error loading admin contacts: {e}")
            contacts = []

    else:
        # Patients see all doctors (regular, PHC, and admin)
        try:
            contacts = conn.execute('''
                SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                       (SELECT COUNT(*) FROM messages
                        WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
                FROM users u
                WHERE u.role IN ('doctor', 'ddhs_admin')
                ORDER BY u.fullname ASC
            ''', (current_user.id,)).fetchall()
        except Exception as e:
            print(f"Error loading patient contacts: {e}")
            contacts = []

    contacts = [dict(row) for row in contacts]

    conn.close()

    return render_template('messages.html', contacts=contacts, user=current_user)

@app.route('/api/messages/<int:contact_id>')
@login_required
def get_messages(contact_id):
    """Get all messages with a specific contact"""
    conn = get_db_connection()

    # Get messages between current user and contact
    messages = conn.execute('''
        SELECT m.*,
               sender.fullname as sender_name,
               receiver.fullname as receiver_name
        FROM messages m
        JOIN users sender ON m.sender_id = sender.id
        JOIN users receiver ON m.receiver_id = receiver.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
    ''', (current_user.id, contact_id, contact_id, current_user.id)).fetchall()

    messages = [dict(row) for row in messages]

    # Mark messages as read
    conn.execute('''
        UPDATE messages
        SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (contact_id, current_user.id))
    conn.commit()

    conn.close()

    return jsonify(messages)

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    """Send a message to another user"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message = data.get('message')

    if not receiver_id or not message:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()

    # Verify receiver exists
    receiver = conn.execute('SELECT id FROM users WHERE id = ?', (receiver_id,)).fetchone()
    if not receiver:
        conn.close()
        return jsonify({'error': 'Receiver not found'}), 404

    # Insert message
    conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (current_user.id, receiver_id, message))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# --- 11. CHATBOT API ---
# PriorityMed AI Chatbot Route - Enhanced Conversational Intelligence
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """
    PriorityMed AI - Smart Clinical Triage Assistant
    Conversational, intelligent, and medically responsible
    """
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'response': "I'm here to help! Could you describe the symptoms or situation you're dealing with?"})

    message_lower = message.lower()

    # --- 1. DETECT EMERGENCY SITUATIONS ---
    emergency_keywords = [
        'chest pain', 'heart attack', 'stroke', 'can\'t breathe', 'cannot breathe',
        'difficulty breathing', 'severe bleeding', 'unconscious', 'seizure',
        'severe head injury', 'suicide', 'overdose', 'choking', 'severe burn'
    ]

    is_emergency = any(keyword in message_lower for keyword in emergency_keywords)

    if is_emergency:
        return jsonify({'response': generate_emergency_response(message_lower)})

    # --- 2. INTELLIGENT SYMPTOM ANALYSIS ---
    analysis = analyze_symptoms(message_lower)

    # --- 3. GENERATE CONVERSATIONAL RESPONSE ---
    response = generate_conversational_response(message, analysis)

    return jsonify({'response': response})

def analyze_symptoms(message):
    """
    Intelligent symptom analysis with context awareness
    Returns: dict with risk_level, department, factors, confidence
    """
    analysis = {
        'risk_level': 'LOW',
        'department': 'General Medicine',
        'factors': [],
        'confidence': 'Moderate',
        'symptom_count': 0
    }

    # Symptom categories with severity weights
    symptoms = {
        'cardiovascular': {
            'keywords': ['chest pain', 'heart', 'palpitation', 'irregular heartbeat', 'chest pressure', 'chest tightness'],
            'risk': 'HIGH',
            'department': 'Cardiology',
            'weight': 3
        },
        'neurological': {
            'keywords': ['headache', 'dizzy', 'dizziness', 'numb', 'numbness', 'slurred speech', 'confusion', 'memory loss', 'seizure', 'tremor'],
            'risk': 'HIGH',
            'department': 'Neurology',
            'weight': 3
        },
        'respiratory': {
            'keywords': ['cough', 'shortness of breath', 'wheezing', 'breathing difficulty', 'chest congestion', 'asthma'],
            'risk': 'MEDIUM',
            'department': 'Pulmonology',
            'weight': 2
        },
        'ophthalmology': {
            'keywords': ['eye', 'vision', 'blur', 'blurry', 'blind', 'eye pain', 'double vision', 'seeing spots'],
            'risk': 'MEDIUM',
            'department': 'Ophthalmology',
            'weight': 2
        },
        'orthopedic': {
            'keywords': ['bone', 'fracture', 'break', 'sprain', 'joint pain', 'back pain', 'leg pain', 'arm pain', 'knee pain'],
            'risk': 'MEDIUM',
            'department': 'Orthopedics',
            'weight': 2
        },
        'gastrointestinal': {
            'keywords': ['stomach', 'abdominal pain', 'nausea', 'vomiting', 'diarrhea', 'constipation', 'bloating'],
            'risk': 'MEDIUM',
            'department': 'Gastroenterology',
            'weight': 2
        },
        'infection': {
            'keywords': ['fever', 'chills', 'infection', 'rash', 'sore throat', 'flu', 'cold', 'runny nose'],
            'risk': 'LOW',
            'department': 'General Medicine',
            'weight': 1
        },
        'general': {
            'keywords': ['fatigue', 'weakness', 'tired', 'malaise', 'body ache', 'pain'],
            'risk': 'LOW',
            'department': 'General Medicine',
            'weight': 1
        }
    }

    # Severity indicators
    severity_high = ['severe', 'extreme', 'unbearable', 'worst', 'intense', 'acute', 'sudden']
    severity_moderate = ['moderate', 'persistent', 'constant', 'ongoing', 'chronic']

    # Analyze message for symptoms
    detected_categories = []
    total_weight = 0

    for category, info in symptoms.items():
        for keyword in info['keywords']:
            if keyword in message:
                detected_categories.append(category)
                total_weight += info['weight']
                analysis['factors'].append(keyword.title())
                analysis['symptom_count'] += 1

                # Update department and risk
                if info['weight'] >= 3:
                    analysis['department'] = info['department']
                    analysis['risk_level'] = info['risk']
                elif analysis['risk_level'] == 'LOW':
                    analysis['department'] = info['department']
                    analysis['risk_level'] = info['risk']
                break

    # Check for severity modifiers
    has_severe = any(word in message for word in severity_high)
    has_moderate = any(word in message for word in severity_moderate)

    if has_severe:
        if analysis['risk_level'] == 'LOW':
            analysis['risk_level'] = 'MEDIUM'
        elif analysis['risk_level'] == 'MEDIUM':
            analysis['risk_level'] = 'HIGH'
        analysis['factors'].append('Severe symptoms reported')

    # Multiple symptoms = escalate risk
    if analysis['symptom_count'] >= 3:
        if analysis['risk_level'] == 'LOW':
            analysis['risk_level'] = 'MEDIUM'
        analysis['factors'].append('Multiple symptoms present')
        analysis['confidence'] = 'High'
    elif analysis['symptom_count'] >= 2:
        analysis['confidence'] = 'Moderate'
    else:
        analysis['confidence'] = 'Moderate'

    # Vital signs analysis
    if 'blood pressure' in message or 'bp' in message:
        # Try to extract BP values
        import re
        bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', message)
        if bp_match:
            systolic = int(bp_match.group(1))
            diastolic = int(bp_match.group(2))

            if systolic >= 180 or diastolic >= 120:
                analysis['risk_level'] = 'HIGH'
                analysis['department'] = 'Cardiology'
                analysis['factors'].append('Hypertensive crisis (BP: {}/{})'.format(systolic, diastolic))
            elif systolic >= 140 or diastolic >= 90:
                if analysis['risk_level'] == 'LOW':
                    analysis['risk_level'] = 'MEDIUM'
                analysis['factors'].append('Elevated blood pressure')

    if 'temperature' in message or 'temp' in message or 'fever' in message:
        import re
        temp_match = re.search(r'(\d{2,3}(?:\.\d)?)', message)
        if temp_match:
            temp = float(temp_match.group(1))
            if temp >= 103:
                if analysis['risk_level'] == 'LOW':
                    analysis['risk_level'] = 'MEDIUM'
                analysis['factors'].append('High fever ({}°F)'.format(temp))

    return analysis

def generate_emergency_response(message):
    """Generate urgent response for emergency situations"""
    acknowledgments = [
        "I understand this is urgent.",
        "This sounds serious.",
        "I'm flagging this as high priority."
    ]

    import random
    ack = random.choice(acknowledgments)

    response = f"{ack} **Based on what you've described, this requires immediate medical attention.**\n\n"
    response += "**🚨 EMERGENCY TRIAGE RESULT:**\n\n"
    response += "- **Risk Level:** HIGH (Emergency)\n"
    response += "- **Recommended:** Emergency Department\n"
    response += "- **Action Required:** Immediate evaluation\n\n"
    response += "**Please proceed to the Emergency Department immediately** or call emergency services if the patient is not already in the hospital.\n\n"
    response += "*This appears consistent with a potentially life-threatening condition that needs urgent assessment.*"

    return response

def generate_conversational_response(message, analysis):
    """
    Generate natural, conversational response with medical intelligence
    """
    # Natural acknowledgments
    acknowledgments = [
        "I understand.",
        "I see.",
        "Thank you for sharing that.",
        "Okay, let's look at this.",
        "Got it.",
        "Alright, here's what I'm seeing."
    ]

    import random
    ack = random.choice(acknowledgments)

    # Build conversational response
    response = f"{ack} "

    # Risk-based opening
    if analysis['risk_level'] == 'HIGH':
        response += "Based on what you've shared, **this situation needs prompt attention**.\n\n"
    elif analysis['risk_level'] == 'MEDIUM':
        response += "Based on the symptoms described, **this should be evaluated soon** to prevent potential complications.\n\n"
    else:
        response += "From what you've described, this appears to be a **lower-risk situation**, though it still warrants medical attention.\n\n"

    # Explain reasoning naturally
    if analysis['factors']:
        response += "Here's what I'm seeing: "
        if len(analysis['factors']) == 1:
            response += f"the patient is experiencing {analysis['factors'][0].lower()}. "
        elif len(analysis['factors']) == 2:
            response += f"the patient has {analysis['factors'][0].lower()} and {analysis['factors'][1].lower()}. "
        else:
            factors_text = ', '.join(analysis['factors'][:-1])
            response += f"the patient is presenting with {factors_text.lower()}, and {analysis['factors'][-1].lower()}. "

        # Add context
        if analysis['symptom_count'] >= 3:
            response += "The combination of multiple symptoms suggests this needs medical evaluation. "

        response += "\n\n"

    # Department recommendation with reasoning
    response += f"I recommend consulting with **{analysis['department']}**"

    # Add reasoning for department choice
    dept_reasoning = {
        'Cardiology': ' for cardiovascular assessment',
        'Neurology': ' for neurological evaluation',
        'Ophthalmology': ' for eye-related concerns',
        'Orthopedics': ' for musculoskeletal issues',
        'Pulmonology': ' for respiratory evaluation',
        'Gastroenterology': ' for digestive system concerns',
        'General Medicine': ' for initial evaluation'
    }

    response += dept_reasoning.get(analysis['department'], '') + ".\n\n"

    # Structured triage result
    response += "**📋 TRIAGE ASSESSMENT:**\n\n"
    response += f"- **Risk Level:** {analysis['risk_level']}\n"
    response += f"- **Recommended Department:** {analysis['department']}\n"

    if analysis['factors']:
        response += f"- **Key Factors:** {', '.join(analysis['factors'][:3])}\n"

    response += f"- **Confidence:** {analysis['confidence']}\n\n"

    # Appropriate closing based on risk
    if analysis['risk_level'] == 'HIGH':
        response += "[WARN] **This patient should be seen promptly.** The symptoms suggest a condition that may worsen without timely intervention."
    elif analysis['risk_level'] == 'MEDIUM':
        response += "💡 **Recommend evaluation within the next few hours** to ensure proper care and prevent complications."
    else:
        response += "[OK] **Standard consultation recommended.** While this appears less urgent, medical evaluation is still important."

    response += "\n\n*I'm here to assist with triage prioritization. This assessment helps guide care decisions but is not a final diagnosis.*"

    return response

# Medical Document Upload and Parsing Route
@app.route('/api/upload-medical-doc', methods=['POST'])
@login_required
def upload_medical_doc():
    """
    Upload medical document (PDF, image, text) and extract patient information
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Get file extension
        filename = file.filename.lower()
        print(f"--- [DEBUG] Processing file: {filename} ---")

        # Extract text based on file type
        extracted_text = ""

        # Helper to extract standard fields from a row (dict-like)
        def extract_patient_data(row, keys):
            print(f"--- [DEBUG] Available columns: {list(keys)} ---")
            print(f"--- [DEBUG] Row data: {dict(row) if hasattr(row, 'items') else row} ---")

            def get_val(col_variations):
                for col in col_variations:
                    # Case-insensitive column search with stripped whitespace and units
                    match = None
                    for key in keys:
                        # Remove units in parentheses (e.g., "Heart Rate (bpm)" -> "Heart Rate")
                        clean_key = str(key).split('(')[0].strip().lower().replace(' ', '').replace('_', '')
                        clean_col = str(col).lower().strip().replace(' ', '').replace('_', '')

                        if clean_key == clean_col:
                            match = key
                            break

                    # Check if key exists and value is not empty/NaN
                    if match:
                        val = row[match]
                        print(f"--- [DEBUG] Matched column '{match}' for '{col}': value = '{val}' (type: {type(val).__name__}) ---")
                        # Handle pandas NaN or empty strings (but not numeric 0)
                        if pd.isna(val):
                            print(f"--- [DEBUG] Value is NaN, skipping ---")
                            continue
                        if isinstance(val, str) and not val.strip():
                            print(f"--- [DEBUG] Value is empty string, skipping ---")
                            continue
                        result = str(val).strip()
                        print(f"--- [DEBUG] Returning value: '{result}' ---")
                        return result
                print(f"--- [DEBUG] No match found for variations: {col_variations} ---")
                return ""

            data = {
                'age': get_val(['Age', 'Age (Years)', 'Patient Age']),
                'gender': get_val(['Gender', 'Sex']),
                'heart_rate': get_val(['Heart Rate', 'HR', 'Pulse', 'Heart_Rate', 'HeartRate', 'heart rate']),
                'temperature': get_val(['Temperature', 'Temp', 'Body Temp', 'Body Temperature', 'Temperatur', 'temperature']),
                'symptoms': get_val(['Current Symptoms', 'Symptoms', 'Complaint', 'Chief Complaint', 'Current Sy']),
                'medical_history': get_val(['Pre-existing Conditions', 'Medical History', 'History', 'Conditions', 'Pre-existing'])
            }

            # Specialized handling for BP
            sys_bp = get_val(['Systolic BP', 'Systolic', 'SBP', 'Systolic_BP', 'systolic bp', 'Systolic Bp'])
            dia_bp = get_val(['Diastolic BP', 'Diastolic', 'DBP', 'Diastolic_BP', 'diastolic bp', 'Diastolic Bp'])
            print(f"--- [DEBUG] Systolic BP: '{sys_bp}', Diastolic BP: '{dia_bp}' ---")
            if sys_bp and dia_bp:
                data['blood_pressure'] = f"{sys_bp}/{dia_bp}"
            else:
                data['blood_pressure'] = get_val(['Blood Pressure', 'BP'])

            print(f"--- [DEBUG] Final extracted data: {data} ---")
            return data

        if filename.endswith('.txt'):
            print("--- [DEBUG] Handling TXT file ---")
            # Read text file directly
            extracted_text = file.read().decode('utf-8', errors='ignore')

        elif filename.endswith('.csv'):
            print("--- [DEBUG] Handling CSV file ---")
            import csv
            import io

            csv_data = file.read().decode('utf-8', errors='ignore')
            csv_reader = csv.DictReader(io.StringIO(csv_data))

            try:
                row = next(csv_reader)
                print(f"--- [DEBUG] CSV columns: {list(row.keys())} ---")
                print(f"--- [DEBUG] CSV first row: {row} ---")
                extracted_data = extract_patient_data(row, row.keys())
                print(f"--- [DEBUG] Extracted data: {extracted_data} ---")

                # Create a text summary
                extracted_text = "Extracted from CSV:\n"
                for k, v in extracted_data.items():
                    if v:
                        extracted_text += f"{k.replace('_', ' ').title()}: {v}\n"

                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'parsed_data': extracted_data
                })
            except StopIteration:
                 return jsonify({'success': False, 'error': 'CSV file is empty'}), 400
            except Exception as e:
                print(f"--- [DEBUG] CSV Error: {e} ---")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'error': f'CSV parsing failed: {str(e)}'}), 500

        elif filename.endswith(('.xlsx', '.xls')):
            print("--- [DEBUG] Handling Excel file ---")
            try:
                # Read Excel
                df = pd.read_excel(file)
                print(f"--- [DEBUG] Excel columns: {list(df.columns)} ---")
                print(f"--- [DEBUG] Excel shape: {df.shape} ---")
                print(f"--- [DEBUG] First row: {df.iloc[0].to_dict() if not df.empty else 'Empty'} ---")

                # Check if empty
                if df.empty:
                    return jsonify({'success': False, 'error': 'Excel file is empty'}), 400

                # Get first row data
                row = df.iloc[0]
                extracted_data = extract_patient_data(row, df.columns)
                print(f"--- [DEBUG] Extracted data: {extracted_data} ---")

                # Create a text summary
                extracted_text = "Extracted from Excel:\n"
                for k, v in extracted_data.items():
                    if v:
                        extracted_text += f"{k.replace('_', ' ').title()}: {v}\n"

                # Return parsed data directly
                print(f"--- [DEBUG] Excel parsed successfully ---")
                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'parsed_data': extracted_data
                })

            except ImportError as ie:
                print(f"--- [DEBUG] Excel Import Error: {ie} ---")
                return jsonify({'success': False, 'error': 'pandas or openpyxl library not installed. Please install: pip install pandas openpyxl'}), 500
            except Exception as e:
                print(f"--- [DEBUG] Excel Error: {e} ---")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'error': f'Excel parsing failed: {str(e)}'}), 500

        elif filename.endswith('.pdf'):
            print("--- [DEBUG] Handling PDF file ---")
            # Extract text from PDF
            try:
                import PyPDF2
                import io
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
                print(f"--- [DEBUG] PDF extracted {len(extracted_text)} chars ---")
            except Exception as e:
                print(f"--- [DEBUG] PDF Error: {e} ---")
                return jsonify({'success': False, 'error': f'PDF extraction failed: {str(e)}'}), 500

        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            print("--- [DEBUG] Handling Image file ---")
            # OCR for images
            try:
                import pytesseract
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(file.read()))
                extracted_text = pytesseract.image_to_string(image)
                print(f"--- [DEBUG] OCR extracted {len(extracted_text)} chars ---")
            except Exception as e:
                print(f"--- [DEBUG] OCR Error: {e} ---")
                # If OCR libraries not available, provide fallback
                return jsonify({
                    'success': False,
                    'error': 'OCR not available. Please install pytesseract and Tesseract-OCR.'
                }), 500

        else:
            print("--- [DEBUG] Unsupported file type ---")
            return jsonify({'success': False, 'error': 'Unsupported file type. Use PDF, PNG, JPG, TXT, CSV, or Excel (.xlsx/.xls)'}), 400

        # Parse extracted text to find patient information
        print("--- [DEBUG] Parsing extracted text ---")
        parsed_data = parse_medical_text(extracted_text)
        print(f"--- [DEBUG] Parsed data: {parsed_data} ---")

        return jsonify({
            'success': True,
            'extracted_text': extracted_text[:500],  # First 500 chars for preview
            'parsed_data': parsed_data
        })

    except Exception as e:
        print(f"--- [DEBUG] General Upload Error: {e} ---")
        return jsonify({'success': False, 'error': str(e)}), 500

def parse_medical_text(text):
    """
    Parse medical text to extract patient information using regex and keywords
    """
    import re

    parsed = {
        'age': '',
        'gender': '',
        'symptoms': '',
        'blood_pressure': '',
        'heart_rate': '',
        'temperature': '',
        'medical_history': ''
    }

    text_lower = text.lower()

    # helper to clean extracted values
    def clean_val(v):
        return v.strip().strip('.').strip()

    # --- 1. Extract Age ---
    age_patterns = [
        r'age[:\s]+(\d{1,3})',
        r'(\d{1,3})\s*(?:years?|yrs?|y/?o)\s*old',
        r'(\d{1,3})\s*(?:years?|yrs?)',
        r'patient\s+is\s+a\s+(\d{1,3})\s*year\s*old',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, text_lower)
        if match:
            age = int(match.group(1))
            if 0 < age < 120:
                parsed['age'] = str(age)
                break

    # --- 2. Extract Gender ---
    if re.search(r'\b(male|man|boy|m)\b', text_lower) and not re.search(r'\bfemale\b', text_lower):
        parsed['gender'] = 'Male'
    elif re.search(r'\b(female|woman|girl|f)\b', text_lower):
        parsed['gender'] = 'Female'

    # --- 3. Extract Blood Pressure ---
    # Matches: BP: 120/80, BP 120/80, 120/80 mmHg, 120/80
    bp_patterns = [
        r'(?:bp|blood\s*pressure)[:\s]*(\d{2,3})[\s/-]+(\d{2,3})',
        r'(\d{2,3})[\s/-]+(\d{2,3})\s*mmhg'
    ]
    for pattern in bp_patterns:
        bp_match = re.search(pattern, text_lower)
        if bp_match:
            parsed['blood_pressure'] = f"{bp_match.group(1)}/{bp_match.group(2)}"
            break

    # --- 4. Extract Heart Rate ---
    # Matches: HR: 80, Pulse 80, 80 bpm, Heart Rate: 80
    hr_patterns = [
        r'(?:hr|heart\s*rate|pulse)[:\s]*(\d{2,3})',
        r'(\d{2,3})\s*bpm',
        r'rate[:\s]*(\d{2,3})'
    ]
    for pattern in hr_patterns:
        hr_match = re.search(pattern, text_lower)
        if hr_match:
            hr = int(hr_match.group(1))
            if 30 < hr < 250:
                parsed['heart_rate'] = str(hr)
                break

    # --- 5. Extract Temperature ---
    # Matches: Temp: 98.6, T: 98.6, 98.6 F, 37 C
    temp_patterns = [
        r'(?:temp|temperature|t)[:\s]*(\d{2,3}(?:\.\d)?)',
        r'(\d{2,3}(?:\.\d)?)\s*°?[cf]',
        r'(\d{2,3}(?:\.\d)?)\s*degrees'
    ]
    for pattern in temp_patterns:
        temp_match = re.search(pattern, text_lower)
        if temp_match:
            parsed['temperature'] = temp_match.group(1)
            break

    # --- 6. Extract Symptoms ---
    # Expanded keyword list
    symptom_keywords = [
        'fever', 'cough', 'headache', 'pain', 'nausea', 'vomiting', 'diarrhea',
        'fatigue', 'dizziness', 'shortness of breath', 'breathlessness', 'dyspnea',
        'chest pain', 'palpitations', 'swelling', 'edema', 'rash', 'itching',
        'sore throat', 'runny nose', 'congestion', 'sneezing', 'chills', 'sweats',
        'numbness', 'tingling', 'weakness', 'confusion', 'fainting', 'seizure',
        'bleeding', 'bruising', 'anxiety', 'depression', 'insomnia', 'loss of appetite',
        'abdominal', 'stomach', 'back', 'joint', 'muscle', 'vision', 'hearing'
    ]

    # Try to capture context around keywords (sentence or phrase)
    found_symptoms = set()
    sentences = re.split(r'[.!?;]', text_lower)

    for sentence in sentences:
        for keyword in symptom_keywords:
            if keyword in sentence:
                # Clean up the sentence/phrase for better display
                clean_sentence = sentence.strip()
                if len(clean_sentence) < 100: # reasonable length
                     found_symptoms.add(clean_sentence.capitalize())
                else:
                     # fallback to just keyword if sentence is too long (likely full paragraph)
                     found_symptoms.add(keyword.title())

    if found_symptoms:
        parsed['symptoms'] = '; '.join(list(found_symptoms)[:5])

    # --- 7. Extract Medical History ---
    history_keywords = [
        'diabetes', 'hypertension', 'asthma', 'copd', 'heart disease',
        'kidney disease', 'liver disease', 'cancer', 'stroke', 'arthritis',
        'allergies', 'epilepsy', 'thyroid', 'cholesterol', 'gerd', 'ulcer',
        'migraine', 'depression', 'anxiety', 'tuberculosis', 'hepatitis'
    ]
    found_history = []
    for condition in history_keywords:
        if condition in text_lower:
             # Basic context check: exclude "no history of X"
             if f"no history of {condition}" not in text_lower and f"neg for {condition}" not in text_lower:
                 found_history.append(condition.title())

    if found_history:
        parsed['medical_history'] = ', '.join(found_history[:5])

    return parsed

@app.route('/api/patient-records/<int:patient_id>')
@login_required
def get_patient_records(patient_id):
    """
    Fetch patient health records for doctor review before appointment approval
    """
    try:
        # Verify user is a doctor
        if current_user.role not in ('doctor',):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        conn = get_db_connection()

        # Get patient info
        patient = conn.execute(
            'SELECT id, fullname FROM users WHERE id = ? AND role = "patient"',
            (patient_id,)
        ).fetchone()

        if not patient:
            return jsonify({'success': False, 'error': 'Patient not found'}), 404

        # Get patient health records (from triage_logs table)
        records = conn.execute('''
            SELECT
                id,
                datetime(timestamp) as timestamp,
                sys_bp,
                dia_bp,
                hr,
                temp,
                symptoms,
                dual_brain_risk,
                routing
            FROM triage_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (patient_id,)).fetchall()

        conn.close()

        # Convert records to list of dicts
        records_list = []
        for record in records:
            records_list.append({
                'id': record['id'],
                'timestamp': record['timestamp'],
                'sys_bp': record['sys_bp'] or '—',
                'dia_bp': record['dia_bp'] or '—',
                'hr': record['hr'] or '—',
                'temp': record['temp'] or '—',
                'symptoms': record['symptoms'] or 'None reported',
                'dual_brain_risk': record['dual_brain_risk'] or 'LOW',
                'routing': record['routing'] or '—'
            })

        return jsonify({
            'success': True,
            'patient_name': patient['fullname'],
            'records': records_list
        })

    except Exception as e:
        app.logger.error(f"Error fetching patient records: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ===== DDHS ADMIN ROUTES =====
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """DDHS Admin Dashboard - Emergency Management System"""
    if current_user.role not in ['admin', 'ddhs_admin']:
        flash('Access denied - this page is for admin only')
        return redirect(url_for('index'))

    return render_template('admin_dashboard.html', user=current_user)


@app.route('/api/emergency/cases', methods=['GET'])
@login_required
def get_emergency_cases():
    """Get all high-risk emergency cases from checkup results"""
    try:
        conn = get_db_connection()

        # Get high-risk checkup results (risk score >= 70 or risk_level = 'URGENT')
        cases = conn.execute("""
            SELECT
                cr.id,
                cr.user_id,
                p.fullname as patient_name,
                cr.symptoms,
                cr.dual_brain_risk as risk_level,
                CAST(COALESCE(cr.overall_risk_score, 0) as INTEGER) as risk_score,
                cr.location,
                COALESCE(cr.status, 'pending') as status,
                datetime(cr.timestamp, 'localtime') as timestamp
            FROM checkup_results cr
            LEFT JOIN patients p ON cr.user_id = p.user_id
            WHERE CAST(COALESCE(cr.overall_risk_score, 0) as INTEGER) >= 70
                OR cr.dual_brain_risk = 'HIGH'
                OR cr.dual_brain_risk = 'CRITICAL'
            ORDER BY cr.timestamp DESC
            LIMIT 50
        """).fetchall()

        conn.close()

        cases_list = []
        for case in cases:
            cases_list.append({
                'id': case['id'],
                'user_id': case['user_id'],
                'patient_name': case['patient_name'] or 'Unknown',
                'symptoms': case['symptoms'] or 'None reported',
                'risk_level': case['risk_level'] or 'high',
                'risk_score': case['risk_score'],
                'location': case['location'] or 'Not provided',
                'status': case['status'],
                'timestamp': case['timestamp']
            })

        return jsonify(cases_list)

    except Exception as e:
        app.logger.error(f"Error fetching emergency cases: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/emergency/dispatch', methods=['POST'])
@login_required
def dispatch_ambulance():
    """Dispatch an ambulance for an emergency case"""
    try:
        if current_user.role not in ['admin', 'ddhs_admin']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()

        # Validate required fields
        required_fields = ['case_id', 'ambulance_id', 'hospital_id', 'priority']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400

        conn = get_db_connection()

        # Create dispatch record
        conn.execute("""
            INSERT INTO ambulance_dispatch (case_id, ambulance_id, paramedic_id, hospital_id, priority, status, notes, dispatched_by, dispatched_at)
            VALUES (?, ?, ?, ?, ?, 'dispatched', ?, ?, datetime('now'))
        """, (
            data['case_id'],
            data['ambulance_id'],
            data.get('paramedic_id'),
            data['hospital_id'],
            data['priority'],
            data.get('notes', ''),
            current_user.id
        ))

        # Update case status
        conn.execute("""
            UPDATE checkup_results
            SET status = 'dispatched'
            WHERE id = ?
        """, (data['case_id'],))

        conn.commit()
        conn.close()

        app.logger.info(f"Ambulance dispatched for case {data['case_id']} by admin {current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Ambulance dispatched successfully',
            'dispatch_id': conn.lastrowid
        })

    except Exception as e:
        app.logger.error(f"Error dispatching ambulance: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/emergency/case/<int:case_id>', methods=['GET'])
@login_required
def get_case_details(case_id):
    """Get details of a specific emergency case"""
    try:
        conn = get_db_connection()

        case = conn.execute("""
            SELECT
                cr.id,
                cr.user_id,
                p.fullname as patient_name,
                p.age,
                p.gender,
                p.blood_type,
                cr.symptoms,
                cr.sys_bp,
                cr.dia_bp,
                cr.hr,
                cr.temp,
                cr.respiration,
                cr.spo2,
                cr.dual_brain_risk,
                CAST(COALESCE(cr.overall_risk_score, 0) as INTEGER) as risk_score,
                cr.location,
                cr.status,
                datetime(cr.timestamp, 'localtime') as timestamp
            FROM checkup_results cr
            LEFT JOIN patients p ON cr.user_id = p.user_id
            WHERE cr.id = ?
        """, (case_id,)).fetchone()

        if not case:
            return jsonify({'error': 'Case not found'}), 404

        # Get dispatch info if exists
        dispatch = conn.execute("""
            SELECT * FROM ambulance_dispatch
            WHERE case_id = ?
            ORDER BY dispatched_at DESC
            LIMIT 1
        """, (case_id,)).fetchone()

        conn.close()

        return jsonify({
            'id': case['id'],
            'patient_name': case['patient_name'],
            'age': case['age'],
            'gender': case['gender'],
            'blood_type': case['blood_type'],
            'symptoms': case['symptoms'],
            'vitals': {
                'bp': f"{case['sys_bp']}/{case['dia_bp']}",
                'hr': case['hr'],
                'temp': case['temp'],
                'respiration': case['respiration'],
                'spo2': case['spo2']
            },
            'risk_level': case['dual_brain_risk'],
            'risk_score': case['risk_score'],
            'location': case['location'],
            'status': case['status'],
            'timestamp': case['timestamp'],
            'dispatch': dict(dispatch) if dispatch else None
        })

    except Exception as e:
        app.logger.error(f"Error fetching case details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/emergency/case/<int:case_id>/timeline', methods=['GET'])
@login_required
def get_case_timeline(case_id):
    """Get timeline of a specific emergency case"""
    try:
        conn = get_db_connection()

        # Get case timeline events
        timeline = conn.execute("""
            SELECT
                event_type,
                timestamp,
                description,
                status
            FROM case_timeline
            WHERE case_id = ?
            ORDER BY timestamp ASC
        """, (case_id,)).fetchall()

        conn.close()

        timeline_list = []
        for event in timeline:
            timeline_list.append({
                'event': event['event_type'],
                'timestamp': event['timestamp'],
                'description': event['description'],
                'status': event['status']
            })

        return jsonify(timeline_list)

    except Exception as e:
        app.logger.error(f"Error fetching case timeline: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/emergency/case/<int:case_id>/update-status', methods=['POST'])
@login_required
def update_case_status(case_id):
    """Update the status of an emergency case"""
    try:
        if current_user.role not in ['admin', 'ddhs_admin']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        new_status = data.get('status')

        if not new_status:
            return jsonify({'success': False, 'message': 'Status not provided'}), 400

        conn = get_db_connection()

        # Update case status
        conn.execute("""
            UPDATE checkup_results
            SET status = ?
            WHERE id = ?
        """, (new_status, case_id))

        # Add timeline event
        conn.execute("""
            INSERT INTO case_timeline (case_id, event_type, description, status, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (case_id, 'status_update', f'Status changed to {new_status}', new_status))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Case status updated to {new_status}'})

    except Exception as e:
        app.logger.error(f"Error updating case status: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/admin/analytics', methods=['GET'])
@login_required
def get_admin_analytics():
    """Get admin analytics and metrics"""
    try:
        if current_user.role not in ['admin', 'ddhs_admin']:
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db_connection()

        # Get statistics
        stats = {
            'total_emergencies': conn.execute(
                "SELECT COUNT(*) as count FROM checkup_results WHERE overall_risk_score >= 70"
            ).fetchone()['count'],

            'dispatched': conn.execute(
                "SELECT COUNT(*) as count FROM checkup_results WHERE status = 'dispatched'"
            ).fetchone()['count'],

            'completed': conn.execute(
                "SELECT COUNT(*) as count FROM checkup_results WHERE status = 'completed'"
            ).fetchone()['count'],

            'response_rate': 95,  # Placeholder
            'success_rate': 88,   # Placeholder
            'ambulance_availability': 92  # Placeholder
        }

        conn.close()

        return jsonify(stats)

    except Exception as e:
        app.logger.error(f"Error fetching admin analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/ddhs-admin/ambulance/<int:ambulance_id>/assign')
@login_required
def ambulance_assign(ambulance_id):
    """Assign ambulance to a patient"""
    if current_user.role not in ['ddhs_admin', 'phc_staff']:
        flash('Access denied')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get ambulance details
        ambulance = c.execute('SELECT * FROM ambulances WHERE id = ?', (ambulance_id,)).fetchone()
        if not ambulance:
            flash('Ambulance not found')
            return redirect(url_for('ddhs_admin_ambulances'))

        # Get available patients needing transport
        patients = c.execute('''
            SELECT u.id, u.name, pl.id as patient_log_id
            FROM users u
            LEFT JOIN patient_logs pl ON u.id = pl.user_id
            WHERE u.role = 'patient'
            LIMIT 20
        ''').fetchall()

        conn.close()

        return render_template('ambulance_assign.html',
                             ambulance=ambulance,
                             patients=patients)
    except Exception as e:
        app.logger.error(f"Error in ambulance_assign: {e}")
        flash('Error loading ambulance details')
        return redirect(url_for('ddhs_admin_ambulances'))


@app.route('/ddhs-admin/ambulance/<int:ambulance_id>/tracking')
@login_required
def ambulance_tracking(ambulance_id):
    """View ambulance real-time tracking"""
    if current_user.role not in ['ddhs_admin', 'phc_staff']:
        flash('Access denied')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get ambulance details
        ambulance = c.execute('SELECT * FROM ambulances WHERE id = ?', (ambulance_id,)).fetchone()
        if not ambulance:
            flash('Ambulance not found')
            return redirect(url_for('ddhs_admin_ambulances'))

        # Get current allocation
        allocation = c.execute('''
            SELECT * FROM ambulance_allocations
            WHERE ambulance_id = ? AND status IN ('allocated', 'picked_up', 'in_transit')
            ORDER BY allocation_time DESC LIMIT 1
        ''', (ambulance_id,)).fetchone()

        # Get tracking history
        tracking = c.execute('''
            SELECT * FROM ambulance_tracking
            WHERE ambulance_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (ambulance_id,)).fetchall()

        conn.close()

        return render_template('ambulance_tracking.html',
                             ambulance=ambulance,
                             allocation=allocation,
                             tracking=tracking)
    except Exception as e:
        app.logger.error(f"Error in ambulance_tracking: {e}")
        flash('Error loading tracking data')
        return redirect(url_for('ddhs_admin_ambulances'))



@app.route('/api/attendance/mark', methods=['POST'])
@login_required
def api_mark_attendance():
    """Mark staff attendance (check-in/out or absent)"""
    if current_user.role != 'ddhs_admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        staff_id = data.get('staff_id')
        status = data.get('status')  # 'present', 'absent', 'late'
        date_str = data.get('date')

        conn = get_db_connection()
        c = conn.cursor()

        # Get staff member info
        staff = c.execute('SELECT phc_id FROM users WHERE id = ?', (staff_id,)).fetchone()
        if not staff:
            return jsonify({'success': False, 'message': 'Staff not found'}), 404

        # Insert attendance record
        status_val = 'Present' if status == 'present' else 'Absent'
        c.execute('''
            INSERT OR REPLACE INTO staff_attendance
            (user_id, phc_id, check_in_time, status)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        ''', (staff_id, staff['phc_id'], status_val))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Attendance marked as {status_val}'})
    except Exception as e:
        app.logger.error(f"Error marking attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== AMBULANCE MANAGEMENT API =====
@app.route('/api/ambulances/add', methods=['POST'])
@login_required
def api_add_ambulance():
    """Add a new ambulance to the fleet"""
    if current_user.role != 'ddhs_admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        ambulance_number = data.get('ambulance_number')
        vehicle_type = data.get('vehicle_type', 'Standard')
        driver_id = data.get('driver_id')
        capacity = data.get('capacity', 4)

        if not ambulance_number:
            return jsonify({'success': False, 'message': 'Ambulance number required'}), 400

        conn = get_db_connection()
        c = conn.cursor()

        # Insert ambulance
        c.execute('''
            INSERT INTO ambulances
            (ambulance_number, vehicle_type, current_driver_id, capacity, status)
            VALUES (?, ?, ?, ?, 'available')
        ''', (ambulance_number, vehicle_type, driver_id or None, capacity))

        ambulance_id = c.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Ambulance added', 'ambulance_id': ambulance_id})
    except Exception as e:
        app.logger.error(f"Error adding ambulance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/ambulances/<int:ambulance_id>/allocate', methods=['POST'])
@login_required
def api_allocate_ambulance(ambulance_id):
    """Allocate an ambulance to a patient"""
    if current_user.role not in ['ddhs_admin', 'phc_staff', 'phc_nurse']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        source_location = data.get('source_location')
        destination_location = data.get('destination_location')
        source_lat = data.get('source_lat')
        source_lon = data.get('source_lon')
        dest_lat = data.get('dest_lat')
        dest_lon = data.get('dest_lon')

        conn = get_db_connection()
        c = conn.cursor()

        # Check ambulance exists and is available
        ambulance = c.execute('SELECT id, status FROM ambulances WHERE id = ?', (ambulance_id,)).fetchone()
        if not ambulance:
            return jsonify({'success': False, 'message': 'Ambulance not found'}), 404

        if ambulance['status'] not in ['available', 'at_facility']:
            return jsonify({'success': False, 'message': 'Ambulance not available'}), 400

        # Calculate estimated time (basic calculation, ~1km per minute)
        distance_km = 0
        estimated_time_min = 0
        if source_lat and source_lon and dest_lat and dest_lon:
            from math import radians, cos, sin, asin, sqrt
            lon1, lat1, lon2, lat2 = map(radians, [source_lon, source_lat, dest_lon, dest_lat])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c_dist = 2 * asin(sqrt(a))
            r = 6371  # km
            distance_km = c_dist * r
            estimated_time_min = int(distance_km * 1.2)  # +20% for traffic

        # Create allocation
        c.execute('''
            INSERT INTO ambulance_allocations
            (ambulance_id, patient_id, source_location, destination_location,
             source_lat, source_lon, dest_lat, dest_lon, distance_km, estimated_time_min, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'allocated')
        ''', (ambulance_id, patient_id, source_location, destination_location,
              source_lat, source_lon, dest_lat, dest_lon, distance_km, estimated_time_min))

        allocation_id = c.lastrowid

        # Update ambulance status to in_transit
        c.execute('UPDATE ambulances SET status = ? WHERE id = ?', ('in_transit', ambulance_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Ambulance allocated',
            'allocation_id': allocation_id,
            'distance_km': round(distance_km, 1),
            'estimated_time_min': estimated_time_min
        })
    except Exception as e:
        app.logger.error(f"Error allocating ambulance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/ambulances/<int:ambulance_id>/tracking', methods=['GET', 'POST'])
@login_required
def api_ambulance_tracking(ambulance_id):
    """Get/update ambulance real-time tracking"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if request.method == 'POST':
            # Update location (from ambulance)
            data = request.get_json()
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            speed_kmh = data.get('speed_kmh')
            heading = data.get('heading')

            # Get current allocation
            allocation = c.execute('''
                SELECT id FROM ambulance_allocations
                WHERE ambulance_id = ? AND status IN ('allocated', 'picked_up', 'in_transit')
                ORDER BY allocation_time DESC LIMIT 1
            ''', (ambulance_id,)).fetchone()

            c.execute('''
                INSERT INTO ambulance_tracking
                (ambulance_id, allocation_id, latitude, longitude, speed_kmh, heading)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ambulance_id, allocation['id'] if allocation else None, latitude, longitude, speed_kmh, heading))

            # Update ambulance location
            c.execute('UPDATE ambulances SET location_lat = ?, location_lon = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
                     (latitude, longitude, ambulance_id))

            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Location updated'})

        else:
            # Get tracking data
            tracking = c.execute('''
                SELECT * FROM ambulance_tracking
                WHERE ambulance_id = ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (ambulance_id,)).fetchall()

            conn.close()

            return jsonify({
                'success': True,
                'tracking': [dict(row) for row in tracking]
            })
    except Exception as e:
        app.logger.error(f"Error in ambulance tracking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    # Use configuration settings (respects production environment)
    app.run(
        debug=config.DEBUG,  # Enable debug mode for development
        port=config.APP_PORT,
        use_reloader=config.DEBUG,  # Only auto-reload in development
        host='0.0.0.0'  # Listen on all interfaces
    )
