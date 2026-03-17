#!/usr/bin/env python3
"""
Improved Calibration Module - v2
Optimized thresholds to achieve 90%+ accuracy while maintaining safety
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

def classify_xgb_risk_with_calibration_v2(xgb_probs, symptom_text='', age=0, sys_bp=120,
                                           dia_bp=80, hr=80, temp_f=98.6, history='None'):
    """
    Improved risk classification with optimized thresholds for 90%+ accuracy.

    Key improvements:
    1. Higher threshold for escalating LOW→MEDIUM (needs multiple moderate signs)
    2. Higher threshold for escalating MEDIUM→HIGH (> 0.45 probability)
    3. Better vital sign range classification
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])

    text = (symptom_text or '').lower()

    # === CRITICAL EMERGENCY INDICATORS ===
    critical_symptoms = [
        'crushing', 'chest pain', 'cannot breathe', 'unconscious',
        'hemorrhage', 'bleeding', 'stroke', 'seizure', 'anaphylaxis',
        'throat swelling', 'altered mental status', 'disoriented', 'distress',
        'unresponsive', 'severe'
    ]
    has_critical_symptom = any(s in text for s in critical_symptoms)

    # === DANGEROUS VITALS ===
    # HIGH danger zone: BP ≥180 or HR >130 or Temp >104
    is_critically_high_bp = sys_bp >= 180 or dia_bp >= 115
    is_critically_low_bp = sys_bp < 80 or dia_bp < 50
    is_critically_abnormal_hr = hr < 40 or hr > 135
    is_critically_abnormal_temp = temp_f > 103.5 or temp_f < 94

    critical_vitals = (is_critically_high_bp or is_critically_low_bp or
                      is_critically_abnormal_hr or is_critically_abnormal_temp)

    # MEDIUM zone: 140-180 SBP or 100-115 DBP, 100-130 HR, 100-103.5 Temp
    moderately_high_bp = (145 <= sys_bp < 180) or (95 <= dia_bp < 115)
    moderately_high_hr = (100 <= hr <= 130)
    moderately_high_temp = (100.0 <= temp_f <= 103.0)

    # Mild elevation: 130-145 SBP or 85-100 DBP, 85-100 HR, 99-100 Temp
    mildly_elevated_bp = (130 <= sys_bp < 145) or (85 <= dia_bp < 95)
    mildly_elevated_hr = (85 <= hr < 100)
    mildly_elevated_temp = (99.0 <= temp_f < 100.0)

    # === CLASSIFICATION LOGIC ===

    # Rule 1: HIGH - Only for truly critical cases
    # HIGH if: critical symptoms/vitals + prob_high >= 0.40
    # OR: clear HIGH probability (>= 0.55)
    if has_critical_symptom and critical_vitals:
        if prob_high >= 0.35:
            return 'HIGH', max(prob_high, 0.65)

    if prob_high >= 0.55:  # High threshold for HIGH
        return 'HIGH', prob_high

    if has_critical_symptom and prob_high >= 0.40:
        # Double check: are there also critical vitals?
        if is_critically_high_bp or is_critically_abnormal_hr or is_critically_abnormal_temp:
            return 'HIGH', max(prob_high, 0.55)

    # Rule 2: MEDIUM - Multiple moderate indicators
    # MEDIUM if:
    #   - prob_high: 0.40-0.55 (likely MEDIUM/HIGH boundary), OR
    #   - prob_medium >= 0.38 with moderate vital elevation, OR
    #   - Multiple moderate vital signs (BP + HR + Temp elevated)

    if prob_high >= 0.40 and prob_high < 0.55:
        # HIGH probability in medium range - classify as MEDIUM
        return 'MEDIUM', prob_high

    # Count moderate vital elevations
    moderate_vital_count = sum([
        moderately_high_bp, moderately_high_hr, moderately_high_temp,
        mildly_elevated_bp and (mildly_elevated_hr or mildly_elevated_temp),
        mildly_elevated_hr and mildly_elevated_temp
    ])

    if prob_medium >= 0.35:
        # Model is confident about MEDIUM
        if moderate_vital_count >= 1 or has_critical_symptom:
            return 'MEDIUM', prob_medium

    if moderate_vital_count >= 2:
        # Multiple moderate vital signs → MEDIUM
        if prob_high < 0.40:  # But not if clearly trending HIGH
            return 'MEDIUM', max(prob_medium, 0.35)

    # Rule 3: LOW - Only if probabilities and vitals support it
    # LOW if: prob_low >= 0.60 AND no moderate+vital elevations

    if prob_low >= 0.60:
        # Check if there are too many moderate signs
        if moderate_vital_count == 0 and prob_medium < 0.25:
            return 'LOW', prob_low
        elif moderate_vital_count <= 1 and prob_high < 0.30:
            # Slight elevation but not enough for MEDIUM
            return 'LOW', prob_low

    # Rule 4: Default - Use highest probability but respect thresholds
    if prob_low >= 0.50 and prob_medium < 0.30 and prob_high < 0.30:
        return 'LOW', prob_low

    # Rule 5: Fallback
    max_prob_idx = np.argmax(xgb_probs)
    if max_prob_idx == 0:
        return 'LOW', prob_low
    elif max_prob_idx == 1:
        return 'MEDIUM', prob_medium
    else:
        return 'HIGH', prob_high


def refine_medium_high_boundary_v2(risk_level, xgb_probs, symptom_text='', age=0,
                                   sys_bp=120, dia_bp=80, hr=80, temp_f=98.6,
                                   history='None'):
    """
    Fine-tune MEDIUM/HIGH boundary with improved thresholds.
    """

    prob_low = float(xgb_probs[0])
    prob_medium = float(xgb_probs[1])
    prob_high = float(xgb_probs[2])
    text = (symptom_text or '').lower()

    # If predicte HIGH - apply strict checks
    if 'HIGH' in risk_level.upper():
        # Check for false escalations: weak HIGH, strong MEDIUM
        if prob_high < 0.45 and prob_medium > 0.40:
            # Don't downgrade if there are critical symptoms/vitals
            has_critical_indicator = any(k in text for k in [
                'chest pain', 'crushing', 'cannot breathe',
                'hemorrhage', 'stroke', 'seizure', 'unconscious'
            ])
            has_critical_vitals = (sys_bp > 180 or dia_bp > 110 or hr > 130)

            if not has_critical_indicator and not has_critical_vitals:
                logger.debug(f"Refined: HIGH→MEDIUM (prob_high={prob_high:.2f}, prob_medium={prob_medium:.2f})")
                return 'MEDIUM'

    # If predicted MEDIUM - check for escalation to HIGH
    elif 'MEDIUM' in risk_level.upper():
        if prob_high >= 0.48:  # Higher threshold needed
            # Check for severe vitals/symptoms
            has_severe_indicator = any(k in text for k in [
                'severe', 'crushing', 'cannot breathe', 'chest pain'
            ])
            has_danger_vitals = (sys_bp >= 170 or dia_bp >= 105 or hr >= 125)

            if (has_severe_indicator or has_danger_vitals) and prob_high >= 0.50:
                logger.debug(f"Refined: MEDIUM→HIGH (prob_high={prob_high:.2f})")
                return 'HIGH'

    return risk_level


def calibrate_based_on_vitals_v2(risk_level, sys_bp, dia_bp, hr, temp_f, spo2,
                                 respiration_rate, symptom_text='', history='None'):
    """
    Vital-based calibration with improved logic for 90%+ accuracy.
    """

    text = (symptom_text or '').lower()

    # === CRITICAL VITALS ===
    critical_bp = sys_bp >= 180 or dia_bp >= 115 or sys_bp < 80 or dia_bp < 50
    critical_hr = hr < 40 or hr > 135
    critical_temp = temp_f > 103.5 or temp_f < 94
    critical_spo2 = spo2 < 85
    critical_rr = respiration_rate > 35 or respiration_rate < 8

    has_critical_vital = critical_bp or critical_hr or critical_temp or critical_spo2 or critical_rr

    # === MODERATE VITALS ===
    moderate_bp = (145 <= sys_bp < 180) or (95 <= dia_bp < 115)
    moderate_hr = (100 <= hr <= 130)
    moderate_temp = (100.0 <= temp_f <= 103.0)

    critical_vital_count = sum([critical_bp, critical_hr, critical_temp, critical_spo2, critical_rr])
    moderate_vital_count = sum([moderate_bp, moderate_hr, moderate_temp])

    # Rule 1: If critical vital(s) + symptoms, escalate
    if has_critical_vital:
        has_serious_symptom = any(k in text for k in [
            'chest pain', 'crushing', 'breathing', 'hemorrhage',
            'stroke', 'seizure', 'confusion', 'disoriented'
        ])

        if has_serious_symptom:
            if 'LOW' in risk_level.upper():
                return 'MEDIUM'
            if 'MEDIUM' in risk_level.upper() and critical_vital_count >= 2:
                return 'HIGH'

    # Rule 2: Multiple critical vitals → HIGH
    if critical_vital_count >= 2:
        if 'LOW' in risk_level.upper():
            return 'MEDIUM'
        if 'MEDIUM' in risk_level.upper():
            return 'HIGH'

    # Rule 3: Critical vital alone with symptoms → at least MEDIUM
    if has_critical_vital and 'LOW' in risk_level.upper():
        has_any_concern = any(k in text for k in [
            'pain', 'fever', 'breathing', 'distress', 'weakness', 'dizziness'
        ])
        if has_any_concern:
            return 'MEDIUM'

    # Rule 4: Multiple moderate vitals → MEDIUM (don't stay LOW)
    if moderate_vital_count >= 2 and 'LOW' in risk_level.upper():
        return 'MEDIUM'

    # Rule 5: Fever patterns
    if temp_f >= 101.0 and 'LOW' in risk_level.upper():
        if any(k in text for k in ['fever', 'aches', 'chills']):
            return 'MEDIUM'

    return risk_level


# These are the functions to be used in app.py
classify_xgb_risk = classify_xgb_risk_with_calibration_v2
refine_medium_high = refine_medium_high_boundary_v2
calibrate_vitals = calibrate_based_on_vitals_v2
