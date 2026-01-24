"""
Event Controllers for Inventory Service
HTTP endpoints for handling Dapr pub/sub event delivery
Protected with service token validation per Architecture spec 6.1
"""

from flask import Blueprint, request, jsonify, current_app
from src.services.inventory_events_service import InventoryEventsService
from src.middlewares.auth import require_service_token

events_bp = Blueprint('events', __name__)
events_service = InventoryEventsService()


# ============================================================================
# Product Events - Protected with service token validation
# ============================================================================

@events_bp.route('/events/product-created', methods=['POST'])
@require_service_token
def product_created():
    """Handle product.created event from Product Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_product_created(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing product.created: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200


@events_bp.route('/events/product-updated', methods=['POST'])
@require_service_token
def product_updated():
    """Handle product.updated event from Product Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_product_updated(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing product.updated: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200


@events_bp.route('/events/product-deleted', methods=['POST'])
@require_service_token
def product_deleted():
    """Handle product.deleted event from Product Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_product_deleted(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing product.deleted: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200


# ============================================================================
# Order Events - Protected with service token validation
# ============================================================================

@events_bp.route('/events/order-created', methods=['POST'])
@require_service_token
def order_created():
    """Handle order.created event from Order Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_order_created(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing order.created: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200


@events_bp.route('/events/order-cancelled', methods=['POST'])
@require_service_token
def order_cancelled():
    """Handle order.cancelled event from Order Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_order_cancelled(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing order.cancelled: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200


@events_bp.route('/events/order-completed', methods=['POST'])
@require_service_token
def order_completed():
    """Handle order.completed event from Order Service"""
    try:
        event_data = request.get_json()
        result = events_service.handle_order_completed(event_data)
        return jsonify({"success": result.get('status') == 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"❌ Error processing order.completed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 200
