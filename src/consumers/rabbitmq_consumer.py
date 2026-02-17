"""
RabbitMQ Consumer for Inventory Service
Provides direct RabbitMQ message consumption for development environments without Dapr.

This consumer:
1. Connects to RabbitMQ directly
2. Subscribes to the same topics as Dapr subscriptions
3. Routes messages to the same event handlers

Usage:
- Set MESSAGING_PROVIDER=rabbitmq in environment
- Call start_rabbitmq_consumer(app) after app creation
"""
import json
import logging
import threading
import os
from typing import Dict, Any, Callable, Optional
from flask import Flask

logger = logging.getLogger(__name__)

# Suppress noisy pika debug logs (heartbeat/timeout internals)
logging.getLogger('pika').setLevel(logging.WARNING)


class RabbitMQConsumer:
    """
    Background consumer for RabbitMQ messages.
    Runs in a separate thread to avoid blocking the Flask app.
    """
    
    # Topic to handler mapping - mirrors the SUBSCRIPTIONS in events.py
    TOPIC_HANDLERS: Dict[str, str] = {
        "product.created": "handle_product_created",
        "product.updated": "handle_product_updated",
        "product.deleted": "handle_product_deleted",
        "order.created": "handle_order_created",
        "order.cancelled": "handle_order_cancelled",
        "order.completed": "handle_order_completed",
        "payment.received": "handle_payment_received",
        "payment.failed": "handle_payment_failed",
        "inventory.release": "handle_inventory_release",
        "inventory.return.release": "handle_inventory_return_release",
    }
    
    def __init__(self, app: Flask, rabbitmq_url: str, exchange: str = "xshopai.events"):
        """
        Initialize RabbitMQ consumer.
        
        Args:
            app: Flask application instance (needed for app context)
            rabbitmq_url: RabbitMQ connection URL
            exchange: Exchange name to bind queues to
        """
        self.app = app
        self.rabbitmq_url = rabbitmq_url
        self.exchange = exchange
        self.connection = None
        self.channel = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._running = False
        self._events_service = None
        
        logger.info(f"RabbitMQConsumer initialized with exchange: {exchange}")
    
    def _get_events_service(self):
        """Lazy load events service to avoid circular imports."""
        if self._events_service is None:
            from src.services.inventory_events_service import InventoryEventsService
            self._events_service = InventoryEventsService()
        return self._events_service
    
    def _setup_connection(self):
        """Set up RabbitMQ connection, exchange, and queue bindings."""
        try:
            import pika
            
            # Parse connection URL and create connection
            parameters = pika.URLParameters(self.rabbitmq_url)
            # Set heartbeat to keep connection alive
            parameters.heartbeat = 30
            parameters.blocked_connection_timeout = 300
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange (topic type for routing by event type)
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Create a unique queue for this service instance
            result = self.channel.queue_declare(
                queue='inventory-service-events',
                durable=True,
                exclusive=False,
                auto_delete=False
            )
            queue_name = result.method.queue
            
            # Bind queue to all topics we're interested in
            for topic in self.TOPIC_HANDLERS.keys():
                self.channel.queue_bind(
                    exchange=self.exchange,
                    queue=queue_name,
                    routing_key=topic
                )
                logger.info(f"Bound queue to topic: {topic}")
            
            # Set prefetch count for fair dispatch
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"RabbitMQ connection established. Queue: {queue_name}")
            return queue_name
            
        except ImportError:
            logger.error("pika package not installed. Install with: pip install pika")
            raise
        except Exception as e:
            logger.error(f"Failed to set up RabbitMQ connection: {e}")
            raise
    
    def _process_message(self, ch, method, properties, body):
        """
        Process incoming message from RabbitMQ.
        Routes to appropriate handler based on routing key (topic).
        """
        topic = method.routing_key
        correlation_id = properties.correlation_id or "unknown"
        
        try:
            # Parse message body as JSON
            raw_data = json.loads(body)
            
            # Normalize to CloudEvents-style envelope.
            # Dapr wraps payloads under a 'data' key (CloudEvents spec),
            # but RabbitMQ direct publishers send the payload at root level.
            # Wrap raw payloads so all handlers can use event_data.get('data', {}).
            if 'data' in raw_data:
                event_data = raw_data
            else:
                event_data = {
                    'topic': topic,
                    'data': raw_data,
                    'traceparent': raw_data.get('traceparent'),
                    'correlationId': correlation_id,
                }
            
            logger.info(
                f"📨 Received message on topic: {topic}",
                extra={"topic": topic, "correlationId": correlation_id}
            )
            
            # Find handler for this topic
            handler_name = self.TOPIC_HANDLERS.get(topic)
            if not handler_name:
                logger.warning(f"No handler found for topic: {topic}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Get handler method from events service
            events_service = self._get_events_service()
            handler = getattr(events_service, handler_name, None)
            
            if not handler:
                logger.error(f"Handler method not found: {handler_name}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Execute handler within Flask app context
            with self.app.app_context():
                result = handler(event_data)
                
                status = result.get('status')
                if status == 'error':
                    # Transient error - requeue for retry (e.g., DB connection issue)
                    logger.error(
                        f"Handler returned transient error - will retry: {result.get('message')}",
                        extra={"topic": topic, "correlationId": correlation_id}
                    )
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                elif status == 'business_error':
                    # Permanent business error - acknowledge but don't retry
                    # (e.g., insufficient stock, item not found)
                    logger.warning(
                        f"⚠️ Handler returned business error - acknowledging without retry: {result.get('message')}",
                        extra={"topic": topic, "correlationId": correlation_id}
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    logger.info(
                        f"✅ Successfully processed message: {topic}",
                        extra={"topic": topic, "correlationId": correlation_id}
                    )
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message body as JSON: {e}")
            # Don't requeue invalid messages
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(
                f"Error processing message: {e}",
                extra={"topic": topic, "correlationId": correlation_id, "error": str(e)}
            )
            # Requeue for retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def _consume_messages(self, queue_name: str):
        """
        Start consuming messages from the queue.
        This runs in a separate thread.
        """
        logger.info(f"Starting message consumption from queue: {queue_name}")
        
        try:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._process_message,
                auto_ack=False
            )
            
            while self._running:
                # Process one message at a time with timeout
                # This allows checking _running flag periodically
                self.connection.process_data_events(time_limit=1)
                
        except Exception as e:
            if self._running:
                logger.error(f"Error in message consumption: {e}")
            else:
                logger.info("Message consumption stopped")
    
    def start(self):
        """Start the consumer in a background thread."""
        if self._running:
            logger.warning("Consumer is already running")
            return
        
        try:
            queue_name = self._setup_connection()
            self._running = True
            
            self._consumer_thread = threading.Thread(
                target=self._consume_messages,
                args=(queue_name,),
                daemon=True,
                name="rabbitmq-consumer"
            )
            self._consumer_thread.start()
            
            logger.info("[RabbitMQ] Consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start RabbitMQ consumer: {e}")
            self._running = False
            raise
    
    def stop(self):
        """Stop the consumer gracefully."""
        logger.info("Stopping RabbitMQ consumer...")
        self._running = False
        
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=5.0)
        
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
        
        logger.info("RabbitMQ consumer stopped")
    
    def is_running(self) -> bool:
        """Check if consumer is currently running."""
        return self._running and self._consumer_thread and self._consumer_thread.is_alive()


# Global consumer instance
_consumer: Optional[RabbitMQConsumer] = None


def start_rabbitmq_consumer(app: Flask) -> Optional[RabbitMQConsumer]:
    """
    Start RabbitMQ consumer for the given Flask app.
    Only starts if MESSAGING_PROVIDER is set to 'rabbitmq'.
    
    Args:
        app: Flask application instance
        
    Returns:
        RabbitMQConsumer instance if started, None otherwise
    """
    global _consumer
    
    messaging_provider = os.environ.get('MESSAGING_PROVIDER', 'dapr').lower()
    
    if messaging_provider != 'rabbitmq':
        logger.info(
            f"RabbitMQ consumer not started (MESSAGING_PROVIDER={messaging_provider}). "
            "Using Dapr for event consumption."
        )
        return None
    
    # Use RABBITMQ_URL if set (preferred), otherwise build from individual vars
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    rabbitmq_exchange = os.environ.get('RABBITMQ_EXCHANGE', 'xshopai.events')
    
    if not rabbitmq_url:
        from urllib.parse import quote as url_quote
        rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        rabbitmq_port = os.environ.get('RABBITMQ_PORT', '5672')
        rabbitmq_user = os.environ.get('RABBITMQ_USER', 'admin')
        rabbitmq_pass = os.environ.get('RABBITMQ_PASSWORD', 'admin123')
        rabbitmq_vhost = os.environ.get('RABBITMQ_VHOST', '/')
        # Percent-encode vhost (/ becomes %2F) per AMQP URL spec
        encoded_vhost = url_quote(rabbitmq_vhost, safe='')
        rabbitmq_url = f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}:{rabbitmq_port}/{encoded_vhost}"
    
    try:
        _consumer = RabbitMQConsumer(app, rabbitmq_url, rabbitmq_exchange)
        _consumer.start()
        return _consumer
    except Exception as e:
        logger.error(f"Failed to start RabbitMQ consumer: {e}")
        return None


def stop_rabbitmq_consumer():
    """Stop the global RabbitMQ consumer if running."""
    global _consumer
    if _consumer:
        _consumer.stop()
        _consumer = None
