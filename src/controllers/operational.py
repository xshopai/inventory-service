"""
Health check endpoints for inventory service
These endpoints are used by monitoring systems, load balancers, and Kubernetes
"""

from flask import Blueprint, jsonify
from datetime import datetime, timezone
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
            'timestamp': datetime.now(timezone.utc).isoformat(),
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
            'timestamp': datetime.now(timezone.utc).isoformat(),
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
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': 'Metrics collection failed',
            'details': str(e),
        }), 500