"""
PHASE 4.2: CONFIDENCE THRESHOLD MODULE
Determines confidence levels and recommendations for predictions
Only reports HIGH-confidence predictions to clinicians
"""

import logging
from typing import Tuple, Dict, List
import numpy as np

class ConfidenceThreshold:
    """
    Manages confidence levels and reporting thresholds
    Prevents false HIGH/LOW predictions from causing harm
    """

    # Confidence thresholds (0-1 scale)
    THRESHOLDS = {
        'high_confidence': 0.80,     # Report with high confidence
        'medium_confidence': 0.43,   # Flag for manual review
        'low_confidence': 0.35,      # Manual review required
        'very_low': 0.30             # Cannot classify
    }

    # Risk level probabilities that trigger special handling
    PROBABILITY_ALERTS = {
        'borderline_high_medium': (0.40, 0.50),  # HIGH vs MEDIUM unclear
        'borderline_medium_low': (0.35, 0.45),   # MEDIUM vs LOW unclear
    }

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def classify_confidence(self, probs: np.ndarray, predicted_class: int) -> Dict:
        """
        Classify confidence level based on prediction probabilities
        probs: array of [P(LOW), P(MEDIUM), P(HIGH)]
        predicted_class: 0 (LOW), 1 (MEDIUM), 2 (HIGH)
        """

        if len(probs) != 3:
            raise ValueError(f"Expected 3 probabilities, got {len(probs)}")

        # Normalize if needed
        if probs.sum() > 0:
            probs = probs / probs.sum()

        confidence = float(np.max(probs))

        # Determine confidence level
        if confidence >= self.THRESHOLDS['high_confidence']:
            level = 'HIGH'
        elif confidence >= self.THRESHOLDS['medium_confidence']:
            level = 'MEDIUM'
        elif confidence >= self.THRESHOLDS['low_confidence']:
            level = 'LOW'
        else:
            level = 'VERY_LOW'

        return {
            'confidence': confidence,
            'level': level,
            'probabilities': {
                'LOW': float(probs[0]),
                'MEDIUM': float(probs[1]),
                'HIGH': float(probs[2])
            },
            'predicted_class': predicted_class,
            'margin': float(np.max(probs) - np.partition(probs, -2)[-2])  # Gap to 2nd best
        }

    def get_recommendation(self, confidence_info: Dict, vitals: Dict = None) -> Dict:
        """
        Get clinical recommendation based on confidence and vital signs
        """
        confidence_level = confidence_info['level']
        confidence = confidence_info['confidence']
        probs = confidence_info['probabilities']
        margin = confidence_info['margin']

        # Base recommendation
        class_map = {0: 'LOW', 1: 'MEDIUM', 2: 'HIGH'}
        predicted_risk = class_map.get(confidence_info['predicted_class'], 'UNKNOWN')

        recommendation = {
            'prediction': predicted_risk,
            'confidence_level': confidence_level,
            'confidence_score': confidence,
            'margin_to_second': margin,
            'action': 'UNKNOWN',
            'severity': 'UNKNOWN',
            'recommendation_text': '',
            'includes_manual_review': False,
            'requires_override': False
        }

        # HIGH CONFIDENCE - Trust the model
        if confidence_level == 'HIGH':
            recommendation['action'] = 'USE_PREDICTION'
            recommendation['recommendation_text'] = f"✅ HIGH confidence ({confidence:.1%}) - {predicted_risk} risk"

            if predicted_risk == 'HIGH':
                recommendation['severity'] = 'CRITICAL'
                recommendation['recommendation_text'] += " | 🚨 URGENT - Escalate immediately"
            elif predicted_risk == 'MEDIUM':
                recommendation['severity'] = 'MODERATE'
                recommendation['recommendation_text'] += " | Monitor closely"
            else:
                recommendation['severity'] = 'LOW'
                recommendation['recommendation_text'] += " | Routine follow-up"

        # MEDIUM CONFIDENCE - Use with caution
        elif confidence_level == 'MEDIUM':
            recommendation['action'] = 'SUGGEST_WITH_REVIEW'
            recommendation['includes_manual_review'] = True
            recommendation['recommendation_text'] = f"⚠️ MEDIUM confidence ({confidence:.1%}) - Suggest {predicted_risk} risk | Recommend clinician review"

            # Check if close to different class
            if margin < 0.05:
                recommendation['recommendation_text'] += " | ⚠️ Close call between classes"

        # LOW CONFIDENCE - Requires manual review
        elif confidence_level == 'LOW':
            recommendation['action'] = 'MANUAL_REVIEW_REQUIRED'
            recommendation['includes_manual_review'] = True
            recommendation['severity'] = 'UNCERTAIN'
            recommendation['recommendation_text'] = f"❌ LOW confidence ({confidence:.1%}) - Cannot confidently classify as {predicted_risk} | Manual review REQUIRED"

        # VERY LOW - Cannot classify
        else:
            recommendation['action'] = 'CANNOT_CLASSIFY'
            recommendation['includes_manual_review'] = True
            recommendation['requires_override'] = True
            recommendation['severity'] = 'UNKNOWN'
            recommendation['recommendation_text'] = f"❌ VERY LOW confidence ({confidence:.1%}) - Unable to classify | Manual assessment required"

        # Clinical safety checks
        if vitals:
            recommendation = self._apply_clinical_safety_checks(
                recommendation, confidence_info, vitals
            )

        return recommendation

    def _apply_clinical_safety_checks(self, recommendation: Dict, confidence_info: Dict, vitals: Dict) -> Dict:
        """Apply clinical safety rules to override/modify recommendations if needed"""

        sys_bp = vitals.get('sys_bp', 120)
        hr = vitals.get('hr', 80)
        temp_c = vitals.get('temp_c', 37)
        age = vitals.get('age', 50)

        # SAFETY RULE 1: Hypotension + Tachycardia + Fever → Always HIGH
        if sys_bp < 90 and hr > 100 and temp_c > 38.5:
            recommendation['action'] = 'OVERRIDE_TO_HIGH'
            recommendation['requires_override'] = True
            recommendation['severity'] = 'CRITICAL'
            recommendation['recommendation_text'] = "🚨 SAFETY OVERRIDE: Shock vital signs detected (low BP + high HR + fever) → HIGH risk"

        # SAFETY RULE 2: Severe hypotension (BP < 80) → Always HIGH
        elif sys_bp < 80:
            recommendation['action'] = 'OVERRIDE_TO_HIGH'
            recommendation['requires_override'] = True
            recommendation['severity'] = 'CRITICAL'
            recommendation['recommendation_text'] = "🚨 SAFETY OVERRIDE: Severe hypotension detected (BP < 80) → HIGH risk"

        # SAFETY RULE 3: Pediatric + High fever → Escalate to at least MEDIUM
        elif age < 18 and temp_c > 39.5 and recommendation['prediction'] == 'LOW':
            recommendation['action'] = 'OVERRIDE_TO_MEDIUM'
            recommendation['requires_override'] = True
            recommendation['recommendation_text'] = "⚠️ SAFETY OVERRIDE: Pediatric patient with high fever → At least MEDIUM risk"

        # SAFETY RULE 4: Elderly + Multiple abnormal vitals → Escalate
        elif age > 75:
            abnormal_count = 0
            if sys_bp > 160 or sys_bp < 90:
                abnormal_count += 1
            if hr > 100 or hr < 60:
                abnormal_count += 1
            if temp_c > 38.5 or temp_c < 36.5:
                abnormal_count += 1

            if abnormal_count >= 2 and recommendation['prediction'] == 'LOW':
                recommendation['action'] = 'ESCALATE_TO_MEDIUM'
                recommendation['requires_override'] = True
                recommendation['recommendation_text'] = "⚠️ ESCALATION: Elderly patient with multiple abnormal vitals → At least MEDIUM risk"

        return recommendation

    def should_report_prediction(self, recommendation: Dict) -> bool:
        """Determine if prediction is safe to report to clinician"""

        # Don't report if cannot classify or requires override
        if recommendation['action'] in ['CANNOT_CLASSIFY', 'MANUAL_REVIEW_REQUIRED']:
            return False

        # Report all others (overrides are still worth reporting as they flag issues)
        return True

    def format_clinical_report(self, recommendation: Dict, vitals: Dict) -> str:
        """Format a clinical-friendly report"""

        report = f"""
╔════════════════════════════════════════════════════════════════╗
║            SMARTTRIAGE CLINICAL DECISION SUPPORT               ║
╚════════════════════════════════════════════════════════════════╝

PATIENT VITALS:
  Age: {vitals.get('age', 'N/A')} years
  BP: {vitals.get('sys_bp', 'N/A')}/{vitals.get('dia_bp', 'N/A')} mmHg
  HR: {vitals.get('hr', 'N/A')} bpm
  Temp: {vitals.get('temp_c', 'N/A')}°C
  SpO2: {vitals.get('spo2', 'N/A')}%

MODEL ASSESSMENT:
  Predicted Risk:        {recommendation['prediction']}
  Confidence:            {recommendation['confidence_score']:.1%} ({recommendation['confidence_level']})
  Probability Distribution:
    - LOW:     {recommendation.get('probabilities', {}).get('LOW', 0):.1%}
    - MEDIUM:  {recommendation.get('probabilities', {}).get('MEDIUM', 0):.1%}
    - HIGH:    {recommendation.get('probabilities', {}).get('HIGH', 0):.1%}

CLINICAL RECOMMENDATION:
  {recommendation['recommendation_text']}

ACTION REQUIRED:
  {recommendation['action']}
  Manual Review: {'YES ⚠️' if recommendation['includes_manual_review'] else 'NO'}
  Safety Override: {'YES 🚨' if recommendation['requires_override'] else 'NO'}

IMPORTANT:
  This is a clinical decision support tool only. All predictions must
  be validated by qualified healthcare professionals. Do not use
  as the sole basis for clinical decisions.
════════════════════════════════════════════════════════════════
"""
        return report


if __name__ == '__main__':
    # Test confidence threshold
    thresh = ConfidenceThreshold()

    # Test case 1: High confidence prediction
    print("Test 1: High confidence (0.9 for HIGH)")
    probs = np.array([0.05, 0.05, 0.90])
    conf_info = thresh.classify_confidence(probs, predicted_class=2)
    rec = thresh.get_recommendation(conf_info)
    print(thresh.format_clinical_report(rec, {'age': 45, 'sys_bp': 140, 'dia_bp': 85, 'hr': 95, 'temp_c': 38.5}))

    # Test case 2: Low confidence prediction
    print("\nTest 2: Low confidence (0.40 for HIGH)")
    probs = np.array([0.30, 0.30, 0.40])
    conf_info = thresh.classify_confidence(probs, predicted_class=2)
    rec = thresh.get_recommendation(conf_info)
    print(rec['recommendation_text'])

    # Test case 3: Shock vitals override
    print("\nTest 3: Shock vitals (should override to HIGH)")
    probs = np.array([0.20, 0.50, 0.30])  # Predicts MEDIUM
    conf_info = thresh.classify_confidence(probs, predicted_class=1)
    rec = thresh.get_recommendation(conf_info, vitals={'sys_bp': 85, 'hr': 135, 'temp_c': 40.0, 'age': 55})
    print(rec['recommendation_text'])
    print(f"Override required: {rec['requires_override']}")
