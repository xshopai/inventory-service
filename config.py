import os
from datetime import timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Module-level flag to detect if SSL is required (set during URL parsing)
_ssl_required = False


def get_database_uri():
    """
    Get database URI from environment variables.
    Falls back to defaults for local development.
    
    Expects MYSQL_SERVER_CONNECTION to be a complete SQLAlchemy URL format:
    mysql+pymysql://user:pass@host/database?ssl_mode=REQUIRED
    
    Note: PyMySQL doesn't support ssl_mode as a URL parameter, so we strip it
    and handle SSL via connect_args in SQLALCHEMY_ENGINE_OPTIONS instead.
    """
    global _ssl_required
    
    # Get connection string from environment (should be complete SQLAlchemy URL)
    server_connection = os.environ.get('MYSQL_SERVER_CONNECTION')
    
    if server_connection:
        # Parse URL to remove ssl_mode parameter (PyMySQL doesn't understand it)
        parsed = urlparse(server_connection)
        query_params = parse_qs(parsed.query)
        
        # Check if ssl_mode is present and set the flag
        if 'ssl_mode' in query_params:
            _ssl_required = True
            del query_params['ssl_mode']
        
        # Also check for ssl parameter
        if 'ssl' in query_params:
            _ssl_required = True
            del query_params['ssl']
        
        # Rebuild URL without ssl_mode
        # parse_qs returns lists, so flatten them for urlencode
        flat_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        new_query = urlencode(flat_params, doseq=True)
        
        # Reconstruct URL
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return clean_url
    
    # Fallback: Defaults for local development
    return "mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db"


def is_ssl_required():
    """Check if SSL is required for database connection."""
    return _ssl_required


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
    
    @classmethod
    def get_engine_options(cls):
        """Get SQLAlchemy engine options with SSL if required."""
        options = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
        
        # Add SSL config if ssl_mode was detected in the connection URL
        # For PyMySQL 1.0+, use ssl_mode as connect_arg (not URL param)
        if is_ssl_required():
            import ssl as ssl_module
            options['connect_args'] = {
                'ssl': {
                    'check_hostname': False,
                    'verify_mode': ssl_module.CERT_NONE
                }
            }
        
        return options

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    # MySQL is the primary database for all environments
    # SSL is auto-detected from connection URL via get_engine_options()

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # SSL is auto-detected from connection URL via get_engine_options()
    # No need to override - base Config.get_engine_options() handles SSL dynamically


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
