"""
PHASE 4.3: LOGGING & MONITORING SYSTEM
Captures all predictions, outcomes, and performance metrics
Enables real-time monitoring and post-deployment analysis
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import csv
import os

class PredictionLogger:
    """Logs all model predictions with context for later analysis"""

    def __init__(self, log_dir: str = './prediction_logs'):
        """Initialize prediction logger"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Setup CSV logger
        self.csv_file = self.log_dir / f"predictions_{datetime.now().strftime('%Y%m%d')}.csv"
        self.json_file = self.log_dir / f"predictions_{datetime.now().strftime('%Y%m%d')}.jsonl"

        # JSON logger (newline-delimited for streaming)
        self.logger = logging.getLogger('prediction_logger')
        self.logger.setLevel(logging.INFO)

        # CSV header
        self.csv_headers = [
            'timestamp', 'patient_id', 'age', 'gender', 'sys_bp', 'dia_bp', 'hr', 'temp_c',
            'symptom', 'pre_condition', 'risk_class_predicted', 'confidence_score',
            'confidence_level', 'probability_low', 'probability_medium', 'probability_high',
            'action_recommended', 'manual_review_required', 'safety_override',
            'actual_outcome', 'actual_risk_level', 'prediction_correct', 'notes'
        ]

        # Ensure CSV file has headers
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writeheader()

    def log_prediction(self,
                      vitals: Dict[str, Any],
                      symptom: str,
                      pre_condition: str,
                      prediction: str,
                      confidence_info: Dict,
                      recommendation: Dict,
                      patient_id: str = None,
                      gender: str = None) -> str:
        """
        Log a single prediction
        Returns: prediction_id for tracking
        """

        timestamp = datetime.now().isoformat()
        prediction_id = f"{timestamp.replace(':', '').replace('.', '')[:14]}_{patient_id or 'ANON'}"

        # Prepare log entry
        log_entry = {
            'timestamp': timestamp,
            'prediction_id': prediction_id,
            'patient_id': patient_id or 'ANONYMOUS',
            'age': vitals.get('age'),
            'gender': gender or 'Unknown',
            'sys_bp': vitals.get('sys_bp'),
            'dia_bp': vitals.get('dia_bp'),
            'hr': vitals.get('hr'),
            'temp_c': vitals.get('temp_c'),
            'spo2': vitals.get('spo2'),
            'respiration_rate': vitals.get('respiration_rate'),
            'symptom': symptom,
            'pre_condition': pre_condition,
            'risk_class_predicted': prediction,
            'confidence_score': confidence_info.get('confidence', 0),
            'confidence_level': confidence_info.get('level', 'UNKNOWN'),
            'probability_low': confidence_info.get('probabilities', {}).get('LOW', 0),
            'probability_medium': confidence_info.get('probabilities', {}).get('MEDIUM', 0),
            'probability_high': confidence_info.get('probabilities', {}).get('HIGH', 0),
            'margin_to_second': confidence_info.get('margin', 0),
            'action_recommended': recommendation.get('action'),
            'manual_review_required': recommendation.get('includes_manual_review', False),
            'safety_override': recommendation.get('requires_override', False),
            'actual_outcome': None,  # To be filled later
            'actual_risk_level': None,  # To be filled later
            'prediction_correct': None,  # To be filled later
            'notes': ''
        }

        # Log to JSON (streaming)
        with open(self.json_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Log to CSV
        csv_entry = {
            'timestamp': log_entry['timestamp'],
            'patient_id': log_entry['patient_id'],
            'age': log_entry['age'],
            'gender': log_entry['gender'],
            'sys_bp': log_entry['sys_bp'],
            'dia_bp': log_entry['dia_bp'],
            'hr': log_entry['hr'],
            'temp_c': log_entry['temp_c'],
            'symptom': log_entry['symptom'],
            'pre_condition': log_entry['pre_condition'],
            'risk_class_predicted': log_entry['risk_class_predicted'],
            'confidence_score': f"{log_entry['confidence_score']:.3f}",
            'confidence_level': log_entry['confidence_level'],
            'probability_low': f"{log_entry['probability_low']:.3f}",
            'probability_medium': f"{log_entry['probability_medium']:.3f}",
            'probability_high': f"{log_entry['probability_high']:.3f}",
            'action_recommended': log_entry['action_recommended'],
            'manual_review_required': log_entry['manual_review_required'],
            'safety_override': log_entry['safety_override'],
            'actual_outcome': '',
            'actual_risk_level': '',
            'prediction_correct': '',
            'notes': ''
        }

        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers)
            writer.writerow(csv_entry)

        return prediction_id

    def log_outcome(self, prediction_id: str, actual_risk_level: str, notes: str = ''):
        """Log the actual outcome for a prediction (for validation)"""
        # This would typically be called when clinician validates the prediction
        # Implementation would update the JSON and CSV logs with actual outcome
        pass


class PerformanceMonitor:
    """Monitors real-time model performance metrics"""

    def __init__(self, window_size: int = 100):
        """Initialize monitor with sliding window for metrics"""
        self.window_size = window_size
        self.predictions = []
        self.outcomes = []

    def add_prediction(self, predicted_class: str, actual_class: str = None):
        """Add a prediction result"""
        self.predictions.append({
            'predicted': predicted_class,
            'actual': actual_class,
            'timestamp': datetime.now(),
            'correct': predicted_class == actual_class if actual_class else None
        })

        # Keep only recent predictions
        if len(self.predictions) > self.window_size:
            self.predictions.pop(0)

    def get_metrics(self) -> Dict[str, Any]:
        """Calculate current performance metrics"""

        if not self.predictions:
            return {
                'total_predictions': 0,
                'accuracy': 0,
                'low_recall': 0,
                'medium_recall': 0,
                'high_recall': 0,
                'low_precision': 0,
                'medium_precision': 0,
                'high_precision': 0,
                'false_negative_rate': 0  # Missed HIGH cases
            }

        # Filter predictions with outcomes
        validated = [p for p in self.predictions if p['actual'] is not None]

        if not validated:
            return {'total_predictions': len(self.predictions), 'validated_count': 0}

        # Calculate metrics
        total = len(validated)
        correct = sum(1 for p in validated if p['correct'])
        accuracy = correct / total if total > 0 else 0

        # Calculate by class
        metrics = {
            'total_predictions': len(self.predictions),
            'validated_count': total,
            'accuracy': accuracy,
            'last_update': datetime.now().isoformat()
        }

        # Per-class metrics
        for pred_class in ['LOW', 'MEDIUM', 'HIGH']:
            # Recall: correct predictions / all actual of this class
            actual_count = sum(1 for p in validated if p['actual'] == pred_class)
            correct_count = sum(1 for p in validated if p['actual'] == pred_class and p['correct'])
            recall = correct_count / actual_count if actual_count > 0 else 0

            # Precision: correct predictions / all predicted as this class
            pred_count = sum(1 for p in validated if p['predicted'] == pred_class)
            correct_pred = sum(1 for p in validated if p['predicted'] == pred_class and p['correct'])
            precision = correct_pred / pred_count if pred_count > 0 else 0

            metrics[f'{pred_class.lower()}_recall'] = recall
            metrics[f'{pred_class.lower()}_precision'] = precision

        # False negative rate (missed HIGH cases - CRITICAL METRIC)
        high_actual = sum(1 for p in validated if p['actual'] == 'HIGH')
        high_missed = sum(1 for p in validated if p['actual'] == 'HIGH' and not p['correct'])
        false_negative_rate = high_missed / high_actual if high_actual > 0 else 0
        metrics['false_negative_rate'] = false_negative_rate

        return metrics

    def check_performance_alert(self, metrics: Dict) -> Dict:
        """Check if performance has degraded (model drift)"""

        alerts = {
            'has_alert': False,
            'alerts': [],
            'severity': 'NORMAL'
        }

        # Alert if overall accuracy drops below 85%
        if metrics.get('accuracy', 1.0) < 0.85:
            alerts['alerts'].append(f"Low accuracy: {metrics['accuracy']:.1%} (target: >85%)")
            alerts['severity'] = 'WARNING'
            alerts['has_alert'] = True

        # CRITICAL: Alert if missing HIGH cases (false negative >10%)
        if metrics.get('false_negative_rate', 0) > 0.10:
            alerts['alerts'].append(f"⚠️ CRITICAL: Missing HIGH cases: {metrics['false_negative_rate']:.1%} false negative rate")
            alerts['severity'] = 'CRITICAL'
            alerts['has_alert'] = True

        # Alert if HIGH recall drops below 95%
        if metrics.get('high_recall', 1.0) < 0.95:
            alerts['alerts'].append(f"LOW class detection: {metrics['high_recall']:.1%} (target: >95%)")
            alerts['severity'] = 'WARNING'
            alerts['has_alert'] = True

        return alerts


class AuditTrail:
    """Maintains audit trail of all system actions and decisions"""

    def __init__(self, log_dir: str = './audit_logs'):
        """Initialize audit trail"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Setup logger
        self.logger = logging.getLogger('audit_trail')
        self.logger.setLevel(logging.INFO)

        # File handler
        handler = logging.FileHandler(self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log")
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_prediction_made(self, prediction_id: str, user: str, vitals: Dict, prediction: str, confidence: float):
        """Log that a prediction was made"""
        self.logger.info(
            f"PREDICTION | ID: {prediction_id} | User: {user} | "
            f"BP: {vitals.get('sys_bp')}/{vitals.get('dia_bp')} | "
            f"Pred: {prediction} ({confidence:.0%})"
        )

    def log_override(self, prediction_id: str, original: str, override: str, reason: str, user: str):
        """Log when a clinician overrides the model"""
        self.logger.warning(
            f"OVERRIDE | ID: {prediction_id} | {original}→{override} | "
            f"Reason: {reason} | User: {user}"
        )

    def log_error(self, prediction_id: str, error_type: str, message: str):
        """Log errors during prediction"""
        self.logger.error(
            f"ERROR | ID: {prediction_id} | Type: {error_type} | Msg: {message}"
        )

    def log_validation(self, prediction_id: str, is_valid: bool, errors: list = None):
        """Log input validation results"""
        if not is_valid:
            self.logger.warning(
                f"VALIDATION_FAILED | ID: {prediction_id} | Errors: {', '.join(errors or [])}"
            )
        else:
            self.logger.info(f"VALIDATION_PASSED | ID: {prediction_id}")


if __name__ == '__main__':
    # Test logging system
    logger = PredictionLogger('./test_logs')
    monitor = PerformanceMonitor()
    audit = AuditTrail('./test_logs')

    # Log a prediction
    vitals = {'age': 45, 'sys_bp': 140, 'dia_bp': 85, 'hr': 92, 'temp_c': 37.5}
    confidence_info = {'confidence': 0.85, 'level': 'HIGH', 'probabilities': {'LOW': 0.05, 'MEDIUM': 0.10, 'HIGH': 0.85}}
    recommendation = {'action': 'USE_PREDICTION', 'includes_manual_review': False, 'requires_override': False}

    pred_id = logger.log_prediction(
        vitals=vitals,
        symptom='Chest pain',
        pre_condition='HTN',
        prediction='HIGH',
        confidence_info=confidence_info,
        recommendation=recommendation,
        patient_id='P12345'
    )

    print(f"✓ Logged prediction: {pred_id}")
    print(f"✓ Log file: {logger.csv_file}"
)

    # Test performance monitoring
    monitor.add_prediction('HIGH', 'HIGH')
    monitor.add_prediction('MEDIUM', 'MEDIUM')
    monitor.add_prediction('LOW', 'LOW')
    metrics = monitor.get_metrics()
    print(f"✓ Performance metrics: {json.dumps(metrics, indent=2, default=str)}")

    # Test audit trail
    audit.log_prediction_made(pred_id, 'DR_SMITH', vitals, 'HIGH', 0.85)
    print(f"✓ Audit logged")
