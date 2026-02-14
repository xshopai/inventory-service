"""
Reservation Model
"""

from src.database import db
from datetime import datetime, timezone
import uuid
from .enums import ReservationStatus


class Reservation(db.Model):
    """Stock reservation model"""
    __tablename__ = 'reservations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), nullable=False, index=True)
    sku = db.Column(db.String(100), db.ForeignKey('inventory_items.sku'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(ReservationStatus), default=ReservationStatus.PENDING, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<Reservation {self.id}>'
    
    @property
    def is_expired(self):
        """Check if reservation has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'sku': self.sku,
            'quantity': self.quantity,
            'status': self.status.value,
            'expires_at': self.expires_at.isoformat(),
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
