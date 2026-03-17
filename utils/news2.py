"""NEWS2 scoring utilities for triage escalation."""


def calculate_news2_score(respiration_rate, spo2, temp_f, sys_bp, hr, is_alert=True):
    """Calculate simplified NEWS2 score from available vitals."""
    score = 0

    # Respiratory rate
    if respiration_rate <= 8:
        score += 3
    elif 9 <= respiration_rate <= 11:
        score += 1
    elif 12 <= respiration_rate <= 20:
        score += 0
    elif 21 <= respiration_rate <= 24:
        score += 2
    else:
        score += 3

    # SpO2 (Scale 1)
    if spo2 <= 91:
        score += 3
    elif 92 <= spo2 <= 93:
        score += 2
    elif 94 <= spo2 <= 95:
        score += 1
    else:
        score += 0

    # Temperature (Celsius thresholds)
    temp_c = (temp_f - 32) * 5 / 9
    if temp_c <= 35.0:
        score += 3
    elif 35.1 <= temp_c <= 36.0:
        score += 1
    elif 36.1 <= temp_c <= 38.0:
        score += 0
    elif 38.1 <= temp_c <= 39.0:
        score += 1
    else:
        score += 2

    # Systolic BP
    if sys_bp <= 90:
        score += 3
    elif 91 <= sys_bp <= 100:
        score += 2
    elif 101 <= sys_bp <= 110:
        score += 1
    elif 111 <= sys_bp <= 219:
        score += 0
    else:
        score += 3

    # Heart rate
    if hr <= 40:
        score += 3
    elif 41 <= hr <= 50:
        score += 1
    elif 51 <= hr <= 90:
        score += 0
    elif 91 <= hr <= 110:
        score += 1
    elif 111 <= hr <= 130:
        score += 2
    else:
        score += 3

    # Consciousness (AVPU)
    if not is_alert:
        score += 3

    return score


def map_news2_to_risk(news2_score):
    """Map NEWS2 score to SmartTriage risk classes."""
    if news2_score >= 7:
        return "HIGH", "Emergency Department / Immediate Care"
    if news2_score >= 5:
        return "MEDIUM", "Urgent Care"
    return "LOW", "General Ward / Primary Care"
