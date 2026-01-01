# 📦 Inventory Service

Inventory management microservice for xShop.ai - handles product stock levels, reservations, stock movements, and automated alerts.

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+ ([Download](https://www.python.org/downloads/))
- **MySQL** 8.0+ ([Download](https://dev.mysql.com/downloads/))
- **Redis** 7+ ([Install Guide](https://redis.io/docs/getting-started/))
- **Dapr CLI** 1.16+ ([Install Guide](https://docs.dapr.io/getting-started/install-dapr-cli/))

### Using Docker Compose (Recommended)

**1. Start All Services**
```bash
cd inventory-service
docker-compose up -d
```

**2. Verify Services**
```bash
docker-compose ps
```

**3. Access the API**
- API Base URL: http://localhost:5003/api/v1
- Documentation: http://localhost:5003/api/v1/docs/
- Health Check: http://localhost:5003/api/v1/health/

### Local Development Setup

**1. Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**2. Install Dependencies**
```bash
pip install -r requirements.txt
```

**3. Set Environment Variables**
```bash
export FLASK_ENV=development
export DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/inventory_db
export REDIS_URL=redis://localhost:6379/0
```

**4. Initialize Database**
```bash
python -c "from app import create_app; from app.models import db; app = create_app('development'); app.app_context().push(); db.create_all()"
```

**5. Run Application**
```bash
python run.py
```

### Common Commands

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Lint code
flake8 app tests

# Format code
black app tests
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [📖 Developer Guide](docs/DEVELOPER_GUIDE.md) | Local setup, debugging, daily workflows |
| [📘 Technical Reference](docs/TECHNICAL.md) | Architecture, security, monitoring |
| [🤝 Contributing](docs/CONTRIBUTING.md) | Contribution guidelines and workflow |

**API Documentation**: Flask-RESTX auto-generates interactive docs at `/api/v1/docs/`.

## ⚙️ Configuration

### Inventory Management

- `GET /api/v1/inventory/` - List inventory items with filtering
- `POST /api/v1/inventory/` - Create new inventory item
- `GET /api/v1/inventory/{product_id}` - Get inventory by product ID
- `PUT /api/v1/inventory/{product_id}` - Update inventory item
- `DELETE /api/v1/inventory/{product_id}` - Delete inventory item
- `POST /api/v1/inventory/{product_id}/adjust` - Adjust stock levels
- `POST /api/v1/inventory/bulk` - Bulk inventory operations

### Reservation Management

- `GET /api/v1/reservations/` - List reservations with filtering
- `POST /api/v1/reservations/` - Create new reservation
- `GET /api/v1/reservations/{id}` - Get reservation details
- `DELETE /api/v1/reservations/{id}` - Cancel reservation
- `POST /api/v1/reservations/confirm` - Confirm multiple reservations

### Health & Monitoring

- `GET /api/v1/health/` - Health check endpoint

## Environment Variables

| Variable                | Description                                  | Default    |
| ----------------------- | -------------------------------------------- | ---------- |
| `FLASK_ENV`             | Environment (development/testing/production) | production |
| `DATABASE_URL`          | MySQL database connection string             | Required   |
| `REDIS_URL`             | Redis connection string                      | Required   |
| `PRODUCT_SERVICE_URL`   | Product service base URL                     | Optional   |
| `CACHE_DEFAULT_TIMEOUT` | Cache TTL in seconds                         | 300        |
| `HOST`                  | Server host                                  | 0.0.0.0    |
| `PORT`                  | Server port                                  | 5000       |

## Running Tests

### Full Test Suite

```bash
pytest
```

### With Coverage Report

```bash
pytest --cov=app --cov-report=html
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/test_models.py tests/test_services.py

# Integration tests only
pytest tests/test_controllers.py

# Repository tests
pytest tests/test_repositories.py
```

## Database Schema

### Inventory Items

- Tracks product stock levels and locations
- Supports minimum/maximum stock thresholds
- Automated low stock alerts

### Reservations

- Time-limited inventory reservations
- Supports order-based grouping
- Automatic expiration handling

### Stock Movements

- Complete audit trail of stock changes
- Multiple movement types (inbound, outbound, adjustment, etc.)
- Reference tracking for traceability

## Caching Strategy

- **Inventory Items**: Cached by product ID with TTL
- **Product Details**: External service responses cached
- **Search Results**: Paginated results cached temporarily
- **Health Checks**: Component status cached briefly

## Performance Features

- **Database Indexing**: Optimized indexes for common queries
- **Connection Pooling**: SQLAlchemy connection pooling
- **Async Processing**: Background tasks for non-critical operations
- **Query Optimization**: Efficient joins and aggregations
- **Bulk Operations**: Batch processing for large datasets

## Security Features

- **Input Validation**: Marshmallow schema validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Error Handling**: Secure error responses
- **Health Checks**: Service availability monitoring

## Monitoring & Observability

### Health Checks

```bash
curl http://localhost:5003/api/v1/health/
```

### Docker Container Logs

```bash
docker-compose logs -f inventory-service
```

### Database Monitoring

```bash
# Access Adminer (if enabled)
docker-compose --profile tools up -d
# Visit http://localhost:8081
```

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/new-feature`
2. **Make changes**: Implement features with tests
3. **Run tests**: `pytest --cov=app`
4. **Check code quality**: `black . && flake8`
5. **Test in Docker**: `docker-compose up --build`
6. **Submit PR**: Create pull request with description

## Production Deployment

### Docker Production Build

```bash
docker build -t inventory-service:latest .
docker run -p 5000:5000 --env-file .env.prod inventory-service:latest
```

### Environment Configuration

Create `.env.prod` with production values:

```
FLASK_ENV=production
DATABASE_URL=mysql+pymysql://user:pass@prod-db:3306/inventory_db
REDIS_URL=redis://prod-redis:6379/0
PRODUCT_SERVICE_URL=https://api.example.com/products/v1
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**

   ```bash
   # Check MySQL service
   docker-compose logs mysql_inventory

   # Verify connection string
   echo $DATABASE_URL
   ```

2. **Redis Connection Failed**

   ```bash
   # Check Redis service
   docker-compose logs redis_inventory

   # Test Redis connectivity
   docker exec -it inventory-service_redis_inventory_1 redis-cli ping
   ```

3. **Migration Issues**

   ```bash
   # Reset database
   docker-compose down -v
   docker-compose up -d mysql_inventory
   # Wait for MySQL to initialize, then start service
   docker-compose up inventory-service
   ```

4. **Performance Issues**

   ```bash
   # Check resource usage
   docker stats

   # Monitor database queries
   # Enable MySQL slow query log
   ```

### Debug Mode

```bash
export FLASK_ENV=development
python run.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Ensure code quality standards
5. Update documentation
6. Submit pull request

## License

This project is part of the AI Outlet e-commerce platform. All rights reserved.

## Support

For issues and questions:

- Create GitHub issues for bugs
- Use discussions for questions
- Check health endpoints for service status
- Review logs for troubleshooting
