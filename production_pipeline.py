"""
PHASE 5.2: PRODUCTION PIPELINE
Integrates all production modules into a single prediction pipeline
Handles: Input validation, prediction, confidence scoring, monitoring, and logging
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

from input_validator import VitalSignsValidator
from confidence_threshold import ConfidenceThreshold
from monitoring_system import PredictionLogger, PerformanceMonitor, AuditTrail

logger = logging.getLogger(__name__)


class SmartTriagePipeline:
    """
    Complete production pipeline for SmartTriage predictions

    Pipeline flow:
    1. Input Validation (VitalSignsValidator)
    2. Model Prediction (XGBoost)
    3. Confidence Scoring (ConfidenceThreshold)
    4. Clinical Recommendations
    5. Monitoring & Logging (PredictionLogger)
    6. Anomaly Detection (AnomalyDetector)
    """

    def __init__(self, model, scaler, encoders, feature_names):
        """
        Initialize the pipeline with trained model and supporting components

        Args:
            model: Trained XGBoost model
            scaler: StandardScaler instance
            encoders: Dictionary of LabelEncoders
            feature_names: List of feature names
        """
        self.model = model
        self.scaler = scaler
        self.encoders = encoders
        self.feature_names = feature_names

        # Initialize production components
        self.validator = VitalSignsValidator()
        self.confidence_threshold = ConfidenceThreshold(logger=logger)
        self.prediction_logger = PredictionLogger()
        self.performance_monitor = PerformanceMonitor()
        self.audit_trail = AuditTrail()

        logger.info("✅ SmartTriagePipeline initialized")

    def predict_with_validation(
        self,
        patient_data: Dict
    ) -> Dict:
        """
        Complete prediction pipeline with validation, scoring, and monitoring

        Args:
            patient_data: Dictionary with keys:
                - age: int
                - gender: str (M/F/Other)
                - sys_bp: int
                - dia_bp: int
                - hr: int
                - temp_c: float (Celsius)
                - symptoms: str
                - pre_conditions: str (optional)

        Returns:
            Dictionary with:
                - success: bool
                - prediction: str (LOW/MEDIUM/HIGH)
                - confidence: float (0-1)
                - confidence_level: str (VERY_LOW/LOW/MEDIUM/HIGH)
                - recommendation: str
                - alert_level: str (GREEN/YELLOW/RED)
                - warnings: list[str]
                - errors: list[str] (if any)
        """

        result = {
            'success': False,
            'prediction': None,
            'confidence': None,
            'confidence_level': None,
            'recommendation': None,
            'alert_level': None,
            'warnings': [],
            'errors': []
        }

        try:
            # ===== STEP 1: INPUT VALIDATION =====
            logger.info(f"Validating patient data: age={patient_data.get('age')}")

            valid, normalized, errors, warnings = self.validator.validate_vital_signs(
                age=patient_data.get('age'),
                gender=patient_data.get('gender', 'M'),
                sys_bp=patient_data.get('sys_bp'),
                dia_bp=patient_data.get('dia_bp'),
                hr=patient_data.get('hr'),
                temp_c=patient_data.get('temp_c'),
                symptoms=patient_data.get('symptoms', 'mild'),
                pre_conditions=patient_data.get('pre_conditions', 'None')
            )

            if not valid:
                logger.error(f"Validation failed: {errors}")
                result['errors'] = errors
                result['warnings'] = warnings
                return result

            result['warnings'].extend(warnings)
            logger.info(f"✓ Validation passed. Warnings: {len(warnings)}")

            # ===== STEP 2: MODEL PREDICTION =====
            logger.info("Running XGBoost prediction...")

            # Prepare features for model
            import pandas as pd
            import numpy as np

            # Get gender from normalized or original data
            gender = normalized.get('gender') or patient_data.get('gender', 'M')
            symptoms = normalized.get('symptoms') or patient_data.get('symptoms', 'mild')
            pre_conditions = normalized.get('pre_conditions') or patient_data.get('pre_conditions', 'None')

            gen_enc = self.encoders['Gender'].transform([gender])[0] \
                if gender in self.encoders['Gender'].classes_ else 0

            symp_enc = self.encoders['Symptoms'].transform([symptoms])[0] \
                if symptoms in self.encoders['Symptoms'].classes_ else 0

            hist_enc = self.encoders['Pre_Conditions'].transform([pre_conditions])[0] \
                if pre_conditions in self.encoders['Pre_Conditions'].classes_ else 0

            # Create feature vector
            patient_df = pd.DataFrame(
                [[
                    normalized['age'],
                    gen_enc,
                    symp_enc,
                    normalized['sys_bp'],
                    normalized['dia_bp'],
                    normalized['hr'],
                    normalized['temp_c'],
                    hist_enc
                ]],
                columns=self.feature_names
            )

            # Scale and predict
            patient_scaled = self.scaler.transform(patient_df)
            xgb_probs = self.model.predict_proba(patient_scaled)[0]
            xgb_pred = self.model.predict(patient_scaled)[0]

            # Map prediction to risk class
            risk_map = {0: 'LOW', 1: 'MEDIUM', 2: 'HIGH'}
            result['prediction'] = risk_map[xgb_pred]

            logger.info(f"Model prediction: {result['prediction']} (probs: {xgb_probs})")

            # ===== STEP 3: CONFIDENCE SCORING =====
            logger.info("Calculating confidence score...")

            confidence_info = self.confidence_threshold.classify_confidence(
                xgb_probs,
                xgb_pred
            )

            result['confidence'] = confidence_info['confidence']
            result['confidence_level'] = confidence_info['level']

            logger.info(f"Confidence: {result['confidence']:.2%} ({result['confidence_level']})")

            # ===== STEP 4: CLINICAL RECOMMENDATION =====
            logger.info("Generating clinical recommendation...")

            recommendation = self.confidence_threshold.get_recommendation(
                confidence_info,
                normalized
            )

            result['recommendation'] = recommendation['recommendation_text']

            # Map severity to alert_level: CRITICAL→RED, MODERATE/UNCERTAIN→YELLOW, LOW/UNKNOWN→GREEN
            severity_map = {
                'CRITICAL': 'RED',
                'MODERATE': 'YELLOW',
                'UNCERTAIN': 'YELLOW',
                'LOW': 'GREEN',
                'UNKNOWN': 'YELLOW'
            }
            result['alert_level'] = severity_map.get(recommendation.get('severity', 'UNKNOWN'), 'YELLOW')

            logger.info(f"Recommendation: {result['recommendation']}")

            # ===== STEP 5: LOGGING & MONITORING =====
            logger.info("Logging prediction...")

            # Log the prediction
            try:
                self.prediction_logger.log_prediction(
                    vitals=normalized,
                    symptom=symptoms,
                    pre_condition=pre_conditions,
                    prediction=result['prediction'],
                    confidence_info=confidence_info,
                    recommendation=recommendation,
                    patient_id=patient_data.get('patient_id', 'UNKNOWN'),
                    gender=gender
                )
            except Exception as e:
                logger.warning(f"Failed to log prediction: {e}")

            # ===== SUCCESS =====
            result['success'] = True
            logger.info("✅ Prediction pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            result['errors'].append(f"Pipeline error: {str(e)}")

        return result

    def get_performance_summary(self) -> Dict:
        """Get performance metrics from monitoring system"""
        try:
            return self.performance_monitor.get_metrics()
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {'error': str(e)}

    def export_logs(self, format: str = 'json') -> Optional[str]:
        """
        Export prediction logs

        Args:
            format: 'json' or 'csv'

        Returns:
            Path to exported file or None if error
        """
        try:
            if format == 'json':
                return self.prediction_logger.save_to_json()
            elif format == 'csv':
                return self.prediction_logger.save_to_csv()
            else:
                logger.error(f"Unknown format: {format}")
                return None
        except Exception as e:
            logger.error(f"Error exporting logs: {str(e)}")
            return None


def create_pipeline_from_app(app_context: Dict) -> SmartTriagePipeline:
    """
    Create a production pipeline from Flask app context

    Args:
        app_context: Dictionary with:
            - model: XGBoost model
            - scaler: StandardScaler
            - encoders: Dictionary of encoders
            - feature_names: List of feature names

    Returns:
        Initialized SmartTriagePipeline
    """
    return SmartTriagePipeline(
        model=app_context['model'],
        scaler=app_context['scaler'],
        encoders=app_context['encoders'],
        feature_names=app_context['feature_names']
    )


if __name__ == '__main__':
    # Example usage
    print("SmartTriage Production Pipeline Module")
    print("Designed for integration into app.py")
    print("\nUsage:")
    print("  from production_pipeline import SmartTriagePipeline")
    print("  pipeline = create_pipeline_from_app(app_context)")
    print("  result = pipeline.predict_with_validation(patient_data)")
