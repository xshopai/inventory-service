# Prerequisites & Common Setup

This guide covers the common prerequisites and setup steps required for local development of the Inventory Service. Complete these steps before proceeding to either:

- [Local Development (without Dapr)](LOCAL_DEVELOPMENT.md)
- [Local Development with Dapr](LOCAL_DEVELOPMENT_DAPR.md)

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Tool                    | Version | Download                                                      |
| ----------------------- | ------- | ------------------------------------------------------------- |
| Python                  | 3.11+   | [python.org](https://www.python.org/downloads/)               |
| Git                     | Latest  | [git-scm.com](https://git-scm.com/downloads)                  |
| Docker & Docker Compose | Latest  | [docker.com](https://www.docker.com/products/docker-desktop/) |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service
```

---

## Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On Windows (Git Bash):
source venv/Scripts/activate
```

You should see `(venv)` in your terminal prompt.

---

## Step 3: Install Python Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (for testing, linting)
pip install -r requirements-dev.txt
```

---

## Step 4: Set Up MySQL Database

### Option A: Using Docker Compose (Recommended)

```bash
# Create the Docker network (first time only)
docker network create xshopai-network

# Start MySQL using docker-compose
docker-compose up -d inventory-mysql
```

This uses the pre-configured settings from `docker-compose.yml`:

- Database: `inventory_service_db`
- User: `admin` / Password: `admin123`
- Port: `3306`

### Option B: Using Docker Run

```bash
docker run --name inventory-mysql \
  -e MYSQL_ROOT_PASSWORD=inventory_root_pass_123 \
  -e MYSQL_DATABASE=inventory_service_db \
  -e MYSQL_USER=admin \
  -e MYSQL_PASSWORD=admin123 \
  -p 3306:3306 \
  -d mysql:latest
```

### Option C: Using Local MySQL Installation

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

### Verify MySQL is Running

```bash
# Check container is running
docker ps | grep mysql

# Test connection (using Docker exec)
docker exec inventory-mysql mysql -u admin -padmin123 -e "SELECT 1"

# Or connect interactively
docker exec -it inventory-mysql mysql -u admin -padmin123 inventory_service_db
```

---

## Step 5: Set Up RabbitMQ Message Broker

> **Note**: RabbitMQ is a shared infrastructure component used by multiple services. You only need to create it once. Skip this step if RabbitMQ is already running.

### Using Docker

```bash
docker run --name xshopai-rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  -d rabbitmq:3-management
```

### Verify RabbitMQ is Running

```bash
# Check container status
docker ps | grep rabbitmq

# Access management UI (optional)
# Open http://localhost:15672 in browser
# Login: guest/guest
```

---

## Step 6: Configure Environment Variables

Edit the `.env` file with your local settings:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-dev-secret-key-change-me

# Database Configuration
DATABASE_URL=mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db

# Service Tokens - Generate with: openssl rand -hex 12
PRODUCT_SERVICE_TOKEN=svc-product-<generate-24-chars>
ORDER_SERVICE_TOKEN=svc-order-<generate-24-chars>
CART_SERVICE_TOKEN=svc-cart-<generate-24-chars>
WEB_BFF_TOKEN=svc-webbff-<generate-24-chars>

# Logging
LOG_LEVEL=DEBUG
```

### Generate Secure Tokens

```bash
# Run this command 4 times for each service token
openssl rand -hex 12
```

---

## Step 7: Initialize Database Schema

Run database migrations to create tables:

```bash
# Set Flask app environment variable
# On Linux/Mac:
export FLASK_APP=run.py

# On Windows (PowerShell):
$env:FLASK_APP="run.py"

# On Windows (Command Prompt):
set FLASK_APP=run.py

# On Windows (Git Bash):
export FLASK_APP=run.py

# Run migrations
flask db upgrade
```

### Verify Database Tables

```bash
# Using docker exec (works on all platforms)
docker exec inventory-mysql mysql -u admin -padmin123 inventory_service_db -e "SHOW TABLES;"

# Or if you have MySQL client installed locally:
mysql -u admin -padmin123 inventory_service_db -e "SHOW TABLES;"
```

You should see:

- `inventory_items`
- `reservations`
- `stock_movements`
- `alembic_version`

---

## Quick Start with Docker Compose

Start MySQL with a single command:

```bash
# Start MySQL
docker-compose up -d inventory-mysql

# Verify it's running
docker-compose ps
```

> **Note**: RabbitMQ must be started separately using `docker run` (see Step 5) as it's not included in docker-compose.yml.

---

## Next Steps

Once you've completed these prerequisites, proceed to:

- **[Local Development (without Dapr)](LOCAL_DEVELOPMENT.md)** - Simple setup using direct RabbitMQ connection
- **[Local Development with Dapr](LOCAL_DEVELOPMENT_DAPR.md)** - Production-like setup with Dapr sidecar

---
