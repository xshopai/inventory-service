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

# Configure Azure Monitor BEFORE importing Flask app
# This must happen before any Flask/requests imports for proper instrumentation
def setup_azure_monitor():
    """Configure Azure Monitor if connection string is available."""
    try:
        from src.utils.secret_manager import get_appinsights_connection_string
        connection_string = get_appinsights_connection_string()
        
        if not connection_string:
            logger.warning("Application Insights not configured - connection string not found")
            return False
        
        # OTEL_SERVICE_NAME, OTEL_RESOURCE_ATTRIBUTES, and OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED
        # are set as environment variables during ACA deployment (see scripts/aca.sh)
        # This keeps configuration external to code (12-factor app principle)
        
        service_name = os.environ.get('OTEL_SERVICE_NAME', os.environ.get('SERVICE_NAME', 'inventory-service'))
        logger.info(f"Configuring Azure Monitor with service name: {service_name}")
        
        from azure.monitor.opentelemetry import configure_azure_monitor
        
        # Explicitly configure with all options for better debugging
        configure_azure_monitor(
            connection_string=connection_string,
            enable_live_metrics=True,
            logger_name="inventory-service",
            # Explicitly enable all instrumentations
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "flask": {"enabled": True},
                "requests": {"enabled": True},
                "sqlalchemy": {"enabled": True},  # Track MySQL/SQLAlchemy calls
                "pymysql": {"enabled": True},  # Track PyMySQL driver calls
                "psycopg2": {"enabled": False},
                "logging": {"enabled": True},
            },
            # Add sampling rate to ensure all traces are sent
            span_processors=[],  # Use default
        )
        
        # Note: SQLAlchemy and PyMySQL instrumentation is done EARLY at top of file
        # before any database imports to ensure all connections are traced
        
        # Test that tracing is working by creating a test span
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("azure-monitor-init-verification") as span:
            span.set_attribute("test", "initialization")
            logger.info("Created test span to verify tracing")
        
        logger.info(f"Azure Monitor configured successfully - cloud_RoleName: {service_name}")
        
        # Force flush to ensure the test span is exported
        from opentelemetry.sdk.trace import TracerProvider
        provider = trace.get_tracer_provider()
        if hasattr(provider, 'force_flush'):
            provider.force_flush(timeout_millis=5000)
            logger.info("Forced flush of trace provider")
        
        return True
    except ImportError as e:
        logger.error(f"Azure Monitor SDK not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure Application Insights: {e}", exc_info=True)
        return False

# Only configure Azure Monitor when running as main module (gunicorn)
# Skip for flask CLI commands (flask db upgrade)
if os.environ.get('FLASK_SKIP_AZURE_MONITOR') != 'true':
    azure_monitor_enabled = setup_azure_monitor()
    logger.info(f"Azure Monitor setup complete: enabled={azure_monitor_enabled}")
else:
    logger.info("Skipping Azure Monitor setup (FLASK_SKIP_AZURE_MONITOR=true)")
    azure_monitor_enabled = False

# Import application factory
from src import create_app

# Create Flask application for gunicorn
# gunicorn will import this as: run:app
env = os.environ.get('FLASK_ENV', 'production')
app = create_app(env)

# Explicitly instrument Flask AFTER app is created
if azure_monitor_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        logger.info("Flask app instrumented for OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument Flask app: {e}")


def main():
    """Main application entry point."""
    # Get environment
    env = os.environ.get('FLASK_ENV', 'production')
    
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
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
