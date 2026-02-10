#!/usr/bin/env python3
"""
Inventory Service
Flask-based microservice for managing product inventory.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set logging level
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('FLASK_DEBUG') == '1' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose Azure SDK logging (Live Metrics pings, HTTP requests)
# Only show warnings and errors from these libraries
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter').setLevel(logging.WARNING)
logging.getLogger('opentelemetry').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# ============================================================================
# CRITICAL: Instrument SQLAlchemy/PyMySQL BEFORE any database imports happen!
# The instrumentation must happen before the SQLAlchemy engine is created.
# ============================================================================
try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    if not SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry:
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation initialized EARLY (before database import)")
except ImportError as e:
    logger.warning(f"SQLAlchemy instrumentation package not available: {e}")
except Exception as e:
    logger.warning(f"Failed to initialize early SQLAlchemy instrumentation: {e}")

try:
    from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor
    if not PyMySQLInstrumentor().is_instrumented_by_opentelemetry:
        PyMySQLInstrumentor().instrument()
        logger.info("PyMySQL instrumentation initialized EARLY (before database import)")
except ImportError as e:
    logger.warning(f"PyMySQL instrumentation package not available: {e}")
except Exception as e:
    logger.warning(f"Failed to initialize early PyMySQL instrumentation: {e}")

# Configure tracing using unified module
from src.tracing import setup_tracing, is_tracing_enabled

tracing_enabled = setup_tracing('inventory-service')
logger.info(f"Tracing setup complete: enabled={tracing_enabled}")

# Import application factory
from src import create_app

# Create Flask application for gunicorn
# gunicorn will import this as: run:app
env = os.environ.get('FLASK_ENV', 'production')
app = create_app(env)

# Explicitly instrument Flask AFTER app is created
if tracing_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        logger.info("Flask app instrumented for OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument Flask app: {e}")


def main():
    """Main application entry point."""
    # Get environment
    env = os.environ.get('ENVIRONMENT', 'production')
    
    logger.info(f"Starting Inventory Service in {env} mode")
    
    # Create Flask application
    app = create_app(env)
    
    # Initialize database tables
    from src.database import db
    with app.app_context():
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))  # Test connection
            db.create_all()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if env == 'production':
                raise
            else:
                logger.warning("Continuing without database in development mode")
    
    # Get host and port from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8005))
    debug = env == 'development'
    
    logger.info(f"Starting Inventory Service on {host}:{port}")
    
    # Run the application
    # IMPORTANT: use_reloader=False is critical for VS Code debugger to work
    # The reloader spawns a child process which the debugger doesn't attach to
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,  # Disable reloader for debugging
        threaded=True
    )


if __name__ == '__main__':
    main()
