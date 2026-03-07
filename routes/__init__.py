"""
Flask Blueprints for SmartTriage Dashboard
Organized route handlers by functionality
"""
from .auth import auth_bp
from .triage import triage_bp

__all__ = ['auth_bp', 'triage_bp']
