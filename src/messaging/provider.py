"""
Base Messaging Provider Interface
Architecture spec section 5.5.2
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class MessagingProvider(ABC):
    """
    Abstract base class for messaging providers.
    Enables deployment flexibility across different Azure hosting options.
    """
    
    @abstractmethod
    def publish_event(self, topic: str, event_data: Dict[str, Any], 
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish an event to the messaging infrastructure.
        
        Args:
            topic: Event topic/type (e.g., 'inventory.stock.updated')
            event_data: CloudEvents-compliant event payload
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self):
        """Clean up resources and close connections."""
        pass
