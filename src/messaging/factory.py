"""
Messaging Provider Factory
Architecture spec section 5.5.3

Selects the appropriate provider based on environment configuration.
Enables deployment flexibility across Azure hosting options.
"""
import os
import logging
from typing import Optional

from .provider import MessagingProvider

logger = logging.getLogger(__name__)


def create_messaging_provider() -> MessagingProvider:
    """
    Create messaging provider based on MESSAGING_PROVIDER environment variable.
    
    This factory pattern enables the same codebase to deploy across different
    Azure hosting options without code changes, only configuration.
    
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
    # Get provider type from environment, default to Dapr
    provider_type = os.getenv('MESSAGING_PROVIDER', 'dapr').lower()
    
    logger.info(f"Creating messaging provider: {provider_type}")
    
    # Select provider based on configuration (lazy import to avoid loading unused providers)
    if provider_type == 'dapr':
        from .dapr_provider import DaprProvider
        return _create_dapr_provider(DaprProvider)
    elif provider_type == 'servicebus':
        from .servicebus_provider import ServiceBusProvider
        return _create_servicebus_provider(ServiceBusProvider)
    elif provider_type == 'rabbitmq':
        from .rabbitmq_provider import RabbitMQProvider
        return _create_rabbitmq_provider(RabbitMQProvider)
    else:
        raise ValueError(
            f"Invalid MESSAGING_PROVIDER: {provider_type}. "
            f"Must be 'dapr', 'servicebus', or 'rabbitmq'"
        )


def _create_dapr_provider(DaprProvider):
    """
    Create and configure Dapr provider.
    Used for Azure Container Apps, AKS, and local Docker Compose.
    """
    # Get Dapr configuration from environment
    pubsub_name = 'pubsub'
    dapr_http_port = os.getenv('DAPR_HTTP_PORT')
    
    # Convert port to integer if provided
    if dapr_http_port:
        dapr_http_port = int(dapr_http_port)
    
    logger.info(f"Creating DaprProvider with pubsub: {pubsub_name}")
    return DaprProvider(pubsub_name=pubsub_name, dapr_http_port=dapr_http_port)


def _create_servicebus_provider(ServiceBusProvider):
    """
    Create and configure Azure Service Bus provider.
    Used for Azure App Service deployments without Dapr sidecar.
    """
    # Get Service Bus configuration - both required
    connection_string = os.getenv('SERVICEBUS_CONNECTION_STRING')
    topic_name = os.getenv('SERVICEBUS_TOPIC_NAME')
    
    # Validate required configuration
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


def _create_rabbitmq_provider(RabbitMQProvider):
    """
    Create and configure RabbitMQ provider.
    Used for local development without Dapr sidecar.
    """
    # Get RabbitMQ configuration
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    exchange = os.getenv('RABBITMQ_EXCHANGE', 'xshopai.events')  # Optional, has default
    
    # Validate required configuration
    if not rabbitmq_url:
        raise ValueError(
            "RABBITMQ_URL is required for RabbitMQProvider"
        )
    
    logger.info(f"Creating RabbitMQProvider with exchange: {exchange}")
    return RabbitMQProvider(
        rabbitmq_url=rabbitmq_url,
        exchange=exchange
    )
