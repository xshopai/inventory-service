"""
Azure Service Bus Provider Implementation
Architecture spec section 5.5.2

For deployment to:
- Azure App Service (no Dapr sidecar available)
"""
import json
import logging
from typing import Dict, Any, Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


class ServiceBusProvider(MessagingProvider):
    """
    Azure Service Bus provider for App Service deployments.
    Uses Azure Service Bus SDK directly (no Dapr sidecar).
    
    Note: Requires azure-servicebus package to be installed.
    """
    
    def __init__(self, connection_string: str, topic_name: str):
        """
        Initialize Service Bus provider.
        
        Args:
            connection_string: Azure Service Bus connection string
            topic_name: Service Bus topic name
        """
        self.connection_string = connection_string
        self.topic_name = topic_name
        self.client = None
        
        logger.info(f"Initialized ServiceBusProvider with topic: {topic_name}")
        
        # Lazy initialization - client created on first publish
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Service Bus client."""
        try:
            # Import here to avoid dependency if not using Service Bus
            from azure.servicebus import ServiceBusClient
            self.client = ServiceBusClient.from_connection_string(
                self.connection_string
            )
            logger.info("Service Bus client initialized successfully")
        except ImportError:
            logger.warning(
                "azure-servicebus package not installed. "
                "Install with: pip install azure-servicebus"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Service Bus client: {e}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event to Azure Service Bus.
        
        Args:
            topic: Event topic (used as message label/subject)
            event_data: CloudEvents payload
            correlation_id: Correlation ID for tracing
            
        Returns:
            bool: True if published successfully
        """
        try:
            if not self.client:
                logger.error("Service Bus client not initialized")
                return False
            
            # Import here to avoid dependency if not using Service Bus
            from azure.servicebus import ServiceBusMessage
            
            # Create message with CloudEvents payload
            message = ServiceBusMessage(
                json.dumps(event_data),
                content_type="application/json",
                subject=topic,  # Event type as subject
                correlation_id=correlation_id
            )
            
            # Send message to topic
            with self.client.get_topic_sender(self.topic_name) as sender:
                sender.send_messages(message)
            
            logger.info(
                f"Published event via Service Bus: {topic}",
                extra={
                    "provider": "servicebus",
                    "topic": topic,
                    "correlationId": correlation_id
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to publish event via Service Bus: {topic} - {str(e)}",
                extra={
                    "provider": "servicebus",
                    "topic": topic,
                    "error": str(e)
                }
            )
            return False
    
    def close(self):
        """Close Service Bus client."""
        if self.client:
            try:
                self.client.close()
                logger.info("Service Bus client closed")
            except Exception as e:
                logger.error(f"Error closing Service Bus client: {e}")
