"""
Home endpoints for inventory service
"""

from flask import Blueprint, jsonify
import os

# Create blueprint for home endpoints
home_bp = Blueprint('home', __name__)


@home_bp.route('/', methods=['GET'])
def info():
    """Service information endpoint"""
    return jsonify({
        'service': os.environ.get('NAME', 'inventory-service'),
        'version': os.environ.get('VERSION', '1.0.0'),
        'description': 'Inventory management microservice for xShop.ai platform',
        'environment': os.environ.get('FLASK_ENV', 'development'),
    }), 200


@home_bp.route('/version', methods=['GET'])
def version():
    """Service version endpoint"""
    return jsonify({
        'version': os.environ.get('VERSION', '1.0.0'),
        'service': os.environ.get('NAME', 'inventory-service'),
    }), 200
