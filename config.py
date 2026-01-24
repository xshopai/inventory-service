import os
from datetime import timedelta


def get_database_uri():
    """
    Get database URI - checks DATABASE_URL first, then individual env vars, then Dapr secrets.
    
    Priority order:
    1. DATABASE_URL (recommended - single connection string)
    2. Individual env vars (MYSQL_USER, MYSQL_PASSWORD, etc.)
    3. Dapr secrets (for production with Dapr sidecar)
    4. Defaults (for local development)
    """
    # Priority 1: Use DATABASE_URL if set (simplest, cloud-friendly)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
    
    # Priority 2: Build from individual env vars (legacy support)
    user = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    host = os.environ.get('DATABASE_HOST')
    database = os.environ.get('MYSQL_DATABASE')
    
    if all([user, password, host, database]):
        port = os.environ.get('DATABASE_PORT', '3306')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    # Priority 3: Try Dapr secrets (for production with Dapr sidecar)
    try:
        from src.utils.secret_manager import get_database_url
        return get_database_url()
    except Exception:
        pass
    
    # Priority 4: Defaults (local development fallback)
    user = user or 'admin'
    password = password or 'admin123'
    host = host or 'localhost'
    port = os.environ.get('DATABASE_PORT', '3306')
    database = database or 'inventory_service_db'
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
