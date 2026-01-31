import os
from datetime import timedelta


def get_database_uri():
    """
    Get database URI.
    
    Uses xshopai-mysql-server-connection + DB_NAME (same env vars in local and ACA).
    Falls back to defaults for local development.
    """
    # Try Dapr secrets / env vars (xshopai-mysql-server-connection + DB_NAME)
    try:
        from src.utils.secret_manager import get_database_url
        return get_database_url()
    except Exception:
        pass
    
    # Fallback: Defaults for local development
    return "mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db"


def get_flask_secret_key():
    """
    Get Flask SECRET_KEY - tries Dapr secrets first, then env vars.
    """
    try:
        from src.utils.secret_manager import get_flask_secret_key
        return get_flask_secret_key()
    except Exception:
        pass
    
    # Fallback to env var (hyphenated key - same as Key Vault)
    return os.environ.get('xshopai-flask-secret') or 'dev-secret-key-change-in-production'


class Config:
    """Base configuration"""
    
    # Flask - loaded from Dapr secrets or env vars
    SECRET_KEY = get_flask_secret_key()
    
    # Database - use lazy loading function instead of direct environment variables
    SQLALCHEMY_DATABASE_URI = None  # Will be set at runtime
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Cache disabled - Redis removed
    
    # Dapr service app IDs
    DAPR_PRODUCT_SERVICE_APP_ID = os.environ.get('DAPR_PRODUCT_SERVICE_APP_ID', 'product-service')
    
    # Pagination
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 20))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'console')  # 'console' or 'json'
    LOG_TO_CONSOLE = os.environ.get('LOG_TO_CONSOLE', 'true').lower() == 'true'
    LOG_TO_FILE = os.environ.get('LOG_TO_FILE', 'false').lower() == 'true'
    LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', './logs/inventory-service.log')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    # MySQL is the primary database for all environments

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Use different Redis DB for testing
    REDIS_DB = 1
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Override with production values if needed


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'test': TestingConfig,  # Alias for 'testing'
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
