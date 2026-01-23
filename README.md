# 📦 Inventory Service

Inventory management microservice for xshopai e-commerce platform. Handles real-time stock levels, reservations, stock movements, and event-driven inventory synchronization.

---

## �� Key Features

- **Real-time Stock Management** - Track inventory across products and variants
- **Reservation System** - Time-limited stock reservations for order processing
- **Event-Driven Architecture** - Pub/sub integration for inventory updates
- **Multi-Platform Deployment** - Azure Container Apps, AKS, or local development
- **Messaging Abstraction** - Flexible provider support (Dapr, Service Bus, RabbitMQ)
- **Comprehensive Security** - JWT authentication + service token validation
- **Complete Audit Trail** - Full history of all stock movements

---

## 🚀 Getting Started

### Quick Start with Docker Compose

```bash
# Clone repository
git clone https://github.com/xshopai/inventory-service.git
cd inventory-service

# Start all services
docker-compose up -d

# Verify health
curl http://localhost:8004/health
```

### Local Development

Choose your setup path:

- **[Local Development (Without Dapr)](docs/LOCAL_DEVELOPMENT.md)** - Simple setup for quick development
- **[Local Development with Dapr](docs/LOCAL_DEVELOPMENT_DAPR.md)** - Production-like environment locally

### Cloud Deployment

Deploy to Azure:

- **[Azure Container Apps](docs/ACA_DEPLOYMENT.md)** - Serverless containers with built-in Dapr
- **[Azure Kubernetes Service](docs/AKS_DEPLOYMENT.md)** - Full Kubernetes deployment with Dapr

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[Local Development](docs/LOCAL_DEVELOPMENT.md)** | Step-by-step local setup without Dapr |
| **[Local Development with Dapr](docs/LOCAL_DEVELOPMENT_DAPR.md)** | Local setup with Dapr integration |
| **[Azure Container Apps](docs/ACA_DEPLOYMENT.md)** | Deploy to Azure Container Apps |
| **[Azure Kubernetes](docs/AKS_DEPLOYMENT.md)** | Deploy to AKS with Dapr |
| **[Product Requirements](docs/PRD.md)** | Complete API specification and requirements |
| **[Architecture](docs/ARCHITECTURE.md)** | System architecture and design patterns |
| **[Security](/.github/SECURITY.md)** | Security policies and practices |

---

## 🧪 Testing

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Test Results:**
- ✅ 33 unit tests passing
- ✅ 91.4% code coverage on new features
- ✅ 0 security vulnerabilities (CodeQL)

---

## 🏗️ Project Structure

```
inventory-service/
├── src/                      # Application source code
│   ├── controllers/          # API endpoints
│   ├── services/             # Business logic
│   ├── repositories/         # Data access layer
│   ├── models/               # Database models
│   ├── messaging/            # Messaging abstraction layer
│   ├── middlewares/          # Auth, logging, tracing
│   └── utils/                # Helper functions
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── migrations/               # Database migrations (Alembic)
├── .dapr/                    # Dapr configuration
│   ├── components/           # Dapr components (pub/sub, secrets)
│   └── config.yaml           # Dapr configuration
├── docs/                     # Documentation
└── docker-compose.yml        # Local containerized setup
```

---

## 🔧 Tech Stack

- **Framework**: Flask 3.0+ with Flask-RESTX
- **Database**: MySQL 8.0+ (via SQLAlchemy ORM)
- **Messaging**: Dapr / Azure Service Bus / RabbitMQ
- **Event Format**: CloudEvents 1.0
- **Testing**: pytest with coverage
- **Migrations**: Alembic (Flask-Migrate)
- **Authentication**: JWT + Service Tokens
- **Observability**: Structured logging, distributed tracing

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run tests (`pytest`)
5. Run code quality checks (`black . && flake8`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open Pull Request

---

## 📝 License

This project is part of the xshopai e-commerce platform. All rights reserved.

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/xshopai/inventory-service/issues)
- **Documentation**: See `docs/` folder
- **API Reference**: See [docs/PRD.md](docs/PRD.md)

---

## ⚡ Quick Commands

```bash
# Start with Docker Compose
docker-compose up -d

# Run locally without Dapr
python run.py

# Run locally with Dapr
dapr run --app-id inventory-service --app-port 8004 -- python run.py

# Run tests
pytest tests/unit/ -v

# Health check
curl http://localhost:8004/health
```

For detailed instructions, see the documentation guides linked above.
