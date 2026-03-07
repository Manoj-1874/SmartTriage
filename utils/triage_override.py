"""
Emergency fix for XGBoost model trained on sick patients only.
Implements rule-based override for obviously healthy vitals.
"""


def is_healthy_vitals(age, sys_bp, dia_bp, hr, temp):
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
        bp_healthy = (90 <= sys_bp <= 140 and 60 <= dia_bp <= 90)
        hr_healthy = 50 <= hr <= 100

    # Age should be reasonable for healthy patient
    # Very young children and very elderly require different assessment
    age_reasonable = 5 <= age <= 90

    return age_reasonable and bp_healthy and hr_healthy and temp_healthy


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
        'gasping', 'choking',

        # Cardiovascular
        'chest pain', 'crushing', 'heart attack', 'cardiac arrest',
        'severe chest pain', 'radiating pain',

        # Neurological
        'unconscious', 'unresponsive', 'seizure', 'stroke',
        'slurred speech', 'weakness of one body side', 'altered sensorium',
        'severe headache', 'sudden confusion', 'confusion', 'disoriented',
        'altered mental status', 'not responding normally',

        # Trauma/Bleeding
        'hemorrhage', 'severe bleeding', 'uncontrolled bleeding',
        'head injury', 'neck injury', 'spinal injury',

        # Poisoning/Allergic
        'poisoning', 'overdose', 'allergic reaction', 'anaphylaxis',
        'swelling of throat', 'difficulty swallowing',

        # Sepsis/Infection
        'sepsis', 'high fever', 'fever above 103', 'fever above 104',

        # Pain severity
        'severe pain', 'excruciating', 'unbearable pain', 'agonizing',

        # Loss of function
        'paralysis', 'cannot move', 'loss of consciousness', 'syncope',
        'sudden vision loss', 'sudden hearing loss'
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
        'after exercise', 'just checking', 'checking vitals'
    ]

    symptom_lower = symptom_text.lower()
    return any(keyword in symptom_lower for keyword in routine_keywords)


def calculate_healthy_score(sys_bp, dia_bp, hr, temp):
    """
    Calculate a "healthy score" (0-100) for patients with healthy vitals.
    Score near 100 = very healthy, score near 50 = borderline.

    Args:
        sys_bp: Systolic BP
        dia_bp: Diastolic BP
        hr: Heart rate
        temp: Temperature (F)

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

    return max(0, min(100, int(score)))


def should_override_to_low_risk(age, sys_bp, dia_bp, hr, temp, symptom_text, history):
    """
    Master decision function: Should we override XGBoost and assign LOW risk?

    This is an emergency patch to fix the model's inability to identify healthy patients.

    Args:
        age, sys_bp, dia_bp, hr, temp: Vital signs
        symptom_text: Patient symptoms
        history: Medical history

    Returns:
        tuple: (should_override: bool, reason: str, score: int)
    """
    # Check 1: Vitals must be healthy
    if not is_healthy_vitals(age, sys_bp, dia_bp, hr, temp):
        return False, "Vitals not in healthy range", 0

    # Check 2: No emergency symptoms
    if has_emergency_symptoms(symptom_text):
        return False, "Emergency symptoms detected", 0

    # Check 3: Routine visit is a strong signal for LOW risk
    if is_routine_visit(symptom_text):
        score = calculate_healthy_score(sys_bp, dia_bp, hr, temp)
        return True, "Routine visit with healthy vitals", score

    # Check 4: No severe pre-existing conditions
    severe_conditions = ['heart disease', 'stroke history', 'cancer', 'organ failure']
    if history and history.lower() != 'none':
        if any(cond in history.lower() for cond in severe_conditions):
            return False, "Severe pre-existing condition", 0

    # Check 5: If vitals are healthy and symptoms are mild, override
    mild_symptoms = [
        'mild', 'slight', 'minor', 'small', 'little',
        'fatigue', 'tired', 'ache', 'sore',
        'cold', 'cough', 'runny nose', 'sniffles',
        'fever'  # If temp is normal but patient reports "fever", it's likely mild/phantom
    ]

    # If symptoms contain "mild" or minor complaint words
    symptom_lower = symptom_text.lower()
    is_mild = any(word in symptom_lower for word in mild_symptoms)

    # Check length - complex symptoms are longer
    is_simple = len(symptom_text.split(',')) <= 2

    if is_mild and is_simple:
        score = calculate_healthy_score(sys_bp, dia_bp, hr, temp)
        return True, "Mild symptoms with healthy vitals", score

    # Default: Don't override, let XGBoost decide
    # (Even though we know XGBoost will likely say HIGH/MEDIUM incorrectly)
    return False, "Symptoms too complex for rule-based override", 0
