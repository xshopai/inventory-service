"""
Inventory Item Model
"""

from src.database import db
from datetime import datetime, timezone
from sqlalchemy import DECIMAL


class InventoryItem(db.Model):
    """Inventory item model"""
    __tablename__ = 'inventory_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    quantity_available = db.Column(db.Integer, default=0, nullable=False)
    quantity_reserved = db.Column(db.Integer, default=0, nullable=False)
    reorder_level = db.Column(db.Integer, default=10, nullable=False)
    max_stock = db.Column(db.Integer, default=1000, nullable=False)
    cost_per_unit = db.Column(DECIMAL(10, 2), default=0.0)
    last_restocked = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    reservations = db.relationship('Reservation', backref='inventory_item', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='inventory_item', lazy=True)
    
    def __repr__(self):
        return f'<InventoryItem {self.sku}>'
    
    @property
    def total_quantity(self):
        """Total quantity including reserved stock"""
        return self.quantity_available + self.quantity_reserved
    
    @property
    def is_low_stock(self):
        """Check if item is below reorder level"""
        return self.quantity_available <= self.reorder_level
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'sku': self.sku,
            'quantity_available': self.quantity_available,
            'quantity_reserved': self.quantity_reserved,
            'total_quantity': self.total_quantity,
            'reorder_level': self.reorder_level,
            'max_stock': self.max_stock,
            'cost_per_unit': float(self.cost_per_unit) if self.cost_per_unit else 0.0,
            'is_low_stock': self.is_low_stock,
            'last_restocked': self.last_restocked.isoformat() if self.last_restocked else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
