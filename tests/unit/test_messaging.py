"""
Unit tests for messaging abstraction layer
Tests all providers and the factory
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, DEFAULT
import os
import json
import sys

from src.messaging.provider import MessagingProvider
from src.messaging.dapr_provider import DaprProvider
from src.messaging.factory import create_messaging_provider

# Mock optional dependencies before importing providers that use them
sys.modules['azure'] = MagicMock()
sys.modules['azure.servicebus'] = MagicMock()
sys.modules['pika'] = MagicMock()

from src.messaging.servicebus_provider import ServiceBusProvider
from src.messaging.rabbitmq_provider import RabbitMQProvider


class TestMessagingProvider:
    """Test the abstract MessagingProvider interface."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that MessagingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MessagingProvider()


class TestDaprProvider:
    """Test DaprProvider implementation."""
    
    def test_init_default_params(self):
        """Test DaprProvider initialization with defaults."""
        provider = DaprProvider()
        assert provider.pubsub_name == "inventory-pubsub"
        assert provider.dapr_http_port is None
    
    def test_init_custom_params(self):
        """Test DaprProvider initialization with custom parameters."""
        provider = DaprProvider(pubsub_name="custom-pubsub", dapr_http_port=3505)
        assert provider.pubsub_name == "custom-pubsub"
        assert provider.dapr_http_port == 3505
    
    @patch('src.messaging.dapr_provider.DaprClient')
    def test_publish_event_success(self, mock_dapr_client):
        """Test successful event publishing via Dapr."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_dapr_client.return_value.__enter__.return_value = mock_client_instance
        
        provider = DaprProvider()
        event_data = {
            "specversion": "1.0",
            "type": "test.event",
            "data": {"test": "value"}
        }
        
        result = provider.publish_event("test.topic", event_data, "corr-123")
        
        assert result is True
        mock_client_instance.publish_event.assert_called_once()
        call_args = mock_client_instance.publish_event.call_args
        assert call_args[1]['pubsub_name'] == "inventory-pubsub"
        assert call_args[1]['topic_name'] == "test.topic"
    
    @patch('src.messaging.dapr_provider.DaprClient')
    def test_publish_event_failure(self, mock_dapr_client):
        """Test event publishing failure handling."""
        # Setup mock to raise exception
        mock_dapr_client.return_value.__enter__.side_effect = Exception("Connection failed")
        
        provider = DaprProvider()
        event_data = {"type": "test.event"}
        
        result = provider.publish_event("test.topic", event_data)
        
        assert result is False
    
    def test_close(self):
        """Test close method (should not raise)."""
        provider = DaprProvider()
        provider.close()  # Should not raise


class TestServiceBusProvider:
    """Test ServiceBusProvider implementation."""
    
    def test_init(self):
        """Test ServiceBusProvider initialization."""
        provider = ServiceBusProvider(
            connection_string="Endpoint=sb://test.servicebus.windows.net/",
            topic_name="test-topic"
        )
        assert provider.connection_string == "Endpoint=sb://test.servicebus.windows.net/"
        assert provider.topic_name == "test-topic"
    
    def test_publish_event_success(self):
        """Test successful event publishing via Service Bus."""
        with patch('azure.servicebus.ServiceBusClient') as mock_sb_client, \
             patch('azure.servicebus.ServiceBusMessage') as mock_message:
            # Setup mocks
            mock_client_instance = MagicMock()
            mock_sb_client.from_connection_string.return_value = mock_client_instance
            
            mock_sender = MagicMock()
            mock_client_instance.get_topic_sender.return_value.__enter__.return_value = mock_sender
            
            provider = ServiceBusProvider(
                connection_string="Endpoint=sb://test.servicebus.windows.net/",
                topic_name="test-topic"
            )
            
            event_data = {"type": "test.event", "data": {"test": "value"}}
            result = provider.publish_event("test.topic", event_data, "corr-123")
            
            assert result is True
            mock_sender.send_messages.assert_called_once()
    
    def test_publish_event_no_client(self):
        """Test event publishing when client is not initialized."""
        with patch('azure.servicebus.ServiceBusClient') as mock_sb_client:
            mock_sb_client.from_connection_string.side_effect = Exception("Init failed")
            
            provider = ServiceBusProvider(
                connection_string="invalid",
                topic_name="test-topic"
            )
            
            event_data = {"type": "test.event"}
            result = provider.publish_event("test.topic", event_data)
            
            assert result is False
    
    def test_close(self):
        """Test close method."""
        with patch('azure.servicebus.ServiceBusClient') as mock_sb_client:
            mock_client_instance = MagicMock()
            mock_sb_client.from_connection_string.return_value = mock_client_instance
            
            provider = ServiceBusProvider(
                connection_string="Endpoint=sb://test.servicebus.windows.net/",
                topic_name="test-topic"
            )
            provider.close()
            
            mock_client_instance.close.assert_called_once()


class TestRabbitMQProvider:
    """Test RabbitMQProvider implementation."""
    
    def test_init(self):
        """Test RabbitMQProvider initialization."""
        provider = RabbitMQProvider(
            rabbitmq_url="******localhost:5672/",
            exchange="test-exchange"
        )
        assert provider.rabbitmq_url == "******localhost:5672/"
        assert provider.exchange == "test-exchange"
    
    def test_publish_event_success(self):
        """Test successful event publishing via RabbitMQ."""
        with patch('pika.BlockingConnection') as mock_conn_class, \
             patch('pika.URLParameters') as mock_params, \
             patch('pika.BasicProperties') as mock_props:
            # Setup mocks
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_conn_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel
            
            provider = RabbitMQProvider(
                rabbitmq_url="******localhost:5672/",
                exchange="test-exchange"
            )
            
            event_data = {"type": "test.event", "data": {"test": "value"}}
            result = provider.publish_event("test.topic", event_data, "corr-123")
            
            assert result is True
            mock_channel.basic_publish.assert_called_once()
    
    def test_publish_event_no_channel(self):
        """Test event publishing when channel is not initialized."""
        with patch('pika.BlockingConnection') as mock_conn_class, \
             patch('pika.URLParameters') as mock_params:
            mock_conn_class.side_effect = Exception("Connection failed")
            
            provider = RabbitMQProvider(
                rabbitmq_url="******localhost:5672/",
                exchange="test-exchange"
            )
            
            event_data = {"type": "test.event"}
            result = provider.publish_event("test.topic", event_data)
            
            assert result is False
    
    def test_close(self):
        """Test close method."""
        with patch('pika.BlockingConnection') as mock_conn_class, \
             patch('pika.URLParameters') as mock_params:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_conn_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel
            
            provider = RabbitMQProvider(
                rabbitmq_url="******localhost:5672/",
                exchange="test-exchange"
            )
            provider.close()
            
            mock_channel.close.assert_called_once()
            mock_connection.close.assert_called_once()


class TestMessagingFactory:
    """Test the messaging provider factory."""
    
    def test_create_dapr_provider_default(self, monkeypatch):
        """Test creating Dapr provider (default)."""
        monkeypatch.delenv('MESSAGING_PROVIDER', raising=False)
        
        provider = create_messaging_provider()
        
        assert isinstance(provider, DaprProvider)
        assert provider.pubsub_name == "inventory-pubsub"
    
    def test_create_dapr_provider_explicit(self, monkeypatch):
        """Test creating Dapr provider explicitly."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'dapr')
        monkeypatch.setenv('DAPR_PUBSUB_NAME', 'custom-pubsub')
        monkeypatch.setenv('DAPR_HTTP_PORT', '3505')
        
        provider = create_messaging_provider()
        
        assert isinstance(provider, DaprProvider)
        assert provider.pubsub_name == "custom-pubsub"
        assert provider.dapr_http_port == 3505
    
    def test_create_servicebus_provider(self, monkeypatch):
        """Test creating Service Bus provider."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'servicebus')
        monkeypatch.setenv('SERVICEBUS_CONNECTION_STRING', 'Endpoint=sb://test/')
        monkeypatch.setenv('SERVICEBUS_TOPIC_NAME', 'test-topic')
        
        with patch('azure.servicebus.ServiceBusClient'):
            provider = create_messaging_provider()
        
        assert isinstance(provider, ServiceBusProvider)
        assert provider.topic_name == "test-topic"
    
    def test_create_servicebus_provider_missing_config(self, monkeypatch):
        """Test Service Bus provider with missing configuration."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'servicebus')
        monkeypatch.delenv('SERVICEBUS_CONNECTION_STRING', raising=False)
        
        with pytest.raises(ValueError, match="SERVICEBUS_CONNECTION_STRING is required"):
            create_messaging_provider()
    
    def test_create_rabbitmq_provider(self, monkeypatch):
        """Test creating RabbitMQ provider."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'rabbitmq')
        monkeypatch.setenv('RABBITMQ_URL', '******localhost:5672/')
        monkeypatch.setenv('RABBITMQ_EXCHANGE', 'custom-exchange')
        
        with patch('pika.BlockingConnection'), patch('pika.URLParameters'):
            provider = create_messaging_provider()
        
        assert isinstance(provider, RabbitMQProvider)
        assert provider.exchange == "custom-exchange"
    
    def test_create_rabbitmq_provider_missing_config(self, monkeypatch):
        """Test RabbitMQ provider with missing configuration."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'rabbitmq')
        monkeypatch.delenv('RABBITMQ_URL', raising=False)
        
        with pytest.raises(ValueError, match="RABBITMQ_URL is required"):
            create_messaging_provider()
    
    def test_create_invalid_provider(self, monkeypatch):
        """Test creating provider with invalid type."""
        monkeypatch.setenv('MESSAGING_PROVIDER', 'invalid')
        
        with pytest.raises(ValueError, match="Invalid MESSAGING_PROVIDER"):
            create_messaging_provider()
