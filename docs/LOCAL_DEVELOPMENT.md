# Local Development Setup Guide

This guide provides step-by-step instructions for setting up the Inventory Service in your local development environment **without Dapr**.

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **MySQL 8.0+** - [Download MySQL](https://dev.mysql.com/downloads/)
- **Git** - [Install Git](https://git-scm.com/downloads)
- **Docker & Docker Compose** (Optional) - For containerized dependencies

---

## Step-by-Step Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service
```

### Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Python Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (for testing, linting)
pip install -r requirements-dev.txt
```

### Step 4: Set Up MySQL Database

**Option A: Using Docker (Recommended)**

```bash
docker run --name inventory-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=inventory_service_db \
  -e MYSQL_USER=admin \
  -e MYSQL_PASSWORD=admin123 \
  -p 3306:3306 \
  -d mysql:8.0
```

**Option B: Using Local MySQL Installation**

```bash
# Connect to MySQL as root
mysql -u root -p

# Create database and user
CREATE DATABASE inventory_service_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'admin123';
GRANT ALL PRIVILEGES ON inventory_service_db.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 5: Configure Environment Variables

Create a local environment file:

```bash
cp .env .env.local
```

Edit `.env.local` with your settings:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-dev-secret-key-change-me

# Database Configuration
DATABASE_URL=mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db

# Messaging Provider (use 'rabbitmq' for local without Dapr)
MESSAGING_PROVIDER=rabbitmq
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=inventory-events

# Service Tokens - Generate with: openssl rand -hex 12
PRODUCT_SERVICE_TOKEN=svc-product-service-<generate-24-chars>
ORDER_SERVICE_TOKEN=svc-order-service-<generate-24-chars>
CART_SERVICE_TOKEN=svc-cart-service-<generate-24-chars>
WEB_BFF_TOKEN=svc-web-bff-<generate-24-chars>

# Logging
LOG_LEVEL=DEBUG

# Reservation Settings
RESERVATION_TTL_MINUTES=30
```

**Generate secure tokens:**
```bash
openssl rand -hex 12
```
Run this command 4 times and use the outputs for each service token.

### Step 6: Set Up RabbitMQ Message Broker

**Using Docker:**

```bash
docker run --name inventory-rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  -d rabbitmq:3-management
```

**Verify RabbitMQ is running:**

```bash
# Check container status
docker ps | grep rabbitmq

# Access management UI (optional)
# Open http://localhost:15672 in browser
# Login: guest/guest
```

### Step 7: Initialize Database Schema

Run database migrations to create tables:

```bash
# Set Flask app environment variable
export FLASK_APP=run.py

# Run migrations
flask db upgrade
```

**Verify database tables were created:**

```bash
mysql -u admin -padmin123 inventory_service_db -e "SHOW TABLES;"
```

You should see:
- inventory_items
- reservations
- stock_movements
- alembic_version

### Step 8: Start the Service

```bash
# Load environment variables from .env.local
export $(cat .env.local | grep -v '^#' | xargs)

# Run the service
python run.py
```

The service should start on http://localhost:8004

### Step 9: Verify Service is Running

Open a new terminal and test the endpoints:

```bash
# Health check
curl http://localhost:8004/health

# Expected response:
# {"status": "healthy", "service": "inventory-service", ...}
```

### Step 10: Run Tests

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Run unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=src --cov-report=term-missing

# Run all tests
pytest tests/ -v
```

---

## Development Workflow

### Making Code Changes

1. Make changes in `src/` directory
2. Flask development server auto-reloads when files change
3. Check logs in terminal for errors
4. Test changes manually with curl or Postman

### Database Changes

```bash
# After modifying models in src/models/
# Create new migration
flask db migrate -m "Description of database changes"

# Review generated migration in migrations/versions/

# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Running Specific Tests

```bash
# Test specific file
pytest tests/unit/test_messaging.py -v

# Test specific class
pytest tests/unit/test_messaging.py::TestDaprProvider -v

# Test specific function
pytest tests/unit/test_messaging.py::TestDaprProvider::test_init_default_params -v

# Run with coverage for specific modules
pytest tests/unit/ --cov=src/messaging --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Code Quality Checks

```bash
# Format code with Black
black src tests

# Check code style
flake8 src tests

# Sort imports
isort src tests
```

---

## Troubleshooting

### MySQL Connection Issues

**Problem:** Can't connect to MySQL database

**Solutions:**
```bash
# Verify MySQL is running
docker ps | grep mysql
# OR for local MySQL:
sudo systemctl status mysql

# Test connection
mysql -h localhost -u admin -padmin123 -e "SELECT 1;"

# Check if port 3306 is available
lsof -i :3306

# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: mysql+pymysql://user:password@host:port/database
```

### RabbitMQ Connection Issues

**Problem:** Messaging provider errors

**Solutions:**
```bash
# Verify RabbitMQ is running
docker ps | grep rabbitmq

# Check RabbitMQ logs
docker logs inventory-rabbitmq

# Restart RabbitMQ
docker restart inventory-rabbitmq

# Access management UI to verify
open http://localhost:15672
```

### Port Conflict

**Problem:** Port 8004 already in use

**Solutions:**
```bash
# Find process using port
lsof -i :8004
# OR on Linux:
sudo netstat -tlnp | grep :8004

# Stop conflicting process or use different port
export PORT=8005
python run.py
```

### Import Errors

**Problem:** ModuleNotFoundError when running service

**Solutions:**
```bash
# Verify virtual environment is activated
which python  # Should show venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path includes current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Migration Issues

**Problem:** Database migration fails

**Solutions:**
```bash
# Check current migration version
flask db current

# Show migration history
flask db history

# Reset database (WARNING: destroys all data)
flask db downgrade base
flask db upgrade

# Or drop and recreate database
mysql -u admin -padmin123 -e "DROP DATABASE inventory_service_db; CREATE DATABASE inventory_service_db;"
flask db upgrade
```

---

## Quick Reference Commands

```bash
# Start MySQL (Docker)
docker start inventory-mysql

# Start RabbitMQ (Docker)
docker start inventory-rabbitmq

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env.local | grep -v '^#' | xargs)

# Run service
python run.py

# Run tests
pytest tests/unit/ -v

# Generate service token
openssl rand -hex 12

# Check service health
curl http://localhost:8004/health

# View RabbitMQ management
open http://localhost:15672

# Access database
mysql -u admin -padmin123 inventory_service_db
```

---

## Next Steps

- **Add Dapr Integration**: See [LOCAL_DEVELOPMENT_DAPR.md](LOCAL_DEVELOPMENT_DAPR.md)
- **Deploy to Azure**: See [ACA_DEPLOYMENT.md](ACA_DEPLOYMENT.md) or [AKS_DEPLOYMENT.md](AKS_DEPLOYMENT.md)
- **API Reference**: See [PRD.md](PRD.md) for complete API documentation
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
