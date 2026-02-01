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
import os
from typing import Dict, Any, Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


class DaprProvider(MessagingProvider):
    """
    Dapr-based messaging provider.
    Uses Dapr sidecar for pub/sub messaging.
    """
    
    def __init__(self, pubsub_name: str = "pubsub", 
                 dapr_http_port: Optional[int] = None):
        """
        Initialize Dapr provider.
        
        Args:
            pubsub_name: Name of Dapr pub/sub component (default: pubsub)
            dapr_http_port: Dapr sidecar HTTP port (optional, sets DAPR_HTTP_PORT env var if provided)
        """
        self.pubsub_name = pubsub_name
        # DaprClient reads from environment variables, so set them if a port is provided
        if dapr_http_port:
            os.environ['DAPR_HTTP_PORT'] = str(dapr_http_port)
        logger.info(f"Initialized DaprProvider with pubsub: {pubsub_name}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event via Dapr pub/sub.
        
        Uses the Dapr SDK to publish events to the configured pub/sub component.
        The Dapr sidecar handles routing to the actual message broker (RabbitMQ, etc.)
        
        Args:
            topic: Event topic name (e.g., 'inventory.stock.updated')
            event_data: CloudEvents-compliant payload with spec, type, data, etc.
            correlation_id: Correlation ID for distributed tracing
            
        Returns:
            bool: True if published successfully, False on error
        """
        try:
            # DaprClient uses environment variables for configuration:
            # - DAPR_GRPC_ENDPOINT or DAPR_RUNTIME_HOST + DAPR_GRPC_PORT (for gRPC)
            # - DAPR_HTTP_ENDPOINT or DAPR_RUNTIME_HOST + DAPR_HTTP_PORT (for HTTP)
            # In Azure Container Apps, Dapr sidecar is at localhost:3500 (HTTP) / localhost:50001 (gRPC)
            with DaprClient() as client:
                # Publish event to Dapr pub/sub component
                client.publish_event(
                    pubsub_name=self.pubsub_name,  # Component name from config
                    topic_name=topic,               # Event topic/routing key
                    data=json.dumps(event_data),    # Serialized CloudEvents payload
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
            # Log error but don't raise - allows service to continue
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
        """
        Dapr client is context-managed, no cleanup needed.
        Connection is automatically closed when exiting the context manager.
        """
        pass
