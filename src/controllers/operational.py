"""
Health check endpoints for inventory service
These endpoints are used by monitoring systems, load balancers, and Kubernetes
"""

from flask import Blueprint, jsonify
from datetime import datetime
import os
import logging
from src.utils.health_checks import (
    perform_readiness_check, 
    perform_liveness_check, 
    get_system_metrics
)

logger = logging.getLogger(__name__)

# Create blueprint for health endpoints
operational_hp = Blueprint('operational', __name__)


@operational_hp.route('/health', methods=['GET'])
def health():
    """Main health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': os.environ.get('NAME', 'inventory-service'),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': os.environ.get('VERSION', '1.0.0'),
        'environment': os.environ.get('FLASK_ENV', 'development'),
    }), 200


@operational_hp.route('/health/ready', methods=['GET'])
def readiness():
    """Readiness probe - checks if service is ready to handle traffic"""
    try:
        readiness_result = perform_readiness_check()
        
        # Log readiness check results for monitoring
        logger.info('Readiness check performed', extra={
            'status': readiness_result['status'],
            'total_check_time': readiness_result['total_check_time'],
            'checks': {key: check['status'] for key, check in readiness_result['checks'].items()},
        })
        
        status_code = 200 if readiness_result['status'] == 'ready' else 503
        
        return jsonify({
            'status': readiness_result['status'],
            'service': 'inventory-service',
            'timestamp': readiness_result['timestamp'],
            'total_check_time': readiness_result['total_check_time'],
            'checks': readiness_result['checks'],
            **({'error': readiness_result['error']} if 'error' in readiness_result else {})
        }), status_code
        
    except Exception as e:
        logger.error('Readiness check failed', extra={'error': str(e)})
        return jsonify({
            'status': 'not ready',
            'service': 'inventory-service',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': 'Readiness check failed',
            'details': str(e),
        }), 503


@operational_hp.route('/health/live', methods=['GET'])
def liveness():
    """Liveness probe - checks if service is alive and responsive"""
    try:
        liveness_result = perform_liveness_check()
        
        # Log liveness issues for monitoring
        if liveness_result['status'] != 'alive':
            logger.warning('Liveness check failed', extra={
                'status': liveness_result['status'],
                'checks': liveness_result['checks'],
            })
        
        status_code = 200 if liveness_result['status'] == 'alive' else 503
        
        return jsonify({
            'status': liveness_result['status'],
            'service': 'inventory-service',
            'timestamp': liveness_result['timestamp'],
            'uptime': liveness_result['uptime'],
            'checks': liveness_result['checks'],
            **({'error': liveness_result['error']} if 'error' in liveness_result else {})
        }), status_code
        
    except Exception as e:
        logger.error('Liveness check failed', extra={'error': str(e)})
        return jsonify({
            'status': 'unhealthy',
            'service': 'inventory-service',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': 'Liveness check failed',
            'details': str(e),
        }), 503


@operational_hp.route('/metrics', methods=['GET'])
def metrics():
    """System metrics endpoint for monitoring"""
    try:
        system_metrics = get_system_metrics()
        
        return jsonify({
            'service': 'inventory-service',
            **system_metrics,
        }), 200
        
    except Exception as e:
        logger.error('Metrics collection failed', extra={'error': str(e)})
        return jsonify({
            'service': 'inventory-service',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': 'Metrics collection failed',
            'details': str(e),
        }), 500


@operational_hp.route('/test/publish', methods=['POST'])
def test_publish():
    """
    Test endpoint to publish a message to the broker.
    For development/testing purposes only.
    
    Request body (optional):
    {
        "topic": "inventory.test.event",
        "product_id": "test-product-123",
        "quantity": 100
    }
    """
    from flask import request
    from src.utils.event_publisher import event_publisher
    
    try:
        data = request.get_json() or {}
        topic = data.get('topic', 'inventory.test.event')
        product_id = data.get('product_id', 'test-product-123')
        quantity = data.get('quantity', 100)
        
        logger.info(f"Test publish requested: topic={topic}, product_id={product_id}")
        
        # Use the event publisher to publish a test event
        success = event_publisher.publish_stock_updated(
            product_id=product_id,
            quantity=quantity,
            warehouse="test-warehouse"
        )
        
        return jsonify({
            'success': success,
            'message': f"Published test event to topic: inventory.stock.updated",
            'data': {
                'topic': 'inventory.stock.updated',
                'product_id': product_id,
                'quantity': quantity,
                'warehouse': 'test-warehouse'
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Test publish failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 500
