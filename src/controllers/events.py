"""
Event Controllers for Inventory Service
HTTP endpoints for handling pub/sub event delivery

Includes:
- /dapr/subscribe endpoint for programmatic subscriptions (Azure Container Apps)
- Event handler endpoints for each subscribed topic
"""

from flask import Blueprint, request, jsonify, current_app
from src.services.inventory_events_service import InventoryEventsService
from src.middlewares.auth import require_service_token

events_bp = Blueprint('events', __name__)
events_service = InventoryEventsService()


# =============================================================================
# SUBSCRIPTION DEFINITIONS
# Single source of truth for programmatic subscriptions (Azure Container Apps)
# For local dev, uses .dapr/components/subscriptions.yaml
# IMPORTANT: Keep both in sync when adding/removing subscriptions
# =============================================================================

SUBSCRIPTIONS = [
    # Product events (from product-service)
    {"pubsubname": "pubsub", "topic": "product.created", "route": "/events/product.created"},
    {"pubsubname": "pubsub", "topic": "product.updated", "route": "/events/product.updated"},
    {"pubsubname": "pubsub", "topic": "product.deleted", "route": "/events/product.deleted"},
    # Order events (from order-service)
    {"pubsubname": "pubsub", "topic": "order.created", "route": "/events/order.created"},
    {"pubsubname": "pubsub", "topic": "order.cancelled", "route": "/events/order.cancelled"},
    {"pubsubname": "pubsub", "topic": "order.completed", "route": "/events/order.completed"},
    # Payment events (from payment-service)
    {"pubsubname": "pubsub", "topic": "payment.received", "route": "/events/payment.received"},
    {"pubsubname": "pubsub", "topic": "payment.failed", "route": "/events/payment.failed"},
]


@events_bp.route('/dapr/subscribe', methods=['GET'])
def get_subscriptions():
    """
    Subscription endpoint (programmatic).
    
    Required for Azure Container Apps - ACA doesn't support declarative
    subscription YAML files, only this programmatic endpoint.
    Dapr sidecar calls this at startup to register subscriptions.
    """
    current_app.logger.info(f"Subscription list requested (count={len(SUBSCRIPTIONS)})")
    return jsonify(SUBSCRIPTIONS)


# ============================================================================
# EVENT HANDLERS
# Routes for pub/sub event handling - these match the SUBSCRIPTIONS list above
# ============================================================================

@events_bp.route('/events/product.created', methods=['POST'])
@require_service_token
def product_created():
    """Handle product.created event"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.created event")
        result = events_service.handle_product_created(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.created: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/product.updated', methods=['POST'])
@require_service_token
def product_updated():
    """Handle product.updated event"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.updated event")
        result = events_service.handle_product_updated(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.updated: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/product.deleted', methods=['POST'])
@require_service_token
def product_deleted():
    """Handle product.deleted event"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.deleted event")
        result = events_service.handle_product_deleted(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.deleted: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/order.created', methods=['POST'])
@require_service_token
def order_created():
    """Handle order.created event - reserve stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.created event")
        result = events_service.handle_order_created(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "RETRY"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.created: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/order.cancelled', methods=['POST'])
@require_service_token
def order_cancelled():
    """Handle order.cancelled event - release stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.cancelled event")
        result = events_service.handle_order_cancelled(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.cancelled: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/order.completed', methods=['POST'])
@require_service_token
def order_completed():
    """Handle order.completed event"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.completed event")
        result = events_service.handle_order_completed(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.completed: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/payment.received', methods=['POST'])
@require_service_token
def payment_received():
    """Handle payment.received event - confirm stock reservation"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received payment.received event")
        result = events_service.handle_payment_received(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing payment.received: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/payment.failed', methods=['POST'])
@require_service_token
def payment_failed():
    """Handle payment.failed event - release reserved stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received payment.failed event")
        result = events_service.handle_payment_failed(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing payment.failed: {str(e)}")
        return jsonify({"status": "RETRY"}), 200

