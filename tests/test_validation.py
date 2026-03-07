"""
Unit tests for input validation utilities
"""
import pytest
from utils.validation import VitalSignsValidator, UserValidator, ValidationError


class TestVitalSignsValidator:
    """Test vital signs validation"""

    def test_validate_age_valid(self):
        """Test valid age validation"""
        assert VitalSignsValidator.validate_age(25) == 25
        assert VitalSignsValidator.validate_age('35') == 35
        assert VitalSignsValidator.validate_age(0) == 0
        assert VitalSignsValidator.validate_age(120) == 120

    def test_validate_age_invalid(self):
        """Test invalid age validation"""
        with pytest.raises(ValidationError, match="Age must be between"):
            VitalSignsValidator.validate_age(-1)

        with pytest.raises(ValidationError, match="Age must be between"):
            VitalSignsValidator.validate_age(121)

        with pytest.raises(ValidationError, match="Age must be a valid number"):
            VitalSignsValidator.validate_age('invalid')

    def test_validate_blood_pressure_valid(self):
        """Test valid blood pressure validation"""
        sys, dia = VitalSignsValidator.validate_blood_pressure(120, 80)
        assert sys == 120
        assert dia == 80

        sys, dia = VitalSignsValidator.validate_blood_pressure('140', '90')
        assert sys == 140
        assert dia == 90

    def test_validate_blood_pressure_invalid(self):
        """Test invalid blood pressure validation"""
        # Systolic too high
        with pytest.raises(ValidationError, match="Systolic BP must be between"):
            VitalSignsValidator.validate_blood_pressure(251, 80)

        # Diastolic too low
        with pytest.raises(ValidationError, match="Diastolic BP must be between"):
            VitalSignsValidator.validate_blood_pressure(120, 39)

        # Systolic lower than diastolic
        with pytest.raises(ValidationError, match="Systolic blood pressure must be higher"):
            VitalSignsValidator.validate_blood_pressure(80, 120)

        # Invalid format
        with pytest.raises(ValidationError, match="Blood pressure must be valid numbers"):
            VitalSignsValidator.validate_blood_pressure('invalid', 80)

    def test_validate_heart_rate_valid(self):
        """Test valid heart rate validation"""
        assert VitalSignsValidator.validate_heart_rate(75) == 75
        assert VitalSignsValidator.validate_heart_rate('60') == 60
        assert VitalSignsValidator.validate_heart_rate(30) == 30
        assert VitalSignsValidator.validate_heart_rate(250) == 250

    def test_validate_heart_rate_invalid(self):
        """Test invalid heart rate validation"""
        with pytest.raises(ValidationError, match="Heart rate must be between"):
            VitalSignsValidator.validate_heart_rate(29)

        with pytest.raises(ValidationError, match="Heart rate must be between"):
            VitalSignsValidator.validate_heart_rate(251)

        with pytest.raises(ValidationError, match="Heart rate must be a valid number"):
            VitalSignsValidator.validate_heart_rate('invalid')

    def test_validate_temperature_fahrenheit_valid(self):
        """Test valid Fahrenheit temperature"""
        assert VitalSignsValidator.validate_temperature(98.6, 'F') == 98.6
        assert VitalSignsValidator.validate_temperature('100.4', 'F') == 100.4

    def test_validate_temperature_celsius_valid(self):
        """Test valid Celsius temperature converts to Fahrenheit"""
        # 37°C should convert to 98.6°F
        temp = VitalSignsValidator.validate_temperature(37, 'C')
        assert abs(temp - 98.6) < 0.1

    def test_validate_temperature_invalid(self):
        """Test invalid temperature validation"""
        with pytest.raises(ValidationError, match="Temperature must be between"):
            VitalSignsValidator.validate_temperature(89, 'F')

        with pytest.raises(ValidationError, match="Temperature must be between"):
            VitalSignsValidator.validate_temperature(116, 'F')

        with pytest.raises(ValidationError, match="Temperature must be a valid number"):
            VitalSignsValidator.validate_temperature('invalid', 'F')

    def test_validate_gender_valid(self):
        """Test valid gender validation"""
        assert VitalSignsValidator.validate_gender('Male') == 'Male'
        assert VitalSignsValidator.validate_gender('female') == 'Female'
        assert VitalSignsValidator.validate_gender('M') == 'Male'
        assert VitalSignsValidator.validate_gender('f') == 'Female'
        assert VitalSignsValidator.validate_gender('other') == 'Other'

    def test_validate_gender_invalid(self):
        """Test invalid gender validation"""
        with pytest.raises(ValidationError, match="Gender must be"):
            VitalSignsValidator.validate_gender('invalid')

        with pytest.raises(ValidationError, match="Gender must be"):
            VitalSignsValidator.validate_gender('')

    def test_validate_symptoms_valid(self):
        """Test valid symptoms validation"""
        symptoms = "Chest pain and shortness of breath"
        assert VitalSignsValidator.validate_symptoms(symptoms) == symptoms

    def test_validate_symptoms_invalid(self):
        """Test invalid symptoms validation"""
        with pytest.raises(ValidationError, match="at least 5 characters"):
            VitalSignsValidator.validate_symptoms("Cold")

        with pytest.raises(ValidationError, match="less than 2000 characters"):
            VitalSignsValidator.validate_symptoms("x" * 2001)

        with pytest.raises(ValidationError, match="Symptoms description is required"):
            VitalSignsValidator.validate_symptoms("")

    def test_validate_medical_history_valid(self):
        """Test valid medical history validation"""
        assert VitalSignsValidator.validate_medical_history('diabetes') == 'Diabetes'
        assert VitalSignsValidator.validate_medical_history('None') == 'None'
        assert VitalSignsValidator.validate_medical_history('') == 'None'

    def test_validate_triage_data_complete(self):
        """Test complete triage data validation"""
        data = {
            'age': '35',
            'gender': 'Male',
            'sys_bp': '120',
            'dia_bp': '80',
            'hr': '75',
            'temp': '98.6',
            'temp_unit': 'F',
            'symptoms': 'Mild headache and fatigue',
            'history': 'None'
        }

        validated = VitalSignsValidator.validate_triage_data(data)

        assert validated['age'] == 35
        assert validated['gender'] == 'Male'
        assert validated['sys_bp'] == 120
        assert validated['dia_bp'] == 80
        assert validated['hr'] == 75
        assert validated['temp'] == 98.6
        assert validated['symptoms'] == 'Mild headache and fatigue'
        assert validated['history'] == 'None'


class TestUserValidator:
    """Test user data validation"""

    def test_validate_email_valid(self):
        """Test valid email validation"""
        assert UserValidator.validate_email('test@example.com') == 'test@example.com'
        assert UserValidator.validate_email('Test@Example.COM') == 'test@example.com'
        assert UserValidator.validate_email('user.name+tag@example.co.uk') == 'user.name+tag@example.co.uk'

    def test_validate_email_invalid(self):
        """Test invalid email validation"""
        with pytest.raises(ValidationError, match="Invalid email format"):
            UserValidator.validate_email('invalid')

        with pytest.raises(ValidationError, match="Invalid email format"):
            UserValidator.validate_email('missing@domain')

        with pytest.raises(ValidationError, match="Email is required"):
            UserValidator.validate_email('')

        with pytest.raises(ValidationError, match="Email is too long"):
            UserValidator.validate_email('a' * 300 + '@example.com')

    def test_validate_password_valid(self):
        """Test valid password validation"""
        assert UserValidator.validate_password('Password123') == 'Password123'
        assert UserValidator.validate_password('Complex1Pass!') == 'Complex1Pass!'

    def test_validate_password_invalid(self):
        """Test invalid password validation"""
        # Too short
        with pytest.raises(ValidationError, match="at least 8 characters"):
            UserValidator.validate_password('Pass1')

        # No number
        with pytest.raises(ValidationError, match="at least one letter and one number"):
            UserValidator.validate_password('PasswordOnly')

        # No letter
        with pytest.raises(ValidationError, match="at least one letter and one number"):
            UserValidator.validate_password('12345678')

        # Empty
        with pytest.raises(ValidationError, match="Password is required"):
            UserValidator.validate_password('')

        # Too long
        with pytest.raises(ValidationError, match="Password is too long"):
            UserValidator.validate_password('a' * 130 + '1')

    def test_validate_fullname_valid(self):
        """Test valid fullname validation"""
        assert UserValidator.validate_fullname('John Doe') == 'John Doe'
        assert UserValidator.validate_fullname('  Jane Smith  ') == 'Jane Smith'

    def test_validate_fullname_invalid(self):
        """Test invalid fullname validation"""
        with pytest.raises(ValidationError, match="at least 2 characters"):
            UserValidator.validate_fullname('A')

        with pytest.raises(ValidationError, match="Full name is required"):
            UserValidator.validate_fullname('')

        with pytest.raises(ValidationError, match="Full name is too long"):
            UserValidator.validate_fullname('A' * 101)
