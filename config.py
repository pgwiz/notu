"""
Configuration classes for different environments
"""
import os
from datetime import timedelta

def get_mysql_uri():
    """Generate MySQL URI from environment variables"""
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'notu')
    
    return f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}'

class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # File upload settings
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
    UPLOAD_FOLDER = 'uploads'
    
    # Storage settings
    STORAGE_LOCAL_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storage', 'local')
    STORAGE_BUCKET_ROOT = 'storage/bucket'
    ACTIVE_STORAGE_BACKEND = os.environ.get('ACTIVE_STORAGE_BACKEND', 'local')  # 'local' or 's3'
    
    # S3 settings (if using S3 backend)
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')  # For Scaleway, DigitalOcean, etc.
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security settings
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_ENABLED = True
    
    # Theme settings
    DEFAULT_THEME = 'green-black'
    
    # Pagination
    DOCUMENTS_PER_PAGE = 20
    
    # Sync settings
    SYNC_DRY_RUN = True  # Default to dry run for safety

class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or get_mysql_uri()
    SQLALCHEMY_ECHO = True

class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or get_mysql_uri()
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True

class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB for testing
