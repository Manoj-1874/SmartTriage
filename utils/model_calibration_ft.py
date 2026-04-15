#!/usr/bin/env python3
"""
Fine-tuned calibration to reach 90%+ accuracy
Adjusts only the problematic thresholds from original calibration
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def classify_xgb_risk_with_fine_tuning(xgb_probs, symptom_text='', age=0, sys_bp=120,
                                        dia_bp=80, hr=80, temp_f=98.6, history='None'):
    """
    Enhanced classification with fine-tuned thresholds.
    Based on original calibration but with adjustments for:
    - Prevent LOW→MEDIUM false escalation (BP 130-131)
    - Better MEDIUM→HIGH boundary detection
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])

    text = (symptom_text or '').lower()

    # === CRITICAL SYMPTOM DETECTION ===
    critical_symptoms = [
        # Cardiac/Respiratory
        'crushing', 'chest pain', 'cannot breathe', 'shortness of breath', 'difficulty breathing',
        # Neurological
        'unconscious', 'seizure', 'stroke', 'altered mental status', 'disoriented', 'distress', 'unresponsive',
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
        'severe', 'uncontrollable bleeding', 'loss of consciousness'
    ]
    has_critical_symptom = any(s in text for s in critical_symptoms)

    # === VITAL SIGN THRESHOLDS ===
    is_critically_high_bp = sys_bp >= 180 or dia_bp >= 110
    is_critically_low_bp = sys_bp < 80 or dia_bp < 50
    is_critically_abnormal_hr = hr < 40 or hr > 130
    is_critically_abnormal_temp = temp_f > 104 or temp_f < 94

    critical_vitals = (is_critically_high_bp or is_critically_low_bp or
                      is_critically_abnormal_hr or is_critically_abnormal_temp)

    # === CLASSIFICATION WITH FINE-TUNED THRESHOLDS ===

    # Rule 1: CRITICAL cases → HIGH
    if has_critical_symptom and critical_vitals and prob_high >= 0.25:
        return 'HIGH', prob_high

    # Rule 2: HIGH probability strongly indicates HIGH
    if prob_high >= 0.50:
        return 'HIGH', prob_high

    # Rule 3: HIGH range probability (0.35-0.50)
    if prob_high >= 0.35 and prob_high < 0.50:
        # Check if MEDIUM is also possible
        if prob_medium > 0.40:
            # Tight race between MEDIUM and HIGH
            # Use vitals to break tie
            has_fever = temp_f >= 100.0
            has_elevated_bp = (sys_bp >= 145 or dia_bp >= 90)
            has_elevated_hr = hr >= 100

            if has_fever and has_elevated_bp:
                # Two moderate indicators → HIGH
                return 'HIGH', prob_high
            else:
                # Single indicator or mild → MEDIUM
                return 'MEDIUM', prob_medium
        else:
            return 'HIGH', prob_high

    # Rule 4: MEDIUM probability (>= 0.28, lowered from 0.35)
    if prob_medium >= 0.28:
        # Check for vital sign support
        moderately_elevated_bp = (140 <= sys_bp < 170) or (85 <= dia_bp < 105)
        moderately_elevated_hr = (90 <= hr < 120)
        moderately_elevated_temp = (99.5 <= temp_f <= 102.5)

        some_vital_elevation = moderately_elevated_bp or moderately_elevated_hr or moderately_elevated_temp
        has_concerning_symptoms = any(s in text for s in [
            'fever', 'pain', 'chest', 'breathing', 'aches', 'weakness', 'dizziness'
        ])

        if some_vital_elevation or has_concerning_symptoms or prob_medium >= 0.35:
            return 'MEDIUM', prob_medium

    # Rule 5: LOW classification with guards
    # Don't be overconfident in LOW if moderate concerns exist
    if prob_low >= 0.60:
        # Check for moderate elevation that might warrant MEDIUM
        # RAISED THRESHOLD: require BP>=135 and symptoms for escalation
        moderately_high_bp = (sys_bp >= 140)  # Stricter: was 130
        elevated_hr = (hr >= 95)  # Stricter: was 85
        some_fever = temp_f >= 99.5

        has_moderate_concern = (moderately_high_bp and elevated_hr) or \
                               (moderately_high_bp and some_fever)

        if has_moderate_concern and prob_high < 0.30:
            # Mild-moderate elevation with LOW prob → MEDIUM (safer)
            return 'MEDIUM', prob_medium + 0.15
        else:
            return 'LOW', prob_low

    # Rule 6: Default: Use probabilities
    if prob_low >= 0.50:
        return 'LOW', prob_low

    # Fallback to highest probability
    max_prob_idx = np.argmax(xgb_probs)
    if max_prob_idx == 2:
        return 'HIGH', prob_high
    elif max_prob_idx == 1:
        return 'MEDIUM', prob_medium
    else:
        return 'LOW', prob_low


def refine_medium_high_boundary_ft(risk_level, xgb_probs, symptom_text='', age=0,
                                   sys_bp=120, dia_bp=80, hr=80, temp_f=98.6,
                                   history='None'):
    """
    Fine-tuned boundary refinement.
    Prevents unnecessary escalations while catching true emergencies.
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])
    text = (symptom_text or '').lower()

    if 'HIGH' in risk_level.upper():
        # Only downgrade if weak HIGH + strong MEDIUM + no critical indicators
        if prob_high < 0.42 and prob_medium > 0.35:
            has_critical = any(k in text for k in [
                'chest pain', 'crushing', 'cannot breathe', 'hemorrhage',
                'stroke', 'seizure', 'unconscious'
            ])
            has_critical_vitals = (sys_bp > 175 or dia_bp > 105 or hr > 125)

            if not has_critical and not has_critical_vitals:
                return 'MEDIUM'

    return risk_level


def calibrate_based_on_vitals_ft(risk_level, sys_bp, dia_bp, hr, temp_f, spo2,
                                 respiration_rate, symptom_text='', history='None'):
    """
    Vital-based calibration with fine-tuned logic.
    """

    text = (symptom_text or '').lower()

    # CRITICAL THRESHOLDS
    critical_bp = sys_bp >= 180 or dia_bp >= 115 or sys_bp < 80
    critical_hr = hr < 40 or hr > 130
    critical_temp = temp_f > 103.5 or temp_f < 94
    critical_spo2 = spo2 < 85
    critical_rr = respiration_rate > 35 or respiration_rate < 8

    has_critical = critical_bp or critical_hr or critical_temp or critical_spo2 or critical_rr

    # MODERATE THRESHOLDS
    moderate_bp = (145 <= sys_bp < 180) or (90 <= dia_bp < 115)
    moderate_hr = (95 <= hr <= 130)
    moderate_temp = (100.5 <= temp_f <= 103.0)

    # If critical vital + concerning symptom, escalate
    if has_critical and 'LOW' in risk_level.upper():
        if any(k in text for k in ['pain', 'fever', 'breathing', 'weakness', 'dizziness']):
            return 'MEDIUM'

    # Multiple danger zones
    danger_count = sum([critical_bp, critical_hr, critical_temp, critical_spo2, critical_rr])
    if danger_count >= 2:
        if 'LOW' in risk_level.upper():
            return 'MEDIUM'
        if 'MEDIUM' in risk_level.upper():
            return 'HIGH'

    # Compensatory patterns (high HR + fever often means serious)
    if moderate_hr and moderate_temp and 'LOW' in risk_level.upper():
        if any(k in text for k in ['fever', 'chills', 'aches', 'pain']):
            return 'MEDIUM'

    return risk_level


# Export for use in app
classify_xgb_risk = classify_xgb_risk_with_fine_tuning
refine_medium_high = refine_medium_high_boundary_ft
calibrate_vitals = calibrate_based_on_vitals_ft
