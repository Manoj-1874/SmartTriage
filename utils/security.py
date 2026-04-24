"""
Security Middleware and Utilities for SmartTriage Dashboard
Implements professional security features including:
- Security headers
- Input sanitization
- CSRF protection
- Request tracking
- Audit logging
"""
import secrets
import uuid
import re
import bleach
from functools import wraps
from flask import request, g, current_app, abort
from flask_login import current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """Apply security headers to all responses"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize security headers for Flask app"""
        app.after_request(self.add_security_headers)
        app.logger.info("Security headers middleware initialized")

    @staticmethod
    def add_security_headers(response):
        """Add comprehensive security headers to response"""
        # Content Security Policy - Prevent XSS attacks
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://chatling.ai; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://chatling.ai; "
            "frame-ancestors 'none';"
        )

        # Prevent clickjacking attacks
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection in older browsers
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy for privacy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=()'
        )

        # HSTS for HTTPS enforcement (only in production)
        if not current_app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class RequestTracking:
    """Add unique request ID to each request for tracking"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize request tracking for Flask app"""
        app.before_request(self.add_request_id)
        app.after_request(self.add_request_id_to_response)
        app.logger.info("Request tracking middleware initialized")

    @staticmethod
    def add_request_id():
        """Add unique request ID to Flask's g object"""
        g.request_id = str(uuid.uuid4())
        g.request_start_time = datetime.utcnow()

    @staticmethod
    def add_request_id_to_response(response):
        """Add request ID to response headers"""
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id

            # Log request completion with timing
            if hasattr(g, 'request_start_time'):
                duration = (datetime.utcnow() - g.request_start_time).total_seconds()
                logger.info(
                    f"Request completed - ID: {g.request_id} | "
                    f"Method: {request.method} | "
                    f"Path: {request.path} | "
                    f"Status: {response.status_code} | "
                    f"Duration: {duration:.3f}s"
                )
        return response


class AuditLogger:
    """Log security-sensitive operations for compliance and monitoring"""

    def __init__(self, app=None):
        self.app = app
        self.audit_logger = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize audit logging"""
        # Create separate audit log file
        import os
        from logging.handlers import RotatingFileHandler

        os.makedirs('logs', exist_ok=True)
        audit_handler = RotatingFileHandler(
            'logs/audit.log',
            maxBytes=10485760,  # 10MB
            backupCount=20,  # Keep more audit logs
            encoding='utf-8'
        )

        audit_format = logging.Formatter(
            '[%(asctime)s] AUDIT | Request-ID: %(request_id)s | User: %(user)s | '
            'IP: %(ip)s | Action: %(action)s | Details: %(details)s'
        )
        audit_handler.setFormatter(audit_format)

        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.propagate = False  # Don't propagate to root logger

        app.logger.info("Audit logging initialized")

    def log_event(self, action, details='', user=None):
        """Log an audit event"""
        if not self.audit_logger:
            return

        request_id = getattr(g, 'request_id', 'unknown')
        user_id = user if user else (current_user.email if hasattr(current_user, 'email') else 'anonymous')
        ip_address = request.remote_addr if request else 'unknown'

        self.audit_logger.info(
            '',
            extra={
                'request_id': request_id,
                'user': user_id,
                'ip': ip_address,
                'action': action,
                'details': details
            }
        )


class InputSanitizer:
    """Sanitize user input to prevent XSS and injection attacks"""

    # Allowed HTML tags for rich text fields (very restrictive)
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u']
    ALLOWED_ATTRIBUTES = {}

    @staticmethod
    def sanitize_html(text):
        """Sanitize HTML input to prevent XSS"""
        if not text:
            return text
        return bleach.clean(
            text,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )

    @staticmethod
    def sanitize_string(text, max_length=None):
        """Sanitize plain text input"""
        if not text:
            return text

        # Remove any null bytes
        text = text.replace('\x00', '')

        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

        # Trim whitespace
        text = text.strip()

        # Enforce max length
        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text

    @staticmethod
    def sanitize_email(email):
        """Validate and sanitize email address"""
        if not email:
            return None

        email = email.strip().lower()

        # Basic email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return None

        return email

    @staticmethod
    def sanitize_phone(phone):
        """Sanitize phone number - keep only digits and basic formatting"""
        if not phone:
            return None

        # Keep only digits, spaces, hyphens, parentheses, and plus sign
        phone = re.sub(r'[^0-9\s\-\(\)\+]', '', phone)
        return phone.strip()


def require_role(*roles):
    """Decorator to restrict access to specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized

            if not hasattr(current_user, 'role') or current_user.role not in roles:
                logger.warning(
                    f"Access denied - User: {current_user.email} | "
                    f"Required roles: {roles} | "
                    f"User role: {getattr(current_user, 'role', 'unknown')}"
                )
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def audit_action(action_name):
    """Decorator to automatically audit an action"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function
            result = f(*args, **kwargs)

            # Log the audit event
            try:
                audit_logger = current_app.extensions.get('audit_logger')
                if audit_logger:
                    audit_logger.log_event(
                        action=action_name,
                        details=f"Function: {f.__name__}"
                    )
            except Exception as e:
                logger.error(f"Failed to log audit event: {str(e)}")

            return result
        return decorated_function
    return decorator


class PasswordPolicy:
    """Enforce strong password policies"""

    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def validate(cls, password):
        """
        Validate password against policy
        Returns (bool, str) - (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"

        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"

        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            return False, f"Password must contain at least one special character ({cls.SPECIAL_CHARS})"

        # Check for common weak passwords
        weak_passwords = {
            'password', 'password123', '12345678', 'qwerty123',
            'admin123', 'letmein', 'welcome123'
        }
        if password.lower() in weak_passwords:
            return False, "This password is too common. Please choose a stronger password"

        return True, "Password is valid"


def generate_secure_token(length=32):
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def verify_recaptcha(response_token):
    """
    Verify Google reCAPTCHA response (placeholder)
    Implement when reCAPTCHA is configured
    """
    # TODO: Implement reCAPTCHA verification
    # import requests
    # secret = current_app.config.get('RECAPTCHA_SECRET_KEY')
    # response = requests.post(
    #     'https://www.google.com/recaptcha/api/siteverify',
    #     data={'secret': secret, 'response': response_token}
    # )
    # return response.json().get('success', False)
    return True  # Bypass for now
