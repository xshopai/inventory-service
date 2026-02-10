<div align="center">

# 📦 Inventory Service

**Enterprise-grade inventory management microservice for the xshopai e-commerce platform**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![Dapr](https://img.shields.io/badge/Dapr-Enabled-0D597F?style=for-the-badge&logo=dapr&logoColor=white)](https://dapr.io)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

[Getting Started](#-getting-started) •
[Documentation](#-documentation) •
[API Reference](docs/PRD.md) •
[Contributing](#-contributing)

</div>

---

## 🎯 Overview

The **Inventory Service** is a critical microservice responsible for managing real-time stock levels, reservations, stock movements, and event-driven inventory synchronization across the xshopai platform. Built with scalability and reliability in mind, it supports multi-cloud deployments and integrates seamlessly with the broader microservices ecosystem.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 📊 Stock Management

- Real-time inventory tracking
- Multi-variant product support
- Low stock alerts & thresholds
- Automatic stock reconciliation

</td>
<td width="50%">

### 🔒 Reservation System

- Time-limited stock reservations
- Automatic expiration handling
- Order processing integration
- Concurrent access control

</td>
</tr>
<tr>
<td width="50%">

### 📡 Event-Driven Architecture

- CloudEvents 1.0 specification
- Pub/sub messaging integration
- Real-time inventory updates
- Cross-service synchronization

</td>
<td width="50%">

### 🛡️ Enterprise Security

- JWT token authentication
- Service-to-service tokens
- Role-based access control
- Complete audit trail

</td>
</tr>
</table>

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Docker & Docker Compose (optional)
- Dapr CLI (for production-like setup)

### Quick Start with Docker Compose

```bash
# Clone the repository
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service

# Start all services (MySQL, service, etc.)
docker-compose up -d

# Verify the service is healthy
curl http://localhost:8005/health
```

### Local Development Setup

<details>
<summary><b>🔧 Without Dapr (Simple Setup)</b></summary>

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
flask db upgrade

# Start the service
python run.py
```

📖 See [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) for detailed instructions.

</details>

<details>
<summary><b>⚡ With Dapr (Production-like)</b></summary>

```bash
# Ensure Dapr is initialized
dapr init

# Start with Dapr sidecar
dapr run \
  --app-id inventory-service \
  --app-port 8005 \
  --dapr-http-port 3500 \
  --resources-path .dapr/components \
  --config .dapr/config.yaml \
  -- python run.py
```

> **Note:** All services now use the standard Dapr ports (3500 for HTTP, 50001 for gRPC). This simplifies configuration and works consistently whether running via Docker Compose or individual service runs.

📖 See [Dapr Development Guide](docs/LOCAL_DEVELOPMENT_DAPR.md) for detailed instructions.

</details>

---

## 📚 Documentation

| Document                                                         | Description                                          |
| :--------------------------------------------------------------- | :--------------------------------------------------- |
| 📘 [Local Development](docs/LOCAL_DEVELOPMENT.md)                | Step-by-step local setup without Dapr                |
| ⚡ [Local Development with Dapr](docs/LOCAL_DEVELOPMENT_DAPR.md) | Local setup with full Dapr integration               |
| ☁️ [Azure Container Apps](docs/ACA_DEPLOYMENT.md)                | Deploy to serverless containers with built-in Dapr   |
| 📋 [Product Requirements](docs/PRD.md)                           | Complete API specification and business requirements |
| 🏗️ [Architecture](docs/ARCHITECTURE.md)                          | System design, patterns, and data flows              |
| 🔐 [Security](.github/SECURITY.md)                               | Security policies and vulnerability reporting        |

---

## 🧪 Testing

We maintain high code quality standards with comprehensive test coverage.

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_inventory_service.py -v

# Run integration tests (requires running services)
pytest tests/integration/ -v
```

### Test Coverage

| Metric        | Status               |
| :------------ | :------------------- |
| Unit Tests    | ✅ 33 passing        |
| Code Coverage | ✅ 91.4%             |
| Security Scan | ✅ 0 vulnerabilities |

---

## 🏗️ Project Structure

```
inventory-service/
├── 📁 src/                       # Application source code
│   ├── 📁 controllers/           # REST API endpoints
│   ├── 📁 services/              # Business logic layer
│   ├── 📁 repositories/          # Data access layer
│   ├── 📁 models/                # SQLAlchemy models
│   ├── 📁 messaging/             # Messaging abstraction (Dapr/ServiceBus/RabbitMQ)
│   ├── 📁 middlewares/           # Authentication, logging, tracing
│   └── 📁 utils/                 # Helper functions & utilities
├── 📁 tests/                     # Test suite
│   ├── 📁 unit/                  # Unit tests
│   ├── 📁 integration/           # Integration tests
│   └── 📁 e2e/                   # End-to-end tests
├── 📁 migrations/                # Alembic database migrations
├── 📁 .dapr/                     # Dapr configuration
│   ├── 📁 components/            # Pub/sub, secrets, state stores
│   └── 📄 config.yaml            # Dapr runtime configuration
├── 📁 docs/                      # Documentation
├── 📄 docker-compose.yml         # Local containerized environment
├── 📄 Dockerfile                 # Production container image
└── 📄 requirements.txt           # Python dependencies
```

---

## 🔧 Technology Stack

| Category          | Technology                                    |
| :---------------- | :-------------------------------------------- |
| 🐍 Runtime        | Python 3.11+                                  |
| 🌐 Framework      | Flask 3.0+ with Flask-RESTX (OpenAPI/Swagger) |
| 🗄️ Database       | MySQL 8.0+ with SQLAlchemy ORM                |
| 📨 Messaging      | Dapr Pub/Sub, Azure Service Bus, RabbitMQ     |
| 📋 Event Format   | CloudEvents 1.0 Specification                 |
| 🔐 Authentication | JWT Tokens + Service-to-Service Tokens        |
| 🧪 Testing        | pytest with coverage reporting                |
| 📊 Observability  | Structured logging, distributed tracing       |

---

## ⚡ Quick Reference

```bash
# 🐳 Docker Compose
docker-compose up -d              # Start all services
docker-compose down               # Stop all services
docker-compose logs -f inventory  # View logs

# 🐍 Local Development
python run.py                     # Run without Dapr
flask db upgrade                  # Apply migrations
flask db migrate -m "message"     # Create migration

# ⚡ Dapr Development
dapr run --app-id inventory-service --app-port 8005 -- python run.py

# 🧪 Testing
pytest tests/unit/ -v             # Run unit tests
pytest --cov=src                  # Run with coverage

# 🔍 Health Check
curl http://localhost:8005/health
curl http://localhost:8005/health/ready
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Write** tests for your changes
4. **Run** the test suite
   ```bash
   pytest && black . && flake8
   ```
5. **Commit** your changes
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
6. **Push** to your branch
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open** a Pull Request

Please ensure your PR:

- ✅ Passes all existing tests
- ✅ Includes tests for new functionality
- ✅ Follows the existing code style
- ✅ Updates documentation as needed

---

## 🆘 Support

| Resource         | Link                                                                           |
| :--------------- | :----------------------------------------------------------------------------- |
| 🐛 Bug Reports   | [GitHub Issues](https://github.com/xshopai/inventory-service/issues)           |
| 📖 Documentation | [docs/](docs/)                                                                 |
| 📋 API Reference | [docs/PRD.md](docs/PRD.md)                                                     |
| 💬 Discussions   | [GitHub Discussions](https://github.com/xshopai/inventory-service/discussions) |

---

## 📄 License

This project is part of the **xshopai** e-commerce platform.  
© 2026 xshopai. All rights reserved.

---

<div align="center">

**[⬆ Back to Top](#-inventory-service)**

Made with ❤️ by the xshopai team

</div>
