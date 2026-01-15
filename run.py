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

# Import application factory
from src import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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
