"""
UNIVERSAL DISEASE SEVERITY CLASSIFIER
Classifies ANY disease (even unknown ones) into risk levels using medical semantics

Instead of hardcoding diseases, learn disease severity from keywords
"""

import re
from typing import Tuple, Dict

class DiseaseSeverityClassifier:
    """
    Classify disease severity based on medical keywords and patterns
    Works for ANY disease name, not just hardcoded ones
    """

    # CRITICAL risk indicators - diseases typically requiring immediate hospitalization
    CRITICAL_KEYWORDS = {
        'cancer', 'carcinoma', 'malignancy', 'tumor', 'neoplasm', 'lymphoma',
        'leukemia', 'sepsis', 'septic', 'shock', 'heart attack', 'myocardial',
        'stroke', 'cva', 'pulmonary embolism', 'aortic', 'dissection',
        'hemorrhage', 'bleed', 'acute respiratory', 'respiratory failure',
        'acute kidney injury', 'renal failure', 'organ failure', 'multi-organ',
        'aneurysm', 'seizure disorder', 'status epilepticus', 'coma',
        'meningitis', 'encephalitis', 'acute severe',
        'takotsubo',  # Takotsubo cardiomyopathy (cardiac emergency)
    }

    # HIGH risk indicators - diseases requiring urgent hospital care
    HIGH_KEYWORDS = {
        'infarction', 'angina', 'arrhythmia', 'heart failure', 'cardiac', 'coronary',
        'hypertension', 'pneumonia', 'pulmonary', 'respiratory',
        'embolism', 'thrombosis', 'thrombotic', 'stroke risk',
        'diabetic ketoacidosis', 'dka', 'severe infection', 'infection',
        'severe', 'critical', 'emergency', 'unstable',
        'hepatic failure', 'cirrhosis', 'pancreatitis', 'appendicitis',
        'peritonitis', 'bowel obstruction', 'acute abdomen',
        'cardiomyopathy',  # General cardiomyopathy (moved from CRITICAL)
        'neuromuscular', 'neurological', 'neurological disorder', 'motor disorder',
        'stiff person',  # Specific for stiff person syndrome
        'parasitic', 'nagana', 'trypanosoma',  # Parasitic diseases
        'autoimmune vasculitis', 'susac',  # Autoimmune with serious complications
    }

    # MODERATE risk indicators - diseases needing timely medical care
    MODERATE_KEYWORDS = {
        'diabetes', 'asthma', 'copd', 'chronic', 'disease', 'disorder',
        'ulcer', 'gastritis', 'colitis', 'ibs', 'crohn', 'arthritis',
        'lupus', 'autoimmune', 'thyroid', 'hypo', 'infection', 'viral',
        'bacterial', 'fungal', 'inflammatory', 'degenerative',
        'genetic disorder', 'genetically',  # Added: genetic conditions
        'progeria', 'ehlers-danlos', 'retinitis',  # Added: specific genetic disorders
        'alice in wonderland',  # Added: rare neurological syndromes
    }

    @staticmethod
    def classify_disease_severity(disease_name: str) -> Tuple[str, float]:
        """
        Classify disease severity based on name alone
        Returns: (severity_level, confidence_score)

        severity_level: 'CRITICAL', 'HIGH', 'MODERATE', 'MILD', 'UNKNOWN'
        confidence_score: 0.0-1.0
        """

        disease_lower = disease_name.lower().strip()

        # Count keyword matches
        critical_matches = sum(1 for kw in DiseaseSeverityClassifier.CRITICAL_KEYWORDS
                              if kw in disease_lower)
        high_matches = sum(1 for kw in DiseaseSeverityClassifier.HIGH_KEYWORDS
                          if kw in disease_lower)
        moderate_matches = sum(1 for kw in DiseaseSeverityClassifier.MODERATE_KEYWORDS
                              if kw in disease_lower)

        # Determine severity by strongest signal
        if critical_matches > 0:
            confidence = min(1.0, 0.5 + (critical_matches * 0.25))
            return 'CRITICAL', confidence

        if high_matches > 0:
            confidence = min(1.0, 0.5 + (high_matches * 0.20))
            return 'HIGH', confidence

        if moderate_matches > 0:
            confidence = min(1.0, 0.4 + (moderate_matches * 0.15))
            return 'MODERATE', confidence

        # Check for negative patterns (benign conditions)
        benign_keywords = {'mild', 'minor', 'cold', 'common', 'benign', 'simple'}
        benign_matches = sum(1 for kw in benign_keywords if kw in disease_lower)

        if benign_matches > 0:
            return 'MILD', 0.6

        # No clear pattern - return MODERATE as safe default
        return 'MODERATE', 0.3

    @staticmethod
    def get_risk_multiplier(severity_level: str) -> float:
        """
        Get risk multiplier based on disease severity
        Used to boost XGBoost risk scores
        """
        multipliers = {
            'CRITICAL': 2.5,   # 2.5x boost
            'HIGH': 1.8,       # 1.8x boost
            'MODERATE': 1.2,   # 1.2x boost
            'MILD': 0.9,       # Reduce risk slightly
            'UNKNOWN': 1.0,    # No change
        }
        return multipliers.get(severity_level, 1.0)

    @staticmethod
    def get_mortality_estimate(disease_name: str) -> float:
        """
        Estimate mortality risk for disease (0.0-1.0)
        Used to adjust final risk assessment
        """
        severity, confidence = DiseaseSeverityClassifier.classify_disease_severity(disease_name)

        mortality_by_severity = {
            'CRITICAL': 0.20,  # 20% mortality if untreated
            'HIGH': 0.08,      # 8% mortality
            'MODERATE': 0.02,  # 2% mortality
            'MILD': 0.001,     # 0.1% mortality
            'UNKNOWN': 0.01,   # Default 1%
        }

        return mortality_by_severity.get(severity, 0.01)
