"""
Event Publisher for Inventory Service
Uses Messaging Abstraction Layer per Architecture spec section 5.5
"""
import os
from flask import current_app
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Import trace context for W3C Trace Context support
from src.middlewares.trace_context import get_trace_id
from src.messaging import create_messaging_provider, MessagingProvider


class InventoryEventPublisher:
    """
    Event publisher for inventory-related events.
    Uses messaging abstraction layer for deployment flexibility.
    """
    
    def __init__(self):
        self.service_name = os.environ.get('SERVICE_NAME', 'inventory-service')
        self.service_version = os.environ.get('VERSION', '1.0.0')
        self._provider: Optional[MessagingProvider] = None
    
    @property
    def provider(self) -> MessagingProvider:
        """Lazy initialization of messaging provider."""
        if self._provider is None:
            self._provider = create_messaging_provider()
        return self._provider
    
    def _build_event_payload(self, event_type: str, data: Dict[str, Any], 
                            correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Build CloudEvents-compliant event payload"""
        return {
            "specversion": "1.0",
            "type": event_type,
            "source": self.service_name,
            "id": str(uuid.uuid4()),
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": data,
            "correlationId": correlation_id or str(uuid.uuid4())
        }
    
    def publish_event(self, event_type: str, data: Dict[str, Any], 
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event via messaging abstraction layer.
        
        Args:
            event_type: Event type/topic name (e.g., 'inventory.stock.updated')
            data: Event payload data
            correlation_id: Optional correlation ID for tracing (defaults to current trace_id)
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Use trace_id from context if correlation_id not provided
            if correlation_id is None:
                correlation_id = get_trace_id()
            
            event_payload = self._build_event_payload(event_type, data, correlation_id)
            
            # Publish via abstraction layer
            success = self.provider.publish_event(
                topic=event_type,
                event_data=event_payload,
                correlation_id=correlation_id
            )
            
            if success:
                current_app.logger.info(
                    f"✅ Published event: {event_type}",
                    extra={
                        "eventType": event_type,
                        "correlationId": correlation_id,
                        "service": self.service_name
                    }
                )
            
            return success
            
        except Exception as e:
            current_app.logger.error(
                f"❌ Failed to publish event: {event_type} - {str(e)}",
                extra={
                    "eventType": event_type,
                    "error": str(e),
                    "correlationId": correlation_id
                }
            )
            return False
    
    # =========================================================================
    # Inventory Stock Events
    # =========================================================================
    
    def publish_stock_updated(self, sku: str, quantity: int, 
                             warehouse: str = "default",
                             correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.stock.updated event"""
        data = {
            "sku": sku,
            "quantity": quantity,
            "warehouse": warehouse,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.stock.updated", data, correlation_id)
    
    def publish_stock_reserved(self, sku: str, quantity: int, 
                              order_id: str, reservation_id: str,
                              correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.stock.reserved event"""
        data = {
            "sku": sku,
            "quantity": quantity,
            "orderId": order_id,
            "reservationId": reservation_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.stock.reserved", data, correlation_id)
    
    def publish_stock_released(self, sku: str, quantity: int,
                              order_id: str, reason: str,
                              correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.stock.released event"""
        data = {
            "sku": sku,
            "quantity": quantity,
            "orderId": order_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.stock.released", data, correlation_id)
    
    def publish_low_stock_alert(self, sku: str, current_quantity: int,
                               threshold: int, correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.low.stock event"""
        data = {
            "sku": sku,
            "currentQuantity": current_quantity,
            "threshold": threshold,
            "severity": "warning",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.low.stock", data, correlation_id)
    
    def publish_out_of_stock_alert(self, sku: str, 
                                   correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.out.of.stock event"""
        data = {
            "sku": sku,
            "severity": "critical",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.out.of.stock", data, correlation_id)
    
    def publish_inventory_created(self, sku: str, initial_quantity: int,
                                 correlation_id: Optional[str] = None) -> bool:
        """Publish inventory.created event"""
        data = {
            "sku": sku,
            "initialQuantity": initial_quantity,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return self.publish_event("inventory.created", data, correlation_id)


# Global singleton instance
event_publisher = InventoryEventPublisher()
