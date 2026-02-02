from marshmallow import Schema, fields, validate, post_load, ValidationError
from datetime import datetime
from src.models import StockMovementType


class InventoryItemRequestSchema(Schema):
    """Schema for creating inventory items (SKU required)"""
    sku = fields.Str(required=True, validate=validate.Length(min=1))
    quantity_available = fields.Int(required=True, validate=validate.Range(min=0))
    quantity_reserved = fields.Int(validate=validate.Range(min=0), load_default=0)
    reorder_level = fields.Int(validate=validate.Range(min=0), load_default=10)
    max_stock = fields.Int(validate=validate.Range(min=0), allow_none=True)
    cost_per_unit = fields.Float(validate=validate.Range(min=0), allow_none=True)
    
    @post_load
    def validate_stock_levels(self, data, **kwargs):
        if (data.get('max_stock') and 
            data.get('reorder_level') > data.get('max_stock')):
            raise ValidationError('Reorder level cannot exceed maximum stock')
        
        if data.get('quantity_reserved', 0) > data.get('quantity_available', 0):
            raise ValidationError('Reserved quantity cannot exceed available quantity')
        
        return data


class InventoryItemUpdateSchema(Schema):
    """Schema for updating inventory items (SKU comes from URL path)"""
    quantity_available = fields.Int(required=True, validate=validate.Range(min=0))
    quantity_reserved = fields.Int(validate=validate.Range(min=0))
    reorder_level = fields.Int(validate=validate.Range(min=0))
    max_stock = fields.Int(validate=validate.Range(min=0), allow_none=True)
    cost_per_unit = fields.Float(validate=validate.Range(min=0), allow_none=True)
    
    @post_load
    def validate_stock_levels(self, data, **kwargs):
        if (data.get('max_stock') and data.get('reorder_level') and
            data.get('reorder_level') > data.get('max_stock')):
            raise ValidationError('Reorder level cannot exceed maximum stock')
        
        if (data.get('quantity_reserved') is not None and 
            data.get('quantity_available') is not None and
            data.get('quantity_reserved') > data.get('quantity_available')):
            raise ValidationError('Reserved quantity cannot exceed available quantity')
        
        return data


class InventoryItemResponseSchema(Schema):
    """Schema for inventory item responses"""
    id = fields.Int(dump_only=True)
    sku = fields.Str()
    quantity_available = fields.Int()
    quantity_reserved = fields.Int()
    total_quantity = fields.Int(dump_only=True)
    reorder_level = fields.Int()
    max_stock = fields.Int(allow_none=True)
    cost_per_unit = fields.Float(allow_none=True)
    is_low_stock = fields.Boolean(dump_only=True)
    last_restocked = fields.Str(allow_none=True)  # Already converted to ISO string
    created_at = fields.Str(dump_only=True)  # Already converted to ISO string
    updated_at = fields.Str(dump_only=True)  # Already converted to ISO string


class ReservationRequestSchema(Schema):
    """Schema for creating reservations"""
    sku = fields.Str(required=True, validate=validate.Length(min=1))
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    customer_id = fields.Str(required=True, validate=validate.Length(min=1))
    order_id = fields.Str(required=True, validate=validate.Length(min=1))
    expires_at = fields.DateTime(allow_none=True)
    notes = fields.Str(validate=validate.Length(max=500), allow_none=True)


class ReservationResponseSchema(Schema):
    """Schema for reservation responses"""
    id = fields.Int(dump_only=True)
    inventory_item_id = fields.Int()
    sku = fields.Str()
    quantity = fields.Int()
    customer_id = fields.Str()
    order_id = fields.Str()
    status = fields.Str()
    expires_at = fields.DateTime(allow_none=True)
    notes = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class StockAdjustmentRequestSchema(Schema):
    """Schema for stock adjustments"""
    sku = fields.Str(required=True, validate=validate.Length(min=1))
    quantity = fields.Int(required=True)
    movement_type = fields.Str(
        required=True, 
        validate=validate.OneOf([mt.value for mt in StockMovementType])
    )
    reference_id = fields.Str(validate=validate.Length(min=1), allow_none=True)
    notes = fields.Str(validate=validate.Length(max=500), allow_none=True)


class StockMovementResponseSchema(Schema):
    """Schema for stock movement responses"""
    id = fields.Int(dump_only=True)
    inventory_item_id = fields.Int()
    sku = fields.Str()
    movement_type = fields.Str()
    quantity = fields.Int()
    reference_id = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class BulkOperationRequestSchema(Schema):
    """Schema for bulk operations"""
    operations = fields.List(fields.Dict(), required=True, validate=validate.Length(min=1))
    
    @post_load
    def validate_operations(self, data, **kwargs):
        operations = data.get('operations', [])
        if len(operations) > 100:
            raise ValidationError('Maximum 100 operations allowed per request')
        
        required_fields = {'sku', 'quantity'}
        for i, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise ValidationError(f'Operation {i} must be a dictionary')
            
            missing_fields = required_fields - set(operation.keys())
            if missing_fields:
                raise ValidationError(f'Operation {i} missing fields: {missing_fields}')
        
        return data


class InventorySearchSchema(Schema):
    """Schema for inventory search parameters"""
    skus = fields.List(fields.Str(), validate=validate.Length(min=1))
    location = fields.Str(validate=validate.Length(min=1))
    low_stock = fields.Bool()
    out_of_stock = fields.Bool()
    has_reservations = fields.Bool()
    page = fields.Int(validate=validate.Range(min=1), load_default=1)
    per_page = fields.Int(validate=validate.Range(min=1, max=100), load_default=20)
    
    @post_load
    def validate_search_params(self, data, **kwargs):
        # Ensure at least one search criterion is provided
        search_fields = ['skus', 'location', 'low_stock', 'out_of_stock', 'has_reservations']
        if not any(data.get(field) for field in search_fields):
            raise ValidationError('At least one search criterion must be provided')
        
        return data


class ReservationConfirmRequestSchema(Schema):
    """Schema for confirming reservations"""
    reservation_ids = fields.List(
        fields.Int(validate=validate.Range(min=1)), 
        required=True, 
        validate=validate.Length(min=1, max=50)
    )
    order_id = fields.Str(required=True, validate=validate.Length(min=1))


class HealthCheckResponseSchema(Schema):
    """Schema for health check responses"""
    status = fields.Str()
    timestamp = fields.DateTime()
    database = fields.Dict()
    redis = fields.Dict()
    external_services = fields.Dict()
