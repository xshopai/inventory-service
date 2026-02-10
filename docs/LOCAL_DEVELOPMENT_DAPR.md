# Local Development with Dapr

This guide shows how to run the Inventory Service locally **with Dapr sidecar** for a production-like environment with event-driven messaging.

> **📋 Prerequisites**: Complete the [Prerequisites & Common Setup](PREREQUISITES.md) before following this guide.

---

## Overview

This setup uses:

- **Dapr sidecar** for service-to-service communication and pub/sub messaging
- **RabbitMQ** as the Dapr pub/sub backing store
- Production-like event handling with proper dead letter queues

For simpler development without Dapr, see [Local Development (without Dapr)](LOCAL_DEVELOPMENT.md).

---

## Additional Prerequisites for Dapr

| Tool     | Version | Installation                                                               |
| -------- | ------- | -------------------------------------------------------------------------- |
| Dapr CLI | 1.12+   | [Install Dapr CLI](https://docs.dapr.io/getting-started/install-dapr-cli/) |

---

## Step 1: Initialize Dapr

```bash
# Initialize Dapr (one-time setup)
dapr init

# Verify Dapr installation
dapr --version

# Check Dapr containers are running
docker ps | grep dapr
```

You should see these containers:

- `dapr_redis`
- `dapr_zipkin`
- `dapr_placement`
- `dapr_scheduler`

---

## Step 2: Configure Environment for Dapr Mode

Copy the Dapr environment template to `.env`:

```bash
# On Linux / Mac / Bash:
cp .env.dapr .env

# On Windows (PowerShell):
Copy-Item .env.dapr .env
```

---

## Step 3: Verify Dapr Component Files

The repository includes pre-configured Dapr components in `.dapr/components/`:

```bash
# List component files
ls -la .dapr/components/

# You should see:
# - event-bus.yaml (RabbitMQ pub/sub, component name: pubsub)
# - subscriptions.yaml (Event subscriptions)
# - secret-store.yaml (Local secrets)
```

---

## Step 5: Start Service with Dapr Sidecar

### Option A: Using dapr run command

> **Note:** All services now use the standard Dapr ports (3500 for HTTP, 50001 for gRPC). This simplifies configuration and works consistently whether running via Docker Compose or individual service runs.

```bash
dapr run \
  --app-id inventory-service \
  --app-port 8005 \
  --dapr-http-port 3500 \
  --dapr-grpc-port 50001 \
  --resources-path ./.dapr/components \
  --config ./.dapr/config.yaml \
  --log-level warn \
  -- python run.py
```

### Option B: Using convenience scripts

```bash
# On Linux/Mac:
./run.sh

# On Windows (PowerShell):
.\run.ps1

# On Windows (Command Prompt):
powershell -ExecutionPolicy Bypass -File run.ps1

# On Windows (Git Bash):
./run.sh
```

---

## Step 6: Verify Dapr Integration

```bash
# Check Dapr sidecar metadata
curl http://localhost:3500/v1.0/metadata

# Check service health
curl http://localhost:8005/health

# Expected metadata response shows:
# - app-id: inventory-service
# - Configured components (pubsub, etc.)
```

---

## Dapr Dashboard (Optional)

```bash
# Start Dapr Dashboard
dapr dashboard

# Access at http://localhost:8080
```

The dashboard shows:

- Running Dapr applications
- Component status
- Pub/sub subscriptions
- Service invocations

---

## Stopping the Service

```bash
# Stop Dapr sidecar and application
dapr stop --app-id inventory-service

# Or use VS Code task: "Stop Dapr Sidecar"
```

---

## Dapr Component Configuration Reference

### Pub/Sub Component (RabbitMQ)

File: `.dapr/components/event-bus.yaml`

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.rabbitmq
  version: v1
  metadata:
    - name: connectionString
      value: 'amqp://guest:guest@127.0.0.1:5672'
    - name: consumerID
      value: 'inventory-service'
    - name: durable
      value: 'true'
    - name: deletedWhenUnused
      value: 'false'
    - name: autoAck
      value: 'false'
    - name: deliveryMode
      value: '2'
    - name: requeueInFailure
      value: 'true'
    - name: prefetchCount
      value: '10'
    - name: reconnectWait
      value: '5'
    - name: concurrencyMode
      value: 'parallel'
    - name: publisherConfirm
      value: 'false'
    - name: enableDeadLetter
      value: 'true'
    - name: exchangeKind
      value: 'topic'
scopes:
  - inventory-service
```

> **Note:** The component name must be `pubsub` to match the hardcoded value in the application code.

**Key Configuration Options:**

| Attribute          | Value                    | Description                                         |
| ------------------ | ------------------------ | --------------------------------------------------- |
| `connectionString` | `amqp://guest:guest@...` | RabbitMQ connection (matches container credentials) |
| `consumerID`       | `inventory-service`      | Consumer group identity                             |
| `durable`          | `true`                   | Queues persist across RabbitMQ restarts             |
| `autoAck`          | `false`                  | Manual acknowledgment for reliability               |
| `deliveryMode`     | `2`                      | Persistent messages (survives broker restart)       |
| `requeueInFailure` | `true`                   | Requeue failed messages for retry                   |
| `prefetchCount`    | `10`                     | Messages prefetched per consumer                    |
| `concurrencyMode`  | `parallel`               | Process multiple messages concurrently              |
| `enableDeadLetter` | `true`                   | Failed messages go to dead letter queue             |
| `exchangeKind`     | `topic`                  | Topic-based routing for flexibility                 |

> **Note**: See [Dapr RabbitMQ documentation](https://docs.dapr.io/reference/components-reference/supported-pubsub/setup-rabbitmq/) for all available options.

### Event Subscriptions

File: `.dapr/components/subscriptions.yaml`

Subscribed events:
| Event | Route |
|-------|-------|
| `product.created` | `/events/product-created` |
| `product.updated` | `/events/product-updated` |
| `product.deleted` | `/events/product-deleted` |
| `order.created`   | `/events/order-created`   |
| `order.cancelled` | `/events/order-cancelled` |
| `order.completed` | `/events/order-completed` |

---

## Next Steps

- Review the [Architecture Documentation](ARCHITECTURE.md)
- See [API Documentation](API.md) for endpoint details
