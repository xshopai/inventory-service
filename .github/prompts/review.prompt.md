# Code Review Checklist for inventory-service

## Instructions

Review the code changes against this checklist. Flag any violations with specific `file:line` references.
Reference `docs/PRD.md` for business requirements when applicable.

---

## 1. Architecture & Project Structure

- [ ] Controllers in `src/controllers/` - HTTP request handling only
- [ ] Business logic in `src/services/` (not in controllers)
- [ ] Database queries in `src/repositories/`
- [ ] Data models in `src/models/`
- [ ] Validation schemas in `src/utils/schemas.py`
- [ ] No circular imports between modules

---

## 2. Flask Patterns

- [ ] Blueprints used for route organization
- [ ] Flask-RESTX for API documentation
- [ ] Request data accessed via `request.json` or `request.args`
- [ ] Response returns tuple `(data, status_code)` or `jsonify()`
- [ ] No direct `print()` statements (use `logging` module)

---

## 3. Error Handling (Architecture Spec 9.1)

- [ ] Uses `ErrorCode` constants from `src/utils/error_codes.py`
- [ ] Uses `create_error_response()` for standardized format
- [ ] Error response includes: `code`, `message`, `timestamp`, `correlation_id`
- [ ] Correct HTTP status codes:
  - `400` - Validation errors (`VALIDATION_ERROR`)
  - `401` - Authentication required (`UNAUTHORIZED`)
  - `403` - Forbidden (`FORBIDDEN`)
  - `404` - Not found (`SKU_NOT_FOUND`, `RESERVATION_NOT_FOUND`)
  - `409` - Conflict (`INSUFFICIENT_STOCK`, `SKU_ALREADY_EXISTS`)
  - `500` - Internal error (`INTERNAL_ERROR`)
- [ ] No sensitive data in error messages (no secrets, no stack traces in production)

---

## 4. Authentication & Authorization

- [ ] Admin endpoints use `@require_admin` decorator
- [ ] Service-to-service endpoints use `@require_service_token` decorator
- [ ] Public endpoints (if any) explicitly documented
- [ ] JWT config loaded from environment variables (via `auth.py`)
- [ ] User context stored in Flask `g` object (`g.user`, `g.correlation_id`)

---

## 5. Database Operations (SQLAlchemy/MySQL)

- [ ] Uses SQLAlchemy ORM (not raw SQL unless justified)
- [ ] Transactions committed via `db.session.commit()`
- [ ] Errors trigger `db.session.rollback()`
- [ ] Uses `session.query()` or model methods (not direct execute)
- [ ] Pagination uses `paginate()` or manual `limit/offset`
- [ ] No N+1 query patterns (use eager loading where needed)
- [ ] Stock operations use row-level locking for concurrency

---

## 6. Event Publishing (Dapr Pub/Sub)

- [ ] Events published via `src/utils/event_publisher.py`
- [ ] Uses `DaprProvider` from `src/messaging/dapr_provider.py`
- [ ] Events follow CloudEvents format:

  ```python
  {
      "specversion": "1.0",
      "type": "inventory.stock.updated",
      "source": "inventory-service",
      "id": "<uuid>",
      "time": "<ISO8601>",
      "data": { ... }
  }
  ```
  
- [ ] `correlation_id` propagated in event metadata
- [ ] Fire-and-forget pattern (log errors, don't fail API request)
- [ ] Event topics match PRD requirements:
  - `inventory.stock.updated` - Stock level changed
  - `inventory.low.stock.alert` - Below reorder level
  - `inventory.reservation.created` - Reservation made
  - `inventory.reservation.confirmed` - Reservation confirmed
  - `inventory.reservation.released` - Reservation released/expired

---

## 7. Secrets Management

- [ ] Secrets accessed from environment variables (`os.environ.get`)
- [ ] Uses Dapr Secret Store (with env var fallback)
- [ ] Required secrets: `MYSQL_SERVER_CONNECTION`, `JWT_SECRET`, `APPINSIGHTS_CONNECTION`
- [ ] Service tokens: `SERVICE_PRODUCT_TOKEN`, `SERVICE_ORDER_TOKEN`, etc.
- [ ] No hardcoded secrets or connection strings in code
- [ ] Secrets not logged (even at DEBUG level)

---

## 8. Logging & Observability

- [ ] Uses Python `logging` module (not `print()`)
- [ ] Structured logging with extra fields:
  ```python
  logger.info("Stock updated", extra={
      "sku": sku,
      "quantity": quantity,
      "correlation_id": g.correlation_id
  })
  ```
- [ ] Log levels appropriate:
  - `ERROR` - Failures requiring attention
  - `WARNING` - Degraded functionality
  - `INFO` - Normal operations
  - `DEBUG` - Diagnostic information
- [ ] `correlation_id` included in all logs
- [ ] No PII or secrets in logs

---

## 9. Input Validation (Marshmallow)

- [ ] Request schemas defined in `src/utils/schemas.py`
- [ ] Uses Marshmallow for validation
- [ ] Required fields explicitly marked
- [ ] SKU format validated (alphanumeric, length constraints)
- [ ] Quantity validated as positive integer
- [ ] Validation errors return `VALIDATION_ERROR` code

---

## 10. Testing

- [ ] Unit tests in `tests/unit/`
- [ ] Integration tests in `tests/integration/`
- [ ] Tests use `TestingConfig` (SQLite in-memory)
- [ ] Mocks for external services (Dapr, other microservices)
- [ ] Test coverage for:
  - Happy path scenarios
  - Error conditions (not found, validation, insufficient stock)
  - Edge cases (zero quantity, concurrent access)

---

## 11. Configuration

- [ ] Config classes in `config.py` (Development, Testing, Production)
- [ ] Environment variables for all configurable values
- [ ] `.env.local` for local without Dapr
- [ ] `.env.dapr` for local with Dapr
- [ ] No framework secrets needed (stateless REST API)

---

## 12. Performance (PRD NFR)

- [ ] API response time target: < 100ms (p95)
- [ ] Reservation success rate: > 99.5%
- [ ] Database indexes exist for queried fields (SKU, reservation_id)
- [ ] Pagination used for list endpoints (default: 20, max: 100)
- [ ] No unbounded queries (always use LIMIT)

---

## 13. Business Logic (PRD Requirements)

- [ ] Stock levels cannot go negative
- [ ] Reservations expire after timeout (default: 15 minutes)
- [ ] Reservation confirmation decrements available stock
- [ ] Low stock alerts triggered at reorder level
- [ ] Bulk operations handled atomically where required

---

## 14. Non-Goals

- [ ] Do NOT suggest changing frameworks or libraries
- [ ] Do NOT introduce new architectural patterns unless required by PRD
- [ ] Do NOT refactor unrelated code
- [ ] Do NOT suggest performance optimizations without evidence in this PR

---

## Quick Reference

### Key Files

| Purpose             | Location                       |
| ------------------- | ------------------------------ |
| Controllers         | `src/controllers/`             |
| Services            | `src/services/`                |
| Models              | `src/models/`                  |
| Repositories        | `src/repositories/`            |
| Schemas             | `src/utils/schemas.py`         |
| Error codes         | `src/utils/error_codes.py`     |
| Auth middleware     | `src/middlewares/auth.py`      |
| Event publisher     | `src/utils/event_publisher.py` |
| Messaging providers | `src/messaging/`               |
| Configuration       | `config.py`                    |

### Common Imports

```python
from flask import Blueprint, request, g, jsonify
from src.services import InventoryService
from src.middlewares.auth import require_admin, require_service_token
from src.utils.error_codes import create_error_response, ErrorCode
from src.utils.event_publisher import event_publisher
import logging

logger = logging.getLogger(__name__)
```

---

## Usage

In VS Code Copilot Chat:

```
Review these changes using the checklist in .github/prompts/review.prompt.md
```

Or with `@workspace`:

```
@workspace /review #file:.github/prompts/review.prompt.md
```
