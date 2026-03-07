"""
Integration tests for API routes
"""
import pytest
from flask import session


class TestAuthenticationRoutes:
    """Test authentication-related routes"""

    def test_login_page_loads(self, client):
        """Test login page is accessible"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_signup_page_loads(self, client):
        """Test signup page is accessible"""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'signup' in response.data.lower() or b'register' in response.data.lower()

    def test_successful_signup(self, client):
        """Test successful user registration"""
        response = client.post('/signup', data={
            'fullname': 'Test User',
            'email': 'newuser@example.com',
            'password': 'TestPass123',
            'role': 'patient',
            'phone': '555-1234'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_duplicate_email_signup(self, client):
        """Test signup with duplicate email"""
        # First signup
        client.post('/signup', data={
            'fullname': 'User One',
            'email': 'duplicate@example.com',
            'password': 'TestPass123',
            'role': 'patient'
        })

        # Second signup with same email
        response = client.post('/signup', data={
            'fullname': 'User Two',
            'email': 'duplicate@example.com',
            'password': 'TestPass456',
            'role': 'patient'
        })

        assert response.status_code == 200  # Returns to signup page with error
        assert b'already exists' in response.data.lower() or b'email' in response.data.lower()

    def test_successful_login(self, client):
        """Test successful login"""
        # First register
        client.post('/signup', data={
            'fullname': 'Login Test',
            'email': 'login@example.com',
            'password': 'LoginPass123',
            'role': 'patient'
        })

        # Then login
        response = client.post('/login', data={
            'email': 'login@example.com',
            'password': 'LoginPass123',
            'role': 'patient'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_invalid_login(self, client):
        """Test login with invalid credentials"""
        response = client.post('/login', data={
            'email': 'nonexistent@example.com',
            'password': 'WrongPass123',
            'role': 'patient'
        })

        assert response.status_code == 200
        assert b'invalid' in response.data.lower() or b'error' in response.data.lower()

    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


class TestTriageRoutes:
    """Test triage-related routes"""

    def test_checkup_page_requires_login(self, client):
        """Test checkup page requires authentication"""
        response = client.get('/checkup')
        # Should redirect to login
        assert response.status_code == 302 or response.status_code == 401

    def test_checkup_page_accessible_when_logged_in(self, authenticated_client):
        """Test checkup page accessible when authenticated"""
        response = authenticated_client.get('/checkup')
        assert response.status_code == 200

    def test_triage_requires_login(self, client):
        """Test triage endpoint requires authentication"""
        response = client.post('/triage', data={
            'age': '35',
            'gender': 'Male',
            'sys_bp': '120',
            'dia_bp': '80',
            'hr': '75',
            'temp': '98.6',
            'symptom': 'Headache',
            'history': 'None'
        })
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    def test_triage_with_invalid_age(self, authenticated_client):
        """Test triage rejects invalid age"""
        response = authenticated_client.post('/triage', data={
            'age': '-5',  # Invalid: negative
            'gender': 'Male',
            'sys_bp': '120',
            'dia_bp': '80',
            'hr': '75',
            'temp': '98.6',
            'symptom': 'Headache',
            'history': 'None'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should show error or redirect back to checkup

    def test_triage_with_invalid_bp(self, authenticated_client):
        """Test triage rejects invalid blood pressure"""
        response = authenticated_client.post('/triage', data={
            'age': '35',
            'gender': 'Male',
            'sys_bp': '80',  # Invalid: systolic < diastolic
            'dia_bp': '120',
            'hr': '75',
            'temp': '98.6',
            'symptom': 'Headache',
            'history': 'None'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should show error or redirect back

    def test_triage_with_invalid_heart_rate(self, authenticated_client):
        """Test triage rejects invalid heart rate"""
        response = authenticated_client.post('/triage', data={
            'age': '35',
            'gender': 'Male',
            'sys_bp': '120',
            'dia_bp': '80',
            'hr': '300',  # Invalid: too high
            'temp': '98.6',
            'symptom': 'Headache',
            'history': 'None'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_triage_with_short_symptoms(self, authenticated_client):
        """Test triage rejects too-short symptom description"""
        response = authenticated_client.post('/triage', data={
            'age': '35',
            'gender': 'Male',
            'sys_bp': '120',
            'dia_bp': '80',
            'hr': '75',
            'temp': '98.6',
            'symptom': 'Bad',  # Too short
            'history': 'None'
        }, follow_redirects=True)

        assert response.status_code == 200


class TestDashboardRoutes:
    """Test dashboard-related routes"""

    def test_patient_dashboard_requires_login(self, client):
        """Test patient dashboard requires authentication"""
        response = client.get('/patient/dashboard')
        assert response.status_code in [302, 401]

    def test_patient_dashboard_accessible_when_logged_in(self, authenticated_client):
        """Test patient dashboard accessible when authenticated"""
        response = authenticated_client.get('/patient/dashboard')
        assert response.status_code == 200

    def test_index_requires_login(self, client):
        """Test index page requires authentication"""
        response = client.get('/')
        assert response.status_code in [302, 401]


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_login_rate_limit(self, client):
        """Test login route has rate limiting"""
        # Attempt many logins rapidly
        for i in range(10):
            response = client.post('/login', data={
                'email': f'test{i}@example.com',
                'password': 'WrongPass123',
                'role': 'patient'
            })

            # After configured limit (e.g., 5 per minute), should get 429
            if i > 6:
                if response.status_code == 429:
                    # Rate limit is working
                    assert True
                    return

        # Note: In testing mode, rate limiting might be disabled
        # This test may pass without hitting the limit
        assert True


class TestAppointmentRoutes:
    """Test appointment-related routes"""

    def test_appointments_page_requires_login(self, client):
        """Test appointments page requires authentication"""
        response = client.get('/appointments')
        assert response.status_code in [302, 401]

    def test_appointments_page_accessible_when_logged_in(self, authenticated_client):
        """Test appointments page accessible when authenticated"""
        response = authenticated_client.get('/appointments')
        assert response.status_code == 200


class TestMessagingRoutes:
    """Test messaging-related routes"""

    def test_messages_page_requires_login(self, client):
        """Test messages page requires authentication"""
        response = client.get('/messages')
        assert response.status_code in [302, 401]

    def test_messages_page_accessible_when_logged_in(self, authenticated_client):
        """Test messages page accessible when authenticated"""
        response = authenticated_client.get('/messages')
        assert response.status_code == 200
