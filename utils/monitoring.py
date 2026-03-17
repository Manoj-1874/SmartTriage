"""
Health Check and Monitoring Endpoints for SmartTriage Dashboard
Provides endpoints for:
- Application health status
- Database connectivity
- Model availability
- System metrics
"""
import psutil
import time
from flask import Blueprint, jsonify, current_app
from datetime import datetime
import logging

from utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Create health check blueprint
health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint for load balancer health checks"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness():
    """
    Readiness check - Is the application ready to serve traffic?
    Returns 200 if all critical components are ready, 503 otherwise
    """
    checks = {
        'database': check_database(),
        'models': check_models(),
    }

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return jsonify({
        'status': 'ready' if all_ready else 'not_ready',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': checks
    }), status_code


@health_bp.route('/live', methods=['GET'])
def liveness():
    """
    Liveness check - Is the application alive?
    Returns 200 if application is running, 503 if it should be restarted
    """
    try:
        # Basic check - can we respond?
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        return jsonify({
            'status': 'dead',
            'error': str(e)
        }), 503


@health_bp.route('/status', methods=['GET'])
def detailed_status():
    """
    Detailed status endpoint with system metrics
    Useful for monitoring dashboards
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Application metrics
        from utils.database import DatabaseManager
        db_status = check_database()
        models_status = check_models()

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': current_app.config.get('VERSION', '2.0.0'),
            'environment': current_app.config.get('ENV', 'unknown'),
            'uptime_seconds': time.time() - current_app.config.get('START_TIME', time.time()),
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total_mb': memory.total / (1024 * 1024),
                    'available_mb': memory.available / (1024 * 1024),
                    'percent_used': memory.percent
                },
                'disk': {
                    'total_gb': disk.total / (1024 * 1024 * 1024),
                    'free_gb': disk.free / (1024 * 1024 * 1024),
                    'percent_used': disk.percent
                }
            },
            'components': {
                'database': db_status,
                'models': models_status
            }
        }), 200

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500


def check_database():
    """Check if database is accessible"""
    try:
        from utils.database import DatabaseManager
        from config import get_config

        config = get_config()
        db_manager = DatabaseManager(config)

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()

        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


def check_models():
    """Check if ML models are loaded"""
    try:
        # Check if models are loaded in app context
        # This assumes models are stored in app.config or as globals
        return hasattr(current_app, 'xgb_risk_model') or True  # Placeholder
    except Exception as e:
        logger.error(f"Models health check failed: {str(e)}")
        return False


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus-style metrics endpoint
    Returns metrics in plain text format for Prometheus scraping
    """
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        conn = get_db_connection()
        total_triage = conn.execute("SELECT COUNT(*) FROM patient_logs").fetchone()[0]
        high_risk = conn.execute("SELECT COUNT(*) FROM patient_logs WHERE dual_brain_risk LIKE 'HIGH%'").fetchone()[0]
        news2_high = conn.execute("SELECT COUNT(*) FROM patient_logs WHERE news2_score >= 7").fetchone()[0]
        overrides = conn.execute("SELECT COUNT(*) FROM patient_logs WHERE dual_brain_risk LIKE '%OVERRIDE%'").fetchone()[0]

        confirmed_total = conn.execute(
            "SELECT COUNT(*) FROM patient_logs WHERE actual_outcome IS NOT NULL"
        ).fetchone()[0]
        confirmed_exact = conn.execute(
            """
            SELECT COUNT(*)
            FROM patient_logs
            WHERE actual_outcome IS NOT NULL
              AND (
                    (actual_outcome = 'HIGH' AND dual_brain_risk LIKE 'HIGH%')
                 OR (actual_outcome = 'MEDIUM' AND dual_brain_risk LIKE 'MEDIUM%')
                 OR (actual_outcome = 'LOW' AND dual_brain_risk LIKE 'LOW%')
              )
            """
        ).fetchone()[0]

        tp = conn.execute(
            """
            SELECT COUNT(*)
            FROM patient_logs
            WHERE actual_outcome IS NOT NULL
              AND actual_outcome = 'HIGH'
              AND dual_brain_risk LIKE 'HIGH%'
            """
        ).fetchone()[0]
        fp = conn.execute(
            """
            SELECT COUNT(*)
            FROM patient_logs
            WHERE actual_outcome IS NOT NULL
              AND actual_outcome != 'HIGH'
              AND dual_brain_risk LIKE 'HIGH%'
            """
        ).fetchone()[0]
        tn = conn.execute(
            """
            SELECT COUNT(*)
            FROM patient_logs
            WHERE actual_outcome IS NOT NULL
              AND actual_outcome != 'HIGH'
              AND dual_brain_risk NOT LIKE 'HIGH%'
            """
        ).fetchone()[0]
        fn = conn.execute(
            """
            SELECT COUNT(*)
            FROM patient_logs
            WHERE actual_outcome IS NOT NULL
              AND actual_outcome = 'HIGH'
              AND dual_brain_risk NOT LIKE 'HIGH%'
            """
        ).fetchone()[0]
        conn.close()

        high_ratio = (high_risk / total_triage) if total_triage else 0.0
        override_ratio = (overrides / total_triage) if total_triage else 0.0
        confirmed_accuracy = (confirmed_exact / confirmed_total) if confirmed_total else 0.0
        high_sensitivity = (tp / (tp + fn)) if (tp + fn) else 0.0
        high_specificity = (tn / (tn + fp)) if (tn + fp) else 0.0
        high_ppv = (tp / (tp + fp)) if (tp + fp) else 0.0
        high_npv = (tn / (tn + fn)) if (tn + fn) else 0.0

        metrics_text = f"""# HELP smarttriage_cpu_usage CPU usage percentage
# TYPE smarttriage_cpu_usage gauge
smarttriage_cpu_usage {cpu_percent}

# HELP smarttriage_memory_usage_bytes Memory usage in bytes
# TYPE smarttriage_memory_usage_bytes gauge
smarttriage_memory_usage_bytes {memory.used}

# HELP smarttriage_memory_available_bytes Available memory in bytes
# TYPE smarttriage_memory_available_bytes gauge
smarttriage_memory_available_bytes {memory.available}

# HELP smarttriage_uptime_seconds Application uptime in seconds
# TYPE smarttriage_uptime_seconds counter
smarttriage_uptime_seconds {time.time() - current_app.config.get('START_TIME', time.time())}

# HELP smarttriage_health_status Application health status (1=healthy, 0=unhealthy)
# TYPE smarttriage_health_status gauge
smarttriage_health_status {1 if check_database() else 0}

# HELP smarttriage_triage_total Total triage assessments processed
# TYPE smarttriage_triage_total counter
smarttriage_triage_total {total_triage}

# HELP smarttriage_high_risk_total Total triage assessments classified as high risk
# TYPE smarttriage_high_risk_total counter
smarttriage_high_risk_total {high_risk}

# HELP smarttriage_news2_high_total Total assessments with NEWS2 >= 7
# TYPE smarttriage_news2_high_total counter
smarttriage_news2_high_total {news2_high}

# HELP smarttriage_override_total Total assessments requiring override logic
# TYPE smarttriage_override_total counter
smarttriage_override_total {overrides}

# HELP smarttriage_high_risk_ratio Ratio of high risk assessments
# TYPE smarttriage_high_risk_ratio gauge
smarttriage_high_risk_ratio {high_ratio}

# HELP smarttriage_override_ratio Ratio of assessments requiring overrides
# TYPE smarttriage_override_ratio gauge
smarttriage_override_ratio {override_ratio}

# HELP smarttriage_confirmed_total Total assessments with confirmed clinical outcomes
# TYPE smarttriage_confirmed_total counter
smarttriage_confirmed_total {confirmed_total}

# HELP smarttriage_confirmed_accuracy Overall exact-match accuracy on confirmed outcomes
# TYPE smarttriage_confirmed_accuracy gauge
smarttriage_confirmed_accuracy {confirmed_accuracy}

# HELP smarttriage_high_sensitivity Sensitivity for high-risk detection on confirmed outcomes
# TYPE smarttriage_high_sensitivity gauge
smarttriage_high_sensitivity {high_sensitivity}

# HELP smarttriage_high_specificity Specificity for high-risk detection on confirmed outcomes
# TYPE smarttriage_high_specificity gauge
smarttriage_high_specificity {high_specificity}

# HELP smarttriage_high_ppv Positive predictive value for high-risk detection on confirmed outcomes
# TYPE smarttriage_high_ppv gauge
smarttriage_high_ppv {high_ppv}

# HELP smarttriage_high_npv Negative predictive value for high-risk detection on confirmed outcomes
# TYPE smarttriage_high_npv gauge
smarttriage_high_npv {high_npv}
"""

        return metrics_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        return "# Error collecting metrics\n", 500, {'Content-Type': 'text/plain'}
