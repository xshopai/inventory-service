# Local Development Guide

This guide covers running the Inventory Service locally using RabbitMQ connection for messaging.

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
* Running on http://0.0.0.0:8005
```

---

## Step 3: Verify the Service

### Health Check

```bash
# Readiness check (verifies database connection)
curl http://localhost:8005/health/ready

# Liveness check
curl http://localhost:8005/health/live
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