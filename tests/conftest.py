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
    flask_app.config.from_object(TestingConfig)

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
    """Create authenticated test client"""
    # Register a test user
    client.post('/signup', data={
        'fullname': 'Test Patient',
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    })

    # Login
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    })

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
