"""
Dapr Provider Implementation
Architecture spec section 5.5.2

For deployment to:
- Azure Container Apps (built-in Dapr)
- Azure Kubernetes Service (Dapr via Helm)
- Local development (Docker Compose with Dapr sidecar)
"""
from dapr.clients import DaprClient
import json
import logging
from typing import Dict, Any, Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


class DaprProvider(MessagingProvider):
    """
    Dapr-based messaging provider.
    Uses Dapr sidecar for pub/sub messaging.
    """
    
    def __init__(self, pubsub_name: str = "inventory-pubsub", 
                 dapr_http_port: Optional[int] = None):
        """
        Initialize Dapr provider.
        
        Args:
            pubsub_name: Name of Dapr pub/sub component
            dapr_http_port: Dapr sidecar HTTP port (default from env)
        """
        self.pubsub_name = pubsub_name
        self.dapr_http_port = dapr_http_port
        logger.info(f"Initialized DaprProvider with pubsub: {pubsub_name}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event via Dapr pub/sub.
        
        Args:
            topic: Event topic name
            event_data: CloudEvents payload
            correlation_id: Correlation ID for tracing
            
        Returns:
            bool: True if published successfully
        """
        try:
            # Create Dapr client with optional port override
            client_kwargs = {}
            if self.dapr_http_port:
                client_kwargs['http_port'] = self.dapr_http_port
            
            with DaprClient(**client_kwargs) as client:
                client.publish_event(
                    pubsub_name=self.pubsub_name,
                    topic_name=topic,
                    data=json.dumps(event_data),
                    data_content_type="application/json"
                )
            
            logger.info(
                f"Published event via Dapr: {topic}",
                extra={
                    "provider": "dapr",
                    "topic": topic,
                    "correlationId": correlation_id
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to publish event via Dapr: {topic} - {str(e)}",
                extra={
                    "provider": "dapr",
                    "topic": topic,
                    "error": str(e)
                }
            )
            return False
    
    def close(self):
        """Dapr client is context-managed, no cleanup needed."""
        pass
