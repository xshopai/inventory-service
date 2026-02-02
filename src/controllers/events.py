"""
Event Controllers for Inventory Service
HTTP endpoints for handling Dapr pub/sub event delivery

Includes:
- /dapr/subscribe endpoint for ACA programmatic subscriptions
- Event handler endpoints for each subscribed topic
"""

from flask import Blueprint, request, jsonify, current_app
from src.services.inventory_events_service import InventoryEventsService

events_bp = Blueprint('events', __name__)
events_service = InventoryEventsService()


# =============================================================================
# DAPR SUBSCRIPTION DEFINITIONS
# Single source of truth for ACA programmatic subscriptions
# For local dev, Dapr CLI uses .dapr/components/subscriptions.yaml
# IMPORTANT: Keep both in sync when adding/removing subscriptions
# =============================================================================

SUBSCRIPTIONS = [
    # Product events (from product-service)
    {"pubsubname": "pubsub", "topic": "product.created", "route": "/dapr/events/product.created"},
    {"pubsubname": "pubsub", "topic": "product.updated", "route": "/dapr/events/product.updated"},
    {"pubsubname": "pubsub", "topic": "product.deleted", "route": "/dapr/events/product.deleted"},
    # Order events (from order-service)
    {"pubsubname": "pubsub", "topic": "order.created", "route": "/dapr/events/order.created"},
    {"pubsubname": "pubsub", "topic": "order.cancelled", "route": "/dapr/events/order.cancelled"},
    {"pubsubname": "pubsub", "topic": "order.completed", "route": "/dapr/events/order.completed"},
    # Payment events (from payment-service)
    {"pubsubname": "pubsub", "topic": "payment.received", "route": "/dapr/events/payment.received"},
    {"pubsubname": "pubsub", "topic": "payment.failed", "route": "/dapr/events/payment.failed"},
]


@events_bp.route('/dapr/subscribe', methods=['GET'])
def get_subscriptions():
    """
    Dapr subscription endpoint (programmatic).
    
    Required for Azure Container Apps - ACA doesn't support declarative
    subscription YAML files, only this programmatic endpoint.
    Dapr sidecar calls this at startup to register subscriptions.
    """
    current_app.logger.info(f"Dapr requested subscription list (count={len(SUBSCRIPTIONS)})")
    return jsonify(SUBSCRIPTIONS)


# ============================================================================
# DAPR EVENT HANDLERS
# Routes for Dapr pub/sub - these match the SUBSCRIPTIONS list above
# ============================================================================

@events_bp.route('/dapr/events/product.created', methods=['POST'])
def dapr_product_created():
    """Handle product.created event via Dapr pub/sub"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.created event via Dapr")
        result = events_service.handle_product_created(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.created: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/product.updated', methods=['POST'])
def dapr_product_updated():
    """Handle product.updated event via Dapr pub/sub"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.updated event via Dapr")
        result = events_service.handle_product_updated(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.updated: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/product.deleted', methods=['POST'])
def dapr_product_deleted():
    """Handle product.deleted event via Dapr pub/sub"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received product.deleted event via Dapr")
        result = events_service.handle_product_deleted(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing product.deleted: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/order.created', methods=['POST'])
def dapr_order_created():
    """Handle order.created event via Dapr pub/sub - reserve stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.created event via Dapr")
        result = events_service.handle_order_created(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "RETRY"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.created: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/order.cancelled', methods=['POST'])
def dapr_order_cancelled():
    """Handle order.cancelled event via Dapr pub/sub - release stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.cancelled event via Dapr")
        result = events_service.handle_order_cancelled(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.cancelled: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/order.completed', methods=['POST'])
def dapr_order_completed():
    """Handle order.completed event via Dapr pub/sub"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received order.completed event via Dapr")
        result = events_service.handle_order_completed(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing order.completed: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/payment.received', methods=['POST'])
def dapr_payment_received():
    """Handle payment.received event via Dapr pub/sub - confirm stock reservation"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received payment.received event via Dapr")
        result = events_service.handle_payment_received(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing payment.received: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/dapr/events/payment.failed', methods=['POST'])
def dapr_payment_failed():
    """Handle payment.failed event via Dapr pub/sub - release reserved stock"""
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received payment.failed event via Dapr")
        result = events_service.handle_payment_failed(event_data)
        return jsonify({"status": "SUCCESS" if result.get('status') == 'success' else "DROP"}), 200
    except Exception as e:
        current_app.logger.error(f"Error processing payment.failed: {str(e)}")
        return jsonify({"status": "RETRY"}), 200

