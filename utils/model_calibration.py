"""
Enhanced Model Calibration Module
Fixes the MEDIUM/HIGH classification boundary to prevent false escalations
while protecting true high-risk cases
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


def classify_xgb_risk_with_calibration(xgb_probs, symptom_text='', age=0, sys_bp=120,
                                       dia_bp=80, hr=80, temp_f=98.6, history='None'):
    """
    Classify risk level using XGBoost probabilities with intelligent calibration.

    Fixes: XGBoost model rarely predicts MEDIUM (gets stuck in LOW/HIGH binary).
    This function redistributes probabilities to properly detect MEDIUM cases.

    Args:
        xgb_probs: Array of [P(LOW), P(MEDIUM), P(HIGH)]
        symptom_text: Patient's symptom description
        age, sys_bp, dia_bp, hr, temp_f, history: Patient vitals/history

    Returns:
        risk_level: 'LOW', 'MEDIUM', or 'HIGH'
        confidence: Confidence in the classification (0-1)
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])

    text = (symptom_text or '').lower()

    # === CRITICAL: Detect inadequate MEDIUM probability (model training issue) ===
    # If model gives <10% to MEDIUM but MULTIPLE moderate vitals exist, boost MEDIUM probability
    if prob_medium < 0.10 and prob_low > 0.75:
        # Check for MULTIPLE moderate signs (require 2+, not just 1)
        has_elevated_bp = (135 <= sys_bp < 160) or (85 <= dia_bp < 100)
        has_elevated_hr = (90 <= hr < 115)
        has_elevated_temp = (99.5 <= temp_f <= 102.5)

        moderate_elevation_count = sum([has_elevated_bp, has_elevated_hr, has_elevated_temp])

        if moderate_elevation_count >= 2:  # Require 2+ moderate signs
            # Redistribute probability towards MEDIUM
            # Take away from LOW bias and give to MEDIUM
            total = prob_low + prob_medium + prob_high
            prob_low = prob_low * 0.60  # Reduce LOW overconfidence
            prob_medium = max(0.30, prob_medium + (total * 0.25))  # Boost MEDIUM
            prob_high = prob_high * 1.1  # Slight HIGH boost
            # Renormalize
            total = prob_low + prob_medium + prob_high
            prob_low /= total
            prob_medium /= total
            prob_high /= total

    # === CRITICAL EMERGENCY INDICATORS ===
    critical_symptoms = [
        # Cardiac/Respiratory
        'crushing', 'chest pain', 'cannot breathe', 'shortness of breath', 'difficulty breathing',
        # Neurological
        'unconscious', 'seizure', 'stroke', 'altered mental status', 'disoriented',
        # Bleeding/Hemorrhage
        'hemorrhage', 'bleeding', 'blood vomiting', 'vomiting blood', 'hematemesis',
        'blood in urine', 'hematuria', 'coughing blood',
        # Allergic/Shock
        'anaphylaxis', 'throat swelling', 'severe allergic',
        # Neurological/Sensory
        'complete vision loss', 'sudden blindness', 'severe eye pain',
        # Urinary/GI
        'kidney pain', 'acute kidney', 'renal failure',
        # General critical indicators
        'severe pain', 'uncontrollable bleeding', 'loss of consciousness'
    ]
    has_critical_symptom = any(s in text for s in critical_symptoms)

    # === DANGEROUS VITALS ===
    is_critically_high_bp = sys_bp >= 180 or dia_bp >= 110
    is_critically_low_bp = sys_bp < 80 or dia_bp < 50
    is_critically_abnormal_hr = hr < 40 or hr > 130
    is_critically_abnormal_temp = temp_f > 104 or temp_f < 94

    critical_vitals = (is_critically_high_bp or is_critically_low_bp or
                      is_critically_abnormal_hr or is_critically_abnormal_temp)

    # === CLASSIFICATION LOGIC ===

    # Rule 1: HIGH confidence cases (protect true emergencies)
    if has_critical_symptom or critical_vitals:
        if prob_high >= 0.30:  # Lower threshold for high-risk cases with critical symptoms
            return 'HIGH', prob_high

    # Rule 2b: HARD THRESHOLD - If all vitals are normal, must be LOW (medical standard)
    # This prevents unnecessary escalations of truly low-risk patients
    all_vitals_normal = (
        sys_bp <= 132 and dia_bp <= 85 and  # Relaxed from < 130 to capture borderline
        hr < 85 and temp_f < 99.5
    )

    if all_vitals_normal and not has_critical_symptom:
        # All vitals truly normal → LOW regardless of probability
        return 'LOW', prob_low

    # Rule 2: Use probability thresholds (not just argmax)
    # Only classify as HIGH if probability is sufficiently high
    if prob_high >= 0.50:  # HIGH requires >= 50% confidence
        return 'HIGH', prob_high

    # Rule 3: MEDIUM classification (now improved)
    # MEDIUM is detected when:
    #   a) HIGH probability 0.30-0.50, OR
    #   b) MEDIUM probability >= 0.30 with vital elevation, OR
    #   c) LOW prob is not overwhelming (< 0.80)

    if prob_high >= 0.30 and prob_high < 0.50:
        return 'MEDIUM', prob_high

    if prob_medium >= 0.25:  # Boosted from 0.35
        # REFINED: Check for vital elevation (require 2+ signs for MEDIUM escalation)
        moderately_elevated_bp = (135 <= sys_bp < 170) or (85 <= dia_bp < 105)  # Stricter thresholds
        moderately_elevated_hr = (90 <= hr < 120)  # Higher threshold
        moderately_elevated_temp = (99.5 <= temp_f <= 102.5)  # Higher threshold

        vital_elevation_count = sum([moderately_elevated_bp, moderately_elevated_hr, moderately_elevated_temp])
        some_vital_elevation = vital_elevation_count >= 2  # Require at least 2 signs

        if some_vital_elevation or has_critical_symptom or prob_medium >= 0.35:
            return 'MEDIUM', prob_medium

    # Rule 4: Don't be over-confident in LOW if there are MULTIPLE moderate signs
    # REFINED: Require at least 2 vital signs elevated to escalate from LOW
    if prob_low >= 0.70:
        # Check for moderate concerns (be stricter: require multiple signs)
        moderately_elevated_bp = (135 <= sys_bp < 160) or (85 <= dia_bp < 100)  # Higher threshold
        moderately_elevated_hr = (90 <= hr < 115)  # Higher threshold
        moderately_elevated_temp = (99.5 <= temp_f <= 102.0)  # Higher threshold

        # Count how many vital signs are elevated
        vital_elevation_count = sum([moderately_elevated_bp, moderately_elevated_hr, moderately_elevated_temp])

        # Only escalate if 2+ vital signs elevated OR clear concerning symptoms
        if vital_elevation_count >= 2 and prob_high < 0.30:
            # Multiple moderate signs should escalate to MEDIUM
            return 'MEDIUM', prob_medium + 0.15

        # Single vital sign only - don't escalate (requires clearer picture)
        elif vital_elevation_count <= 1:
            return 'LOW', prob_low

    # Rule 5: LOW classification
    if prob_low >= 0.50:
        return 'LOW', prob_low

    # Default: Use probabilities to decide
    max_prob_idx = np.argmax(xgb_probs)
    if max_prob_idx == 2:
        if prob_high < 0.35:
            return 'MEDIUM', prob_medium


def refine_medium_high_boundary(risk_level, xgb_probs, symptom_text='', age=0,
                                sys_bp=120, dia_bp=80, hr=80, temp_f=98.6,
                                history='None'):
    """
    Fine-tune the MEDIUM/HIGH boundary to prevent false escalations.

    This is called as a secondary filter after initial classification.
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])
    text = (symptom_text or '').lower()

    # If model predicted HIGH but probabilities suggest otherwise
    if 'HIGH' in risk_level.upper():
        # Check for false escalations
        if prob_high < 0.40 and prob_medium > 0.35:
            # Weak HIGH, strong MEDIUM → downgrade

            # But protect critical cases
            critical_indicator = any(k in text for k in [
                'chest pain', 'crossing', 'breathing', 'conscious',
                'hemorrhage', 'stroke', 'seizure'
            ])

            if not critical_indicator and not (sys_bp > 170 or dia_bp > 105 or hr > 120):
                logger.info(f"Refined: HIGH → MEDIUM (prob_high={prob_high:.2f}, prob_medium={prob_medium:.2f})")
                return 'MEDIUM'

    # If model predicted MEDIUM but should be HIGH
    elif 'MEDIUM' in risk_level.upper():
        # Escalate MEDIUM to HIGH if:
        # 1. HIGH probability >= 0.42 (was 0.45), OR
        # 2. Elevated BP + elevated HR + fever symptoms

        if prob_high >= 0.42:
            # Moderate-high probability + concerning vitals
            has_elevated_bp = (sys_bp >= 145)
            has_elevated_hr = (hr >= 100)
            has_fever = temp_f >= 100.5

            has_concerning_symptom = any(k in text for k in [
                'chest pain', 'crushing', 'severe', 'fever', 'difficulty breathing'
            ])

            if has_concerning_symptom or (has_elevated_bp and has_elevated_hr and has_fever):
                logger.info(f"Refined: MEDIUM → HIGH (prob_high={prob_high:.2f})")
                return 'HIGH'

    return risk_level


def calibrate_based_on_vitals(risk_level, sys_bp, dia_bp, hr, temp_f, spo2,
                              respiration_rate, symptom_text='', history='None'):
    """
    Apply vital-sign based calibration and validate the risk classification.

    Ensures that extreme vital signs are properly reflected in risk level.
    """

    text = (symptom_text or '').lower()
    history_lower = (history or '').lower()

    # === DANGER ZONE VITALS ===
    critical_bp = sys_bp >= 200 or dia_bp >= 120 or sys_bp < 70 or dia_bp < 40
    critical_hr = hr < 35 or hr > 140
    critical_temp = temp_f > 105 or temp_f < 94
    critical_spo2 = spo2 < 85
    critical_rr = respiration_rate > 35 or respiration_rate < 8

    has_critical_vital = critical_bp or critical_hr or critical_temp or critical_spo2 or critical_rr

    # If critical vitals exist, must be at least MEDIUM
    if has_critical_vital and 'LOW' in risk_level.upper():
        return 'MEDIUM'

    # If multiple danger zones + symptoms, escalate to HIGH
    danger_count = sum([critical_bp, critical_hr, critical_temp, critical_spo2, critical_rr])
    if danger_count >= 2:
        if not 'HIGH' in risk_level.upper():
            return 'HIGH'

    # === NEW: Escalate MEDIUM to HIGH if multiple moderate vitals + concerning symptoms ===
    if 'MEDIUM' in risk_level.upper():
        # Multiple moderate elevations with symptoms should be HIGH (medical best practice)
        moderately_high_bp = (142 <= sys_bp < 180)  # Multiple moderate vital zone
        moderately_high_hr = (98 <= hr <= 130)
        moderately_high_temp = (100.0 <= temp_f <= 103.0)

        moderate_count = sum([moderately_high_bp, moderately_high_hr, moderately_high_temp])

        # If 2+ moderate vital elevations, escalate appropriately
        if moderate_count >= 2:
            has_concerning_symptom = any(word in symptoms.lower() for word in [
                'fever', 'body aches', 'aches', 'pain', 'serious', 'severe', 'distress', 'difficulty'
            ])
            if has_concerning_symptom:
                return 'HIGH'

    # === PROTECT CRITICAL CASES - DO NOT DOWNGRADE IF CRITICAL VITALS ===
    if 'HIGH' in risk_level.upper():
        # Only downgrade if BOTH conditions met:
        # 1) All vitals are actually MODERATE (not critical)
        # 2) Symptoms are truly benign

        # Check: do we have CRITICAL vitals that warrant HIGH?
        has_critical_bp = sys_bp >= 180 or dia_bp >= 110
        has_critical_hr = hr >= 130
        has_critical_temp = temp_f > 103.5

        # NEVER downgrade if we have truly critical vitals
        if has_critical_bp or has_critical_hr or has_critical_temp:
            return 'HIGH'

        # Only downgrade if ALL of: moderate vitals AND clearly benign symptoms
        mild_vit_bp = (140 <= sys_bp < 180) and (85 <= dia_bp < 110)
        mild_vit_hr = (100 <= hr < 130)
        mild_vit_temp = (99.5 <= temp_f <= 103.5)

        all_moderate = mild_vit_bp and mild_vit_hr and mild_vit_temp

        # Only benign symptoms (fever + aches, but NOT chest pain/breathing issues)
        only_benign = any(word in text for word in ['fever', 'aches', 'malaise']) \
                     and not any(word in text for word in ['chest', 'breathing', 'distress', 'crushing', 'hemorrhage'])

        # Only downgrade to MEDIUM if BOTH conditions: all vitals moderate AND only benign symptoms
        if all_moderate and only_benign:
            return 'MEDIUM'

    return risk_level
