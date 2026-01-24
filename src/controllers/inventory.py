"""
Inventory Controller - Handles inventory CRUD operations and stock management
"""

from flask import Blueprint, request, g, jsonify
from flask_restx import Api, Resource, fields
from marshmallow import ValidationError
from src.services import InventoryService
from src.middlewares.auth import require_admin, require_service_token
from src.utils.schemas import (
    InventoryItemRequestSchema, InventoryItemResponseSchema,
    StockAdjustmentRequestSchema, StockMovementResponseSchema,
    InventorySearchSchema, BulkOperationRequestSchema
)
from src.utils.event_publisher import event_publisher
from src.utils.error_codes import (
    sku_not_found_error, sku_already_exists_error, 
    validation_error, create_error_response, ErrorCode
)
import logging

logger = logging.getLogger(__name__)

# Create blueprint
inventory_bp = Blueprint('inventory', __name__)
api = Api(inventory_bp, version='1.0', title='Inventory API',
          description='Inventory management endpoints', doc='/docs/')

# Create namespaces
inventory_ns = api.namespace('inventory', description='Inventory operations')
stock_ns = api.namespace('inventory/stock', description='Stock query operations')

# Initialize schemas
inventory_request_schema = InventoryItemRequestSchema()
inventory_response_schema = InventoryItemResponseSchema()
stock_adjustment_schema = StockAdjustmentRequestSchema()
stock_movement_schema = StockMovementResponseSchema()
search_schema = InventorySearchSchema()
bulk_operation_schema = BulkOperationRequestSchema()


def get_inventory_models(api):
    """Define API models for inventory operations"""
    inventory_item_model = api.model('InventoryItem', {
        'id': fields.Integer(description='Inventory item ID'),
        'product_id': fields.String(required=True, description='Product identifier'),
        'quantity': fields.Integer(required=True, description='Total quantity'),
        'reserved_quantity': fields.Integer(description='Reserved quantity'),
        'available_quantity': fields.Integer(description='Available quantity'),
        'minimum_stock_level': fields.Integer(description='Minimum stock level'),
        'maximum_stock_level': fields.Integer(description='Maximum stock level'),
        'location': fields.String(description='Storage location'),
        'created_at': fields.DateTime(description='Creation timestamp'),
        'updated_at': fields.DateTime(description='Last update timestamp')
    })

    stock_adjustment_model = api.model('StockAdjustment', {
        'product_id': fields.String(required=True, description='Product identifier'),
        'quantity': fields.Integer(required=True, description='Adjustment quantity'),
        'movement_type': fields.String(required=True, description='Movement type'),
        'reference_id': fields.String(description='Reference identifier'),
        'notes': fields.String(description='Additional notes')
    })

    return inventory_item_model, stock_adjustment_model


# Define models
inventory_item_model, stock_adjustment_model = get_inventory_models(api)

# Register routes
@inventory_ns.route('/')
class InventoryList(Resource):
        @api.doc('list_inventory')
        @api.marshal_list_with(inventory_item_model)
        @require_admin
        def get(self):
            """Get all inventory items with optional filtering (Admin only)"""
            try:
                # Validate query parameters
                search_params = search_schema.load(request.args.to_dict())
                
                inventory_service = InventoryService()
                items, total = inventory_service.search_inventory(**search_params)
                
                # Serialize response
                result = inventory_response_schema.dump(items, many=True)
                
                limit = search_params.get('per_page', 20)
                return {
                    'items': result,
                    'pagination': {
                        'page': search_params.get('page', 1),
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }, 200
                
            except ValidationError as e:
                return {'error': 'Validation failed', 'details': e.messages}, 400
            except Exception as e:
                logger.error(f"Error listing inventory: {e}")
                return {'error': 'Internal server error'}, 500

        @api.doc('create_inventory')
        @api.expect(inventory_item_model)
        @require_admin
        def post(self):
            """Create new inventory item (Admin only)"""
            try:
                # Validate request data
                data = inventory_request_schema.load(request.json)
                
                inventory_service = InventoryService()
                item = inventory_service.create_inventory_item(**data)
                
                # Publish inventory.created event
                correlation_id = getattr(g, 'correlation_id', None)
                event_publisher.publish_inventory_created(
                    product_id=item.sku,  # Using SKU as identifier
                    initial_quantity=item.quantity_available,
                    correlation_id=correlation_id
                )
                
                # Serialize response
                result = inventory_response_schema.dump(item)
                return result, 201
                
            except ValidationError as e:
                return {'error': 'Validation failed', 'details': e.messages}, 400
            except ValueError as e:
                return {'error': str(e)}, 400
            except Exception as e:
                logger.error(f"Error creating inventory item: {e}")
                return {'error': 'Internal server error'}, 500

        @api.doc('bulk_update_inventory')
        def put(self):
            """Bulk update inventory items"""
            try:
                # Validate request data
                data = bulk_operation_schema.load(request.json)
                
                inventory_service = InventoryService()
                results = inventory_service.bulk_update_inventory(data['operations'])
                
                return {'results': results}, 200
                
            except ValidationError as e:
                return {'error': 'Validation failed', 'details': e.messages}, 400
            except Exception as e:
                logger.error(f"Error performing bulk update: {e}")
                return {'error': 'Internal server error'}, 500

        @api.doc('bulk_delete_inventory')
        def delete(self):
            """Bulk delete inventory items"""
            try:
                # Expect request body with 'skus' array
                if not request.json or 'skus' not in request.json:
                    return {'error': 'Request must contain "skus" array'}, 400
                
                skus = request.json['skus']
                if not isinstance(skus, list) or not skus:
                    return {'error': '"skus" must be a non-empty array'}, 400
                
                inventory_service = InventoryService()
                results = []
                
                for sku in skus:
                    try:
                        success = inventory_service.delete_inventory_item(sku)
                        results.append({
                            'sku': sku,
                            'success': success,
                            'message': 'Deleted successfully' if success else 'Not found'
                        })
                    except Exception as e:
                        results.append({
                            'sku': sku,
                            'success': False,
                            'message': str(e)
                        })
                
                return {'results': results}, 200
                
            except Exception as e:
                logger.error(f"Error performing bulk delete: {e}")
                return {'error': 'Internal server error', 'details': str(e)}, 500

@inventory_ns.route('/<string:identifier>')
class InventoryItem(Resource):
        @api.doc('get_inventory')
        def get(self, identifier):
            """Get inventory item by SKU"""
            try:
                inventory_service = InventoryService()
                item = inventory_service.get_inventory_by_sku(identifier)
                
                if not item:
                    return {'error': 'Inventory item not found'}, 404
                
                result = inventory_response_schema.dump(item)
                return result, 200
                
            except Exception as e:
                logger.error(f"Error getting inventory for SKU {identifier}: {e}")
                return {'error': 'Internal server error'}, 500

        @api.doc('update_inventory')
        @api.expect(inventory_item_model)
        @api.marshal_with(inventory_item_model)
        @require_service_token
        def put(self, identifier):
            """Update inventory item by SKU (Service Token required)"""
            try:
                # Validate request data
                data = inventory_request_schema.load(request.json)
                
                inventory_service = InventoryService()
                item = inventory_service.update_inventory_item(identifier, **data)
                
                if not item:
                    return sku_not_found_error(identifier)
                
                # Publish inventory.stock.updated event
                correlation_id = getattr(g, 'correlation_id', None)
                event_publisher.publish_stock_updated(
                    product_id=item.sku,  # Using SKU as identifier
                    quantity=item.quantity_available,
                    correlation_id=correlation_id
                )
                
                result = inventory_response_schema.dump(item)
                return result, 200
                
            except ValidationError as e:
                return validation_error("Invalid request data", e.messages)
            except ValueError as e:
                return create_error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
            except Exception as e:
                logger.error(f"Error updating inventory: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

        @api.doc('delete_inventory')
        @require_admin
        def delete(self, identifier):
            """Delete inventory item (Admin only)"""
            try:
                inventory_service = InventoryService()
                success = inventory_service.delete_inventory_item(identifier)
                
                if not success:
                    return sku_not_found_error(identifier)
                
                # Return 204 No Content as per PRD
                return '', 204
                
            except Exception as e:
                logger.error(f"Error deleting inventory: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

@inventory_ns.route('/<string:identifier>/adjust')
class StockAdjustment(Resource):
        @api.doc('adjust_stock')
        @api.expect(stock_adjustment_model)
        @require_admin
        def post(self, identifier):
            """Adjust stock for inventory item (Admin only)"""
            try:
                # Validate request data
                data = stock_adjustment_schema.load(request.json)
                data['product_id'] = identifier  # Ensure consistency
                
                inventory_service = InventoryService()
                movement = inventory_service.adjust_stock(**data)
                
                if not movement:
                    return {'error': 'Failed to adjust stock'}, 400
                
                # Get updated inventory to publish event
                item = inventory_service.get_inventory_by_sku(identifier)
                if item:
                    correlation_id = getattr(g, 'correlation_id', None)
                    event_publisher.publish_stock_updated(
                        product_id=item.sku,  # Using SKU as identifier
                        quantity=item.quantity_available,
                        correlation_id=correlation_id
                    )
                    
                    # Check for low stock alert
                    if item.quantity_available <= item.reorder_level:
                        if item.quantity_available == 0:
                            event_publisher.publish_out_of_stock_alert(
                                product_id=item.sku,  # Using SKU as identifier
                                correlation_id=correlation_id
                            )
                        else:
                            event_publisher.publish_low_stock_alert(
                                product_id=item.sku,  # Using SKU as identifier
                                current_quantity=item.quantity_available,
                                threshold=item.reorder_level,
                                correlation_id=correlation_id
                            )
                
                result = stock_movement_schema.dump(movement)
                return result, 200
                
            except ValidationError as e:
                return {'error': 'Validation failed', 'details': e.messages}, 400
            except ValueError as e:
                return {'error': str(e)}, 400
            except Exception as e:
                logger.error(f"Error adjusting stock for product {identifier}: {e}")
                return {'error': 'Internal server error'}, 500

@inventory_ns.route('/check')
class CheckAvailability(Resource):
        @api.doc('check_stock_availability')
        def post(self):
            """Check stock availability for one or multiple items"""
            try:
                if not request.json:
                    return {'error': 'Request body required'}, 400
                
                # Support both single item {sku, quantity} and multiple items {items: [...]}
                if 'items' in request.json:
                    items = request.json['items']
                    if not isinstance(items, list) or not items:
                        return {'error': 'Items must be a non-empty array'}, 400
                elif 'sku' in request.json and 'quantity' in request.json:
                    # Single item - convert to array format
                    items = [{'sku': request.json['sku'], 'quantity': request.json['quantity']}]
                else:
                    return {'error': 'Request must contain either "items" array or "sku" and "quantity"'}, 400
                
                # Validate items format
                for item in items:
                    if not isinstance(item, dict) or 'sku' not in item or 'quantity' not in item:
                        return {'error': 'Each item must have sku and quantity'}, 400
                
                inventory_service = InventoryService()
                result = inventory_service.check_stock_availability(items)
                
                return result, 200
                
            except Exception as e:
                logger.error(f"Error checking stock availability: {e}")
                return {'error': 'Internal server error', 'details': str(e)}, 500

@inventory_ns.route('/batch')
class BatchInventoryRetrieval(Resource):
        @api.doc('batch_inventory_retrieval')
        def post(self):
            """Get inventory data for multiple SKUs (supports both base and variant SKUs)"""
            try:
                # Validate request has 'skus' array
                data = request.json
                if not data or 'skus' not in data:
                    return validation_error("Request must contain 'skus' array")
                
                skus = data['skus']
                if not isinstance(skus, list):
                    return validation_error("'skus' must be an array")
                
                # Check for inStockOnly filter from query params or request body
                in_stock_only = request.args.get('inStockOnly', 'false').lower() == 'true' or data.get('in_stock_only', False)
                
                # Use service method for business logic
                inventory_service = InventoryService()
                result = inventory_service.get_batch_inventory(skus, in_stock_only)
                
                return result, 200
                
            except Exception as e:
                logger.error(f"Error retrieving batch inventory: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)


# ============================================================================
# Stock Query Endpoints (per ARCHITECTURE.md Section 4.2.1-4.2.2)
# These are the primary endpoints for service-to-service stock queries
# ============================================================================

@stock_ns.route('/<string:sku>')
class StockQuery(Resource):
        @api.doc('query_stock_single')
        @require_service_token
        def get(self, sku):
            """Query stock for single SKU (Service Token required)
            
            Returns availability info for a single SKU.
            Used by Product Service and Order Service.
            
            Per ARCHITECTURE.md Section 4.2.1:
            - Endpoint: GET /api/inventory/stock/{sku}
            - Authentication: Service Token (X-Service-Token header)
            """
            try:
                inventory_service = InventoryService()
                item = inventory_service.get_inventory_by_sku(sku)
                
                if not item:
                    return sku_not_found_error(sku)
                
                # Return stock info in documented format
                return {
                    'sku': item.sku,
                    'quantity_available': item.quantity_available,
                    'quantity_reserved': item.quantity_reserved,
                    'in_stock': item.quantity_available > 0
                }, 200
                
            except Exception as e:
                logger.error(f"Error querying stock for SKU {sku}: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)


@stock_ns.route('/batch')
class StockBatchQuery(Resource):
        @api.doc('query_stock_batch')
        @require_service_token
        def post(self):
            """Query stock for multiple SKUs (Service Token required)
            
            Returns availability info for multiple SKUs in a single request.
            Used by Product Service and Cart Service for bulk checks.
            
            Per ARCHITECTURE.md Section 4.2.2:
            - Endpoint: POST /api/inventory/stock/batch
            - Authentication: Service Token (X-Service-Token header)
            """
            try:
                data = request.json
                if not data or 'skus' not in data:
                    return validation_error("Request must contain 'skus' array")
                
                skus = data['skus']
                if not isinstance(skus, list):
                    return validation_error("'skus' must be an array")
                
                if len(skus) > 50:
                    return validation_error("Maximum 50 SKUs per batch request")
                
                in_stock_only = data.get('in_stock_only', False)
                
                inventory_service = InventoryService()
                items = []
                not_found = []
                
                for sku in skus:
                    item = inventory_service.get_inventory_by_sku(sku)
                    if item:
                        is_in_stock = item.quantity_available > 0
                        if not in_stock_only or is_in_stock:
                            items.append({
                                'sku': item.sku,
                                'quantity_available': item.quantity_available,
                                'quantity_reserved': item.quantity_reserved,
                                'in_stock': is_in_stock
                            })
                    else:
                        not_found.append(sku)
                
                return {
                    'items': items,
                    'not_found': not_found
                }, 200
                
            except Exception as e:
                logger.error(f"Error querying batch stock: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)
