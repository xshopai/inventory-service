import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from src.models import db


def configure_azure_monitor(app):
    """
    Configure Azure Monitor / Application Insights for distributed tracing.
    Connection string from APPINSIGHTS_CONNECTION environment variable.
    """
    try:
        connection_string = os.environ.get('APPINSIGHTS_CONNECTION')
        
        if not connection_string:
            app.logger.info("Application Insights not configured - telemetry disabled")
            return False
        
        from azure.monitor.opentelemetry import configure_azure_monitor as setup_azure_monitor
        
        setup_azure_monitor(
            connection_string=connection_string,
            enable_live_metrics=True,
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "flask": {"enabled": True},
                "requests": {"enabled": True},
                "psycopg2": {"enabled": False},  # Not using PostgreSQL
            }
        )
        
        app.logger.info("Application Insights configured successfully")
        return True
        
    except ImportError as e:
        app.logger.warning(f"Azure Monitor SDK not installed: {e}")
        return False
    except Exception as e:
        app.logger.warning(f"Failed to configure Application Insights: {e}")
        return False


def configure_logging(app):
    """
    Configure logging based on environment variables.
    Supports console and file logging with JSON or console format.
    Color-coded output for development consistency with other services.
    """
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
    log_format = app.config.get('LOG_FORMAT', 'console')
    log_to_console = app.config.get('LOG_TO_CONSOLE', True)
    log_to_file = app.config.get('LOG_TO_FILE', False)
    log_file_path = app.config.get('LOG_FILE_PATH', './logs/inventory-service.log')
    service_name = 'inventory-service'
    
    # ANSI color codes for console output
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
    }
    RESET = '\033[0m'
    
    class ColorFormatter(logging.Formatter):
        """Colored formatter for development console output - matches Node.js services format"""
        def format(self, record):
            from datetime import datetime
            timestamp = datetime.fromtimestamp(record.created).isoformat()
            color = COLORS.get(record.levelname, '')
            
            # Format: [timestamp] [LEVEL] service [trace:xxx]: message
            base_msg = f"[{timestamp}] [{record.levelname}] {service_name} [no-trace]: {record.getMessage()}"
            
            if color:
                base_msg = f"{color}{base_msg}{RESET}"
            
            return base_msg
    
    # Create formatter based on format type
    if log_format == 'json':
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"service": "inventory-service", "logger": "%(name)s", '
            '"message": "%(message)s"}'
        )
    else:
        formatter = ColorFormatter()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        # Always use JSON format for file logging
        file_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"service": "inventory-service", "logger": "%(name)s", '
            '"message": "%(message)s"}'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config, get_database_uri
    app.config.from_object(config[config_name])
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # NOTE: Azure Monitor is configured in run.py AFTER app creation
    # This avoids issues with flask CLI commands (flask db upgrade)
    
    # Set database URI from Dapr secrets (lazy loading)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    
    # Initialize W3C Trace Context middleware
    from src.middlewares.trace_context import TraceContextMiddleware
    trace_middleware = TraceContextMiddleware(app)
    
    # Initialize database
    from src.database import init_db
    db = init_db(app)
    
    # Configure logging
    if not app.testing:
        configure_logging(app)
    
    # Register API blueprints
    try:
        from src.controllers import inventory_bp
        app.register_blueprint(inventory_bp, url_prefix='/api')
        app.logger.info("Inventory API registered successfully")
    except Exception as e:
        app.logger.warning(f"Inventory API registration failed: {e}. Running without API endpoints.")
    
    # Register admin blueprint (admin-only endpoints at /api/admin)
    try:
        from src.controllers import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.logger.info("Admin API registered successfully at /api/admin")
    except Exception as e:
        app.logger.warning(f"Admin API registration failed: {e}")
    
    # Register reservations blueprint
    # Per ARCHITECTURE.md Section 4.1, reservations are at /api/inventory/reservations
    try:
        from src.controllers import reservations_bp
        app.register_blueprint(reservations_bp, url_prefix='/api/inventory')
        app.logger.info("Reservations API registered successfully")
    except Exception as e:
        app.logger.warning(f"Reservations API registration failed: {e}")
    
    # Register operational/health blueprint
    try:
        from src.controllers import operational_hp
        app.register_blueprint(operational_hp)
        app.logger.info("Operational endpoints registered successfully")
    except Exception as e:
        app.logger.warning(f"Operational endpoints registration failed: {e}")
    
    # Register home endpoints blueprint
    try:
        from src.controllers.home import home_bp
        app.register_blueprint(home_bp)
        app.logger.info("Home endpoints registered successfully")
    except Exception as e:
        app.logger.warning(f"Home endpoints registration failed: {e}")
    
    # Register Dapr events blueprint
    try:
        from src.controllers.events import events_bp
        app.register_blueprint(events_bp)
        app.logger.info("Dapr events blueprint registered successfully")
    except Exception as e:
        app.logger.warning(f"Dapr events blueprint registration failed: {e}")
    
    # Register stats blueprint
    try:
        from src.controllers.stats import stats_bp
        app.register_blueprint(stats_bp)
        app.logger.info("Stats blueprint registered successfully")
    except Exception as e:
        app.logger.warning(f"Stats blueprint registration failed: {e}")
    
    # Register error handlers
    from src.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Database tables creation is deferred to init_database() function
    return app


def init_db(app):
    """Initialize database tables - call this explicitly when ready"""
    from src.database import db
    with app.app_context():
        try:
            # Only create tables if database connection is successful
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))  # Test connection
            db.create_all()
            app.logger.info("Database tables created successfully")
            return True
        except Exception as e:
            app.logger.error(f"Failed to create database tables: {e}")
            if app.config.get('FLASK_ENV') == 'production':
                # In production, fail fast
                raise
            else:
                # In development, continue without database connection for now
                app.logger.warning("Continuing without database connection in development mode")
                return False
