"""
Event Controllers for Inventory Service
HTTP endpoints for handling pub/sub event delivery

Includes:
- /dapr/subscribe endpoint for programmatic subscriptions (Azure Container Apps)
- Event handler endpoints for each subscribed topic
"""

from flask import Blueprint, request, jsonify, current_app
from src.services.inventory_events_service import InventoryEventsService
from src.middlewares.auth import require_dapr_token

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
    # Saga compensation events (from order-processor-service)
    {"pubsubname": "pubsub", "topic": "inventory.release", "route": "/events/inventory.release"},
    # Return events (from order-processor-service)
    {"pubsubname": "pubsub", "topic": "inventory.return.release", "route": "/events/inventory.return.release"},
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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
@require_dapr_token
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


@events_bp.route('/events/inventory.release', methods=['POST'])
@require_dapr_token
def inventory_release():
    """
    Handle inventory.release event - saga compensation transaction
    
    Triggered by order-processor-service when saga fails and needs rollback.
    Releases inventory reservation to return stock to available pool.
    
    Critical for preventing inventory leaks in failed order scenarios:
    - Payment fails after inventory reserved → Release inventory
    - Shipping fails after inventory reserved → Release inventory
    - Order cancelled after inventory reserved → Release inventory
    """
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received inventory.release compensation event")
        
        # Extract order ID and reservation ID from event
        data = event_data.get('data', {})
        order_id = data.get('orderId')
        reservation_id = data.get('reservationId')
        
        if not order_id:
            current_app.logger.error("inventory.release event missing orderId")
            return jsonify({"status": "DROP"}), 200
        
        current_app.logger.warn(
            f"Processing saga compensation: Releasing inventory for order {order_id}",
            extra={"correlationId": event_data.get('correlationId'), "orderId": order_id, "reservationId": reservation_id}
        )
        
        # Call service to release inventory
        result = events_service.handle_inventory_release(event_data)
        
        if result.get('status') == 'success':
            current_app.logger.info(
                f"Saga compensation completed: Inventory released for order {order_id}",
                extra={"correlationId": event_data.get('correlationId'), "orderId": order_id}
            )
            return jsonify({"status": "SUCCESS"}), 200
        else:
            # Retry compensation on failure - critical for data consistency
            current_app.logger.error(
                f"Saga compensation failed: Could not release inventory for order {order_id}",
                extra={"correlationId": event_data.get('correlationId'), "orderId": order_id, "error": result.get('message')}
            )
            return jsonify({"status": "RETRY"}), 200
            
    except Exception as e:
        current_app.logger.error(f"Error processing inventory.release compensation: {str(e)}")
        return jsonify({"status": "RETRY"}), 200


@events_bp.route('/events/inventory.return.release', methods=['POST'])
@require_dapr_token
def inventory_return_release():
    """
    Handle inventory.return.release event - return items to stock
    
    Triggered by order-processor-service when a return is approved.
    Adds returned items back to available stock.
    
    Event flow:
    1. Customer requests return via order-service
    2. Admin approves return → order-service publishes return.approved
    3. Order-processor-service handles return.approved → publishes inventory.return.release
    4. Inventory-service adds items back to stock
    """
    try:
        event_data = request.get_json()
        current_app.logger.info(f"Received inventory.return.release event")
        
        # Extract return details from event
        data = event_data.get('data', {})
        return_id = data.get('returnId')
        return_number = data.get('returnNumber')
        
        if not return_id:
            current_app.logger.error("inventory.return.release event missing returnId")
            return jsonify({"status": "DROP"}), 200
        
        current_app.logger.info(
            f"Processing inventory return: {return_number}",
            extra={
                "correlationId": event_data.get('correlationId'), 
                "returnId": return_id,
                "returnNumber": return_number
            }
        )
        
        # Call service to add items back to stock
        result = events_service.handle_inventory_return_release(event_data)
        
        if result.get('status') == 'success':
            current_app.logger.info(
                f"Inventory return completed: {return_number}",
                extra={
                    "correlationId": event_data.get('correlationId'), 
                    "returnId": return_id,
                    "itemsReturned": result.get('itemsReturned', 0)
                }
            )
            return jsonify({"status": "SUCCESS"}), 200
        else:
            # Retry on failure - critical for data consistency
            current_app.logger.error(
                f"Inventory return failed: {return_number}",
                extra={
                    "correlationId": event_data.get('correlationId'), 
                    "returnId": return_id, 
                    "error": result.get('message')
                }
            )
            return jsonify({"status": "RETRY"}), 200
            
    except Exception as e:
        current_app.logger.error(f"Error processing inventory.return.release: {str(e)}")
        return jsonify({"status": "RETRY"}), 200

