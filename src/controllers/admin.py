"""
Admin Controller - Handles admin-only inventory operations
Per standardization: All admin endpoints use /api/admin/inventory prefix
"""

from flask import Blueprint, request, g
from flask_restx import Api, Resource, fields
from marshmallow import ValidationError
from src.services import InventoryService
from src.middlewares.auth import require_admin
from src.utils.schemas import (
    InventoryItemRequestSchema, InventoryItemResponseSchema,
    StockAdjustmentRequestSchema, StockMovementResponseSchema,
    InventorySearchSchema, ReservationResponseSchema
)
from src.utils.event_publisher import event_publisher
from src.utils.error_codes import (
    sku_not_found_error, validation_error, create_error_response, ErrorCode
)
import logging

logger = logging.getLogger(__name__)

# Create blueprint for admin operations
admin_bp = Blueprint('admin', __name__)
admin_api = Api(admin_bp, version='1.0', title='Inventory Admin API',
                description='Admin-only inventory management endpoints', doc='/docs/')

# Create namespaces
admin_inventory_ns = admin_api.namespace('inventory', description='Admin inventory operations')
admin_reservations_ns = admin_api.namespace('inventory/reservations', description='Admin reservation operations')

# Initialize schemas
inventory_request_schema = InventoryItemRequestSchema()
inventory_response_schema = InventoryItemResponseSchema()
stock_adjustment_schema = StockAdjustmentRequestSchema()
stock_movement_schema = StockMovementResponseSchema()
search_schema = InventorySearchSchema()
reservation_response_schema = ReservationResponseSchema()


def get_inventory_models(api):
    """Define API models for inventory operations"""
    inventory_item_model = api.model('InventoryItem', {
        'id': fields.Integer(description='Inventory item ID'),
        'sku': fields.String(required=True, description='Stock Keeping Unit - unique product variant identifier'),
        'quantity_available': fields.Integer(required=True, description='Available quantity'),
        'quantity_reserved': fields.Integer(description='Reserved quantity'),
        'total_quantity': fields.Integer(description='Total quantity (available + reserved)'),
        'reorder_level': fields.Integer(description='Reorder threshold level'),
        'max_stock': fields.Integer(description='Maximum stock level'),
        'cost_per_unit': fields.Float(description='Cost per unit'),
        'is_low_stock': fields.Boolean(description='Whether stock is below reorder level'),
        'last_restocked': fields.DateTime(description='Last restock timestamp'),
        'created_at': fields.DateTime(description='Creation timestamp'),
        'updated_at': fields.DateTime(description='Last update timestamp')
    })

    stock_adjustment_model = api.model('StockAdjustment', {
        'sku': fields.String(required=True, description='Stock Keeping Unit'),
        'quantity': fields.Integer(required=True, description='Adjustment quantity'),
        'movement_type': fields.String(required=True, description='Movement type'),
        'reference_id': fields.String(description='Reference identifier'),
        'notes': fields.String(description='Additional notes')
    })

    reservation_model = api.model('Reservation', {
        'id': fields.Integer(description='Reservation ID'),
        'sku': fields.String(description='SKU'),
        'quantity': fields.Integer(description='Reserved quantity'),
        'customer_id': fields.String(description='Customer ID'),
        'order_id': fields.String(description='Order ID'),
        'status': fields.String(description='Reservation status'),
        'expires_at': fields.DateTime(description='Expiration time'),
        'created_at': fields.DateTime(description='Creation timestamp')
    })

    return inventory_item_model, stock_adjustment_model, reservation_model


# Define models
inventory_item_model, stock_adjustment_model, reservation_model = get_inventory_models(admin_api)


# ============================================================================
# Admin Inventory Endpoints
# All endpoints require admin authentication
# ============================================================================

@admin_inventory_ns.route('/')
class AdminInventoryList(Resource):
    @admin_api.doc('list_inventory')
    @admin_api.marshal_list_with(inventory_item_model)
    @require_admin
    def get(self):
        """Get all inventory items with optional filtering (Admin only)
        
        GET /api/admin/inventory/
        """
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

    @admin_api.doc('create_inventory')
    @admin_api.expect(inventory_item_model)
    @require_admin
    def post(self):
        """Create new inventory item (Admin only)
        
        POST /api/admin/inventory/
        """
        try:
            # Validate request data
            data = inventory_request_schema.load(request.json)
            
            inventory_service = InventoryService()
            item = inventory_service.create_inventory_item(**data)
            
            # Publish inventory.created event
            correlation_id = getattr(g, 'correlation_id', None)
            event_publisher.publish_inventory_created(
                sku=item.sku,
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


@admin_inventory_ns.route('/<string:identifier>')
class AdminInventoryItem(Resource):
    @admin_api.doc('get_inventory')
    @require_admin
    def get(self, identifier):
        """Get inventory item by SKU (Admin only)
        
        GET /api/admin/inventory/<identifier>
        """
        try:
            inventory_service = InventoryService()
            item = inventory_service.get_inventory_by_sku(identifier)
            
            if not item:
                return sku_not_found_error(identifier)
            
            result = inventory_response_schema.dump(item)
            return result, 200
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)
    
    @admin_api.doc('update_inventory')
    @admin_api.expect(inventory_item_model)
    @require_admin
    def put(self, identifier):
        """Update inventory item (Admin only) - PRD 4.15
        
        PUT /api/admin/inventory/<identifier>
        """
        try:
            # Validate request data
            data = inventory_request_schema.load(request.json)
            
            inventory_service = InventoryService()
            item = inventory_service.update_inventory_item(identifier, **data)
            
            # Publish inventory.stock.updated event (PRD 4.18)
            correlation_id = getattr(g, 'correlation_id', None)
            event_publisher.publish_stock_updated(
                sku=item['sku'],
                quantity=item['quantity_available'],
                correlation_id=correlation_id
            )
            
            result = inventory_response_schema.dump(item)
            return result, 200
            
        except ValidationError as e:
            return {'error': 'Validation failed', 'details': e.messages}, 400
        except ValueError as e:
            return {'error': str(e)}, 404
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)
    
    @admin_api.doc('delete_inventory')
    @require_admin
    def delete(self, identifier):
        """Delete inventory item (Admin only)
        
        DELETE /api/admin/inventory/<identifier>
        """
        try:
            inventory_service = InventoryService()
            
            # Get item before deleting for event publishing
            item = inventory_service.get_inventory_by_sku(identifier)
            
            success = inventory_service.delete_inventory_item(identifier)
            
            if not success:
                return sku_not_found_error(identifier)
            
            # Publish inventory.stock.updated event (PRD 4.18)
            if item:
                correlation_id = getattr(g, 'correlation_id', None)
                event_publisher.publish_stock_updated(
                    sku=identifier,
                    quantity=0,  # Deleted items have 0 available
                    correlation_id=correlation_id
                )
            
            # Return 204 No Content as per PRD
            return '', 204
            
        except Exception as e:
            logger.error(f"Error deleting inventory: {e}")
            return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)


@admin_inventory_ns.route('/<string:identifier>/adjust')
class AdminStockAdjustment(Resource):
    @admin_api.doc('adjust_stock')
    @admin_api.expect(stock_adjustment_model)
    @require_admin
    def post(self, identifier):
        """Adjust stock for inventory item (Admin only)
        
        POST /api/admin/inventory/<identifier>/adjust
        """
        try:
            # Validate request data
            data = stock_adjustment_schema.load(request.json)
            data['sku'] = identifier  # Ensure consistency
            
            inventory_service = InventoryService()
            movement = inventory_service.adjust_stock(**data)
            
            if not movement:
                return {'error': 'Failed to adjust stock'}, 400
            
            # Get updated inventory to publish event
            item = inventory_service.get_inventory_by_sku(identifier)
            if item:
                correlation_id = getattr(g, 'correlation_id', None)
                event_publisher.publish_stock_updated(
                    sku=item.sku,
                    quantity=item.quantity_available,
                    correlation_id=correlation_id
                )
                
                # Check for low stock alert
                if item.quantity_available <= item.reorder_level:
                    if item.quantity_available == 0:
                        event_publisher.publish_out_of_stock_alert(
                            sku=item.sku,
                            correlation_id=correlation_id
                        )
                    else:
                        event_publisher.publish_low_stock_alert(
                            sku=item.sku,
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


# ============================================================================
# Admin Reservation Endpoints
# ============================================================================

@admin_reservations_ns.route('/')
class AdminReservationList(Resource):
    @admin_api.doc('list_reservations')
    @admin_api.marshal_list_with(reservation_model)
    @require_admin
    def get(self):
        """Get all reservations with optional filtering (Admin only)
        
        GET /api/admin/inventory/reservations/
        """
        try:
            # Get query parameters
            customer_id = request.args.get('customer_id')
            order_id = request.args.get('order_id')
            status = request.args.get('status')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            inventory_service = InventoryService()
            reservations, total = inventory_service.search_reservations(
                customer_id=customer_id,
                order_id=order_id,
                status=status,
                page=page,
                per_page=per_page
            )
            
            result = reservation_response_schema.dump(reservations, many=True)
            
            return {
                'items': result,
                'pagination': {
                    'page': page,
                    'limit': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error listing reservations: {e}")
            return {'error': 'Internal server error'}, 500
