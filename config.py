import os
from datetime import timedelta


def get_database_uri():
    """
    Get database URI from environment variables.
    Falls back to defaults for local development.
    
    Expects MYSQL_SERVER_CONNECTION to be a complete SQLAlchemy URL format:
    mysql+pymysql://user:pass@host/database?ssl_mode=REQUIRED
    
    Note: The ssl_mode parameter is stripped from the URL because PyMySQL doesn't 
    support it as a query parameter. SSL is configured via SQLALCHEMY_ENGINE_OPTIONS instead.
    """
    # Get connection string from environment (should be complete SQLAlchemy URL)
    server_connection = os.environ.get('MYSQL_SERVER_CONNECTION')
    
    if server_connection:
        # Strip ssl_mode from URL - PyMySQL doesn't support it as query parameter
        # SSL is handled via connect_args in SQLALCHEMY_ENGINE_OPTIONS
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(server_connection)
        query_params = parse_qs(parsed.query)
        # Remove ssl_mode parameter (PyMySQL uses 'ssl' connect_arg instead)
        query_params.pop('ssl_mode', None)
        # Reconstruct URL without ssl_mode
        new_query = urlencode(query_params, doseq=True)
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                parsed.params, new_query, parsed.fragment))
        return clean_url
    
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
    
    # Service Invocation Mode (for consistency with other services)
    SERVICE_INVOCATION_MODE = os.environ.get('SERVICE_INVOCATION_MODE', 'http')
    
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
    

# Dynamically set SSL options based on connection string
# This runs after class definition but before app initialization
_mysql_conn = os.environ.get('MYSQL_SERVER_CONNECTION', '')
if 'azure.com' in _mysql_conn or 'mysql.database' in _mysql_conn:
    DevelopmentConfig.SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'ssl': True}
    }
else:
    DevelopmentConfig.SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

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
