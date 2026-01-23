# Messaging Abstraction Layer

## Overview

The Inventory Service implements a **Messaging Abstraction Layer** as specified in Architecture document section 5.5. This enables deployment flexibility across different Azure hosting options without code changes.

## Architecture

```
Business Logic (inventory_service.py)
    ↓
Event Publisher (event_publisher.py)
    ↓
Messaging Abstraction Layer (messaging/)
    ↓
Provider Implementations
    ├── DaprProvider (Azure Container Apps, AKS)
    ├── ServiceBusProvider (Azure App Service)
    └── RabbitMQProvider (Local development)
    ↓
Messaging Infrastructure
    ├── Dapr Sidecar → RabbitMQ/Kafka/Azure Service Bus/Redis
    ├── Azure Service Bus SDK
    └── RabbitMQ SDK (pika)
```

## Supported Providers

### 1. DaprProvider (Default)

**Use for:**
- Azure Container Apps (built-in Dapr sidecar)
- Azure Kubernetes Service (Dapr via Helm)
- Local development with Docker Compose

**Configuration:**
```bash
export MESSAGING_PROVIDER=dapr
export DAPR_PUBSUB_NAME=inventory-pubsub  # Default
export DAPR_HTTP_PORT=3504                # Optional, defaults to 3504
```

**Backend Support:**
- RabbitMQ (default)
- Azure Service Bus
- Kafka
- Redis Streams

### 2. ServiceBusProvider

**Use for:**
- Azure App Service (no Dapr sidecar available)

**Configuration:**
```bash
export MESSAGING_PROVIDER=servicebus
export SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
export SERVICEBUS_TOPIC_NAME="inventory-events"
```

**Dependencies:**
```bash
pip install azure-servicebus
```

### 3. RabbitMQProvider

**Use for:**
- Local development without Dapr
- Direct RabbitMQ integration

**Configuration:**
```bash
export MESSAGING_PROVIDER=rabbitmq
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
export RABBITMQ_EXCHANGE="inventory-events"  # Optional
```

**Dependencies:**
```bash
pip install pika
```

## Deployment Scenarios

### Azure Container Apps

```yaml
# container-app.yaml
properties:
  configuration:
    dapr:
      enabled: true
      appId: inventory-service
      appPort: 8004
  template:
    containers:
      - name: inventory-service
        env:
          - name: MESSAGING_PROVIDER
            value: dapr
          - name: DAPR_PUBSUB_NAME
            value: inventory-pubsub
```

### Azure App Service

```bash
# App Service Application Settings
MESSAGING_PROVIDER=servicebus
SERVICEBUS_CONNECTION_STRING=<from-key-vault>
SERVICEBUS_TOPIC_NAME=inventory-events
```

### Azure Kubernetes (AKS)

```yaml
# deployment.yaml
spec:
  template:
    metadata:
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "inventory-service"
        dapr.io/app-port: "8004"
    spec:
      containers:
        - name: inventory-service
          env:
            - name: MESSAGING_PROVIDER
              value: dapr
```

### Local Development (Docker Compose)

```yaml
# docker-compose.yml
services:
  inventory-service:
    environment:
      - MESSAGING_PROVIDER=dapr  # or rabbitmq
      - DAPR_PUBSUB_NAME=inventory-pubsub
  
  inventory-service-dapr:
    image: daprio/daprd:latest
    command: ["./daprd",
      "-app-id", "inventory-service",
      "-app-port", "8004",
      "-components-path", "/components"]
```

## Usage in Code

The abstraction layer is transparent to business logic:

```python
from src.utils.event_publisher import event_publisher

# Publish event - provider selected automatically
event_publisher.publish_stock_updated(
    product_id="SKU-12345",
    quantity=100,
    correlation_id="req-abc-123"
)
```

The `event_publisher` uses the messaging abstraction layer internally:

```python
class InventoryEventPublisher:
    def __init__(self):
        self._provider = None  # Lazy initialization
    
    @property
    def provider(self):
        if self._provider is None:
            self._provider = create_messaging_provider()  # Factory
        return self._provider
```

## Provider Selection Logic

```python
# src/messaging/factory.py
def create_messaging_provider() -> MessagingProvider:
    provider_type = os.getenv('MESSAGING_PROVIDER', 'dapr')
    
    if provider_type == 'dapr':
        return DaprProvider(...)
    elif provider_type == 'servicebus':
        return ServiceBusProvider(...)
    elif provider_type == 'rabbitmq':
        return RabbitMQProvider(...)
```

## Testing Different Providers

### Test with Dapr (Default)

```bash
export MESSAGING_PROVIDER=dapr
python run.py
```

### Test with Service Bus

```bash
export MESSAGING_PROVIDER=servicebus
export SERVICEBUS_CONNECTION_STRING="Endpoint=sb://test.servicebus.windows.net/..."
export SERVICEBUS_TOPIC_NAME="inventory-events"
python run.py
```

### Test with RabbitMQ

```bash
export MESSAGING_PROVIDER=rabbitmq
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
python run.py
```

## Benefits

1. **Deployment Flexibility**: Same codebase works on Container Apps, AKS, and App Service
2. **No Vendor Lock-in**: Switch message brokers without code changes
3. **Testability**: Easy to mock providers for unit tests
4. **Local Development**: Run with or without Dapr sidecar
5. **Gradual Migration**: Start with App Service, migrate to Container Apps when ready
6. **Cost Optimization**: Choose broker based on pricing and requirements

## Migration Path

### Phase 1: App Service (Current)
```
Business Logic → ServiceBusProvider → Azure Service Bus
```

### Phase 2: Container Apps (Future)
```
Business Logic → DaprProvider → Dapr Sidecar → Azure Service Bus
```

**No code changes required** - just update environment variables!

## CloudEvents Compliance

All providers publish CloudEvents 1.0 compliant messages:

```json
{
  "specversion": "1.0",
  "type": "inventory.stock.updated",
  "source": "inventory-service",
  "id": "evt-550e8400-e29b-41d4-a716-446655440000",
  "time": "2025-01-20T15:30:00Z",
  "datacontenttype": "application/json",
  "correlationid": "req-abc-123",
  "data": {
    "productId": "SKU-12345",
    "quantity": 100
  }
}
```

## Troubleshooting

### Provider not initialized

**Error:** `ValueError: SERVICEBUS_CONNECTION_STRING is required`

**Solution:** Set required environment variables for selected provider

### Import errors

**Error:** `ModuleNotFoundError: No module named 'azure.servicebus'`

**Solution:** Install provider-specific dependencies:
```bash
pip install azure-servicebus  # For ServiceBusProvider
pip install pika              # For RabbitMQProvider
```

### Dapr connection failed

**Error:** `DaprInternalError: Dapr Encountered an Error`

**Solution:** Ensure Dapr sidecar is running on port 3504

## References

- Architecture Document: `docs/ARCHITECTURE.md` Section 5.5
- PRD Document: `docs/PRD.md` Section 4.11 (Event Publishing)
- CloudEvents Spec: https://cloudevents.io/
