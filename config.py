"""
Configuration Management for SmartTriage Dashboard
Loads environment variables and provides configuration classes
"""
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class"""

    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')

    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///triage.db')

    # Determine database type from URL
    if DATABASE_URL.startswith('postgresql'):
        DATABASE_TYPE = 'postgresql'
    else:
        DATABASE_TYPE = 'sqlite'

    # PostgreSQL specific settings
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'smarttriage_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'smarttriage')

    # Hugging Face Configuration
    USE_HUGGINGFACE = os.getenv('USE_HUGGINGFACE', 'false').lower() == 'true'
    HF_REPO_ID = os.getenv('HF_REPO_ID', 'Manoj-palanisamy/smarttriage-models')
    HF_TOKEN = os.getenv('HF_TOKEN', None)

    # Email Configuration
    SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'false').lower() == 'true'
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', 'noreply@prioritymed.com')
    SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'PriorityMed')

    # Security Configuration
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600')))
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))

    # Rate Limiting Configuration
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '200 per day;50 per hour')
    RATELIMIT_LOGIN = os.getenv('RATELIMIT_LOGIN', '5 per minute')
    RATELIMIT_SIGNUP = os.getenv('RATELIMIT_SIGNUP', '3 per hour')
    RATELIMIT_TRIAGE = os.getenv('RATELIMIT_TRIAGE', '10 per minute')

    # Application Configuration
    APP_NAME = os.getenv('APP_NAME', 'PriorityMed')
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', '5000'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,png,jpg,jpeg,txt,csv,xlsx').split(','))

    # Model Paths
    MODEL_DIR = "models/experimental_brain"
    STABLE_MODEL_PATH = "models/triage_assets_mingled.pkl"
    HF_CACHE_DIR = "./hf_cache"


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    DATABASE_URL = 'sqlite:///:memory:'
    DATABASE_TYPE = 'sqlite'
    RATELIMIT_ENABLED = False
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
