# Local Development with Dapr Integration

This guide shows how to run the Inventory Service locally **with Dapr sidecar** for a production-like environment with event-driven messaging.

---

## Prerequisites

- Completed basic local setup from [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **Dapr CLI 1.12+** installed - [Install Dapr CLI](https://docs.dapr.io/getting-started/install-dapr-cli/)
- **Docker** running (Dapr uses Docker for components)
- MySQL and RabbitMQ already running (from basic setup)

---

## Step-by-Step Dapr Setup

### Step 1: Initialize Dapr

```bash
# Initialize Dapr (one-time setup)
dapr init

# Verify Dapr installation
dapr --version

# Check Dapr containers are running
docker ps | grep dapr
```

You should see:
- dapr_redis
- dapr_zipkin
- dapr_placement

### Step 2: Configure Environment for Dapr

Update `.env.local` to use Dapr provider:

```bash
# Messaging Provider - Switch to Dapr
MESSAGING_PROVIDER=dapr
DAPR_PUBSUB_NAME=event-bus
DAPR_HTTP_PORT=3500

# Remove RabbitMQ direct connection settings
# RABBITMQ_URL=...  # Not needed with Dapr
# RABBITMQ_EXCHANGE=...  # Not needed with Dapr

# Database and service tokens remain the same
```

### Step 3: Verify Dapr Component Files

The repository includes pre-configured Dapr components in `.dapr/components/`:

```bash
# List component files
ls -la .dapr/components/

# You should see:
# - event-bus.yaml (RabbitMQ pub/sub)
# - subscriptions.yaml (Event subscriptions)
# - secret-store.yaml (Local secrets)
```

### Step 4: Configure Dapr Secrets

Update `.dapr/secrets.json` with your database credentials:

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

**Security Note:** This file is gitignored. Never commit secrets.json to version control.

### Step 5: Start Service with Dapr Sidecar

```bash
# Run with Dapr
dapr run \
  --app-id inventory-service \
  --app-port 8004 \
  --dapr-http-port 3500 \
  --dapr-grpc-port 50001 \
  --components-path ./.dapr/components \
  --config ./.dapr/config.yaml \
  -- python run.py
```

**Or use the convenience script:**

```bash
# Linux/Mac
./run.sh

# Windows
.\run.ps1
```

### Step 6: Verify Dapr Integration

```bash
# Check Dapr sidecar is running
curl http://localhost:3500/v1.0/metadata

# Check service health
curl http://localhost:8004/health

# Check Dapr pub/sub component
dapr components -k ./.dapr/components/
```

### Step 7: Test Event Publishing

```bash
# Trigger an inventory update (requires admin JWT)
curl -X POST http://localhost:8004/api/inventory/ \
  -H "Authorization: Bearer <admin-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-SKU-001",
    "quantity": 100
  }'

# Check Dapr logs for published event
# Look for "Published event via Dapr: inventory.created"
```

### Step 8: Test Event Subscriptions

```bash
# Publish a test event to Dapr
curl -X POST http://localhost:3500/v1.0/publish/event-bus/product.created \
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

### Install Dapr Dashboard

```bash
# Install dashboard
dapr dashboard

# Access at http://localhost:8080
```

The dashboard shows:
- Running Dapr applications
- Components status
- Pub/sub subscriptions
- Service invocations
- Logs and metrics

---

## Development Workflow with Dapr

### 1. Start Dependencies

```bash
# Start MySQL and RabbitMQ only
docker-compose up -d mysql rabbitmq

# Verify they're running
docker ps
```

### 2. Start Service with Dapr

```bash
dapr run --app-id inventory-service \
  --app-port 8004 \
  --components-path ./.dapr/components \
  -- python run.py
```

### 3. Test Event Publishing

```bash
# Create inventory (publishes inventory.created event)
curl -X POST http://localhost:8004/api/inventory/ \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-001", "quantity": 50}'
```

### 4. Test Event Receiving

```bash
# Simulate product.created event from Product Service
curl -X POST http://localhost:3500/v1.0/publish/event-bus/product.created \
  -H "X-Service-Token: <your-product-service-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "productId": "prod-456",
      "sku": "SKU-456",
      "name": "New Product"
    }
  }'

# Check service logs for event handling
```

### 5. View Logs

Dapr provides enhanced logging:

```bash
# Dapr automatically displays application logs
# Plus Dapr sidecar logs showing:
# - Event publishing
# - Event subscriptions
# - Service invocations
# - Component health
```

---

## Dapr Component Configuration

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

Defines 6 event subscriptions:
- product.created → `/events/product-created`
- product.updated → `/events/product-updated`
- product.deleted → `/events/product-deleted`
- order.created → `/events/order-created`
- order.cancelled → `/events/order-cancelled`
- order.completed → `/events/order-completed`

All events are routed to the Flask service with dead letter queue support.

---

## Troubleshooting

### Dapr Initialization Failed

**Problem:** `dapr init` fails

**Solutions:**
```bash
# Uninstall and reinstall
dapr uninstall
dapr init

# Check Docker is running
docker ps

# Check Dapr status
dapr --version
```

### Dapr Sidecar Not Starting

**Problem:** Service starts but Dapr sidecar fails

**Solutions:**
```bash
# Check port 3500 is available
lsof -i :3500

# Verify components path
ls -la .dapr/components/

# Check component YAML syntax
dapr components -k .dapr/components/

# View Dapr logs
# Logs are shown in the same terminal where dapr run was executed
```

### Events Not Publishing

**Problem:** Events not appearing in RabbitMQ

**Solutions:**
```bash
# Verify RabbitMQ is running
docker ps | grep rabbitmq

# Check RabbitMQ queues
# Open http://localhost:15672 → Queues tab

# Verify event-bus component is loaded
dapr components -k .dapr/components/ | grep event-bus

# Check service logs for "Published event via Dapr"
```

### Events Not Being Received

**Problem:** Service doesn't receive subscribed events

**Solutions:**
```bash
# Verify subscriptions are loaded
curl http://localhost:3500/v1.0/metadata | jq .subscriptions

# Check subscription configuration
cat .dapr/components/subscriptions.yaml

# Test publishing directly to Dapr
curl -X POST http://localhost:3500/v1.0/publish/event-bus/product.created \
  -H "Content-Type: application/json" \
  -d '{"data": {"test": "value"}}'

# Check service logs for event handler execution
```

### Component Not Found Error

**Problem:** Dapr can't find components

**Solutions:**
```bash
# Verify components path is correct
dapr run --components-path ./.dapr/components/ ...

# Check component files exist
ls .dapr/components/*.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.dapr/components/event-bus.yaml'))"
```

---

## Dapr CLI Quick Reference

```bash
# Initialize Dapr
dapr init

# Run application with Dapr
dapr run --app-id inventory-service --app-port 8004 -- python run.py

# List Dapr applications
dapr list

# View Dapr logs
# Shown in terminal where dapr run was executed

# Stop Dapr application
# Press Ctrl+C in the terminal running dapr run

# Dapr dashboard
dapr dashboard

# Check components
dapr components -k ./.dapr/components/

# Uninstall Dapr
dapr uninstall
```

---

## Testing with Dapr

### Unit Tests (No Dapr Required)

```bash
# Unit tests mock Dapr client
pytest tests/unit/test_messaging.py -v
```

### Integration Tests (With Dapr)

```bash
# Start service with Dapr
dapr run --app-id inventory-service --app-port 8004 \
  --components-path ./.dapr/components -- python run.py &

# Wait for service to start
sleep 5

# Run integration tests
pytest tests/integration/ -v

# Stop Dapr app
dapr stop --app-id inventory-service
```

---

## Dapr vs Non-Dapr Development

| Feature | Without Dapr | With Dapr |
|---------|--------------|-----------|
| **Messaging** | Direct RabbitMQ SDK | Dapr pub/sub abstraction |
| **Service Discovery** | Manual URLs | Dapr service invocation |
| **Secrets** | Environment variables | Dapr secret store |
| **Observability** | Application logs only | Dapr metrics + tracing |
| **Setup Complexity** | Simpler | More components |
| **Production Similarity** | Less similar | Very similar |

**Recommendation:**
- Use **without Dapr** for quick iteration and simple debugging
- Use **with Dapr** before pushing to staging/production to catch integration issues

---

## Next Steps

- **Docker Compose with Dapr**: For full containerized setup, see docker-compose.yml
- **Deploy to Azure**: See [ACA_DEPLOYMENT.md](ACA_DEPLOYMENT.md) for Azure Container Apps
- **Deploy to Kubernetes**: See [AKS_DEPLOYMENT.md](AKS_DEPLOYMENT.md) for AKS deployment
