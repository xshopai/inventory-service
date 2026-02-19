import os
from datetime import timedelta


def get_database_uri():
    """
    Get database URI from environment variables.
    Falls back to defaults for local development.
    """
    # Get connection string and database name from environment
    server_connection = os.environ.get('MYSQL_SERVER_CONNECTION')
    db_name = os.environ.get('DB_NAME', 'inventory_service_db')
    
    if server_connection:
        # Append database name to connection string
        if '?' in server_connection:
            return f"{server_connection.split('?')[0]}/{db_name}?{server_connection.split('?')[1]}"
        return f"{server_connection}/{db_name}"
    
    # Fallback: Defaults for local development
    return "mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db"


class Config:
    """Base configuration"""
    
    # Flask SECRET_KEY - Sessions disabled (stateless REST API)
    # Set to None to make it explicit that sessions are not used
    SECRET_KEY = os.environ.get('SECRET_KEY') if os.environ.get('ENABLE_SESSIONS') else None
    
    # Database - use lazy loading function instead of direct environment variables
    SQLALCHEMY_DATABASE_URI = None  # Will be set at runtime
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Dapr service app IDs
    DAPR_PRODUCT_SERVICE_APP_ID = os.environ.get('DAPR_PRODUCT_SERVICE_APP_ID', 'product-service')
    
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

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'ssl': {
                'ca': '/etc/ssl/certs/DigiCertGlobalRootG2.crt.pem'
            }
        }
    }


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    # Use SQLite in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
