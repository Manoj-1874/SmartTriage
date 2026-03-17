"""
PHASE 4.1: INPUT VALIDATION MODULE
Validates vitals and parameters before model prediction
Prevents crashes on out-of-range or invalid inputs
"""

import logging
from typing import Tuple, Dict, List
import numpy as np

class VitalSignsValidator:
    """Validates patient vital signs and parameters"""

    # Safe ranges based on training data + clinical practicality
    VALID_RANGES = {
        'age': (1, 120),
        'sys_bp': (60, 250),          # Allow extreme but catch unrealistic
        'dia_bp': (30, 150),
        'hr': (30, 220),              # Allow extreme tachycardia
        'temp_c': (32.0, 43.0),       # Allow extreme but not impossible
        'spo2': (50, 100),
        'respiration_rate': (8, 50)
    }

    # Clinical alert thresholds (for logging/monitoring)
    ALERT_THRESHOLDS = {
        'age_pediatric': 18,           # Below = pediatric
        'age_elderly': 65,             # Above = elderly
        'sys_bp_low': 90,              # Hypotension indicator
        'sys_bp_high': 180,            # Hypertension indicator
        'hr_low': 60,                  # Bradycardia
        'hr_high': 100,                # Tachycardia
        'temp_fever': 38.0,            # Fever threshold
        'temp_hypothermia': 36.5       # Hypothermia
    }

    # Normalization bounds (clip extreme values gracefully)
    NORMALIZE_BOUNDS = {
        'age': (1, 100),
        'sys_bp': (70, 240),
        'dia_bp': (40, 140),
        'hr': (40, 200),
        'temp_c': (35.0, 42.0)
    }

    def __init__(self, logger=None):
        """Initialize validator with optional logger"""
        self.logger = logger or logging.getLogger(__name__)
        self.validation_errors = []
        self.validation_warnings = []

    def validate_vital_signs(self, **vitals) -> Tuple[bool, Dict, List[str], List[str]]:
        """
        Validate patient vital signs
        Returns: (is_valid, normalized_vitals, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []
        normalized = {}

        # Validate age
        if 'age' not in vitals or vitals['age'] is None:
            self.validation_errors.append("Age is required")
        else:
            age = vitals['age']
            if isinstance(age, str):
                try:
                    age = int(float(age))
                except ValueError:
                    self.validation_errors.append(f"Age must be numeric, got: {age}")
                    return False, {}, self.validation_errors, self.validation_warnings

            if age < self.VALID_RANGES['age'][0] or age > self.VALID_RANGES['age'][1]:
                self.validation_errors.append(
                    f"Age {age} out of range {self.VALID_RANGES['age']}"
                )
            else:
                normalized['age'] = int(age)
                if age < self.ALERT_THRESHOLDS['age_pediatric']:
                    self.validation_warnings.append("PEDIATRIC patient - special care")
                elif age > self.ALERT_THRESHOLDS['age_elderly']:
                    self.validation_warnings.append("ELDERLY patient")

        # Validate systolic BP
        if 'sys_bp' not in vitals or vitals['sys_bp'] is None:
            self.validation_errors.append("Systolic BP is required")
        else:
            sys_bp = vitals['sys_bp']
            try:
                sys_bp = float(sys_bp)
            except (ValueError, TypeError):
                self.validation_errors.append(f"Systolic BP must be numeric, got: {sys_bp}")
                return False, {}, self.validation_errors, self.validation_warnings

            if sys_bp < self.VALID_RANGES['sys_bp'][0]:
                self.validation_errors.append(f"Systolic BP {sys_bp} is EXTREMELY LOW (critical hypotension)")
                # Don't reject, just warn
                normalized['sys_bp'] = max(sys_bp, self.NORMALIZE_BOUNDS['sys_bp'][0])
                self.validation_warnings.append(f"BP clipped from {sys_bp} to {normalized['sys_bp']}")
            elif sys_bp > self.VALID_RANGES['sys_bp'][1]:
                self.validation_errors.append(f"Systolic BP {sys_bp} > 250 (unrealistic)")
            else:
                normalized['sys_bp'] = int(sys_bp)
                if sys_bp < self.ALERT_THRESHOLDS['sys_bp_low']:
                    self.validation_warnings.append("ALERT: Hypotension - likely shock/emergency")
                elif sys_bp > self.ALERT_THRESHOLDS['sys_bp_high']:
                    self.validation_warnings.append("ALERT: Severe hypertension")

        # Validate diastolic BP
        if 'dia_bp' not in vitals or vitals['dia_bp'] is None:
            self.validation_errors.append("Diastolic BP is required")
        else:
            dia_bp = vitals['dia_bp']
            try:
                dia_bp = float(dia_bp)
            except (ValueError, TypeError):
                self.validation_errors.append(f"Diastolic BP must be numeric, got: {dia_bp}")
                return False, {}, self.validation_errors, self.validation_warnings

            if dia_bp < self.VALID_RANGES['dia_bp'][0] or dia_bp > self.VALID_RANGES['dia_bp'][1]:
                self.validation_errors.append(f"Diastolic BP {dia_bp} out of range")
            else:
                normalized['dia_bp'] = int(dia_bp)

        # Validate heart rate
        if 'hr' not in vitals or vitals['hr'] is None:
            self.validation_errors.append("Heart Rate is required")
        else:
            hr = vitals['hr']
            try:
                hr = float(hr)
            except (ValueError, TypeError):
                self.validation_errors.append(f"HR must be numeric, got: {hr}")
                return False, {}, self.validation_errors, self.validation_warnings

            if hr < self.VALID_RANGES['hr'][0] or hr > self.VALID_RANGES['hr'][1]:
                self.validation_errors.append(f"HR {hr} out of range {self.VALID_RANGES['hr']}")
            else:
                normalized['hr'] = int(hr)
                if hr < self.ALERT_THRESHOLDS['hr_low']:
                    self.validation_warnings.append("ALERT: Bradycardia - possible critical emergency")
                elif hr > self.ALERT_THRESHOLDS['hr_high']:
                    self.validation_warnings.append("ALERT: Tachycardia detected")

        # Validate temperature
        if 'temp_c' not in vitals or vitals['temp_c'] is None:
            self.validation_errors.append("Temperature is required")
        else:
            temp_c = vitals['temp_c']
            try:
                temp_c = float(temp_c)
            except (ValueError, TypeError):
                self.validation_errors.append(f"Temperature must be numeric, got: {temp_c}")
                return False, {}, self.validation_errors, self.validation_warnings

            if temp_c < self.VALID_RANGES['temp_c'][0] or temp_c > self.VALID_RANGES['temp_c'][1]:
                self.validation_errors.append(f"Temperature {temp_c}°C out of range")
            else:
                normalized['temp_c'] = round(temp_c, 1)
                if temp_c > self.ALERT_THRESHOLDS['temp_fever']:
                    self.validation_warnings.append(f"ALERT: Fever {temp_c}°C")
                elif temp_c < self.ALERT_THRESHOLDS['temp_hypothermia']:
                    self.validation_warnings.append(f"ALERT: Hypothermia {temp_c}°C")

        # Validate optional parameters
        if 'spo2' in vitals and vitals['spo2'] is not None:
            try:
                spo2 = float(vitals['spo2'])
                if spo2 < self.VALID_RANGES['spo2'][0] or spo2 > self.VALID_RANGES['spo2'][1]:
                    self.validation_warnings.append(f"SpO2 {spo2} out of range")
                else:
                    normalized['spo2'] = round(spo2, 1)
                    if spo2 < 90:
                        self.validation_warnings.append("ALERT: Low oxygen saturation")
            except (ValueError, TypeError):
                self.validation_warnings.append(f"Invalid SpO2 value: {vitals['spo2']}")

        if 'respiration_rate' in vitals and vitals['respiration_rate'] is not None:
            try:
                rr = float(vitals['respiration_rate'])
                if rr < self.VALID_RANGES['respiration_rate'][0] or rr > self.VALID_RANGES['respiration_rate'][1]:
                    self.validation_warnings.append(f"RR {rr} out of range")
                else:
                    normalized['respiration_rate'] = int(rr)
            except (ValueError, TypeError):
                self.validation_warnings.append(f"Invalid RR value: {vitals['respiration_rate']}")

        # Check consistency
        if 'sys_bp' in normalized and 'dia_bp' in normalized:
            if normalized['sys_bp'] < normalized['dia_bp']:
                self.validation_errors.append(
                    f"Systolic BP ({normalized['sys_bp']}) < Diastolic BP ({normalized['dia_bp']}) - invalid"
                )

        is_valid = len(self.validation_errors) == 0
        return is_valid, normalized, self.validation_errors, self.validation_warnings

    def validate_symptoms(self, symptom: str, max_length: int = 500) -> Tuple[bool, str, List[str]]:
        """Validate symptom input"""
        errors = []

        if not symptom or len(str(symptom).strip()) == 0:
            errors.append("Symptom cannot be empty")
            return False, "", errors

        symptom = str(symptom).strip()

        if len(symptom) > max_length:
            errors.append(f"Symptom too long ({len(symptom)} > {max_length} chars)")
            symptom = symptom[:max_length]

        # Check for injection/malicious input
        dangerous_chars = ['<', '>', '{', '}', '$(', '`']
        for char in dangerous_chars:
            if char in symptom:
                errors.append(f"Invalid character in symptom: {char}")
                return False, symptom, errors

        return len(errors) == 0, symptom, errors

    def validate_history(self, history: str, max_length: int = 500) -> Tuple[bool, str, List[str]]:
        """Validate medical history input"""
        errors = []

        if history is None or len(str(history).strip()) == 0:
            return True, "None", errors  # Optional field

        history = str(history).strip()

        if len(history) > max_length:
            errors.append(f"History too long ({len(history)} > {max_length} chars)")
            history = history[:max_length]

        # Check for injection/malicious input
        dangerous_chars = ['<', '>', '{', '}', '$(', '`']
        for char in dangerous_chars:
            if char in history:
                errors.append(f"Invalid character in history: {char}")
                return False, history, errors

        return len(errors) == 0, history, errors

    def get_validation_report(self) -> Dict:
        """Get detailed validation report"""
        return {
            'errors': self.validation_errors,
            'warnings': self.validation_warnings,
            'has_errors': len(self.validation_errors) > 0,
            'has_warnings': len(self.validation_warnings) > 0
        }


class PredictionValidator:
    """Validates model predictions for clinical reasonableness"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def validate_prediction(self, prediction: str, confidence: float, vitals: Dict) -> Dict:
        """
        Validate that prediction makes clinical sense given vitals
        Returns: validation report with flags
        """
        report = {
            'prediction': prediction,
            'confidence': confidence,
            'is_reasonable': True,
            'flags': [],
            'recommendation': 'Use model prediction'
        }

        # Check confidence level
        if confidence < 0.5:
            report['flags'].append("LOW_CONFIDENCE")
            report['recommendation'] = "⚠️ Manual review recommended"
        elif confidence < 0.7:
            report['flags'].append("MEDIUM_LOW_CONFIDENCE")

        # Sanity checks based on vitals
        sys_bp = vitals.get('sys_bp', 0)
        hr = vitals.get('hr', 0)
        temp_c = vitals.get('temp_c', 37)

        # If hypotensive + high HR + fever → likely septic shock (should be HIGH)
        if sys_bp < 90 and hr > 100 and temp_c > 38.5:
            if prediction != 'HIGH':
                report['flags'].append("SHOCK_PATTERN_NOT_HIGH")
                report['is_reasonable'] = False
                report['recommendation'] = "🚨 Override: Shock pattern detected → HIGH risk"

        # If normal vitals → should not be HIGH
        if sys_bp > 110 and sys_bp < 160 and 60 < hr < 100 and 36.5 < temp_c < 38:
            if prediction == 'HIGH':
                report['flags'].append("NORMAL_VITALS_BUT_HIGH")
                report['recommendation'] = "⚠️ Verify: Normal vitals but HIGH prediction"

        return report


if __name__ == '__main__':
    # Test validator
    validator = VitalSignsValidator()

    # Test case 1: Normal vitals
    print("Test 1: Normal vitals")
    valid, norm, errors, warnings = validator.validate_vital_signs(
        age=35, sys_bp=120, dia_bp=78, hr=72, temp_c=37.2
    )
    print(f"  Valid: {valid}")
    print(f"  Normalized: {norm}")
    print(f"  Warnings: {warnings}")

    # Test case 2: Shock vitals
    print("\nTest 2: Shock vitals")
    valid, norm, errors, warnings = validator.validate_vital_signs(
        age=55, sys_bp=85, dia_bp=52, hr=135, temp_c=40.0
    )
    print(f"  Valid: {valid}")
    print(f"  Normalized: {norm}")
    print(f"  Warnings: {warnings}")

    # Test case 3: Invalid input
    print("\nTest 3: Invalid age")
    valid, norm, errors, warnings = validator.validate_vital_signs(
        age="invalid", sys_bp=120, dia_bp=78, hr=72, temp_c=37.2
    )
    print(f"  Valid: {valid}")
    print(f"  Errors: {errors}")
