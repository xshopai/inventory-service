# Local Development Guide (without Dapr)

This guide covers running the Inventory Service locally without Dapr, using direct RabbitMQ connection for messaging.

> **📋 Prerequisites**: Complete the [Prerequisites & Common Setup](PREREQUISITES.md) before following this guide.

---

## Overview

This setup uses:

- **Flask development server** for the application
- **Direct RabbitMQ connection** for messaging (via Pika library)
- Simpler configuration, good for basic development and debugging

For production-like local development with Dapr, see [Local Development with Dapr](LOCAL_DEVELOPMENT_DAPR.md).

---

## Step 1: Configure Environment for Non-Dapr Mode

Copy the local environment template to `.env`:

```bash
# On Linux / Mac / Bash:
cp .env.local .env

# On Windows (PowerShell):
Copy-Item .env.local .env
```

The `.env.local` file contains:

```bash
PORT=8004

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-dev-secret-key-change-me

# Database Configuration
DATABASE_URL=mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db

# Messaging Configuration - Direct RabbitMQ
MESSAGING_PROVIDER=rabbitmq
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=inventory-events

# JWT Configuration (required for non-Dapr mode)
JWT_SECRET=8tDBDMcpxroHoHjXjk8xp/uAn8rzD4y8ZZremFkC4gI=

# Service Tokens (for service-to-service communication)
PRODUCT_SERVICE_TOKEN=svc-product-service-4ff5876fc86cc45a18d88e5d
ORDER_SERVICE_TOKEN=svc-order-service-4ff5876fc86cc45a18d88e5d
CART_SERVICE_TOKEN=svc-cart-service-4ff5876fc86cc45a18d88e5d
WEB_BFF_TOKEN=svc-web-bff-4ff5876fc86cc45a18d88e5d

# Logging
LOG_LEVEL=DEBUG
```

> **Note**:
>
> - `MESSAGING_PROVIDER=rabbitmq` uses direct RabbitMQ connection (no Dapr required)
> - `JWT_SECRET` is required for non-Dapr mode (in Dapr mode, it's retrieved from the Secret Store)
> - Service tokens must match tokens configured in calling services

---

## Step 2: Start the Service

```bash
# Make sure virtual environment is activated
# On Linux/Mac:
source venv/bin/activate

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On Windows (Git Bash):
source venv/Scripts/activate

# Start the Flask development server
python run.py
```

Expected output:

```
* Serving Flask app 'src'
* Debug mode: on
* Running on http://0.0.0.0:8004
```

---

## Step 3: Verify the Service

### Health Check

```bash
# Basic health check
curl http://localhost:8004/health

# Readiness check (verifies database connection)
curl http://localhost:8004/health/ready

# Liveness check
curl http://localhost:8004/health/live
```

## Step 4: Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_inventory.py -v

# Run specific test
pytest tests/test_inventory.py::test_create_inventory_item -v
```

---

## Common Tasks

### View Logs

Logs are output to console in development mode. Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

### Database Operations

```bash
# Create a new migration after model changes
flask db migrate -m "description of change"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Reset Database

```bash
# Drop and recreate (WARNING: destroys all data)
mysql -u admin -padmin123 -e "DROP DATABASE inventory_service_db; CREATE DATABASE inventory_service_db;"
flask db upgrade
```

---

## Next Steps

- For production-like local development with Dapr: [Local Development with Dapr](LOCAL_DEVELOPMENT_DAPR.md)
- Review the [Architecture Documentation](ARCHITECTURE.md) for service design details

---
