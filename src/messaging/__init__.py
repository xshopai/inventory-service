"""
Messaging Abstraction Layer for Inventory Service
Implements Architecture spec section 5.5

This module provides messaging PUBLISHING infrastructure.
For message CONSUMPTION, see src/consumers/ module.

Supported Providers:
- Dapr (default): Uses Dapr Pub/Sub for broker abstraction
- RabbitMQ: Direct RabbitMQ connection for local development
- ServiceBus: Azure Service Bus for Azure deployments
"""
from .provider import MessagingProvider
from .factory import create_messaging_provider

__all__ = [
    'MessagingProvider', 
    'create_messaging_provider',
]
