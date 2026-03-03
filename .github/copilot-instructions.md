# Copilot Instructions — inventory-service

## Service Identity

- **Name**: inventory-service
- **Purpose**: Inventory management — stock levels, reservations, stock movements, reorder alerts
- **Port**: 8005
- **Language**: Python 3.11+
- **Framework**: Flask 3.0+ with Flask-RESTX (Swagger auto-generated)
- **Database**: MySQL 8.0+ (port 3306) via SQLAlchemy ORM + Flask-Migrate (Alembic)
- **Dapr App ID**: `inventory-service`

## Architecture

- **Pattern**: Layered MVC — routes (Flask-RESTX resources) → services → models (SQLAlchemy)
- **API Style**: RESTful with auto-generated Swagger/OpenAPI via Flask-RESTX
- **Authentication**: JWT Bearer tokens + service token validation
- **Messaging**: Dapr pub/sub for inventory events (CloudEvents 1.0)
- **Event Format**: CloudEvents 1.0 specification

## Project Structure

```
inventory-service/
├── src/
│   ├── __init__.py          # Flask app factory
│   ├── controllers/         # Flask-RESTX Resource classes
│   ├── services/            # Business logic
│   ├── models/              # SQLAlchemy models
│   │   ├── inventory_item.py
│   │   ├── reservation.py
│   │   └── stock_movement.py
│   ├── middlewares/          # Auth, logging, tracing
│   ├── utils/               # Schemas (Marshmallow), event publisher, error codes
│   └── database.py          # SQLAlchemy + Flask-Migrate init
├── migrations/              # Alembic migration scripts
├── tests/
│   ├── unit/
│   └── integration/
├── config.py                # Configuration classes
├── main.py                  # Application entry point
├── .dapr/components/
└── requirements.txt
```

## Code Conventions

- Use **Flask-RESTX** `Resource` classes for API endpoints (auto-generates Swagger)
- Use **SQLAlchemy ORM** models with type hints
- Use **Marshmallow** schemas for request/response validation
- Use **Flask-Migrate** (Alembic) for database migrations
- Model `to_dict()` methods for serialization
- Config classes in `config.py` (Config, DevelopmentConfig, ProductionConfig, TestingConfig)
- Structured logging with color-coded console output matching Node.js services format
- SSL handling for Azure MySQL connections (strip `ssl_mode` from URL, use `connect_args`)
- Error handling via custom error codes in `src/utils/error_codes.py`

## Database Patterns

- MySQL via SQLAlchemy ORM
- Models: `InventoryItem`, `Reservation`, `StockMovement`
- InventoryItem: `sku` (unique, indexed), `quantity_available`, `quantity_reserved`, `reorder_level`, `max_stock`, `cost_per_unit`
- Reservation model for order-based stock reservations
- StockMovement for audit trail of quantity changes
- Timestamps: `created_at`, `updated_at` on all models
- Migrations via `flask db migrate`, `flask db upgrade`

## Key Patterns

- `@require_admin` decorator for admin-only endpoints
- `@require_service_token` decorator for service-to-service calls
- Bulk operations support (batch stock adjustments)
- Low stock detection via `reorder_level` comparison
- Azure Monitor / Application Insights integration (optional)
- Consul service registration

## Testing Requirements

- All new controllers MUST have unit tests
- Use **pytest** + **pytest-cov** as the test framework
- Mock SQLAlchemy/MySQL calls in unit tests
- Do NOT call real databases or downstream services in unit tests
- Run: `pytest tests/ -v`
- Coverage: `pytest --cov=src --cov-report=html`
- Target: ~91% code coverage

## Dapr Integration

- **Pub/Sub**: Publishes `inventory.reserved`, `inventory.released`, `inventory.low-stock` events
- **Service Invocation**: Calls product-service via Dapr for product validation
- **Ports**: Dapr HTTP 3500, Dapr gRPC 50001

## Security Rules

- JWT MUST be validated before accessing any route logic
- `@require_admin` decorator MUST be used for all admin-only endpoints
- `@require_service_token` decorator MUST be used for all service-to-service calls
- Validate all request bodies using **Marshmallow** schemas before reaching service logic
- Sanitize all inputs
- Rate limiting applies to all mutation endpoints

## Error Handling Contract

All errors MUST follow this JSON structure:

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human readable message",
    "correlationId": "uuid"
  }
}
```

- Never expose stack traces in production
- Use centralized error handler only

## Logging Rules

- Use structured JSON logging only
- Include:
  - timestamp
  - level
  - serviceName
  - correlationId
  - message
- Never log JWT tokens
- Never log secrets

## Non-Goals

- This service does NOT manage the product catalog — handled by product-service
- This service does NOT process orders or payments
- This service does NOT handle authentication or JWT issuance
- This service does NOT manage user profiles

## Environment Variables

```
PORT=8005
FLASK_ENV=development
MYSQL_SERVER_CONNECTION=mysql+pymysql://admin:admin123@localhost:3306/inventory_service_db
JWT_SECRET=<shared-secret>
DAPR_HTTP_PORT=3500
LOG_LEVEL=INFO
LOG_FORMAT=console
PLATFORM_MODE=direct
```

## Common Commands

```bash
python main.py                           # Run service
flask db migrate -m "description"        # Create migration
flask db upgrade                         # Apply migrations
pytest tests/ -v                         # Run tests
pytest --cov=src --cov-report=html       # Coverage report
```
