"""
PHASE 5.3: INTEGRATION & DEPLOYMENT GUIDE
Step-by-step instructions for integrating production modules into app.py

This guide walks through:
1. Adding imports to app.py
2. Initializing the production pipeline
3. Modifying the prediction endpoint
4. Testing the integrated pipeline
5. Deploying to production
"""

# ===== STEP 1: ADD IMPORTS TO app.py =====

# Add these imports at the top of app.py (alongside existing imports):

"""
from production_pipeline import SmartTriagePipeline, create_pipeline_from_app
from input_validator import VitalSignsValidator
from confidence_threshold import ConfidenceThreshold
from monitoring_system import PredictionLogger, PerformanceTracker, AnomalyDetector
"""

# ===== STEP 2: INITIALIZE PIPELINE IN app.py =====

# After model loading (around line 700), add:

"""
# --- 5. INITIALIZE PRODUCTION PIPELINE ---
app.logger.info("🏥 Initializing SmartTriage Production Pipeline...")

production_pipeline = None
if xgb_risk_model and scaler and encoders and feature_names:
    try:
        production_pipeline = SmartTriagePipeline(
            model=xgb_risk_model,
            scaler=scaler,
            encoders=encoders,
            feature_names=feature_names
        )
        app.logger.info("✅ Production Pipeline initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize pipeline: {e}")
        production_pipeline = None
else:
    app.logger.warning("Cannot initialize pipeline: models not loaded")
    production_pipeline = None
"""

# ===== STEP 3: MODIFY /triage ENDPOINT =====

# Replace the existing /triage prediction logic (around line 1650) with:

"""
if not production_pipeline:
    flash("⚠️ Production pipeline not available. Please refresh.", 'error')
    return redirect(url_for('checkup'))

# Prepare patient data for pipeline
patient_data = {
    'patient_id': current_user.id,
    'age': age,
    'gender': gender,
    'sys_bp': sys_bp,
    'dia_bp': dia_bp,
    'hr': hr,
    'temp_c': temp,  # Already in Celsius from validation
    'symptoms': symptom,
    'pre_conditions': history
}

# Run production pipeline
pipeline_result = production_pipeline.predict_with_validation(patient_data)

if not pipeline_result['success']:
    errors_str = ', '.join(pipeline_result['errors'])
    flash(f"⚠️ Prediction error: {errors_str}", 'error')
    return redirect(url_for('checkup'))

# Extract results from pipeline
final_risk = pipeline_result['prediction']
confidence_score = pipeline_result['confidence']
confidence_level = pipeline_result['confidence_level']
recommendation_text = pipeline_result['recommendation']
alert_level = pipeline_result['alert_level']
warnings = pipeline_result['warnings']

# Log any warnings
for warning in warnings:
    app.logger.warning(f"Patient {current_user.id}: {warning}")
"""

# ===== STEP 4: TESTING THE INTEGRATION =====

# Run test_integration.py (included below) to verify the integration:

"""
cd e:\\Nilal_thiruvila\\SmartTriage_Dashboard
python test_integration.py
"""

# ===== STEP 5: DEPLOYMENT =====

# 1. Ensure all files are in place:
#    - input_validator.py
#    - confidence_threshold.py
#    - monitoring_system.py
#    - production_pipeline.py
#    - app.py (modified with integration code)

# 2. Verify all tests pass:
#    - python test_suite_phase5.py (should show 100% pass rate)
#    - python test_integration.py (should show successful integration)

# 3. Check logs are created:
#    - logs/smarttriage.log
#    - logs/errors.log
#    - predictions.json
#    - predictions.csv

# 4. Monitor performance:
#    - Check /api/health endpoint for system status
#    - Review predictions.json for anomalies
#    - Track confidence distribution

# 5. Staged rollout:
#    - Stage 1: Test with 10% of traffic for 24 hours
#    - Stage 2: Increase to 50% of traffic for 7 days
#    - Stage 3: Full rollout to 100% of traffic


# ===== FULL INTEGRATION EXAMPLE =====

"""
MODIFICATION TO app.py (Lines ~1580-1700):

@app.route('/triage', methods=['GET', 'POST'])
@login_required
@limiter.limit(config.RATELIMIT_TRIAGE if config.RATELIMIT_ENABLED else "1000 per minute")
def triage():
    # Redirect GET requests to the checkup page
    if request.method == 'GET':
        return redirect(url_for('checkup'))

    if not production_pipeline:
        flash("⚠️ Production system unavailable", 'error')
        return redirect(url_for('checkup'))

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
            'respiration_rate': request.form.get('respiration_rate'),
            'spo2': request.form.get('spo2'),
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
        temp_fahrenheit = validated_data['temp']
        temp = (temp_fahrenheit - 32) * 5/9  # Convert to Celsius
        symptom = validated_data['symptoms']
        history = validated_data['history']

    except ValidationError as e:
        flash(f'Validation Error: {e.message}', 'error')
        return redirect(url_for('checkup'))

    # 2. USE PRODUCTION PIPELINE FOR PREDICTION
    patient_data = {
        'patient_id': current_user.id,
        'age': age,
        'gender': gender,
        'sys_bp': sys_bp,
        'dia_bp': dia_bp,
        'hr': hr,
        'temp_c': temp,
        'symptoms': symptom,
        'pre_conditions': history
    }

    # Run production pipeline with all safety checks
    pipeline_result = production_pipeline.predict_with_validation(patient_data)

    if not pipeline_result['success']:
        error_msg = ', '.join(pipeline_result['errors'])
        app.logger.error(f"Pipeline failed for patient {current_user.id}: {error_msg}")
        flash(f"⚠️ Prediction system error. Using fallback logic.", 'warning')
        # Fallback to simple rule-based prediction
        final_risk = 'LOW'
        confidence_score = 0.5
    else:
        final_risk = pipeline_result['prediction']
        confidence_score = pipeline_result['confidence']
        recommendation_text = pipeline_result['recommendation']
        alert_level = pipeline_result['alert_level']

        # Log any warnings
        for warning in pipeline_result['warnings']:
            app.logger.warning(f"Patient {current_user.id}: {warning}")

    # 3. DETERMINE ROUTING
    routing_map = {
        'LOW': 'General Ward / Waiting Room',
        'MEDIUM': 'Urgent Care',
        'HIGH': 'Emergency Department'
    }
    routing = routing_map.get(final_risk, 'General Ward / Waiting Room')

    # 4. STORE RESULT IN SESSION
    session['last_checkup_result'] = {
        'risk_level': final_risk,
        'confidence_score': confidence_score,
        'recommendation': recommendation_text if pipeline_result['success'] else 'See a healthcare provider',
        'routing': routing,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'alert_level': alert_level if pipeline_result['success'] else 'YELLOW'
    }

    # 5. SAVE TO DATABASE
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO patient_logs
        (user_id, age, gender, sys_bp, dia_bp, hr, temp, symptoms, pre_conditions,
         dual_brain_risk, confidence_score, alert_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        current_user.id, age, gender, sys_bp, dia_bp, hr, temp_fahrenheit, symptom, history,
        final_risk, confidence_score, alert_level if pipeline_result['success'] else 'YELLOW'
    ))
    conn.commit()
    conn.close()

    # 6. REDIRECT TO RESULTS
    return redirect(url_for('checkup_result'))
"""

print("✅ Integration Guide Ready")
print("Next: Follow steps 1-5 to integrate into app.py")
