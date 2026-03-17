"""
Test configuration for SmartTriage Dashboard
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from config import TestingConfig


@pytest.fixture
def app():
    """Create application for testing"""
    # Monkey-patch the limiter to disable rate limiting during tests
    # This bypasses the pre-initialized limiter from app.py
    from unittest.mock import MagicMock

    if hasattr(flask_app, 'limiter_instance'):
        # Replace the limiter's hit method with a no-op
        flask_app.limiter_instance.hit = MagicMock(return_value=True)
        flask_app.limiter_instance.test_limit_method = MagicMock(return_value=None)

    # Now apply test config
    flask_app.config['TESTING'] = True
    flask_app.config['RATELIMIT_ENABLED'] = False
    flask_app.config.from_object(TestingConfig)
    flask_app.config['WTF_CSRF_ENABLED'] = False

    # Create tables
    with flask_app.app_context():
        from utils.database import DatabaseManager
        db = DatabaseManager(TestingConfig())
        db.init_database()

    yield flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client with persistent session"""
    # Register a test user
    response = client.post('/signup', data={
        'fullname': 'Test Patient',
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    })

    # Login and verify session is set
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    }, follow_redirects=True)  # Follow redirects to ensure session persists

    return client


@pytest.fixture
def sample_triage_data():
    """Sample valid triage data"""
    return {
        'age': '35',
        'gender': 'Male',
        'sys_bp': '120',
        'dia_bp': '80',
        'hr': '75',
        'temp': '98.6',
        'temp_unit': 'F',
        'respiration_rate': '16',  # Now provided (but optional in validator)
        'spo2': '98',  # Now provided (but optional in validator)
        'history': 'None',
        'symptom': 'Mild headache and fatigue'
    }


@pytest.fixture
def sample_user_data():
    """Sample valid user registration data"""
    return {
        'fullname': 'John Doe',
        'email': 'john.doe@example.com',
        'password': 'SecurePass123',
        'role': 'patient',
        'phone': '555-1234'
    }
