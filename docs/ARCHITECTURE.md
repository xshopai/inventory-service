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

<!-- TODO: Add Mermaid diagram showing inventory-service with external systems -->

### 2.2 External Interfaces

| System        | Direction            | Protocol                  | Description          |
| ------------- | -------------------- | ------------------------- | -------------------- |
| <!-- TODO --> | <!-- in/out/both --> | <!-- HTTP/gRPC/Events --> | <!-- description --> |

### 2.3 Dependencies

#### 2.3.1 Upstream Dependencies

<!-- TODO: Services this service depends on -->

#### 2.3.2 Downstream Consumers

<!-- TODO: Services that consume from this service -->

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
