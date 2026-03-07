"""
Triage Blueprint
Handles health assessment and AI-powered triage
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from datetime import datetime
import pandas as pd
import numpy as np

from utils.database import get_db_connection
from utils.validation import VitalSignsValidator, ValidationError

triage_bp = Blueprint('triage', __name__)

# These will be set by the main app
xgb_risk_model = None
exp_brain = None
encoders = None
scaler = None
feature_names = None


def init_models(xgb_model, bert_model, model_encoders, model_scaler, features):
    """Initialize ML models (called from main app)"""
    global xgb_risk_model, exp_brain, encoders, scaler, feature_names
    xgb_risk_model = xgb_model
    exp_brain = bert_model
    encoders = model_encoders
    scaler = model_scaler
    feature_names = features


@triage_bp.route('/checkup', methods=['GET'])
@login_required
def checkup():
    """Health checkup form"""
    return render_template('checkup.html')


@triage_bp.route('/triage', methods=['GET', 'POST'])
@login_required
def triage():
    """Process triage assessment"""
    # Redirect GET requests to the checkup page
    if request.method == 'GET':
        return redirect(url_for('triage.checkup'))

    if not xgb_risk_model or not exp_brain:
        flash('AI models not loaded. Please contact administrator.', 'error')
        return redirect(url_for('triage.checkup'))

    try:
        # 1. Grab and VALIDATE data from form
        form_data = {
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'sys_bp': request.form.get('sys_bp'),
            'dia_bp': request.form.get('dia_bp'),
            'hr': request.form.get('hr'),
            'temp': request.form.get('temp'),
            'temp_unit': request.form.get('temp_unit', 'F'),
            'history': request.form.get('history', 'None'),
            'symptoms': request.form.get('symptom')
        }

        # Validate all inputs
        validated_data = VitalSignsValidator.validate_triage_data(form_data)

        # Extract validated values
        age = validated_data['age']
        gender = validated_data['gender']
        sys_bp = validated_data['sys_bp']
        dia_bp = validated_data['dia_bp']
        hr = validated_data['hr']
        temp = validated_data['temp']
        history = validated_data['history']
        symptom = validated_data['symptoms']

    except ValidationError as e:
        flash(f'Validation Error: {e.message}', 'error')
        return redirect(url_for('triage.checkup'))
    except Exception as e:
        flash(f'Error processing form data: {str(e)}', 'error')
        return redirect(url_for('triage.checkup'))

    # 2. RUN SYSTEM 1 (XGBoost)
    gen_enc = encoders['Gender'].transform([gender])[0] if gender in encoders['Gender'].classes_ else 0
    symp_enc = encoders['Symptoms'].transform([symptom])[0] if symptom in encoders['Symptoms'].classes_ else 0
    hist_enc = encoders['Pre_Conditions'].transform([history])[0] if history in encoders['Pre_Conditions'].classes_ else 0

    patient_df = pd.DataFrame([[age, gen_enc, symp_enc, sys_bp, dia_bp, hr, temp, hist_enc]], columns=feature_names)
    patient_scaled = scaler.transform(patient_df)

    xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
    xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

    # 3. RUN SYSTEM 2 (BERT + Safety Net)
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

    # 5. Calculate risk score
    score = calculate_risk_score(final_risk, sys_bp, dia_bp, hr, temp, history)

    # 6. SAVE TO DB
    conn = get_db_connection()
    conn.execute('''INSERT INTO patient_logs
                 (user_id, age, gender, symptoms, sys_bp, dia_bp, hr, temp, history,
                  xgb_risk, dual_brain_risk, routing, risk_score)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (current_user.id, age, gender, symptom, sys_bp, dia_bp, hr, temp,
               history, xgb_risk, final_risk, routing, score))
    conn.commit()
    log_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()

    # 7. Store result in session for result page
    if current_user.role == 'patient':
        session['last_checkup_result'] = {
            'risk_level': final_risk,
            'routing': routing,
            'vitals': {
                'bp': f"{sys_bp}/{dia_bp}",
                'hr': str(hr),
                'temp': str(temp)
            },
            'symptoms': symptom,
            'age': age,
            'gender': gender,
            'history': history,
            'score': score,
            'timestamp': datetime.now().isoformat(),
            'log_id': log_id
        }
        flash(f'Health assessment completed! Risk Level: {final_risk}', 'success')
        return redirect(url_for('triage.checkup_result'))

    return redirect(url_for('dashboard.patient_dashboard'))


@triage_bp.route('/checkup-result')
@login_required
def checkup_result():
    """Display triage result"""
    result = session.get('last_checkup_result')

    if not result:
        flash('No assessment result found. Please complete a health checkup first.', 'warning')
        return redirect(url_for('triage.checkup'))

    return render_template('checkup_result.html', result=result)


@triage_bp.route('/health-report')
@login_required
def health_report():
    """Display patient's health history and trends"""
    conn = get_db_connection()

    # Get patient's assessment history
    logs = conn.execute('''
        SELECT * FROM patient_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 50
    ''', (current_user.id,)).fetchall()

    conn.close()

    return render_template('health_report.html', logs=logs)


def calculate_risk_score(risk_level, sys_bp, dia_bp, hr, temp, history):
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
