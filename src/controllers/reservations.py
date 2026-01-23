"""
Reservations Controller - Handles inventory reservation operations
"""

from flask import Blueprint, request
from flask_restx import Api, Resource, fields
from marshmallow import ValidationError
from src.services import InventoryService
from src.utils.schemas import (
    ReservationRequestSchema, ReservationResponseSchema,
    ReservationConfirmRequestSchema
)
from src.utils.error_codes import (
    reservation_not_found_error, insufficient_stock_error,
    validation_error, create_error_response, ErrorCode
)
import logging

logger = logging.getLogger(__name__)

# Create blueprint
reservations_bp = Blueprint('reservations', __name__)
api = Api(reservations_bp, version='1.0', title='Reservations API',
          description='Inventory reservation endpoints', doc='/docs/')

# Create namespace
reservations_ns = api.namespace('reservations', description='Reservation operations')

# Initialize schemas
reservation_request_schema = ReservationRequestSchema()
reservation_response_schema = ReservationResponseSchema()
reservation_confirm_schema = ReservationConfirmRequestSchema()


def get_reservation_models(api):
    """Define API models for reservation operations"""
    reservation_model = api.model('Reservation', {
        'id': fields.Integer(description='Reservation ID'),
        'product_id': fields.String(required=True, description='Product identifier'),
        'quantity': fields.Integer(required=True, description='Reserved quantity'),
        'customer_id': fields.String(required=True, description='Customer identifier'),
        'order_id': fields.String(required=True, description='Order identifier'),
        'status': fields.String(description='Reservation status'),
        'expires_at': fields.DateTime(description='Expiration timestamp'),
        'notes': fields.String(description='Additional notes'),
        'created_at': fields.DateTime(description='Creation timestamp'),
        'updated_at': fields.DateTime(description='Last update timestamp')
    })

    return reservation_model


# Define models
reservation_model = get_reservation_models(api)

# Register routes
@reservations_ns.route('/')
class ReservationList(Resource):
        @api.doc('list_reservations')
        @api.marshal_list_with(reservation_model)
        def get(self):
            """Get all reservations with optional filtering"""
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
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }, 200
                
            except Exception as e:
                logger.error(f"Error listing reservations: {e}")
                return {'error': 'Internal server error'}, 500

        @api.doc('create_reservation')
        @api.expect(reservation_model)
        @api.marshal_with(reservation_model)
        def post(self):
            """Create new reservation"""
            try:
                # Validate request data
                data = reservation_request_schema.load(request.json)
                
                inventory_service = InventoryService()
                reservation = inventory_service.create_reservation(**data)
                
                if not reservation:
                    # Get SKU from request to provide better error
                    sku = data.get('sku', 'unknown')
                    return insufficient_stock_error(sku, data.get('quantity', 0), 0)
                
                result = reservation_response_schema.dump(reservation)
                return result, 201
                
            except ValidationError as e:
                return validation_error("Invalid request data", e.messages)
            except ValueError as e:
                return create_error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
            except Exception as e:
                logger.error(f"Error creating reservation: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

@reservations_ns.route('/<string:reservation_id>')
class Reservation(Resource):
        @api.doc('get_reservation')
        @api.marshal_with(reservation_model)
        def get(self, reservation_id):
            """Get reservation by ID"""
            try:
                inventory_service = InventoryService()
                reservation = inventory_service.get_reservation(reservation_id)
                
                if not reservation:
                    return reservation_not_found_error(reservation_id)
                
                result = reservation_response_schema.dump(reservation)
                return result, 200
                
            except Exception as e:
                logger.error(f"Error getting reservation {reservation_id}: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

        @api.doc('cancel_reservation')
        def delete(self, reservation_id):
            """Cancel reservation"""
            try:
                inventory_service = InventoryService()
                success = inventory_service.cancel_reservation(reservation_id)
                
                if not success:
                    return reservation_not_found_error(reservation_id)
                
                return {'message': 'Reservation cancelled successfully'}, 200
                
            except Exception as e:
                logger.error(f"Error cancelling reservation {reservation_id}: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

@reservations_ns.route('/<string:reservation_id>/confirm')
class ReservationConfirmSingle(Resource):
        @api.doc('confirm_reservation')
        def post(self, reservation_id):
            """Confirm a single reservation (PRD 4.8)"""
            try:
                # Get order_id from request body if provided
                data = request.json or {}
                order_id = data.get('order_id')
                
                # If order_id not in body, try to get it from the reservation itself
                if not order_id:
                    inventory_service = InventoryService()
                    reservation = inventory_service.get_reservation(reservation_id)
                    if reservation:
                        order_id = reservation.get('order_id')
                
                if not order_id:
                    return validation_error("order_id is required")
                
                inventory_service = InventoryService()
                success = inventory_service.confirm_reservation(reservation_id, order_id)
                
                if not success:
                    return reservation_not_found_error(reservation_id)
                
                return {'message': 'Reservation confirmed successfully', 'reservation_id': reservation_id}, 200
                
            except ValueError as e:
                return create_error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
            except Exception as e:
                logger.error(f"Error confirming reservation {reservation_id}: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

@reservations_ns.route('/<string:reservation_id>/release')
class ReservationRelease(Resource):
        @api.doc('release_reservation')
        def post(self, reservation_id):
            """Release a reservation - restores reserved quantity back to available (PRD 4.9)"""
            try:
                inventory_service = InventoryService()
                reservation = inventory_service.release_reservation(reservation_id)
                
                if not reservation:
                    return reservation_not_found_error(reservation_id)
                
                return {
                    'message': 'Reservation released successfully',
                    'reservation': reservation
                }, 200
                
            except ValueError as e:
                return create_error_response(ErrorCode.VALIDATION_ERROR, str(e), status_code=400)
            except Exception as e:
                logger.error(f"Error releasing reservation {reservation_id}: {e}")
                return create_error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", status_code=500)

@reservations_ns.route('/confirm')
class ReservationConfirm(Resource):
        @api.doc('confirm_reservations')
        def post(self):
            """Confirm multiple reservations"""
            try:
                # Validate request data
                data = reservation_confirm_schema.load(request.json)
                
                inventory_service = InventoryService()
                results = inventory_service.confirm_reservations(
                    data['reservation_ids'], 
                    data['order_id']
                )
                
                return {'results': results}, 200
                
            except ValidationError as e:
                return {'error': 'Validation failed', 'details': e.messages}, 400
            except Exception as e:
                logger.error(f"Error confirming reservations: {e}")
                return {'error': 'Internal server error'}, 500
