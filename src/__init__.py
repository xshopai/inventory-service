import os
import sys
import logging
from flask import Flask
from src.models import db


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config, get_database_uri
    app.config.from_object(config[config_name])
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
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
        logging.basicConfig(
            level=getattr(logging, app.config['LOG_LEVEL']),
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )
    
    # Register API blueprints
    try:
        from src.controllers import inventory_bp
        app.register_blueprint(inventory_bp, url_prefix='/api')
        app.logger.info("Inventory API registered successfully")
    except Exception as e:
        app.logger.warning(f"Inventory API registration failed: {e}. Running without API endpoints.")
    
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
