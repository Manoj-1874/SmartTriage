from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
import numpy as np
import joblib
from transformers import pipeline
import os
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'provoheal-secret-key-change-in-production-2026'

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
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
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
        return redirect(url_for('index'))
    
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
    # If not authenticated, redirect to login
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # If authenticated, redirect based on role
    if current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    else:
        return redirect(url_for('patient_dashboard'))

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

if __name__ == '__main__':
    # Standard local Flask deployment
    # Set use_reloader=False to avoid Windows socket warnings (but you'll need to manually restart)
    app.run(debug=True, port=5000, use_reloader=True)