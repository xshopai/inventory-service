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

---

## Step 2: Configure Environment for Dapr Mode

Update your `.env` file for Dapr messaging:

```bash
# Messaging Provider - Use Dapr
MESSAGING_PROVIDER=dapr
DAPR_PUBSUB_NAME=event-bus
DAPR_HTTP_PORT=3504

# Database and service tokens remain the same as PREREQUISITES.md
```

---

## Step 3: Verify Dapr Component Files

The repository includes pre-configured Dapr components in `.dapr/components/`:

```bash
# List component files
ls -la .dapr/components/

# You should see:
# - event-bus.yaml (RabbitMQ pub/sub)
# - subscriptions.yaml (Event subscriptions)
# - secret-store.yaml (Local secrets)
```

---

## Step 4: Configure Dapr Secrets (Optional)

If using Dapr secret store, create `.dapr/secrets.json`:

```json
{
  "mysql-host": "localhost",
  "mysql-port": "3306",
  "mysql-database": "inventory_service_db",
  "mysql-username": "admin",
  "mysql-password": "admin123",
  "jwt-secret": "your-jwt-secret-key"
}
```

> **Security Note:** This file is gitignored. Never commit secrets.json to version control.

---

## Step 5: Start Service with Dapr Sidecar

### Option A: Using dapr run command

```bash
dapr run \
  --app-id inventory-service \
  --app-port 8004 \
  --dapr-http-port 3504 \
  --dapr-grpc-port 50004 \
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
curl http://localhost:3504/v1.0/metadata

# Check service health
curl http://localhost:8004/health

# Expected metadata response shows:
# - app-id: inventory-service
# - Configured components (event-bus, etc.)
```

---

## Step 7: Test Event Publishing

```bash
# Create inventory item (requires service token)
curl -X POST http://localhost:8004/api/inventory \
  -H "X-Service-Token: svc-product-<your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-SKU-001",
    "quantity": 100,
    "product_id": "prod-123"
  }'

# Check Dapr logs for:
# "Published event via Dapr: inventory.created"
```

---

## Step 8: Test Event Subscriptions

```bash
# Simulate product.created event from Product Service
curl -X POST http://localhost:3504/v1.0/publish/event-bus/product.created \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "productId": "prod-123",
      "sku": "SKU-TEST-001",
      "name": "Test Product"
    }
  }'

# Check service logs - should see "Received product.created event"
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

## Development Workflow with Dapr

1. **Start dependencies**: `docker-compose up -d inventory-mysql xshopai-rabbitmq`
2. **Activate venv**:
   - Linux/Mac: `source venv/bin/activate`
   - Windows PowerShell: `.\venv\Scripts\Activate.ps1`
   - Windows CMD: `venv\Scripts\activate.bat`
   - Windows Git Bash: `source venv/Scripts/activate`
3. **Start with Dapr**:
   - Linux/Mac: `./run.sh`
   - Windows: `.\run.ps1`
4. **Make changes**: Edit code (restart required with Dapr)
5. **Test events**: Use curl to publish/subscribe
6. **Stop service**: `dapr stop --app-id inventory-service`

---

## Stopping the Service

```bash
# Stop Dapr sidecar and application
dapr stop --app-id inventory-service

# Or use VS Code task: "Stop Dapr Sidecar"
```

---

## Dapr Component Configuration Reference

### Event Bus (RabbitMQ)

File: `.dapr/components/event-bus.yaml`

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: event-bus
spec:
  type: pubsub.rabbitmq
  version: v1
  metadata:
    - name: connectionString
      value: 'amqp://guest:guest@127.0.0.1:5672'
    - name: durable
      value: 'true'
    - name: deletedWhenUnused
      value: 'false'
```

### Event Subscriptions

File: `.dapr/components/subscriptions.yaml`

Subscribed events:
| Event | Route |
|-------|-------|
| `product.created` | `/events/product-created` |
| `product.updated` | `/events/product-updated` |
| `product.deleted` | `/events/product-deleted` |
| `order.created` | `/events/order-created` |
| `order.cancelled` | `/events/order-cancelled` |
| `order.completed` | `/events/order-completed` |

---

## Troubleshooting

### Dapr Sidecar Not Starting

```bash
# Check if Dapr is initialized
dapr --version

# Re-initialize Dapr
dapr uninstall
dapr init
```

### Event Not Being Published

```bash
# Check pub/sub component is loaded
curl http://localhost:3504/v1.0/metadata | jq '.components'

# Verify RabbitMQ is accessible
curl -u guest:guest http://localhost:15672/api/overview
```

### Cannot Receive Events

```bash
# Verify subscriptions are configured
curl http://localhost:3504/v1.0/metadata | jq '.subscriptions'

# Check event route is responding
curl http://localhost:8004/events/product-created -X POST \
  -H "Content-Type: application/json" \
  -d '{"data": {"test": true}}'
```

---

## Next Steps

- Review the [Architecture Documentation](ARCHITECTURE.md)
- See [API Documentation](API.md) for endpoint details
