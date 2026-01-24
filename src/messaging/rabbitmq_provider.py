"""
RabbitMQ Provider Implementation
Architecture spec section 5.5.2

For deployment to:
- Local development without Dapr
- Direct RabbitMQ integration scenarios
"""
import json
import logging
from typing import Dict, Any, Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


class RabbitMQProvider(MessagingProvider):
    """
    Direct RabbitMQ provider for local development.
    Uses pika library to connect to RabbitMQ directly.
    
    Note: Requires pika package to be installed.
    """
    
    def __init__(self, rabbitmq_url: str, exchange: str = "inventory-events"):
        """
        Initialize RabbitMQ provider.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
            exchange: Exchange name for event publishing
        """
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.connection = None
        self.channel = None
        
        logger.info(f"Initialized RabbitMQProvider with exchange: {exchange}")
        
        # Lazy initialization - connection created on first publish
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize RabbitMQ connection."""
        try:
            # Import here to avoid dependency if not using RabbitMQ
            import pika
            
            # Parse connection URL and create connection
            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info("RabbitMQ connection initialized successfully")
            
        except ImportError:
            logger.warning(
                "pika package not installed. "
                "Install with: pip install pika"
            )
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ connection: {e}")
    
    def publish_event(self, topic: str, event_data: Dict[str, Any],
                     correlation_id: Optional[str] = None) -> bool:
        """
        Publish event to RabbitMQ exchange.
        
        Args:
            topic: Event topic (used as routing key)
            event_data: CloudEvents payload
            correlation_id: Correlation ID for tracing
            
        Returns:
            bool: True if published successfully
        """
        try:
            if not self.channel:
                logger.error("RabbitMQ channel not initialized")
                return False
            
            # Import here to avoid dependency if not using RabbitMQ
            import pika
            
            # Publish message to exchange with topic as routing key
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=topic,
                body=json.dumps(event_data),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=2,  # Persistent
                    correlation_id=correlation_id
                )
            )
            
            logger.info(
                f"Published event via RabbitMQ: {topic}",
                extra={
                    "provider": "rabbitmq",
                    "topic": topic,
                    "correlationId": correlation_id
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to publish event via RabbitMQ: {topic} - {str(e)}",
                extra={
                    "provider": "rabbitmq",
                    "topic": topic,
                    "error": str(e)
                }
            )
            return False
    
    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
