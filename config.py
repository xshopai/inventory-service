import os
from datetime import timedelta


def get_database_uri():
    """
    Lazy load database URI from Dapr secrets
    Called when database connection is actually needed
    """
    try:
        from src.utils.secret_manager import get_database_config
        db_config = get_database_config()
        return (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
    except Exception as e:
        # Fallback to environment variables if Dapr not available (for local dev/testing)
        # Note: These use uppercase env vars (standard convention) while Dapr secrets use lowercase-hyphenated
        user = os.environ.get('MYSQL_USER', 'admin')
        password = os.environ.get('MYSQL_PASSWORD', 'admin123')
        host = os.environ.get('DATABASE_HOST', 'localhost')
        port = os.environ.get('DATABASE_PORT', '3306')
        database = os.environ.get('MYSQL_DATABASE', 'inventory_service_db')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database - use lazy loading function instead of direct environment variables
    SQLALCHEMY_DATABASE_URI = None  # Will be set at runtime
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Cache disabled - Redis removed
    
    # Reservation settings
    RESERVATION_TTL_MINUTES = int(os.environ.get('RESERVATION_TTL_MINUTES', 30))
    
    # Dapr service app IDs
    DAPR_PRODUCT_SERVICE_APP_ID = os.environ.get('DAPR_PRODUCT_SERVICE_APP_ID', 'product-service')
    
    # Pagination
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 20))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    



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
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
