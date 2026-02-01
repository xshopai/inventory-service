"""
Dapr Provider Implementation
Architecture spec section 5.5.2

For deployment to:
- Azure Container Apps (built-in Dapr)
- Azure Kubernetes Service (Dapr via Helm)
- Local development (Docker Compose with Dapr sidecar)
"""
import json
import logging
import os
import requests
from typing import Dict, Any, Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


class DaprProvider(MessagingProvider):
    """
    Dapr-based messaging provider.
    Uses Dapr sidecar for pub/sub messaging via HTTP API.
    """
    
    def __init__(self, pubsub_name: str = "pubsub", 
                 dapr_http_port: Optional[int] = None):
        """
        Initialize Dapr provider.
        
        Args:
            pubsub_name: Name of Dapr pub/sub component (default: pubsub)
            dapr_http_port: Dapr sidecar HTTP port (optional, defaults to DAPR_HTTP_PORT env var or 3500)
        """
        self.pubsub_name = pubsub_name
        self.dapr_http_port = dapr_http_port or int(os.environ.get('DAPR_HTTP_PORT', 3500))
        self.dapr_base_url = f"http://localhost:{self.dapr_http_port}"
        logger.info(f"Initialized DaprProvider with pubsub: {pubsub_name}, HTTP port: {self.dapr_http_port}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event via Dapr pub/sub HTTP API.
        
        Uses the Dapr HTTP API to publish events to the configured pub/sub component.
        The Dapr sidecar handles routing to the actual message broker (Service Bus, RabbitMQ, etc.)
        
        Args:
            topic: Event topic name (e.g., 'inventory.stock.updated')
            event_data: CloudEvents-compliant payload with spec, type, data, etc.
            correlation_id: Correlation ID for distributed tracing
            
        Returns:
            bool: True if published successfully, False on error
        """
        try:
            # Dapr Pub/Sub HTTP API endpoint
            # https://docs.dapr.io/reference/api/pubsub_api/#publish-a-message-to-a-given-topic
            url = f"{self.dapr_base_url}/v1.0/publish/{self.pubsub_name}/{topic}"
            
            # Publish via HTTP POST
            response = requests.post(
                url,
                json=event_data,
                headers={
                    "Content-Type": "application/json",
                    "traceparent": correlation_id or ""
                },
                timeout=5
            )
            
            if response.status_code in (200, 204):
                logger.info(
                    f"Published event via Dapr HTTP: {topic}",
                    extra={
                        "provider": "dapr-http",
                        "topic": topic,
                        "correlationId": correlation_id
                    }
                )
                return True
            else:
                logger.error(
                    f"Dapr HTTP publish failed: {topic} - Status: {response.status_code}, Response: {response.text}",
                    extra={
                        "provider": "dapr-http",
                        "topic": topic,
                        "status_code": response.status_code
                    }
                )
                return False
            
        except Exception as e:
            # Log error but don't raise - allows service to continue
            logger.error(
                f"Failed to publish event via Dapr HTTP: {topic} - {str(e)}",
                extra={
                    "provider": "dapr-http",
                    "topic": topic,
                    "error": str(e)
                }
            )
            return False
    
    def close(self):
        """
        HTTP-based provider, no cleanup needed.
        """
        pass
