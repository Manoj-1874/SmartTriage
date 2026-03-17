"""
Emergency fix for XGBoost model trained on sick patients only.
Implements rule-based override for obviously healthy vitals.
"""


def is_healthy_vitals(age, sys_bp, dia_bp, hr, temp, respiration_rate=None, spo2=None):
    """
    Quick check for obviously healthy vitals before running XGBoost.

    Returns True if vitals are clearly within healthy ranges and patient
    is not elderly (where slightly elevated vitals might be normal).

    Args:
        age: Patient age in years
        sys_bp: Systolic blood pressure (mmHg)
        dia_bp: Diastolic blood pressure (mmHg)
        hr: Heart rate (bpm)
        temp: Temperature (Fahrenheit)
        respiration_rate: Respiratory rate (breaths/min), optional
        spo2: Oxygen saturation (%), optional

    Returns:
        bool: True if vitals suggest healthy patient
    """
    # Blood pressure ranges (American Heart Association guidelines)
    # Normal: <120 systolic AND <80 diastolic
    # Elevated: 120-129 systolic AND <80 diastolic
    # Stage 1 Hypertension: 130-139 OR 80-89

    bp_healthy = (
        90 <= sys_bp <= 129 and  # Normal to elevated range
        60 <= dia_bp <= 84       # Normal to upper normal
    )

    # Heart rate (adults)
    # Normal resting: 60-100 bpm
    # Athletes: 40-60 bpm
    # Well-conditioned: 50-90 bpm
    hr_healthy = 50 <= hr <= 95

    # Temperature (Fahrenheit)
    # Normal: 97.0-99.0°F (36.1-37.2°C)
    # Slight variation acceptable: 96.5-99.5°F
    temp_healthy = 96.5 <= temp <= 99.5

    # Age consideration
    # For elderly (65+), slightly elevated BP/HR might be normal
    # For them, use wider ranges
    if age >= 65:
        bp_healthy = (90 <= sys_bp <= 145 and 60 <= dia_bp <= 92)
        hr_healthy = 48 <= hr <= 100

    if age >= 75:
        # Older adults often have slightly higher baseline BP in outpatient settings.
        bp_healthy = (90 <= sys_bp <= 150 and 60 <= dia_bp <= 95)
        hr_healthy = 48 <= hr <= 102

    # Age should be reasonable for healthy patient
    # Very young children and very elderly require different assessment
    age_reasonable = 5 <= age <= 90

    rr_healthy = True if respiration_rate is None else (12 <= respiration_rate <= 20)
    spo2_healthy = True if spo2 is None else (spo2 >= 95)

    return age_reasonable and bp_healthy and hr_healthy and temp_healthy and rr_healthy and spo2_healthy


def has_emergency_symptoms(symptom_text):
    """
    Check if symptom description contains emergency keywords.

    Args:
        symptom_text: Patient's symptom description (string)

    Returns:
        bool: True if emergency keywords detected
    """
    emergency_keywords = [
        # Respiratory distress
        'distress', 'breathlessness', 'shortness of breath', 'cannot breathe',
        'gasping', 'choking', 'cannot breathe well', 'can\'t breathe',

        # Cardiovascular
        'chest pain', 'crushing', 'heart attack', 'cardiac arrest',
        'severe chest pain', 'radiating pain',

        # Neurological
        'unconscious', 'unresponsive', 'seizure', 'stroke',
        'slurred speech', 'weakness of one body side', 'altered sensorium',
        'severe headache', 'sudden confusion', 'confusion', 'disoriented',
        'altered mental status', 'not responding normally', 'diabetic emergency',
        'worst headache', 'neck stiffness', 'neck stiff',

        # Trauma/Bleeding
        'hemorrhage', 'severe bleeding', 'uncontrolled bleeding',
        'head injury', 'neck injury', 'spinal injury',

        # Poisoning/Allergic
        'poisoning', 'overdose', 'allergic reaction', 'anaphylaxis',
        'swelling of throat', 'difficulty swallowing', 'throat swelling',

        # Sepsis/Infection
        'sepsis', 'high fever', 'fever above 103', 'fever above 104',

        # Loss of function
        'paralysis', 'cannot move', 'loss of consciousness', 'syncope',
        'sudden vision loss', 'sudden hearing loss', 'fainted', 'passed out'
    ]

    symptom_lower = symptom_text.lower()
    return any(keyword in symptom_lower for keyword in emergency_keywords)


def is_routine_visit(symptom_text):
    """
    Check if visit is routine/non-urgent.

    Args:
        symptom_text: Patient's symptom description (string)

    Returns:
        bool: True if visit appears routine
    """
    routine_keywords = [
        'routine', 'checkup', 'check-up', 'check up',
        'annual', 'physical exam', 'physical examination',
        'wellness', 'preventive', 'screening',
        'follow-up', 'follow up', 'followup',
        'no symptoms', 'no symptom', 'feeling fine', 'feeling good',
        'healthy', 'well visit', 'regular visit',
        'gym', 'workout', 'exercise', 'after gym', 'post-workout', 'post workout',
        'after exercise', 'just checking', 'checking vitals',
        'health check', 'school physical', 'college', 'prenatal',
        'blood pressure check', 'prescription renewal', 'refill', 'medication refill'
    ]

    symptom_lower = symptom_text.lower()
    return any(keyword in symptom_lower for keyword in routine_keywords)


def calculate_healthy_score(sys_bp, dia_bp, hr, temp, respiration_rate=None, spo2=None):
    """
    Calculate a "healthy score" (0-100) for patients with healthy vitals.
    Score near 100 = very healthy, score near 50 = borderline.

    Args:
        sys_bp: Systolic BP
        dia_bp: Diastolic BP
        hr: Heart rate
        temp: Temperature (F)
        respiration_rate: Respiratory rate (breaths/min), optional
        spo2: Oxygen saturation (%), optional

    Returns:
        int: Health score 0-100
    """
    score = 100

    # Deduct points for deviations from ideal

    # Ideal BP: 120/80
    bp_deviation = abs(sys_bp - 120) + abs(dia_bp - 80)
    score -= min(bp_deviation * 0.3, 20)  # Max 20 points for BP

    # Ideal HR: 70
    hr_deviation = abs(hr - 70)
    score -= min(hr_deviation * 0.4, 15)  # Max 15 points for HR

    # Ideal temp: 98.6
    temp_deviation = abs(temp - 98.6)
    score -= min(temp_deviation * 5, 15)  # Max 15 points for temp

    if respiration_rate is not None:
        rr_deviation = abs(respiration_rate - 16)
        score -= min(rr_deviation * 1.2, 12)

    if spo2 is not None:
        spo2_deviation = max(0, 98 - spo2)
        score -= min(spo2_deviation * 4, 18)

    return max(0, min(100, int(score)))


def check_clinical_danger_zones(age, sys_bp, dia_bp, hr, temp, symptom_text, respiration_rate=None, spo2=None):
    """
    Check for CRITICAL vital signs that MUST be HIGH RISK regardless of ML model.

    Medical standards for immediate escalation:
    - Hypertensive Crisis: Sys BP > 180 OR Dia BP > 120 (immediate stroke/organ damage risk)
    - Severe Hypertension: Sys BP > 160 OR Dia BP > 100 (urgent treatment needed)
    - Hypotension/Shock: Sys BP < 90 OR Dia BP < 60 (perfusion failure)
    - Severe Tachycardia: HR > 120 (cardiac stress)
    - Severe Bradycardia: HR < 50 (except trained athletes)
    - High Fever: Temp > 103°F (potential sepsis)
    - Hypothermia: Temp < 95°F (medical emergency)

    Args:
        age, sys_bp, dia_bp, hr, temp: Vital signs
        symptom_text: Patient symptoms (for context)
        respiration_rate: Respiratory rate (breaths/min), optional
        spo2: Oxygen saturation (%), optional

    Returns:
        tuple: (is_danger: bool, reason: str, severity: str)
            severity: 'CRITICAL' or 'SEVERE' for logging
    """
    # CRITICAL - Immediate life threat
    if sys_bp >= 180 or dia_bp >= 120:
        return True, f"HYPERTENSIVE CRISIS ({sys_bp}/{dia_bp}) - Immediate stroke risk", "CRITICAL"

    if sys_bp < 90 or dia_bp < 60:
        return True, f"HYPOTENSION/SHOCK ({sys_bp}/{dia_bp}) - Organ perfusion failure", "CRITICAL"

    if temp >= 104.0:  # 40°C
        return True, f"EXTREME HYPERTHERMIA ({temp}°F) - Potential heat stroke/sepsis", "CRITICAL"

    if temp < 95.0:  # 35°C
        return True, f"HYPOTHERMIA ({temp}°F) - Medical emergency", "CRITICAL"

    if hr >= 150:
        return True, f"EXTREME TACHYCARDIA ({hr} bpm) - Critical cardiac stress", "CRITICAL"

    if hr < 40:
        return True, f"SEVERE BRADYCARDIA ({hr} bpm) - Heart block risk", "CRITICAL"

    if spo2 is not None and spo2 < 90:
        return True, f"SEVERE HYPOXEMIA (SpO2 {spo2}%) - Immediate oxygen support needed", "CRITICAL"

    if respiration_rate is not None and (respiration_rate >= 30 or respiration_rate <= 8):
        return True, f"CRITICAL RESPIRATORY RATE ({respiration_rate}/min) - Respiratory failure risk", "CRITICAL"

    # SEVERE - Urgent treatment needed (may override LOW/MEDIUM predictions)
    if sys_bp >= 160 or dia_bp >= 100:
        return True, f"SEVERE HYPERTENSION ({sys_bp}/{dia_bp}) - Urgent treatment needed", "SEVERE"

    if hr >= 120:
        return True, f"TACHYCARDIA ({hr} bpm) - Cardiac evaluation needed", "SEVERE"

    if hr < 50 and age > 40:  # Bradycardia (not athlete)
        # Check if patient is likely an athlete
        athlete_keywords = ['athlete', 'runner', 'marathon', 'triathlon', 'cyclist', 'gym', 'workout', 'exercise']
        is_likely_athlete = any(kw in symptom_text.lower() for kw in athlete_keywords)

        if not is_likely_athlete:
            return True, f"BRADYCARDIA ({hr} bpm) - Cardiac evaluation needed", "SEVERE"

    if temp >= 103.0:  # 39.4°C
        return True, f"HIGH FEVER ({temp}°F) - Possible sepsis/infection", "SEVERE"

    if spo2 is not None and spo2 < 94:
        return True, f"LOW OXYGEN SATURATION (SpO2 {spo2}%) - Urgent respiratory assessment", "SEVERE"

    if respiration_rate is not None and (respiration_rate >= 22 or respiration_rate <= 10):
        return True, f"ABNORMAL RESPIRATORY RATE ({respiration_rate}/min) - Urgent assessment needed", "SEVERE"

    # Elderly sepsis/decompensation pattern: borderline hypotension + fever can be dangerous.
    if age >= 70 and temp >= 100.4 and sys_bp <= 105:
        return True, f"ELDERLY FEVER WITH LOW BP ({sys_bp} mmHg, {temp}°F) - Sepsis/dehydration risk", "SEVERE"

    # No danger zones detected
    return False, "Vitals within acceptable ranges", "NORMAL"


def should_override_to_low_risk(age, sys_bp, dia_bp, hr, temp, symptom_text, history, respiration_rate=None, spo2=None):
    """
    Master decision function: Should we override XGBoost and assign LOW risk?

    This is an emergency patch to fix the model's inability to identify healthy patients.

    Args:
        age, sys_bp, dia_bp, hr, temp: Vital signs
        symptom_text: Patient symptoms
        history: Medical history
        respiration_rate: Respiratory rate (breaths/min), optional
        spo2: Oxygen saturation (%), optional

    Returns:
        tuple: (should_override: bool, reason: str, score: int)
    """
    symptom_lower = (symptom_text or '').lower()
    history_lower = (history or '').lower()

    athlete_keywords = ['athlete', 'runner', 'marathon', 'triathlon', 'cyclist', 'gym', 'workout', 'training']
    is_likely_athlete = any(kw in symptom_lower for kw in athlete_keywords)

    # Check 1: Vitals must be healthy (with athlete fallback for resting bradycardia)
    healthy_vitals = is_healthy_vitals(age, sys_bp, dia_bp, hr, temp, respiration_rate, spo2)
    if not healthy_vitals:
        athlete_vitals = (
            is_likely_athlete and
            90 <= sys_bp <= 130 and
            60 <= dia_bp <= 85 and
            45 <= hr <= 95 and
            96.5 <= temp <= 99.5 and
            (respiration_rate is None or 10 <= respiration_rate <= 22) and
            (spo2 is None or spo2 >= 95)
        )
        if not athlete_vitals:
            return False, "Vitals not in healthy range", 0

    # Check 2: No emergency symptoms
    if has_emergency_symptoms(symptom_text):
        return False, "Emergency symptoms detected", 0

    # Check 3: Routine visit is a strong signal for LOW risk
    if is_routine_visit(symptom_text):
        score = calculate_healthy_score(sys_bp, dia_bp, hr, temp, respiration_rate, spo2)
        return True, "Routine visit with healthy vitals", score

    # Check 4: No severe pre-existing conditions
    severe_conditions = ['heart disease', 'stroke history', 'cancer', 'organ failure']
    if history and history_lower != 'none':
        if any(cond in history_lower for cond in severe_conditions):
            return False, "Severe pre-existing condition", 0

    # Check 4.5: Stable chronic syndromes with healthy vitals should not over-trigger MEDIUM.
    chronic_low_conditions = ['fibromyalgia', 'anxiety', 'panic disorder']
    if any(cond in history_lower for cond in chronic_low_conditions):
        mild_vitals = (
            sys_bp <= 140 and dia_bp <= 90 and hr <= 95 and temp <= 99.5 and
            (respiration_rate is None or respiration_rate <= 21) and
            (spo2 is None or spo2 >= 95)
        )
        if mild_vitals and 'chest pain' not in symptom_lower and 'shortness of breath' not in symptom_lower:
            score = calculate_healthy_score(sys_bp, dia_bp, hr, temp, respiration_rate, spo2)
            return True, "Stable chronic condition with healthy vitals", score

    # Check 5: If vitals are healthy and symptoms are mild, override
    mild_symptoms = [
        'mild', 'slight', 'minor', 'small', 'little',
        'fatigue', 'tired', 'ache', 'sore',
        'cold', 'cough', 'runny nose', 'sniffles'
    ]

    # IMPORTANT: Only treat fever as mild if vitals are ALSO mild
    # Don't use fever keyword alone as it can indicate moderate illness
    fever_mentioned = 'fever' in symptom_lower

    # If symptoms contain "mild" or minor complaint words
    is_mild = any(word in symptom_lower for word in mild_symptoms)

    # Check length - complex symptoms are longer
    is_simple = len(symptom_text.split(',')) <= 2

    # CRITICAL FIX: Check vitals BEFORE applying mild override
    # Only override to LOW if BOTH symptoms are mild AND vitals are actually mild
    actually_mild_vitals = (
        sys_bp <= 135 and dia_bp <= 85 and hr <= 95 and temp <= 99.5 and
        (respiration_rate is None or respiration_rate <= 20) and
        (spo2 is None or spo2 >= 95)
    )

    if is_mild and is_simple and actually_mild_vitals:
        score = calculate_healthy_score(sys_bp, dia_bp, hr, temp, respiration_rate, spo2)
        return True, "Mild symptoms with mild vitals", score

    # If mentions fever but vitals are elevated, DON'T override
    if fever_mentioned and (sys_bp > 135 or dia_bp > 85 or hr > 95 or temp > 99.5):
        return False, "Fever with elevated vitals - requires evaluation", 0

    # Default: Don't override, let XGBoost decide
    # (Even though we know XGBoost will likely say HIGH/MEDIUM incorrectly)
    return False, "Symptoms too complex for rule-based override", 0


def _risk_rank(risk_level):
    text = (risk_level or '').upper()
    if 'HIGH' in text:
        return 3
    if 'MEDIUM' in text:
        return 2
    return 1


def _risk_label(rank):
    if rank >= 3:
        return 'HIGH'
    if rank == 2:
        return 'MEDIUM'
    return 'LOW'


def apply_contextual_risk_adjustments(risk_level, age, sys_bp, dia_bp, hr, temp, symptom_text, history='None'):
    """Apply context-aware post-processing to reduce known misclassifications.

    Returns:
        tuple: (adjusted_risk, reason)
    """
    symptom_lower = (symptom_text or '').lower()
    history_lower = (history or '').lower()
    rank = _risk_rank(risk_level)
    reason = ''

    # Escalate to HIGH for older patients with chest symptoms and concerning BP.
    chest_concern = (
        'chest pain' in symptom_lower or
        'chest discomfort' in symptom_lower or
        'discomfort in chest' in symptom_lower
    )
    if age >= 65 and chest_concern:
        if sys_bp >= 150 or dia_bp >= 95:
            if rank < 3:
                rank = 3
                reason = 'Elderly chest symptom escalation'

    # Escalate to HIGH for elderly low-BP fever/dehydration pattern.
    dehydration_words = ['dehydr', 'not drinking', 'weak', 'dizzy']
    if age >= 70 and temp >= 100.4 and sys_bp <= 105 and any(w in symptom_lower for w in dehydration_words):
        if rank < 3:
            rank = 3
            reason = 'Elderly fever + low BP dehydration/sepsis pattern'

    # Ensure at least MEDIUM for neurologic red-flag descriptions.
    neuro_words = ['worst headache', 'neck stiffness', 'neck stiff', 'syncope', 'passed out', 'fainted']
    if any(w in symptom_lower for w in neuro_words):
        if rank < 2:
            rank = 2
            reason = reason or 'Neurologic concern minimum MEDIUM'

    # Escalate to HIGH for severe headache + neck stiffness combo (possible bleed/meningitis/dissection).
    if (('severe headache' in symptom_lower or 'worst headache' in symptom_lower) and
            ('neck stiffness' in symptom_lower or 'neck stiff' in symptom_lower)):
        if rank < 3:
            rank = 3
            reason = 'Severe headache with neck stiffness escalation'

    # Escalate allergic-respiratory presentations with unstable vitals.
    allergy_words = ['swelling', 'hives', 'throat']
    if 'difficulty breathing' in symptom_lower and any(w in symptom_lower for w in allergy_words):
        if sys_bp <= 100 or hr >= 110:
            if rank < 3:
                rank = 3
                reason = 'Allergic respiratory instability escalation'

    # Cap to MEDIUM for probable benign chest discomfort in younger stable adults.
    if age < 60 and 'chest discomfort' in symptom_lower and 'crushing' not in symptom_lower and 'radiating' not in symptom_lower:
        if sys_bp < 150 and dia_bp < 95 and hr < 110:
            if rank > 2:
                rank = 2
                reason = 'Younger stable chest discomfort capped at MEDIUM'

    # Cap to MEDIUM for severe headache with normal vitals when no severe neuro deficit words.
    severe_neuro_words = ['slurred speech', 'weakness of one body side', 'paralysis', 'unconscious']
    has_neck_stiffness = ('neck stiffness' in symptom_lower or 'neck stiff' in symptom_lower)
    if (('worst headache' in symptom_lower or 'severe headache' in symptom_lower) and
            not has_neck_stiffness and
            not any(w in symptom_lower for w in severe_neuro_words)):
        if 100 <= sys_bp <= 145 and 60 <= dia_bp <= 92 and hr <= 100 and 97.0 <= temp <= 100.0:
            if rank > 2:
                rank = 2
                reason = 'Severe headache with stable vitals capped at MEDIUM'

    # Keep stable chronic pain/anxiety patterns from drifting to MEDIUM/HIGH.
    chronic_low_conditions = ['fibromyalgia', 'anxiety', 'panic disorder']
    if any(c in history_lower for c in chronic_low_conditions):
        if sys_bp <= 140 and dia_bp <= 90 and hr <= 95 and temp <= 99.5:
            if 'chest pain' not in symptom_lower and 'shortness of breath' not in symptom_lower:
                if rank > 1:
                    rank = 1
                    reason = 'Stable chronic syndrome downscaled to LOW'

    return _risk_label(rank), reason


def calibrate_medium_high_risk(risk_level, xgb_probs, news2_score, semantic_emergency,
                               is_danger=False, danger_severity='NORMAL', symptom_text='', age=0):
    """Refine MEDIUM/HIGH boundary using model probabilities and clinical context.

    This reduces false HIGH inflation while protecting true HIGH-risk cases.
    """
    high_prob = float(xgb_probs[2])
    med_prob = float(xgb_probs[1])
    text = (symptom_text or '').lower()
    risk = (risk_level or '').upper()

    chest_or_neuro = any(k in text for k in [
        'chest pain', 'crushing', 'speech', 'stroke', 'unconscious',
        'severe headache', 'worst headache', 'neck stiffness', 'neck stiff'
    ])

    # Protect clearly dangerous paths from accidental downgrades.
    if 'HIGH' in risk and (semantic_emergency or danger_severity == 'CRITICAL' or news2_score >= 7):
        return risk_level, 'Protected HIGH by clinical severity'

    # Downgrade uncertain HIGH to MEDIUM when evidence is weak.
    if 'HIGH' in risk and not semantic_emergency and danger_severity != 'CRITICAL':
        if high_prob < 0.45 and med_prob >= (high_prob * 0.9) and news2_score < 7 and not chest_or_neuro:
            return 'MEDIUM', 'Probability calibration downgraded uncertain HIGH'

    # Upgrade MEDIUM when high-risk probability and context align.
    if 'MEDIUM' in risk:
        strong_context = chest_or_neuro or (age >= 65 and 'chest' in text)
        if high_prob >= 0.40 and (news2_score >= 5 or strong_context or danger_severity == 'SEVERE'):
            return 'HIGH', 'Probability calibration upgraded MEDIUM to HIGH'

    return risk_level, 'No probability calibration change'
