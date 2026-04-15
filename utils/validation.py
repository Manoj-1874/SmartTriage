"""
Input Validation Utilities for SmartTriage Dashboard
Validates medical data inputs to prevent invalid or malicious data
"""
from functools import wraps
from flask import jsonify, request
import re


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class VitalSignsValidator:
    """Validator for medical vital signs"""

    # Validation ranges (based on medical standards)
    AGE_MIN = 0
    AGE_MAX = 120

    SYSTOLIC_BP_MIN = 60
    SYSTOLIC_BP_MAX = 250

    DIASTOLIC_BP_MIN = 40
    DIASTOLIC_BP_MAX = 150

    HEART_RATE_MIN = 30
    HEART_RATE_MAX = 250

    RESPIRATION_RATE_MIN = 8
    RESPIRATION_RATE_MAX = 60

    SPO2_MIN = 50
    SPO2_MAX = 100

    TEMP_F_MIN = 90.0
    TEMP_F_MAX = 115.0

    TEMP_C_MIN = 32.0
    TEMP_C_MAX = 46.0

    @staticmethod
    def validate_age(age):
        """Validate patient age"""
        try:
            age = int(age)
        except (ValueError, TypeError):
            raise ValidationError("Age must be a valid number", "age")

        if age < VitalSignsValidator.AGE_MIN or age > VitalSignsValidator.AGE_MAX:
            raise ValidationError(
                f"Age must be between {VitalSignsValidator.AGE_MIN} and {VitalSignsValidator.AGE_MAX}",
                "age"
            )

        return age

    @staticmethod
    def validate_blood_pressure(systolic, diastolic):
        """Validate blood pressure readings"""
        try:
            systolic = int(systolic)
            diastolic = int(diastolic)
        except (ValueError, TypeError):
            raise ValidationError("Blood pressure must be valid numbers", "blood_pressure")

        # Validate systolic
        if systolic < VitalSignsValidator.SYSTOLIC_BP_MIN or systolic > VitalSignsValidator.SYSTOLIC_BP_MAX:
            raise ValidationError(
                f"Systolic BP must be between {VitalSignsValidator.SYSTOLIC_BP_MIN} and {VitalSignsValidator.SYSTOLIC_BP_MAX} mmHg",
                "systolic_bp"
            )

        # Validate diastolic
        if diastolic < VitalSignsValidator.DIASTOLIC_BP_MIN or diastolic > VitalSignsValidator.DIASTOLIC_BP_MAX:
            raise ValidationError(
                f"Diastolic BP must be between {VitalSignsValidator.DIASTOLIC_BP_MIN} and {VitalSignsValidator.DIASTOLIC_BP_MAX} mmHg",
                "diastolic_bp"
            )

        # Validate relationship (systolic should be higher than diastolic)
        if systolic <= diastolic:
            raise ValidationError(
                "Systolic blood pressure must be higher than diastolic blood pressure",
                "blood_pressure"
            )

        return systolic, diastolic

    @staticmethod
    def validate_heart_rate(heart_rate):
        """Validate heart rate"""
        try:
            heart_rate = int(heart_rate)
        except (ValueError, TypeError):
            raise ValidationError("Heart rate must be a valid number", "heart_rate")

        if heart_rate < VitalSignsValidator.HEART_RATE_MIN or heart_rate > VitalSignsValidator.HEART_RATE_MAX:
            raise ValidationError(
                f"Heart rate must be between {VitalSignsValidator.HEART_RATE_MIN} and {VitalSignsValidator.HEART_RATE_MAX} bpm",
                "heart_rate"
            )

        return heart_rate

    @staticmethod
    def validate_temperature(temperature, unit='F'):
        """Validate temperature and return in Fahrenheit for display"""
        try:
            temperature = float(temperature)
        except (ValueError, TypeError):
            raise ValidationError("Temperature must be a valid number", "temperature")

        if unit.upper() == 'F':
            if temperature < VitalSignsValidator.TEMP_F_MIN or temperature > VitalSignsValidator.TEMP_F_MAX:
                raise ValidationError(
                    f"Temperature must be between {VitalSignsValidator.TEMP_F_MIN}°F and {VitalSignsValidator.TEMP_F_MAX}°F",
                    "temperature"
                )
        elif unit.upper() == 'C':
            if temperature < VitalSignsValidator.TEMP_C_MIN or temperature > VitalSignsValidator.TEMP_C_MAX:
                raise ValidationError(
                    f"Temperature must be between {VitalSignsValidator.TEMP_C_MIN}°C and {VitalSignsValidator.TEMP_C_MAX}°C",
                    "temperature"
                )
            # Convert Celsius to Fahrenheit for display consistency
            temperature = (temperature * 9/5) + 32
        else:
            raise ValidationError("Temperature unit must be 'F' or 'C'", "temperature")

        return temperature

    @staticmethod
    def validate_respiration_rate(respiration_rate):
        """Validate respiration rate (breaths per minute). Optional with default 16 (normal average)."""
        # Allow None for backward compatibility with forms that don't provide RR
        if respiration_rate is None:
            return 16  # Normal average respiration rate

        try:
            respiration_rate = int(respiration_rate)
        except (ValueError, TypeError):
            raise ValidationError("Respiration rate must be a valid number", "respiration_rate")

        if respiration_rate < VitalSignsValidator.RESPIRATION_RATE_MIN or respiration_rate > VitalSignsValidator.RESPIRATION_RATE_MAX:
            raise ValidationError(
                f"Respiration rate must be between {VitalSignsValidator.RESPIRATION_RATE_MIN} and {VitalSignsValidator.RESPIRATION_RATE_MAX} breaths/min",
                "respiration_rate"
            )

        return respiration_rate

    @staticmethod
    def validate_spo2(spo2):
        """Validate oxygen saturation (SpO2 percentage). Optional with default 98 (healthy normal)."""
        # Allow None for backward compatibility with forms that don't provide SpO2
        if spo2 is None:
            return 98  # Healthy normal SpO2

        try:
            spo2 = int(spo2)
        except (ValueError, TypeError):
            raise ValidationError("SpO2 must be a valid number", "spo2")

        if spo2 < VitalSignsValidator.SPO2_MIN or spo2 > VitalSignsValidator.SPO2_MAX:
            raise ValidationError(
                f"SpO2 must be between {VitalSignsValidator.SPO2_MIN}% and {VitalSignsValidator.SPO2_MAX}%",
                "spo2"
            )

        return spo2

    @staticmethod
    def fahrenheit_to_celsius(temp_f):
        """Convert Fahrenheit to Celsius for ML model input

        CRITICAL: The XGBoost model was trained on Celsius values (avg 37.7°C).
        Feeding Fahrenheit values (98.6°F) causes the model to see them as outliers.

        Args:
            temp_f: Temperature in Fahrenheit

        Returns:
            float: Temperature in Celsius
        """
        return (temp_f - 32) * 5/9

    @staticmethod
    def validate_gender(gender):
        """Validate gender input"""
        valid_genders = ['male', 'female', 'other', 'm', 'f']

        if not gender or str(gender).lower() not in valid_genders:
            raise ValidationError(
                "Gender must be 'Male', 'Female', or 'Other'",
                "gender"
            )

        # Normalize to full name
        gender_lower = str(gender).lower()
        if gender_lower in ['m', 'male']:
            return 'Male'
        elif gender_lower in ['f', 'female']:
            return 'Female'
        else:
            return 'Other'

    @staticmethod
    def validate_symptoms(symptoms):
        """Validate symptom description"""
        if not symptoms or not isinstance(symptoms, str):
            raise ValidationError("Symptoms description is required", "symptoms")

        # Clean and validate
        symptoms = symptoms.strip()

        if len(symptoms) < 5:
            raise ValidationError(
                "Symptoms description must be at least 5 characters long",
                "symptoms"
            )

        if len(symptoms) > 2000:
            raise ValidationError(
                "Symptoms description must be less than 2000 characters",
                "symptoms"
            )

        return symptoms

    @staticmethod
    def validate_medical_history(history):
        """Validate medical history input"""
        valid_options = ['none', 'diabetes', 'hypertension', 'heart disease', 'asthma',
                        'kidney disease', 'cancer', 'other']

        if not history:
            return 'None'

        history_lower = str(history).lower()

        if history_lower not in valid_options:
            raise ValidationError(
                f"Medical history must be one of: {', '.join(valid_options)}",
                "medical_history"
            )

        return history

    @staticmethod
    def validate_pain_level(pain_level):
        """Validate pain intensity level (1-10)"""
        if pain_level is None or pain_level == '':
            return 0  # Default to 0 if not provided

        try:
            pain = int(pain_level)
        except (ValueError, TypeError):
            raise ValidationError("Pain level must be a valid number", "pain_level")

        if pain < 0 or pain > 10:
            raise ValidationError(
                "Pain level must be between 0 and 10",
                "pain_level"
            )

        return pain

    @staticmethod
    def validate_duration(duration):
        """Validate symptom duration"""
        print(f"[VALIDATE_DURATION] Input: {repr(duration)} (type: {type(duration).__name__})")

        if duration is None or duration == '':
            print(f"[VALIDATE_DURATION] Empty/None, returning 'Unknown'")
            return 'Unknown'  # Default to Unknown if not provided

        valid_durations = ['Today', '2-3 days', '1 week', '2+ weeks', 'Unknown']

        if duration not in valid_durations:
            print(f"[VALIDATE_DURATION] '{duration}' not in valid list: {valid_durations}")
            raise ValidationError(
                f"Duration must be one of: {', '.join(valid_durations)}",
                "duration"
            )

        print(f"[VALIDATE_DURATION] Valid, returning: {repr(duration)}")
        return duration  # Return exact format, don't modify case

    @classmethod
    def validate_triage_data(cls, data):
        """Validate complete triage assessment data"""
        validated = {}

        try:
            # Validate age
            validated['age'] = cls.validate_age(data.get('age'))

            # Validate gender
            validated['gender'] = cls.validate_gender(data.get('gender'))

            # Validate blood pressure
            sys_bp, dia_bp = cls.validate_blood_pressure(
                data.get('sys_bp'),
                data.get('dia_bp')
            )
            validated['sys_bp'] = sys_bp
            validated['dia_bp'] = dia_bp

            # Validate heart rate
            validated['hr'] = cls.validate_heart_rate(data.get('hr'))

            # Validate temperature
            temp_f = cls.validate_temperature(
                data.get('temp'),
                data.get('temp_unit', 'F')
            )
            validated['temp'] = temp_f  # Fahrenheit for display/storage
            validated['temp_celsius'] = cls.fahrenheit_to_celsius(temp_f)  # Celsius for ML model

            # Validate respiration and oxygen saturation (NEWS2 critical vitals)
            validated['respiration_rate'] = cls.validate_respiration_rate(data.get('respiration_rate'))
            validated['spo2'] = cls.validate_spo2(data.get('spo2'))

            # Validate symptoms
            validated['symptoms'] = cls.validate_symptoms(data.get('symptoms'))

            # Validate medical history
            validated['history'] = cls.validate_medical_history(data.get('history'))

            # Validate pain level and duration
            validated['pain_level'] = cls.validate_pain_level(data.get('pain_level'))
            validated['duration'] = cls.validate_duration(data.get('duration'))

            return validated

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation error: {str(e)}")


class UserValidator:
    """Validator for user registration and authentication data"""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", "email")

        email = email.strip().lower()

        if not UserValidator.EMAIL_REGEX.match(email):
            raise ValidationError("Invalid email format", "email")

        if len(email) > 255:
            raise ValidationError("Email is too long", "email")

        return email

    @staticmethod
    def validate_password(password, min_length=8):
        """Validate password strength"""
        if not password:
            raise ValidationError("Password is required", "password")

        if len(password) < min_length:
            raise ValidationError(
                f"Password must be at least {min_length} characters long",
                "password"
            )

        if len(password) > 128:
            raise ValidationError("Password is too long (max 128 characters)", "password")

        # Check for at least one number and one letter (optional, but recommended)
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)

        if not (has_letter and has_number):
            raise ValidationError(
                "Password must contain at least one letter and one number",
                "password"
            )

        return password

    @staticmethod
    def validate_fullname(fullname):
        """Validate full name"""
        if not fullname or not isinstance(fullname, str):
            raise ValidationError("Full name is required", "fullname")

        fullname = fullname.strip()

        if len(fullname) < 2:
            raise ValidationError("Full name must be at least 2 characters long", "fullname")

        if len(fullname) > 100:
            raise ValidationError("Full name is too long", "fullname")

        return fullname


def validate_request(validation_func):
    """Decorator to validate request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get data from request
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()

                # Validate data
                validated_data = validation_func(data)

                # Add validated data to kwargs
                kwargs['validated_data'] = validated_data

                return f(*args, **kwargs)

            except ValidationError as e:
                return jsonify({
                    'success': False,
                    'error': e.message,
                    'field': e.field
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f"Validation error: {str(e)}"
                }), 400

        return decorated_function
    return decorator
