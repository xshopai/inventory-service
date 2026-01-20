# Inventory Service - Architecture Document

## Table of Contents

1. [Overview](#1-overview)
2. [System Context](#2-system-context)
3. [Data Architecture](#3-data-architecture)
4. [API Design](#4-api-design)
5. [Event Architecture](#5-event-architecture)
6. [Configuration & Deployment](#6-configuration--deployment)
7. [Security](#7-security)

---

## 1. Overview

### 1.1 Purpose

The Inventory Service is a core microservice within the xshopai e-commerce platform responsible for managing stock levels, reservations, and product availability across all warehouses. It serves as the **single source of truth** for product availability data and provides both synchronous APIs and event-driven integration patterns for real-time inventory updates.

### 1.2 Service Summary

| Attribute      | Value                                       |
| -------------- | ------------------------------------------- |
| Service Name   | inventory-service                           |
| Tech Stack     | Python 3.x / Flask 3.0 / Flask-RESTX        |
| Database       | MySQL 8.x (SQLAlchemy ORM + PyMySQL driver) |
| Migrations     | Flask-Migrate (Alembic)                     |
| Cache          | None (Redis integration removed)            |
| API Docs       | Swagger/OpenAPI via Flask-RESTX             |
| Messaging      | Dapr Pub/Sub (abstracted via DaprProvider)  |
| Main Port      | 8004                                        |
| Dapr HTTP Port | 3504                                        |
| Dapr gRPC Port | 50004                                       |

### 1.3 Key Responsibilities

1. **Stock Management** - Track real-time stock levels by SKU and warehouse; handle stock adjustments (received, damaged, returned)
2. **Reservation System** - Create time-bound reservations during checkout; auto-expire uncommitted reservations; confirm reservations on order placement
3. **Event Publishing** - Publish `inventory.stock.updated`, `inventory.reserved`, `inventory.released` events for downstream services
4. **Stock Queries** - Provide availability checks for Product Service (denormalized status) and Order Service (validation)
5. **Admin Operations** - Bulk stock updates, low-stock threshold configuration, inventory auditing

### 1.4 References

| Document             | Link                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| PRD                  | [docs/PRD.md](./PRD.md)                                               |
| Copilot Instructions | [.github/copilot-instructions.md](../.github/copilot-instructions.md) |

---

## 2. System Context

### 2.1 Context Diagram

```mermaid
C4Context
    title System Context - Inventory Service

    Person(admin, "Admin User", "Manages inventory via Admin UI")

    System(inventory, "Inventory Service", "Manages stock levels, reservations, and availability")

    System_Ext(product, "Product Service", "Product catalog management")
    System_Ext(order, "Order Service", "Order processing")
    System_Ext(notification, "Notification Service", "Sends alerts and notifications")
    System_Ext(audit, "Audit Service", "Audit logging")
    System_Ext(auth, "Auth Service", "JWT authentication")
    System_Ext(adminui, "Admin UI", "Administrative interface")

    System_Ext(mysql, "MySQL Database", "Persistent storage")
    System_Ext(dapr, "Dapr Sidecar", "Pub/sub messaging")
    System_Ext(otel, "OpenTelemetry Collector", "Observability")

    Rel(admin, adminui, "Uses")
    Rel(adminui, inventory, "HTTP/REST", "Inventory management")

    Rel(product, inventory, "HTTP", "Check availability")
    Rel(order, inventory, "HTTP", "Reserve/release stock")
    Rel(inventory, auth, "HTTP", "Validate JWT tokens")

    Rel(product, dapr, "Events", "product.created/updated/deleted")
    Rel(order, dapr, "Events", "order.created/cancelled/completed")
    Rel(dapr, inventory, "Events", "Subscribed events")

    Rel(inventory, dapr, "Events", "inventory.* events")
    Rel(dapr, product, "Events", "Stock updates")
    Rel(dapr, notification, "Events", "Low stock alerts")
    Rel(dapr, audit, "Events", "Audit trail")

    Rel(inventory, mysql, "SQL", "Persistent storage")
    Rel(inventory, otel, "OTLP", "Traces and metrics")
```

### 2.2 External Interfaces

| System               | Direction | Protocol    | Description                                         |
| -------------------- | --------- | ----------- | --------------------------------------------------- |
| Product Service      | In        | HTTP        | Queries stock availability for products             |
| Product Service      | In        | Dapr Events | Receives product.created/updated/deleted events     |
| Order Service        | In        | HTTP        | Reserve and release inventory for orders            |
| Order Service        | In        | Dapr Events | Receives order.created/cancelled/completed events   |
| Auth Service         | Out       | HTTP        | JWT token validation for protected endpoints        |
| Admin UI             | In        | HTTP        | Administrative inventory management                 |
| Product Service      | Out       | Dapr Events | Publishes inventory.stock.updated events            |
| Notification Service | Out       | Dapr Events | Publishes inventory.low.stock alerts                |
| Audit Service        | Out       | Dapr Events | Publishes inventory change events for audit logging |
| MySQL                | Out       | SQL         | Persistent storage for inventory and reservations   |

### 2.3 Dependencies

#### 2.3.1 Upstream Dependencies

| Service         | Dependency Type | Purpose                                      |
| --------------- | --------------- | -------------------------------------------- |
| Product Service | Event           | Sync inventory records when products change  |
| Order Service   | Event           | Process order-related inventory operations   |
| Auth Service    | HTTP            | JWT validation for admin/protected endpoints |

#### 2.3.2 Downstream Consumers

| Consumer             | Interface   | Data Provided                               |
| -------------------- | ----------- | ------------------------------------------- |
| Product Service      | HTTP        | Stock availability queries                  |
| Product Service      | Dapr Events | inventory.stock.updated, inventory.created  |
| Order Service        | HTTP        | Reserve/release/check operations            |
| Order Service        | Dapr Events | inventory.reserved, inventory.released      |
| Notification Service | Dapr Events | inventory.low.stock, inventory.out.of.stock |
| Audit Service        | Dapr Events | All inventory change events                 |
| Admin UI             | HTTP        | Full inventory management API               |

#### 2.3.3 Infrastructure Dependencies

| Component               | Purpose                       | Port/Connection          |
| ----------------------- | ----------------------------- | ------------------------ |
| MySQL 8.x               | Persistent storage            | 3306 (configurable)      |
| Dapr Sidecar            | Pub/sub messaging             | HTTP: 3504, gRPC: 50004  |
| RabbitMQ (via Dapr)     | Message broker backend        | Abstracted by Dapr       |
| OpenTelemetry Collector | Distributed tracing & metrics | 4317 (gRPC), 4318 (HTTP) |

---

## 3. Data Architecture

### 3.1 Database Schema

#### 3.1.1 inventory Table

| Column        | Type          | Constraints          | Description          |
| ------------- | ------------- | -------------------- | -------------------- |
| <!-- TODO --> | <!-- type --> | <!-- constraints --> | <!-- description --> |

#### 3.1.2 reservations Table

| Column        | Type          | Constraints          | Description          |
| ------------- | ------------- | -------------------- | -------------------- |
| <!-- TODO --> | <!-- type --> | <!-- constraints --> | <!-- description --> |

### 3.2 Indexes

| Table         | Index Name    | Columns          | Type                | Purpose          |
| ------------- | ------------- | ---------------- | ------------------- | ---------------- |
| <!-- TODO --> | <!-- name --> | <!-- columns --> | <!-- B-tree/etc --> | <!-- purpose --> |

### 3.3 Caching Strategy

| Data Type     | Cache Key Pattern | TTL               | Invalidation      |
| ------------- | ----------------- | ----------------- | ----------------- |
| <!-- TODO --> | <!-- pattern -->  | <!-- duration --> | <!-- strategy --> |

---

## 4. API Design

### 4.1 Endpoint Summary

| Method                                   | Endpoint | Description | Auth |
| ---------------------------------------- | -------- | ----------- | ---- |
| <!-- TODO: All 18 endpoints from PRD --> |          |             |      |

### 4.2 Request/Response Specifications

<!-- TODO: Detailed specs for each endpoint -->

### 4.3 Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

---

## 5. Event Architecture

### 5.1 Published Events

| Event Type              | Topic            | Trigger            | Payload       |
| ----------------------- | ---------------- | ------------------ | ------------- |
| inventory.stock.updated | inventory-events | Stock level change | <!-- TODO --> |

### 5.2 Event Schema

#### 5.2.1 inventory.stock.updated

```json
{
  // TODO: Event payload structure
}
```

### 5.3 Messaging Abstraction Layer

The service uses a messaging abstraction layer to support multiple deployment targets.

```
┌─────────────────────────────────────────────────────────────┐
│                    inventory-service                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Messaging Abstraction Layer                     │
│                   (MessagePublisher)                         │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│ DaprProvider  │ │ ServiceBus    │ │ RabbitMQ      │
│               │ │ Provider      │ │ Provider      │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
   Dapr Sidecar      Direct SDK        Direct SDK
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  RabbitMQ /   │ │ Azure Service │ │   RabbitMQ    │
│  Service Bus  │ │     Bus       │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

### 5.4 Provider Interface

<!-- TODO: Define the MessagePublisher interface -->

---

## 6. Configuration & Deployment

### 6.1 Environment Variables

| Variable                                 | Description                                | Required | Default |
| ---------------------------------------- | ------------------------------------------ | -------- | ------- |
| `PORT`                                   | Service port                               | No       | 8004    |
| `DATABASE_URL`                           | PostgreSQL connection string               | Yes      | -       |
| `REDIS_URL`                              | Redis connection string                    | Yes      | -       |
| `MESSAGING_PROVIDER`                     | Provider: `dapr`, `servicebus`, `rabbitmq` | No       | `dapr`  |
| <!-- TODO: Add all required env vars --> |                                            |          |         |

### 6.2 Messaging Provider Configuration

#### 6.2.1 Dapr Provider (Default - Local Development)

| Variable           | Description            | Required           |
| ------------------ | ---------------------- | ------------------ |
| `DAPR_HTTP_PORT`   | Dapr sidecar HTTP port | No (default: 3504) |
| `DAPR_PUBSUB_NAME` | Pub/sub component name | Yes                |

#### 6.2.2 Service Bus Provider (Azure)

| Variable                       | Description                  | Required |
| ------------------------------ | ---------------------------- | -------- |
| `SERVICEBUS_CONNECTION_STRING` | Azure Service Bus connection | Yes      |
| `SERVICEBUS_TOPIC_NAME`        | Topic name                   | Yes      |

#### 6.2.3 RabbitMQ Provider (Direct)

| Variable            | Description                | Required |
| ------------------- | -------------------------- | -------- |
| `RABBITMQ_URL`      | RabbitMQ connection string | Yes      |
| `RABBITMQ_EXCHANGE` | Exchange name              | Yes      |

### 6.3 Deployment Targets

| Target                 | Messaging Provider | Notes                           |
| ---------------------- | ------------------ | ------------------------------- |
| Local (Docker Compose) | `dapr`             | Uses Dapr sidecar with RabbitMQ |
| Azure App Service      | `servicebus`       | Direct SDK, no sidecar          |
| Azure Container Apps   | `dapr`             | Managed Dapr integration        |
| AKS                    | `dapr`             | Self-managed Dapr               |

---

## 7. Security

### 7.1 Authentication

<!-- TODO: JWT validation approach -->

### 7.2 Authorization Matrix

| Endpoint Pattern           | Required Role    | Notes               |
| -------------------------- | ---------------- | ------------------- |
| `GET /api/inventory/*`     | Public / Service | Stock queries       |
| `POST /api/inventory/*`    | Admin            | Stock modifications |
| `POST /api/reservations/*` | Service          | Internal only       |
| `GET /api/admin/*`         | Admin            | Admin operations    |

### 7.3 Service-to-Service Authentication

<!-- TODO: How services authenticate with inventory-service -->
