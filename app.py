from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
import numpy as np
import joblib
from transformers import pipeline
import os
import sys
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'prioritymed-secret-key-change-in-production-2026'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 1. DATABASE & MODEL PATHS ---
# Use forward slashes to prevent Python from reading \t as a tab!
DB_PATH = 'triage.db'
MODEL_DIR = "models/experimental_brain"
STABLE_MODEL_PATH = "models/triage_assets_mingled.pkl"

# --- 2. USER CLASS FOR FLASK-LOGIN ---
class User(UserMixin):
    def __init__(self, id, email, fullname, role, phone, specialization=None, license=None, experience=None):
        self.id = id
        self.email = email
        self.fullname = fullname
        self.role = role
        self.phone = phone
        self.specialization = specialization
        self.license = license
        self.experience = experience

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(
            id=user_data[0],
            email=user_data[1],
            fullname=user_data[3],
            role=user_data[4],
            phone=user_data[5],
            specialization=user_data[6],
            license=user_data[7],
            experience=user_data[8]
        )
    return None

# --- 3. INITIALIZE DATABASE ---
# --- 3. INITIALIZE DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            specialization TEXT,
            license TEXT,
            experience INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Patient logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS patient_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            age INTEGER, gender TEXT, symptoms TEXT, 
            sys_bp INTEGER, dia_bp INTEGER, hr INTEGER, 
            temp REAL, history TEXT, 
            xgb_risk TEXT, dual_brain_risk TEXT, routing TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Check if appointments table needs migration
    c.execute("PRAGMA table_info(appointments)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'doctor_id' not in columns:
        # Need to migrate old appointments table
        print("🔄 Migrating appointments table to new schema...")
        
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
        
        print("✅ Migration completed!")
    else:
        # Create appointments table with correct schema if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
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
    
    # Check if patient_logs table needs migration for user_id column
    c.execute("PRAGMA table_info(patient_logs)")
    pl_columns = [column[1] for column in c.fetchall()]
    
    if 'user_id' not in pl_columns:
        print("🔄 Migrating patient_logs table to add user_id column...")
        
        # First, add the user_id column
        try:
            c.execute("ALTER TABLE patient_logs ADD COLUMN user_id INTEGER")
            print("✅ Added user_id column to patient_logs table")
        except sqlite3.OperationalError as e:
            print(f"⚠️ Column might already exist: {e}")
    
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
    
    conn.commit()
    conn.close()

init_db()

# --- 3. LOAD DUAL-BRAIN MODELS ---
print("🏥 Loading SmartTriage Dual-Brain Engine...")

# Set environment variable to reduce OpenBLAS memory usage
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

try:
    assets = joblib.load(STABLE_MODEL_PATH)
    encoders = assets['encoders']
    xgb_risk_model = assets['risk_model']
    scaler = assets['scaler']
    feature_names = assets['features']
    exp_brain = pipeline("text-classification", model=MODEL_DIR, tokenizer=MODEL_DIR)
    print("✅ System 1 (XGBoost) & System 2 (Shadow Brain) Online.")
except Exception as e:
    print(f"⚠️ Warning: Model load error, running in UI-only mode: {e}")
    # Create dummy models for UI testing if loading fails
    xgb_risk_model = None
    exp_brain = None
    encoders = None
    scaler = None
    feature_names = []

# --- 4. HELPER FUNCTIONS ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ? AND role = ?', (email, role)).fetchone()
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
                experience=user_data['experience']
            )
            login_user(user, remember=request.form.get('remember'))
            
            # Redirect based on role
            if user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            return render_template('login.html', error='Invalid email, password, or role')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
       pass # Allow signup even if logged in just in case
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        fullname = request.form.get('fullname')
        phone = request.form.get('phone')
        role = request.form.get('role')
        
        # Validation
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')
        
        conn = get_db_connection()
        
        # Check if email already exists
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            conn.close()
            return render_template('signup.html', error='Email already registered')
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        try:
            if role == 'doctor':
                specialization = request.form.get('specialization')
                license = request.form.get('license')
                experience = request.form.get('experience')
                
                conn.execute('''
                    INSERT INTO users (email, password_hash, fullname, role, phone, specialization, license, experience)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, password_hash, fullname, role, phone, specialization, license, experience))
            else:
                conn.execute('''
                    INSERT INTO users (email, password_hash, fullname, role, phone)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, password_hash, fullname, role, phone))
            
            conn.commit()
            conn.close()
            
            return render_template('login.html', success='Account created successfully! Please login.')
        except Exception as e:
            conn.close()
            return render_template('signup.html', error=f'Registration failed: {str(e)}')
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

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
    
    stats = get_dashboard_stats()
    conn = get_db_connection()
    
    # Get patient's appointments (recent 20 for display and charts)
    appointments = conn.execute(
        '''SELECT a.*, u.fullname as doctor_name, u.specialization
           FROM appointments a
           LEFT JOIN users u ON a.doctor_id = u.id
           WHERE a.patient_id = ?
           ORDER BY a.appointment_date DESC, a.appointment_time DESC
           LIMIT 20''',
        (current_user.id,)
    ).fetchall()
    appointments = [dict(row) for row in appointments]
    
    # Get patient's health stats from all appointments
    total_appointments = conn.execute(
        "SELECT COUNT(*) as count FROM appointments WHERE patient_id = ?",
        (current_user.id,)
    ).fetchone()
    
    completed_appointments = conn.execute(
        "SELECT COUNT(*) as count FROM appointments WHERE patient_id = ? AND status = 'Completed'",
        (current_user.id,)
    ).fetchone()
    
    pending_appointments = conn.execute(
        "SELECT COUNT(*) as count FROM appointments WHERE patient_id = ? AND status = 'Pending'",
        (current_user.id,)
    ).fetchone()
    
    conn.close()
    
    patient_stats = {
        'total': total_appointments['count'] if total_appointments else 0,
        'completed': completed_appointments['count'] if completed_appointments else 0,
        'pending': pending_appointments['count'] if pending_appointments else 0
    }
    
    return render_template('patient_dashboard.html', 
                         appointments=appointments, 
                         stats=stats,
                         patient_stats=patient_stats,
                         user=current_user)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Access denied')
        return redirect(url_for('index'))
    
    stats = get_dashboard_stats()
    conn = get_db_connection()
    patients = conn.execute("SELECT * FROM patient_logs ORDER BY id DESC LIMIT 10").fetchall()
    latest_patient = conn.execute("SELECT * FROM patient_logs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    return render_template('index.html', 
                         patients=patients, 
                         stats=stats, 
                         latest_patient=latest_patient,
                         user=current_user)

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
    
    if not xgb_risk_model or not exp_brain:
        return "⚠️ Models not loaded. Check server logs."

    # 1. Grab data from form
    age = int(request.form['age'])
    gender = request.form['gender']
    sys_bp = int(request.form['sys_bp'])
    dia_bp = int(request.form['dia_bp'])
    hr = int(request.form['hr'])
    temp = float(request.form['temp'])
    history = request.form['history']
    symptom = request.form['symptom']

    # 2. RUN SYSTEM 1 (XGBoost)
    gen_enc = encoders['Gender'].transform([gender])[0] if gender in encoders['Gender'].classes_ else 0
    symp_enc = encoders['Symptoms'].transform([symptom])[0] if symptom in encoders['Symptoms'].classes_ else 0
    hist_enc = encoders['Pre_Conditions'].transform([history])[0] if history in encoders['Pre_Conditions'].classes_ else 0
    
    patient_df = pd.DataFrame([[age, gen_enc, symp_enc, sys_bp, dia_bp, hr, temp, hist_enc]], columns=feature_names)
    patient_scaled = scaler.transform(patient_df)

    xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
    xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

    # 3. RUN SYSTEM 2 (Shadow Brain + Safety Net)
    bert_res = exp_brain(symptom)[0]
    is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.5)
    critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious']
    semantic_emergency = any(word in symptom.lower() for word in critical_words) or is_bert_emergency

    # 4. DUAL-BRAIN CONSENSUS LOGIC
    if semantic_emergency and xgb_risk != "HIGH":
        final_risk = "HIGH (SAFETY OVERRIDE)"
        routing = "Resuscitation / Cardiology"
    elif xgb_risk == "HIGH":
        final_risk = "HIGH"
        routing = "Emergency Department"
    elif xgb_risk == "MEDIUM":
        final_risk = "MEDIUM"
        routing = "Urgent Care"
    else:
        final_risk = "LOW"
        routing = "General Ward / Waiting Room"

    # 5. SAVE TO DB with user_id
    conn = get_db_connection()
    conn.execute('''INSERT INTO patient_logs 
                 (user_id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, history, xgb_risk, dual_brain_risk, routing) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (current_user.id, age, gender, symptom, sys_bp, dia_bp, hr, temp, history, xgb_risk, final_risk, routing))
    conn.commit()
    log_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    # 6. Store result in session for patient view
    if current_user.role == 'patient':
        session['last_checkup_result'] = {
            'risk_level': final_risk,
            'routing': routing,
            'vitals': {
                'bp': f"{sys_bp}/{dia_bp}",
                'hr': hr,
                'temp': temp
            },
            'symptoms': symptom,
            'log_id': log_id
        }
        flash(f'Health assessment completed! Risk Level: {final_risk}')
        return redirect(url_for('checkup_result'))
    
    return redirect(url_for('doctor_dashboard'))

# --- 8. APPOINTMENTS ROUTES ---
@app.route('/appointments', methods=['GET'])
@login_required
def appointments():
    conn = get_db_connection()
    
    if current_user.role == 'doctor':
        # Doctors see appointments assigned to them or pending requests
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
    if current_user.role == 'doctor':
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
    
    # Get recent patients for quick appointment booking (doctors only)
    recent_patients = []
    if current_user.role == 'doctor':
        recent_patients = conn.execute('''
            SELECT id, age, gender, symptoms, routing, timestamp
            FROM patient_logs
            ORDER BY id DESC LIMIT 20
        ''').fetchall()
        recent_patients = [dict(row) for row in recent_patients]
    
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
                         recent_patients=recent_patients,
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
    # Only doctors can access patient directory
    if current_user.role != 'doctor':
        flash('Access denied. Only doctors can view patient directory.')
        return redirect(url_for('patient_dashboard'))
    
    conn = get_db_connection()
    
    # Get all patients with their appointment statistics
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
    
    if current_user.role == 'patient':
        # Patient creates appointment request
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        symptoms = request.form.get('symptoms', '')
        notes = request.form.get('notes', '')
        
        # Get doctor info
        doctor = conn.execute('SELECT fullname, specialization FROM users WHERE id = ?', (doctor_id,)).fetchone()
        
        conn.execute('''
            INSERT INTO appointments 
            (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date, appointment_time, symptoms, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        ''', (current_user.id, current_user.fullname, doctor_id, doctor['fullname'], 
              doctor['specialization'], appointment_date, appointment_time, symptoms, notes))
        
        flash('Appointment request sent! Waiting for doctor approval.')
    
    else:
        # Doctor creates appointment (auto-approved)
        patient_id = request.form.get('patient_id')
        patient_name = request.form['patient_name']
        doctor_name = request.form.get('doctor_name', current_user.fullname)
        department = request.form['department']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        symptoms = request.form.get('symptoms', '')
        notes = request.form.get('notes', '')
        
        conn.execute('''
            INSERT INTO appointments 
            (patient_id, patient_name, doctor_id, doctor_name, department, appointment_date, appointment_time, symptoms, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Approved')
        ''', (patient_id or current_user.id, patient_name, current_user.id, doctor_name, 
              department, appointment_date, appointment_time, symptoms, notes))
        
        flash('Appointment created successfully!')
    
    conn.commit()
    conn.close()
    
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
        # Doctors can approve/reject pending appointments or update their own
        if appointment['status'] == 'Pending' or appointment['doctor_id'] == current_user.id:
            conn.execute('UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                        (status, id))
            flash(f'Appointment {status.lower()} successfully!')
        else:
            flash('Unauthorized action!')
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
    if current_user.role == 'doctor' or (current_user.role == 'patient' and appointment['patient_id'] == current_user.id):
        conn.execute('DELETE FROM appointments WHERE id = ?', (id,))
        conn.commit()
        flash('Appointment deleted!')
    else:
        flash('Unauthorized action!')
    
    conn.close()
    
    return redirect(url_for('appointments'))

@app.route('/api/appointments/dates', methods=['GET'])
@login_required
def get_appointment_dates():
    conn = get_db_connection()
    
    if current_user.role == 'doctor':
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
        return redirect(url_for('doctor_dashboard'))
    
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
        
        # Adjust based on risk
        high_risk_count = sum(1 for r in health_records if 'HIGH' in r['dual_brain_risk'])
        low_risk_count = sum(1 for r in health_records if 'LOW' in r['dual_brain_risk'])
        
        if low_risk_count > high_risk_count:
            score_data['overall_score'] = 85
        elif high_risk_count > len(health_records) * 0.5:
            score_data['overall_score'] = 55
        
        # Risk improvement percentage
        if summary['risk_improvement']:
            score_data['risk_improvement'] = '+15'
        else:
            score_data['risk_improvement'] = '0'
        
        # Vitals stability (lower standard deviation = more stable)
        bp_std = np.std([r['sys_bp'] for r in health_records])
        score_data['vitals_stability'] = int(max(0, 100 - bp_std))
        
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
    
    return render_template('health_report.html',
                         health_records=health_records,
                         summary=summary,
                         score_data=score_data,
                         user=current_user)

@app.route('/reports')
@login_required
def reports():
    """Doctor's view of all patient reports"""
    if current_user.role != 'doctor':
        flash('This page is only accessible to doctors')
        return redirect(url_for('patient_dashboard'))
    
    conn = get_db_connection()
    
    # Get all patients with their health statistics
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
    
    return render_template('reports.html',
                         patient_reports=patient_reports,
                         patient_details=patient_details,
                         stats=stats,
                         user=current_user)

# --- AI CHECKUP ROUTES ---
@app.route('/checkup')
@login_required
def checkup():
    """AI health checkup page for patients"""
    if current_user.role != 'patient':
        flash('AI checkup is only available for patients')
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('checkup.html', user=current_user)

@app.route('/checkup/result')
@login_required
def checkup_result():
    """Show AI checkup results to patient"""
    if current_user.role != 'patient':
        flash('Access denied')
        return redirect(url_for('doctor_dashboard'))
    
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
        # Doctors see all their patients
        contacts = conn.execute('''
            SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                   (SELECT COUNT(*) FROM messages 
                    WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
            FROM users u
            WHERE u.role = 'patient' AND u.id IN (
                SELECT DISTINCT patient_id FROM appointments WHERE doctor_id = ?
                UNION
                SELECT DISTINCT sender_id FROM messages WHERE receiver_id = ?
                UNION  
                SELECT DISTINCT receiver_id FROM messages WHERE sender_id = ?
            )
            ORDER BY u.fullname ASC
        ''', (current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()
    else:
        # Patients see all doctors
        contacts = conn.execute('''
            SELECT DISTINCT u.id, u.fullname, u.email, u.role, u.specialization,
                   (SELECT COUNT(*) FROM messages 
                    WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) as unread_count
            FROM users u
            WHERE u.role = 'doctor'
            ORDER BY u.fullname ASC
        ''', (current_user.id,)).fetchall()
    
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
        response += "⚠️ **This patient should be seen promptly.** The symptoms suggest a condition that may worsen without timely intervention."
    elif analysis['risk_level'] == 'MEDIUM':
        response += "💡 **Recommend evaluation within the next few hours** to ensure proper care and prevent complications."
    else:
        response += "✅ **Standard consultation recommended.** While this appears less urgent, medical evaluation is still important."
    
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

if __name__ == '__main__':
    # Standard local Flask deployment
    # Set use_reloader=False to avoid Windows socket warnings (but you'll need to manually restart)
    app.run(debug=True, port=5000, use_reloader=True)