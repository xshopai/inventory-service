"""
Inventory Repository Implementation
"""

from typing import List, Optional
from src.database import db
from src.models import InventoryItem, StockMovement, StockMovementType
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from .base import InventoryRepositoryInterface


class InventoryRepository(InventoryRepositoryInterface):
    """Concrete implementation of inventory repository"""
    
    def get_by_sku(self, sku: str) -> Optional[InventoryItem]:
        """Get inventory item by SKU"""
        return InventoryItem.query.filter_by(sku=sku).first()
    

    
    def get_multiple_by_skus(self, skus: List[str]) -> List[InventoryItem]:
        """Get multiple inventory items by SKUs"""
        return InventoryItem.query.filter(InventoryItem.sku.in_(skus)).all()
    
    def get_variants_by_base_sku(self, base_sku: str) -> List[InventoryItem]:
        """Get all variant inventory items matching base SKU pattern"""
        return InventoryItem.query.filter(InventoryItem.sku.like(f"{base_sku}-%")).all()
    
    def create(self, item: InventoryItem) -> InventoryItem:
        """Create new inventory item"""
        try:
            db.session.add(item)
            db.session.commit()
            return item
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Inventory item with SKU {item.sku} already exists")
    
    def update(self, item: InventoryItem) -> InventoryItem:
        """Update inventory item"""
        item.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return item
    
    def delete(self, sku: str) -> bool:
        """Delete inventory item by SKU"""
        try:
            item = self.get_by_sku(sku)
            if not item:
                return False
            
            db.session.delete(item)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update_stock(self, sku: str, quantity_change: int, movement_type: StockMovementType,
                    reference: str = None, reason: str = None, created_by: str = 'system') -> bool:
        """Update stock quantity and record movement"""
        try:
            # Get inventory item
            item = self.get_by_sku(sku)
            if not item:
                return False
            
            # Update quantities based on movement type
            if movement_type == StockMovementType.IN:
                item.quantity_available += quantity_change
            elif movement_type == StockMovementType.OUT:
                if item.quantity_available < quantity_change:
                    raise ValueError(f"Insufficient stock for SKU {sku}")
                item.quantity_available -= quantity_change
            elif movement_type == StockMovementType.RESERVED:
                if item.quantity_available < quantity_change:
                    raise ValueError(f"Insufficient stock to reserve for SKU {sku}")
                item.quantity_available -= quantity_change
                item.quantity_reserved += quantity_change
            elif movement_type == StockMovementType.RELEASED:
                item.quantity_reserved -= quantity_change
                item.quantity_available += quantity_change
            elif movement_type == StockMovementType.ADJUSTMENT:
                item.quantity_available = quantity_change  # Set to absolute value
            
            # Ensure quantities don't go negative
            if item.quantity_available < 0:
                item.quantity_available = 0
            if item.quantity_reserved < 0:
                item.quantity_reserved = 0
            
            # Record stock movement
            movement = StockMovement(
                sku=sku,
                movement_type=movement_type,
                quantity=quantity_change,
                reference=reference,
                reason=reason,
                created_by=created_by
            )
            db.session.add(movement)
            
            # Update timestamp
            item.updated_at = datetime.utcnow()
            if movement_type == StockMovementType.IN:
                item.last_restocked = datetime.utcnow()
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_low_stock_items(self) -> List[InventoryItem]:
        """Get items below reorder level"""
        return InventoryItem.query.filter(
            InventoryItem.quantity_available <= InventoryItem.reorder_level
        ).all()
    
    def search_inventory(self, query: str, limit: int = 20, offset: int = 0) -> List[InventoryItem]:
        """Search inventory items"""
        search_term = f"%{query}%"
        return InventoryItem.query.filter(
            or_(
                InventoryItem.sku.ilike(search_term)
            )
        ).limit(limit).offset(offset).all()

    def get_by_id(self, id: str) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        return InventoryItem.query.filter_by(id=id).first()

    def get_all(self, page: int = 1, per_page: int = 20) -> tuple[List[InventoryItem], int]:
        """Get all inventory items with pagination"""
        items = InventoryItem.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        return items.items, items.total

    def search(self, **kwargs) -> tuple[List[InventoryItem], int]:
        """Search inventory items with filters"""
        query = InventoryItem.query
        
        
        
        if 'low_stock' in kwargs and kwargs['low_stock']:
            query = query.filter(InventoryItem.quantity_available <= InventoryItem.reorder_level)
        
        if 'out_of_stock' in kwargs and kwargs['out_of_stock']:
            query = query.filter(InventoryItem.quantity_available == 0)
        
        total = query.count()
        page = kwargs.get('page', 1)
        per_page = kwargs.get('per_page', 20)
        
        items = query.paginate(page=page, per_page=per_page, error_out=False).items
        return items, total

    def bulk_update(self, updates: List[dict]) -> List[dict]:
        """Bulk update inventory items"""
        results = []
        for update in updates:
            try:
                item = self.get_by_sku(update['sku'])
                if item:
                    for key, value in update.items():
                        if key != 'sku' and hasattr(item, key):
                            setattr(item, key, value)
                    item.updated_at = datetime.utcnow()
                    results.append({'sku': update['sku'], 'success': True})
                else:
                    results.append({'sku': update['sku'], 'success': False, 'error': 'Item not found'})
            except Exception as e:
                results.append({'sku': update['sku'], 'success': False, 'error': str(e)})
        
        db.session.commit()
        return results

    def create_stock_movement(self, **kwargs) -> StockMovement:
        """Create stock movement record"""
        movement = StockMovement(
            sku=kwargs['sku'],
            movement_type=kwargs['movement_type'],
            quantity=kwargs['quantity'],
            reference=kwargs.get('reference'),
            reason=kwargs.get('reason'),
            created_by=kwargs.get('created_by', 'system')
        )
        db.session.add(movement)
        db.session.commit()
        return movement

    def get_stock_movements(self, sku: str) -> List[StockMovement]:
        """Get stock movements for a SKU"""
        return StockMovement.query.filter_by(sku=sku).order_by(StockMovement.created_at.desc()).all()

    def count_low_stock(self) -> int:
        """Count items below reorder level"""
        return InventoryItem.query.filter(
            InventoryItem.quantity_available < InventoryItem.reorder_level
        ).count()

    def count_out_of_stock(self) -> int:
        """Count items with zero quantity"""
        return InventoryItem.query.filter(
            InventoryItem.quantity_available == 0
        ).count()

    def count_products_with_stock(self) -> int:
        """Count items with quantity > 0"""
        return InventoryItem.query.filter(
            InventoryItem.quantity_available > 0
        ).count()

    def count_total(self) -> int:
        """Count total inventory items"""
        return InventoryItem.query.count()

    def calculate_total_value(self) -> float:
        """Calculate total inventory value (sum of quantity * cost_per_unit)"""
        from sqlalchemy import func
        result = db.session.query(
            func.sum(InventoryItem.quantity_available * InventoryItem.cost_per_unit)
        ).filter(
            InventoryItem.cost_per_unit.isnot(None)
        ).scalar()
        return float(result) if result else 0.0

    def calculate_total_units(self) -> int:
        """Calculate total units in inventory"""
        from sqlalchemy import func
        result = db.session.query(
            func.sum(InventoryItem.quantity_available)
        ).scalar()
        return int(result) if result else 0

    def get_recent_movements(self, limit: int = 10) -> List[StockMovement]:
        """Get recent stock movements"""
        return StockMovement.query.order_by(
            StockMovement.created_at.desc()
        ).limit(limit).all()
