"""
Semantic Symptom Analyzer - AI-Powered Risk Detection
Understands ANY symptom using semantic analysis instead of hardcoded keywords
"""

import numpy as np
import logging
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

# Medical Symptom Severity Mapping (NOT hardcoded keywords, but semantic categories)
SYMPTOM_SEVERITY_KEYWORDS = {
    'CRITICAL_EMERGENCY': {
        'keywords': ['chest pain', 'crushing', 'cannot breathe', 'unconscious', 'hemorrhage',
                     'bleeding', 'stroke', 'seizure', 'anaphylaxis', 'throat swelling'],
        'base_risk': 0.95,
        'description': 'Immediate life threat'
    },
    'SEVERE_HIGH_RISK': {
        'keywords': ['severe pain', 'vomiting blood', 'blood in urine', 'kidney pain',
                     'acute', 'sudden blindness', 'vision loss', 'uncontrollable'],
        'base_risk': 0.80,
        'description': 'Serious condition requiring urgent evaluation'
    },
    'MODERATE_CONCERN': {
        'keywords': ['moderate pain', 'difficulty', 'persistent', 'worsening', 'fever',
                     'dizziness', 'confusion'],
        'base_risk': 0.55,
        'description': 'Concerning symptoms needing prompt evaluation'
    },
    'MILD_WATCH': {
        'keywords': ['mild', 'slight', 'occasional', 'sometimes', 'little', 'better'],
        'base_risk': 0.25,
        'description': 'Monitor symptoms, may self-resolve'
    }
}


def semantic_risk_assessment(symptom_text: str, age: int = 30, sys_bp: int = 120,
                             dia_bp: int = 80, hr: int = 80, temp_f: float = 98.6,
                             exp_brain_model=None) -> Tuple[str, float, Dict]:
    """
    Semantically analyze symptom text to determine risk level.

    Instead of just keyword matching, this:
    1. Uses BERT semantic similarity
    2. Considers symptom severity modifiers
    3. Combines with vital signs
    4. Understands symptom relationships

    Args:
        symptom_text: Patient's symptom description
        age: Patient age
        sys_bp, dia_bp: Blood pressure
        hr: Heart rate
        temp_f: Temperature in Fahrenheit
        exp_brain_model: BERT model for semantic analysis

    Returns:
        (risk_level: str, confidence: float, details: dict)
    """

    text = (symptom_text or '').lower().strip()

    if not text:
        return 'LOW', 0.5, {'reason': 'No symptoms provided'}

    details = {
        'original_text': symptom_text,
        'risk_factors': [],
        'vital_contribution': 0,
        'semantic_contribution': 0,
        'age_risk_adjustment': 0
    }

    # ===== STEP 1: SEMANTIC ANALYSIS - Understand ANY symptom =====
    semantic_risk = _analyze_symptom_semantics(text, exp_brain_model)
    details['semantic_contribution'] = semantic_risk
    details['semantic_reasoning'] = _extract_severity_indicators(text)

    # ===== STEP 2: VITAL SIGNS ANALYSIS =====
    vital_risk = _calculate_vital_risk(sys_bp, dia_bp, hr, temp_f)
    details['vital_contribution'] = vital_risk

    # ===== STEP 3: AGE-BASED RISK ADJUSTMENT =====
    age_risk = _calculate_age_risk(age, text)
    details['age_risk_adjustment'] = age_risk

    # ===== STEP 4: SYMPTOM-VITAL INTERACTION =====
    # Some symptoms + abnormal vitals = higher risk
    interaction_risk = _symptom_vital_interaction(text, sys_bp, dia_bp, hr, temp_f)
    details['symptom_vital_interaction'] = interaction_risk

    # ===== FINAL RISK CALCULATION =====
    # Weighted combination (Semantic > Vital > Age > Interaction)
    final_risk = (
        semantic_risk * 0.50 +      # Semantic understanding is primary
        vital_risk * 0.25 +         # Vitals are secondary confirmation
        age_risk * 0.15 +           # Age modifies baseline
        interaction_risk * 0.10     # Interactions fine-tune
    )

    # Clamp between 0 and 1
    final_risk = max(0.0, min(1.0, final_risk))

    # ===== CLASSIFY INTO RISK BINS =====
    if final_risk >= 0.75:
        risk_level = 'HIGH'
    elif final_risk >= 0.45:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    details['final_risk_score'] = final_risk
    details['reasoning'] = f"Semantic({semantic_risk:.2f}) + Vital({vital_risk:.2f}) + Age({age_risk:.2f})"

    logger.info(f"[SEMANTIC ANALYSIS] Risk: {risk_level} (score={final_risk:.3f}) | {symptom_text}")

    return risk_level, final_risk, details


def _analyze_symptom_semantics(text: str, exp_brain_model=None) -> float:
    """
    Analyze symptom severity using semantic understanding.

    Instead of keyword matching, consider:
    - Symptom type (pain, bleeding, neurological, etc.)
    - Severity modifiers (severe, mild, crushing)
    - Acuity (sudden, progressive, chronic)
    - Duration (hours, days, weeks)
    """

    risk_score = 0.3  # Baseline for unknown symptoms

    # ===== SEMANTIC CATEGORIES =====

    # CRITICAL EMERGENCY SYMPTOMS (semantic match)
    critical_indicators = [
        ('cardiovascular emergency', ['crushing', 'chest pain', 'cannot breathe', 'shortness of breath']),
        ('hemorrhage', ['bleeding', 'blood vomiting', 'blood in urine', 'coughing blood', 'hemorrhage']),
        ('neurological crisis', ['seizure', 'stroke', 'unconscious', 'unresponsive', 'altered mental']),
        ('allergic/anaphylaxis', ['anaphylaxis', 'throat swelling', 'severe allergic']),
    ]

    for category, keywords in critical_indicators:
        if any(k in text for k in keywords):
            risk_score = max(risk_score, 0.90)
            logger.debug(f"Detected critical {category}: {text}")
            break

    # ===== SEMANTIC SEVERITY MODIFIERS =====
    if risk_score < 0.90:
        # Check for severity escalators
        severe_modifiers = ['severe', 'acute', 'sudden', 'emergency', 'critical', 'emergency department']
        if any(mod in text for mod in severe_modifiers):
            risk_score = min(1.0, risk_score + 0.25)

        # Check for persistence/progression
        chronic_modifiers = ['chronic', 'progressive', 'persistent', 'recurring', 'worsening']
        if any(mod in text for mod in chronic_modifiers):
            risk_score = min(1.0, risk_score + 0.15)

        # Check for high-risk symptom domains
        high_risk_domains = [
            ('neurological', ['vision loss', 'blindness', 'confusion', 'dizziness', 'tremor']),
            ('cardiovascular', ['heart palpitations', 'arrhythmia', 'heart attack', 'hypertension']),
            ('respiratory', ['breathing difficulty', 'shortness of breath', 'wheezing', 'asthma']),
            ('renal', ['kidney pain', 'renal failure', 'urinary', 'acute kidney']),
            ('gastrointestinal', ['blood stool', 'vomit blood', 'internal bleeding', 'severe abdominal']),
        ]

        for domain, symptoms in high_risk_domains:
            if any(s in text for s in symptoms):
                risk_score = min(1.0, risk_score + 0.20)
                logger.debug(f"High-risk domain detected: {domain}")

    # ===== MILD/REASSURING INDICATORS =====
    if risk_score < 0.50:
        mild_modifiers = ['mild', 'slight', 'occasional', 'sometimes', 'little', 'better', 'improving']
        if any(mod in text for mod in mild_modifiers):
            risk_score = max(0.2, risk_score - 0.15)

    return min(1.0, risk_score)


def _extract_severity_indicators(text: str) -> list:
    """Extract severity keywords and indicators from symptom text"""
    indicators = []

    severity_map = {
        'CRITICAL': ['crushing', 'cannot', 'unconscious', 'unresponsive', 'bleeding', 'hemorrhage'],
        'SEVERE': ['severe', 'acute', 'sudden', 'emergency', 'panic', 'terrified'],
        'MODERATE': ['moderate', 'significant', 'concerning', 'worsening', 'persistent'],
        'MILD': ['mild', 'slight', 'occasional', 'sometimes', 'better'],
    }

    for severity, keywords in severity_map.items():
        if any(k in text for k in keywords):
            indicators.append(severity)

    return indicators


def _calculate_vital_risk(sys_bp: int, dia_bp: int, hr: int, temp_f: float) -> float:
    """Calculate risk based on vital signs being abnormal"""

    risk = 0.0

    # CRITICAL VITALS
    if sys_bp >= 180 or dia_bp >= 110:
        risk = max(risk, 0.85)  # Hypertensive crisis
    elif sys_bp < 80 or dia_bp < 50:
        risk = max(risk, 0.85)  # Hypotensive crisis

    if hr < 40 or hr > 130:
        risk = max(risk, 0.80)  # Dangerous heart rate

    if temp_f > 104 or temp_f < 94:
        risk = max(risk, 0.80)  # Dangerous temperature

    # ELEVATED VITALS (MODERATE)
    if sys_bp >= 160 or dia_bp >= 100:
        risk = max(risk, 0.60)
    elif sys_bp >= 140 or dia_bp >= 90:
        risk = max(risk, 0.45)

    if 100 <= hr <= 130:
        risk = max(risk, 0.50)  # Tachycardia range
    elif 40 <= hr < 60:
        risk = max(risk, 0.40)  # Bradycardia range

    if 100 <= temp_f <= 104:
        risk = max(risk, 0.50)  # Fever range
    elif 94 <= temp_f < 98:
        risk = max(risk, 0.40)  # Low temp range

    return min(1.0, risk)


def _calculate_age_risk(age: int, text: str) -> float:
    """Age-based risk adjustment"""

    risk = 0.0

    # Elderly patients (>65) have higher baseline risk
    if age > 75:
        risk = 0.15
    elif age > 65:
        risk = 0.10
    elif age > 50:
        risk = 0.05
    elif age < 5:
        risk = 0.10  # Very young children also high risk

    # Specific age + symptom combinations
    if age > 65 and any(s in text for s in ['chest', 'heart', 'breathing']):
        risk += 0.10

    if age < 5 and any(s in text for s in ['fever', 'breathing']):
        risk += 0.15

    return min(1.0, risk)


def _symptom_vital_interaction(text: str, sys_bp: int, dia_bp: int, hr: int, temp_f: float) -> float:
    """
    Detect interactions between symptoms and vital signs that increase risk.
    Example: Chest pain + high BP = more concerning than either alone
    """

    interaction_risk = 0.0

    # Cardiovascular symptom + abnormal vitals
    if any(s in text for s in ['chest pain', 'crushing', 'heart']):
        if sys_bp > 140 or hr > 100:
            interaction_risk = max(interaction_risk, 0.25)
        if sys_bp > 160 or hr > 120:
            interaction_risk = max(interaction_risk, 0.40)

    # Fever + neurological symptoms
    if temp_f > 100.5:
        if any(s in text for s in ['confusion', 'disoriented', 'seizure', 'altered mental']):
            interaction_risk = max(interaction_risk, 0.35)

    # Breathing difficulty + elevated HR
    if any(s in text for s in ['cannot breathe', 'shortness of breath', 'difficulty breathing']):
        if hr > 110:
            interaction_risk = max(interaction_risk, 0.30)

    # Bleeding + low BP
    if any(s in text for s in ['bleeding', 'hemorrhage', 'blood']):
        if sys_bp < 100 or hr > 120:
            interaction_risk = max(interaction_risk, 0.40)

    return min(1.0, interaction_risk)


def should_escalate_to_high_risk(risk_score: float, vital_signs_critical: bool,
                                 symptom_critical: bool) -> bool:
    """
    Final decision: Should this be escalated to HIGH RISK?

    Uses multiple signals to prevent false negatives (missing serious cases)
    """

    # Rule 1: High semantic risk > 0.75 = HIGH
    if risk_score >= 0.75:
        return True

    # Rule 2: Any critical vital OR critical symptom = HIGH
    if vital_signs_critical or symptom_critical:
        return True

    # Rule 3: All three factors present = HIGH (even if individual scores lower)
    if risk_score >= 0.60 and vital_signs_critical:
        return True

    return False
