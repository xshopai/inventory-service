# 📦 Inventory Service

Inventory management microservice for xshopai - handles product stock levels, reservations, stock movements, and real-time inventory synchronization via event-driven architecture.

---

## 🎯 Features

- **Real-time Stock Management**: Track inventory levels across products and variants
- **Reservation System**: Time-limited stock reservations for orders
- **Event-Driven Architecture**: Pub/sub integration via Dapr
- **Multi-Platform Deployment**: Supports Azure Container Apps, AKS, App Service
- **Flexible Messaging**: Abstraction layer for Dapr, Service Bus, or RabbitMQ
- **Comprehensive Security**: JWT authentication + service token validation
- **Complete Audit Trail**: Stock movement history with full traceability

---

## 🚀 Quick Start - Local Development

### Prerequisites

Before starting, ensure you have:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **MySQL 8.0+** ([Download](https://dev.mysql.com/downloads/))
- **Dapr CLI 1.12+** ([Install Guide](https://docs.dapr.io/getting-started/install-dapr-cli/))
- **Docker & Docker Compose** (Optional, for containerized setup)

### Option 1: Docker Compose Setup (Recommended)

This is the **easiest** way to get started - everything runs in containers.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service
```

#### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
- Inventory Service (Flask app)
- MySQL database
- RabbitMQ message broker
- Dapr sidecar

#### Step 3: Verify Services Are Running

```bash
docker-compose ps
```

You should see all services in "Up" state.

#### Step 4: Access the Application

- **API Base**: http://localhost:8004/api
- **Health Check**: http://localhost:8004/health
- **API Docs**: http://localhost:8004/api/inventory/docs/

#### Step 5: Test the API

```bash
# Health check
curl http://localhost:8004/health

# Get inventory list (requires admin token - see Authentication section)
curl -H "Authorization: ****** <admin-jwt>" http://localhost:8004/api/inventory/
```

#### Stop Services

```bash
docker-compose down
```

---

### Option 2: Local Development (Without Docker)

For development with hot-reloading and debugging.

#### Step 1: Clone and Navigate

```bash
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service
```

#### Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (for testing)
pip install -r requirements-dev.txt
```

#### Step 4: Set Up MySQL Database

```bash
# Option A: Using Docker
docker run --name inventory-mysql -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=inventory_service_db \
  -e MYSQL_USER=admin -e MYSQL_PASSWORD=admin123 \
  -p 3306:3306 -d mysql:8.0

# Option B: Using local MySQL installation
mysql -u root -p
CREATE DATABASE inventory_service_db;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'admin123';
GRANT ALL PRIVILEGES ON inventory_service_db.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 5: Set Up RabbitMQ (for Dapr)

```bash
# Using Docker
docker run --name inventory-rabbitmq \
  -p 5672:5672 -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  -d rabbitmq:3-management
```

#### Step 6: Configure Environment Variables

Copy and configure the `.env` file:

```bash
cp .env .env.local
```

Edit `.env.local` and update these critical values:

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database (update if using different credentials)
# Dapr will load these from .dapr/secrets.json
# For local dev without Dapr, set DATABASE_URL directly

# Dapr Configuration
DAPR_HTTP_PORT=3500
DAPR_PUBSUB_NAME=event-bus

# Service Tokens (IMPORTANT: Update these!)
# Generate new tokens with: openssl rand -hex 12
PRODUCT_SERVICE_TOKEN=svc-product-service-<your-random-24-chars>
ORDER_SERVICE_TOKEN=svc-order-service-<your-random-24-chars>
CART_SERVICE_TOKEN=svc-cart-service-<your-random-24-chars>
WEB_BFF_TOKEN=svc-web-bff-<your-random-24-chars>
```

**Generate secure tokens:**
```bash
# Generate tokens (run 4 times for each service)
openssl rand -hex 12
```

#### Step 7: Initialize Dapr

```bash
# Initialize Dapr (one-time setup)
dapr init

# Verify Dapr installation
dapr --version
```

#### Step 8: Run Database Migrations

```bash
# Apply database migrations
flask db upgrade

# Or if using run script
python run.py db upgrade
```

#### Step 9: Start the Service with Dapr

```bash
# Run with Dapr sidecar (recommended)
dapr run --app-id inventory-service \
  --app-port 8004 \
  --dapr-http-port 3500 \
  --components-path ./.dapr/components \
  --config ./.dapr/config.yaml \
  -- python run.py

# Or use the convenience script
./run.sh  # Linux/Mac
run.ps1   # Windows
```

#### Step 10: Verify It's Working

```bash
# Check health
curl http://localhost:8004/health

# Check Dapr sidecar
curl http://localhost:3500/v1.0/metadata
```

---

## 🧪 Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

Coverage report will be in `htmlcov/index.html`

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E workflow tests
pytest tests/e2e/ -v

# Run a specific test file
pytest tests/unit/test_messaging.py -v
```

### Test with Different Messaging Providers

```bash
# Test with Dapr (default)
export MESSAGING_PROVIDER=dapr
pytest

# Test with RabbitMQ direct
export MESSAGING_PROVIDER=rabbitmq
export RABBITMQ_URL=******localhost:5672/
pytest

# Note: ServiceBus provider requires Azure credentials
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FLASK_ENV` | Environment mode | No | `development` |
| `SECRET_KEY` | Flask secret key | Yes | - |
| `DATABASE_URL` | MySQL connection string | No* | From Dapr secrets |
| `DAPR_HTTP_PORT` | Dapr sidecar HTTP port | No | `3500` |
| `DAPR_PUBSUB_NAME` | Dapr pub/sub component name | No | `event-bus` |
| `MESSAGING_PROVIDER` | Provider: dapr/servicebus/rabbitmq | No | `dapr` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `RESERVATION_TTL_MINUTES` | Reservation expiry time | No | `30` |

\* Database credentials loaded from `.dapr/secrets.json` in local dev, or Azure Key Vault in production

### Service Token Configuration

For service-to-service authentication, configure these tokens in `.env`:

```bash
# Generate tokens with: openssl rand -hex 12
PRODUCT_SERVICE_TOKEN=svc-product-service-a1b2c3d4e5f6g7h8i9j0k1l2
ORDER_SERVICE_TOKEN=svc-order-service-m3n4o5p6q7r8s9t0u1v2w3x4
CART_SERVICE_TOKEN=svc-cart-service-y5z6a7b8c9d0e1f2g3h4i5j6
WEB_BFF_TOKEN=svc-web-bff-k7l8m9n0o1p2q3r4s5t6u7v8
```

**Important**: These tokens must match in both the calling service and inventory-service.

### Messaging Provider Selection

The service supports multiple messaging backends through an abstraction layer:

```bash
# For Azure Container Apps / AKS (with Dapr)
export MESSAGING_PROVIDER=dapr
export DAPR_PUBSUB_NAME=inventory-pubsub

# For Azure App Service (without Dapr)
export MESSAGING_PROVIDER=servicebus
export SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
export SERVICEBUS_TOPIC_NAME="inventory-events"

# For local development (direct RabbitMQ)
export MESSAGING_PROVIDER=rabbitmq
export RABBITMQ_URL="******localhost:5672/"
export RABBITMQ_EXCHANGE="inventory-events"
```

---

## 📚 API Documentation

### Core Inventory APIs

#### List Inventory (Admin Only)
```bash
GET /api/inventory/
Authorization: ****** <admin-jwt>
Query Parameters:
  - page: Page number (default: 1)
  - per_page: Items per page (default: 20)
  - min_quantity: Filter by minimum available quantity
  - low_stock: true/false - only low stock items
```

#### Get Single Inventory Item
```bash
GET /api/inventory/{sku}
Returns: Inventory details for specified SKU
```

#### Batch Inventory Query
```bash
POST /api/inventory/batch
Content-Type: application/json

{
  "skus": ["SKU-001", "SKU-002", "SKU-003"],
  "in_stock_only": true  // Optional: filter out zero-quantity items
}

# Or use query parameter
POST /api/inventory/batch?inStockOnly=true
```

#### Create Inventory (Admin Only)
```bash
POST /api/inventory/
Authorization: ****** <admin-jwt>
Content-Type: application/json

{
  "sku": "SKU-NEW-001",
  "quantity": 100,
  "reorder_level": 10,
  "max_stock": 500
}
```

#### Update Inventory (Admin Only)
```bash
PUT /api/inventory/{sku}
Authorization: ****** <admin-jwt>
Content-Type: application/json

{
  "quantity": 150,
  "reorder_level": 15
}
```

#### Delete Inventory (Admin Only)
```bash
DELETE /api/inventory/{sku}
Authorization: ****** <admin-jwt>

Returns: 204 No Content
```

### Reservation APIs

#### Create Reservation
```bash
POST /api/reservations/
Content-Type: application/json

{
  "sku": "SKU-001",
  "order_id": "order-123",
  "quantity": 2
}
```

#### Confirm Reservation
```bash
POST /api/reservations/{reservation_id}/confirm
Content-Type: application/json

{
  "order_id": "order-123"
}
```

#### Release Reservation
```bash
POST /api/reservations/{reservation_id}/release

Returns: Reservation details with status updated to RELEASED
```

#### Cancel Reservation
```bash
DELETE /api/reservations/{reservation_id}

Returns: Success message
```

---

## 🔐 Authentication

The service uses two authentication mechanisms:

### 1. JWT for User Requests

Admin endpoints require JWT with `admin` role:

```bash
# Example JWT payload
{
  "id": "user-123",
  "email": "admin@example.com",
  "roles": ["admin"],
  "exp": 1234567890
}
```

### 2. Service Tokens for Service-to-Service Calls

Event handlers validate service tokens via `X-Service-Token` header:

```bash
curl -H "X-Service-Token: svc-product-service-a1b2c3..." \
  http://localhost:8004/events/product-created \
  -d '{"productId": "123", "action": "created"}'
```

---

## 🏗️ Architecture

### Layered Architecture

```
Controllers (HTTP handlers)
    ↓
Services (Business logic)
    ↓
Repositories (Data access)
    ↓
Database (MySQL)
```

### Messaging Architecture

```
Business Logic
    ↓
Event Publisher
    ↓
Messaging Abstraction Layer
    ├─ DaprProvider (Azure Container Apps/AKS)
    ├─ ServiceBusProvider (Azure App Service)
    └─ RabbitMQProvider (Local development)
    ↓
Message Brokers (RabbitMQ/Kafka/Service Bus)
```

### Database Schema

**inventory_items**
- `sku` (PK, unique) - Product SKU identifier
- `quantity_available` - Stock available for purchase
- `quantity_reserved` - Stock reserved by pending orders
- `reorder_level` - Minimum stock threshold
- `max_stock` - Maximum stock capacity

**reservations**
- `id` (PK, UUID) - Reservation identifier
- `order_id` - Associated order
- `sku` - Product SKU (FK)
- `quantity` - Reserved quantity
- `status` - PENDING, CONFIRMED, RELEASED, EXPIRED
- `expires_at` - Auto-expiration timestamp

**stock_movements**
- Audit trail of all inventory changes
- Types: IN, OUT, ADJUSTMENT, RESERVED, RELEASED

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check MySQL is running
docker ps | grep mysql

# Check connection string in .dapr/secrets.json
cat .dapr/secrets.json

# Test MySQL connection
mysql -h localhost -u admin -p inventory_service_db
```

#### 2. Dapr Initialization Failed

```bash
# Reinitialize Dapr
dapr uninstall
dapr init

# Verify Dapr components
dapr components -k .dapr/components/
```

#### 3. RabbitMQ Connection Error

```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq

# Access RabbitMQ management UI
open http://localhost:15672  # guest/guest
```

#### 4. Migration Issues

```bash
# Check current migration version
flask db current

# Apply pending migrations
flask db upgrade

# If migrations fail, reset database
docker-compose down -v
docker-compose up -d
flask db upgrade
```

#### 5. Service Token Validation Errors

If you see "Service authentication failed" in logs:

```bash
# Verify token is set in .env
grep SERVICE_TOKEN .env

# Verify token header in request
curl -v -H "X-Service-Token: svc-product-service-..." \
  http://localhost:8004/events/product-created
```

#### 6. Import Errors

```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📊 Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_messaging.py -v

# Run with coverage
pytest tests/unit/ --cov=src/messaging --cov-report=term-missing
```

### Integration Tests

```bash
# Requires database
pytest tests/integration/ -v
```

### E2E Tests

```bash
# Full workflow tests
pytest tests/e2e/ -v
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report in browser
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

---

## 🚢 Deployment

### Azure Container Apps

```bash
# Set messaging provider
az containerapp update \
  --name inventory-service \
  --set-env-vars MESSAGING_PROVIDER=dapr

# Dapr sidecar is automatically configured
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

### Azure App Service

```bash
# Configure Service Bus (no Dapr available)
az webapp config appsettings set \
  --name inventory-service \
  --settings MESSAGING_PROVIDER=servicebus \
             SERVICEBUS_CONNECTION_STRING="<from-keyvault>" \
             SERVICEBUS_TOPIC_NAME=inventory-events
```

---

## 🔍 Monitoring & Observability

### Health Check Endpoint

```bash
curl http://localhost:8004/health
```

Response:
```json
{
  "status": "healthy",
  "service": "inventory-service",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "messaging": "ok"
  }
}
```

### Logs

```bash
# View application logs
docker-compose logs -f inventory-service

# View Dapr logs
docker-compose logs -f inventory-service-dapr

# Filter for errors only
docker-compose logs inventory-service | grep ERROR
```

### Metrics

Dapr automatically collects metrics. Access via:

```bash
# Dapr metrics endpoint
curl http://localhost:9090/metrics
```

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/your-feature`
3. **Make changes** with tests
4. **Run tests**: `pytest --cov=src`
5. **Run linter**: `flake8 src tests`
6. **Format code**: `black src tests`
7. **Commit**: `git commit -m "Add feature"`
8. **Push**: `git push origin feature/your-feature`
9. **Create Pull Request**

---

## 📖 Additional Documentation

- **PRD**: See `docs/PRD.md` for product requirements
- **Architecture**: See `docs/ARCHITECTURE.md` for technical architecture
- **Security**: See `.github/SECURITY.md` for security practices

---

## 📝 License

This project is part of the xshopai e-commerce platform. All rights reserved.

---

## 💡 Quick Reference

### Start Service (Local)
```bash
source venv/bin/activate
dapr run --app-id inventory-service --app-port 8004 --components-path ./.dapr/components -- python run.py
```

### Start Service (Docker)
```bash
docker-compose up -d
```

### Run Tests
```bash
pytest --cov=src --cov-report=term-missing
```

### Generate Service Token
```bash
openssl rand -hex 12
```

### Check Service Health
```bash
curl http://localhost:8004/health
```

### View Logs
```bash
docker-compose logs -f inventory-service
```

---

## 🆘 Support

- **Issues**: Create GitHub issues for bugs
- **Questions**: Use GitHub Discussions
- **Slack**: #inventory-service channel (internal)
- **Email**: dev@xshopai.com
