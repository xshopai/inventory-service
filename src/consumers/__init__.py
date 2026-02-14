"""
Event Consumers for Inventory Service

This module contains background message consumers for different messaging providers.
Consumers are used in environments where Dapr is not available (e.g., local development).

Architecture:
- Dapr mode: Events are received via HTTP endpoints in controllers/events.py
- RabbitMQ mode: Events are consumed by background thread in this module

Both modes route events to the same InventoryEventsService for processing.
"""

from src.consumers.rabbitmq_consumer import (
    RabbitMQConsumer,
    start_rabbitmq_consumer,
    stop_rabbitmq_consumer,
)

__all__ = [
    'RabbitMQConsumer',
    'start_rabbitmq_consumer',
    'stop_rabbitmq_consumer',
]
