"""
Messaging Provider Factory
Architecture spec section 5.5.3

Selects the appropriate provider based on environment configuration.
"""
import os
import logging
from typing import Optional

from .provider import MessagingProvider
from .dapr_provider import DaprProvider
from .servicebus_provider import ServiceBusProvider
from .rabbitmq_provider import RabbitMQProvider

logger = logging.getLogger(__name__)


def create_messaging_provider() -> MessagingProvider:
    """
    Create messaging provider based on MESSAGING_PROVIDER environment variable.
    
    Environment Variables:
    - MESSAGING_PROVIDER: 'dapr', 'servicebus', or 'rabbitmq' (default: 'dapr')
    - For DaprProvider: DAPR_PUBSUB_NAME, DAPR_HTTP_PORT
    - For ServiceBusProvider: SERVICEBUS_CONNECTION_STRING, SERVICEBUS_TOPIC_NAME
    - For RabbitMQProvider: RABBITMQ_URL, RABBITMQ_EXCHANGE
    
    Returns:
        MessagingProvider: Configured provider instance
        
    Raises:
        ValueError: If provider type is invalid or required config is missing
    """
    provider_type = os.getenv('MESSAGING_PROVIDER', 'dapr').lower()
    
    logger.info(f"Creating messaging provider: {provider_type}")
    
    if provider_type == 'dapr':
        return _create_dapr_provider()
    elif provider_type == 'servicebus':
        return _create_servicebus_provider()
    elif provider_type == 'rabbitmq':
        return _create_rabbitmq_provider()
    else:
        raise ValueError(
            f"Invalid MESSAGING_PROVIDER: {provider_type}. "
            f"Must be 'dapr', 'servicebus', or 'rabbitmq'"
        )


def _create_dapr_provider() -> DaprProvider:
    """Create and configure Dapr provider."""
    pubsub_name = os.getenv('DAPR_PUBSUB_NAME', 'inventory-pubsub')
    dapr_http_port = os.getenv('DAPR_HTTP_PORT')
    
    if dapr_http_port:
        dapr_http_port = int(dapr_http_port)
    
    logger.info(f"Creating DaprProvider with pubsub: {pubsub_name}")
    return DaprProvider(pubsub_name=pubsub_name, dapr_http_port=dapr_http_port)


def _create_servicebus_provider() -> ServiceBusProvider:
    """Create and configure Azure Service Bus provider."""
    connection_string = os.getenv('SERVICEBUS_CONNECTION_STRING')
    topic_name = os.getenv('SERVICEBUS_TOPIC_NAME')
    
    if not connection_string:
        raise ValueError(
            "SERVICEBUS_CONNECTION_STRING is required for ServiceBusProvider"
        )
    if not topic_name:
        raise ValueError(
            "SERVICEBUS_TOPIC_NAME is required for ServiceBusProvider"
        )
    
    logger.info(f"Creating ServiceBusProvider with topic: {topic_name}")
    return ServiceBusProvider(
        connection_string=connection_string,
        topic_name=topic_name
    )


def _create_rabbitmq_provider() -> RabbitMQProvider:
    """Create and configure RabbitMQ provider."""
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    exchange = os.getenv('RABBITMQ_EXCHANGE', 'inventory-events')
    
    if not rabbitmq_url:
        raise ValueError(
            "RABBITMQ_URL is required for RabbitMQProvider"
        )
    
    logger.info(f"Creating RabbitMQProvider with exchange: {exchange}")
    return RabbitMQProvider(
        rabbitmq_url=rabbitmq_url,
        exchange=exchange
    )
