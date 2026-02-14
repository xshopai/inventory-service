"""
Stock Movement Model
"""

from src.database import db
from datetime import datetime, timezone
from .enums import StockMovementType


class StockMovement(db.Model):
    """Stock movement history model"""
    __tablename__ = 'stock_movements'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), db.ForeignKey('inventory_items.sku'), nullable=False)
    movement_type = db.Column(db.Enum(StockMovementType), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(255), nullable=True)  # Order ID, Restock ID, etc.
    reason = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(100), default='system', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<StockMovement {self.sku} {self.movement_type.value} {self.quantity}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'sku': self.sku,
            'movement_type': self.movement_type.value,
            'quantity': self.quantity,
            'reference': self.reference,
            'reason': self.reason,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }
