# Inventory Service - Architecture Document

## Table of Contents

1. [Overview](#1-overview)
   - 1.1 [Purpose](#11-purpose)
   - 1.2 [Scope](#12-scope)
   - 1.3 [Service Summary](#13-service-summary)
   - 1.4 [Directory Structure](#14-directory-structure)
   - 1.5 [Key Responsibilities](#15-key-responsibilities)
   - 1.6 [References](#16-references)
2. [System Context](#2-system-context)
   - 2.1 [Context Diagram](#21-context-diagram)
   - 2.2 [External Interfaces](#22-external-interfaces)
   - 2.3 [Dependencies](#23-dependencies)
3. [Data Architecture](#3-data-architecture)
   - 3.1 [Entity Relationship Diagram](#31-entity-relationship-diagram)
   - 3.2 [Database Schema](#32-database-schema)
   - 3.3 [Indexes](#33-indexes)
   - 3.4 [Caching Strategy](#34-caching-strategy)
   - 3.5 [Database Configuration](#35-database-configuration)
4. [API Design](#4-api-design)
   - 4.1 [Endpoint Summary](#41-endpoint-summary)
   - 4.2 [Request/Response Specifications](#42-requestresponse-specifications)
   - 4.3 [Error Response Format](#43-error-response-format)
   - 4.4 [Error Code Reference](#44-error-code-reference)
   - 4.5 [Authentication](#45-authentication)
5. [Event Architecture](#5-event-architecture)
   - 5.1 [Event Summary](#51-event-summary)
   - 5.2 [Published Events](#52-published-events)
   - 5.3 [Subscribed Events](#53-subscribed-events)
   - 5.4 [Dapr Configuration](#54-dapr-configuration)
   - 5.5 [Messaging Abstraction Layer](#55-messaging-abstraction-layer)
6. [Configuration](#6-configuration)
   - 6.1 [Environment Variables](#61-environment-variables)
   - 6.2 [Messaging Provider Configuration](#62-messaging-provider-configuration)
7. [Deployment](#7-deployment)
   - 7.1 [Deployment Targets](#71-deployment-targets)
8. [Observability](#8-observability)
   - 8.1 [Distributed Tracing](#81-distributed-tracing)
   - 8.2 [Structured Logging](#82-structured-logging)
   - 8.3 [Metrics & Alerting](#83-metrics--alerting)
9. [Error Handling](#9-error-handling)
   - 9.1 [Error Response Format](#91-error-response-format)
10. [Security](#10-security)
    - 10.1 [Authentication](#101-authentication)
    - 10.2 [Authorization](#102-authorization)
    - 10.3 [Service-to-Service Communication](#103-service-to-service-communication)
    - 10.4 [Input Validation](#104-input-validation)
    - 10.5 [CORS Configuration](#105-cors-configuration)

---

## 1. Overview

### 1.1 Purpose

The Inventory Service is a core microservice within the xshopai e-commerce platform responsible for managing stock levels, reservations, and product availability across all warehouses. It serves as the **single source of truth** for product availability data and provides both synchronous APIs and event-driven integration patterns for real-time inventory updates.

### 1.2 Scope

#### In Scope

- Real-time stock level tracking by SKU and warehouse
- Inventory reservation management for checkout flow
- Stock adjustment operations (received, damaged, returned, sold)
- Automatic reservation expiration handling
- Low stock and out-of-stock alert generation
- Event-driven synchronization with Product Service
- Bulk inventory operations for admin users
- Multi-warehouse inventory aggregation

#### Out of Scope

- Product catalog management (handled by Product Service)
- Order processing logic (handled by Order Service)
- Warehouse physical location management
- Shipping and logistics coordination
- Purchase order management
- Supplier management
- Demand forecasting and analytics
- Physical inventory counting workflows

### 1.3 Service Summary

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

### 1.4 Directory Structure

```
inventory-service/
├── .dapr/                      # Dapr configuration
│   └── components/             # Pub/sub component definitions
├── .github/                    # GitHub workflows and copilot instructions
├── .vscode/                    # VS Code settings
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # This file
│   └── PRD.md                  # Product requirements document
├── migrations/                 # Database migration files (Alembic)
│   └── versions/               # Migration version scripts
├── src/                        # Application source code
│   ├── controllers/            # API endpoint handlers
│   │   ├── inventory_controller.py
│   │   └── health_controller.py
│   ├── middlewares/            # Request/response middleware
│   │   ├── correlation_id.py   # Correlation ID tracking
│   │   ├── error_handler.py    # Global error handling
│   │   └── request_logger.py   # Request logging
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── inventory_item.py   # Inventory item model
│   │   ├── reservation.py      # Reservation model
│   │   └── stock_movement.py   # Stock movement model
│   ├── repositories/           # Data access layer
│   │   ├── inventory_repository.py
│   │   └── reservation_repository.py
│   ├── services/               # Business logic layer
│   │   ├── inventory_service.py
│   │   ├── reservation_service.py
│   │   └── event_publisher.py  # Dapr event publishing
│   ├── utils/                  # Utility functions
│   │   ├── validators.py       # Input validation
│   │   └── helpers.py          # Common helpers
│   ├── database.py             # Database connection setup
│   └── __init__.py             # Flask app factory
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Pytest fixtures
├── config.py                   # Application configuration
├── docker-compose.yml          # Local development setup
├── Dockerfile                  # Container build instructions
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── run.py                      # Application entry point
├── run.ps1                     # Windows run script
└── run.sh                      # Linux/macOS run script
```

### 1.5 Key Responsibilities

1. **Stock Management** - Track real-time stock levels by SKU and warehouse; handle stock adjustments (received, damaged, returned)
2. **Reservation System** - Create time-bound reservations during checkout; auto-expire uncommitted reservations; confirm reservations on order placement
3. **Event Publishing** - Publish `inventory.stock.updated`, `inventory.reserved`, `inventory.released` events for downstream services
4. **Stock Queries** - Provide availability checks for Product Service (denormalized status) and Order Service (validation)
5. **Admin Operations** - Bulk stock updates, low-stock threshold configuration, inventory auditing

### 1.6 References

| Document             | Link                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| PRD                  | [docs/PRD.md](./PRD.md)                                               |
| Copilot Instructions | [.github/copilot-instructions.md](../.github/copilot-instructions.md) |

---

## 2. System Context

### 2.1 Context Diagram

```mermaid
flowchart TB
    subgraph Users["<b>👤 USERS</b>"]
        Admin[("🧑‍💼 Admin User")]
    end

    subgraph Clients["<b>📱 CLIENT APPLICATIONS</b>"]
        AdminUI["🖥️ Admin UI<br/><i>Web Interface</i>"]
    end

    subgraph BFF["<b>🌐 BACKEND FOR FRONTEND</b>"]
        WebBFF["🔀 Web BFF<br/><i>API Gateway</i>"]
    end

    subgraph Core["<b>🎯 CORE SERVICE</b>"]
        INV["<b>Inventory Service</b><br/>━━━━━━━━━━━━━━━<br/>📦 Port: 8004<br/>Manages stock levels,<br/>reservations & availability"]
    end

    subgraph Services["<b>🔗 DEPENDENT SERVICES</b>"]
        direction LR
        Product["📦 Product Service<br/><i>Catalog Management</i>"]
        Order["🛒 Order Service<br/><i>Order Processing</i>"]
        Auth["🔐 Auth Service<br/><i>JWT Authentication</i>"]
    end

    subgraph EventConsumers["<b>📤 EVENT CONSUMERS</b>"]
        direction LR
        Notification["🔔 Notification Service<br/><i>Alerts & Notifications</i>"]
        Audit["📋 Audit Service<br/><i>Audit Logging</i>"]
    end

    subgraph Infrastructure["<b>⚙️ INFRASTRUCTURE</b>"]
        direction TB
        MySQL[("🗄️ MySQL 8.x<br/>Port: 3306")]
        RabbitMQ[("🐰 RabbitMQ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Message Broker &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Port: 5672")]
        Dapr["📡 Dapr Sidecar<br/>HTTP: 3504"]
        OTEL["📊 OpenTelemetry<br/>Collector"]
    end

    %% User flows
    Admin -->|"Uses"| AdminUI
    AdminUI -->|"HTTP/REST"| WebBFF
    WebBFF -->|"HTTP/REST<br/>Inventory Management"| INV

    %% Service integrations - HTTP
    Product -->|"HTTP GET<br/>Check Availability"| INV
    Order -->|"HTTP POST<br/>Reserve/Release Stock"| INV

    %% Auth provides JWT public key at startup (no per-request calls)
    Auth -.->|"JWT Public Key<br/>(startup only)"| WebBFF

    %% Event flows - Inbound (Publishers → Broker → Subscriber)
    Product -.->|"Publish"| RabbitMQ
    Order -.->|"Publish"| RabbitMQ
    RabbitMQ -.->|"product.*<br/>order.*"| Dapr
    Dapr -.->|"Subscribe"| INV

    %% Event flows - Outbound (Publisher → Broker → Consumers)
    INV -.->|"Publish"| Dapr
    Dapr -.->|"inventory.*"| RabbitMQ
    RabbitMQ -.->|"inventory.stock.updated"| Product
    RabbitMQ -.->|"inventory.low.stock"| Notification
    RabbitMQ -.->|"inventory.*"| Audit

    %% Infrastructure connections
    INV -->|"SQL Queries"| MySQL
    INV -->|"OTLP Traces"| OTEL

    %% Styling - Core Service
    classDef core fill:#0969da,stroke:#0550ae,color:#fff,stroke-width:3px,font-weight:bold

    %% Styling - Users
    classDef user fill:#8250df,stroke:#6639ba,color:#fff,stroke-width:2px

    %% Styling - Client Apps
    classDef client fill:#1f6feb,stroke:#1158c7,color:#fff,stroke-width:2px

    %% Styling - BFF
    classDef bff fill:#6366f1,stroke:#4f46e5,color:#fff,stroke-width:2px

    %% Styling - Dependent Services (different colors by type)
    classDef productSvc fill:#7c3aed,stroke:#6d28d9,color:#fff,stroke-width:2px
    classDef orderSvc fill:#0891b2,stroke:#0e7490,color:#fff,stroke-width:2px
    classDef authSvc fill:#dc2626,stroke:#b91c1c,color:#fff,stroke-width:2px

    %% Styling - Event Consumers
    classDef notifySvc fill:#ea580c,stroke:#c2410c,color:#fff,stroke-width:2px
    classDef auditSvc fill:#65a30d,stroke:#4d7c0f,color:#fff,stroke-width:2px

    %% Styling - Infrastructure
    classDef database fill:#059669,stroke:#047857,color:#fff,stroke-width:2px
    classDef broker fill:#f472b6,stroke:#db2777,color:#fff,stroke-width:2px
    classDef messaging fill:#d97706,stroke:#b45309,color:#fff,stroke-width:2px
    classDef observability fill:#0284c7,stroke:#0369a1,color:#fff,stroke-width:2px

    %% Apply styles
    class INV core
    class Admin user
    class AdminUI client
    class WebBFF bff
    class Product productSvc
    class Order orderSvc
    class Auth authSvc
    class Notification notifySvc
    class Audit auditSvc
    class MySQL database
    class RabbitMQ broker
    class Dapr messaging
    class OTEL observability
```

#### Diagram Legend

|      Color      | Component                    | Description                              |
| :-------------: | ---------------------------- | ---------------------------------------- |
|   🔵 **Blue**   | Inventory Service            | Core service being documented            |
|  🟣 **Purple**  | Admin User / Product Service | User actors and catalog integration      |
|   🔷 **Cyan**   | Admin UI / Order Service     | Client applications and order processing |
|   🔴 **Red**    | Auth Service                 | Authentication and security              |
|  🟠 **Orange**  | Notification Service / Dapr  | Alerts and messaging sidecar             |
|  🟢 **Green**   | Audit Service / MySQL        | Logging and data persistence             |
|   🩷 **Pink**   | RabbitMQ                     | Message broker infrastructure            |
| 🔵 **Sky Blue** | OpenTelemetry                | Observability infrastructure             |

| Arrow Style       | Meaning                               |
| ----------------- | ------------------------------------- |
| **━━━▶** Solid    | Synchronous HTTP/SQL request-response |
| **─ ─ ─▶** Dashed | Asynchronous event-based messaging    |

### 2.2 External Interfaces

| System               | Direction | Protocol    | Description                                         |
| -------------------- | --------- | ----------- | --------------------------------------------------- |
| Product Service      | In        | HTTP        | Queries stock availability for products             |
| Product Service      | In        | Dapr Events | Receives product.created/updated/deleted events     |
| Order Service        | In        | HTTP        | Reserve and release inventory for orders            |
| Order Service        | In        | Dapr Events | Receives order.created/cancelled/completed events   |
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

### 3.1 Entity Relationship Diagram

```mermaid
erDiagram
    inventory_items ||--o{ reservations : "has"
    inventory_items ||--o{ stock_movements : "tracks"

    inventory_items {
        int id PK
        string sku UK
        int quantity_available
        int quantity_reserved
        int reorder_level
        int max_stock
        decimal cost_per_unit
        datetime last_restocked
    }

    reservations {
        int id PK
        string order_id UK
        string sku FK
        int quantity
        enum status
        datetime expires_at
    }

    stock_movements {
        int id PK
        string sku FK
        enum movement_type
        int quantity
        string reference
        string reason
        string created_by
    }
```

### 3.2 Database Schema

#### 3.2.1 inventory_items Table

| Column               | Type          | Constraints               | Description                                                 |
| -------------------- | ------------- | ------------------------- | ----------------------------------------------------------- |
| `id`                 | INT           | PK, AUTO_INCREMENT        | Primary key                                                 |
| `sku`                | VARCHAR(100)  | UNIQUE, NOT NULL, INDEX   | Stock Keeping Unit - shared identifier with Product Service |
| `quantity_available` | INT           | NOT NULL, DEFAULT 0       | Current available stock quantity                            |
| `quantity_reserved`  | INT           | NOT NULL, DEFAULT 0       | Quantity reserved for pending orders                        |
| `reorder_level`      | INT           | NOT NULL, DEFAULT 10      | Threshold for low stock alerts                              |
| `max_stock`          | INT           | DEFAULT NULL              | Maximum stock capacity                                      |
| `cost_per_unit`      | DECIMAL(10,2) | DEFAULT NULL              | Unit cost for inventory valuation                           |
| `last_restocked`     | DATETIME      | DEFAULT NULL              | Timestamp of last restock operation                         |
| `created_at`         | DATETIME      | NOT NULL, DEFAULT NOW()   | Record creation timestamp                                   |
| `updated_at`         | DATETIME      | NOT NULL, ON UPDATE NOW() | Last modification timestamp                                 |

#### 3.2.2 reservations Table

| Column       | Type        | Constraints                 | Description                                                 |
| ------------ | ----------- | --------------------------- | ----------------------------------------------------------- |
| `id`         | INT         | PK, AUTO_INCREMENT          | Primary key                                                 |
| `order_id`   | VARCHAR(50) | UNIQUE, NOT NULL, INDEX     | Order identifier from Order Service                         |
| `sku`        | VARCHAR(50) | NOT NULL, INDEX, FK         | References inventory_items.sku                              |
| `quantity`   | INT         | NOT NULL                    | Quantity reserved                                           |
| `status`     | ENUM        | NOT NULL, DEFAULT 'PENDING' | PENDING, CONFIRMED, COMPLETED, CANCELLED, EXPIRED, RELEASED |
| `expires_at` | DATETIME    | NOT NULL, INDEX             | Reservation expiration timestamp                            |
| `created_at` | DATETIME    | NOT NULL, DEFAULT NOW()     | Record creation timestamp                                   |
| `updated_at` | DATETIME    | NOT NULL, ON UPDATE NOW()   | Last modification timestamp                                 |

**ReservationStatus Enum Values:**

- `PENDING` - Reservation created, awaiting confirmation
- `CONFIRMED` - Reservation confirmed by order service
- `COMPLETED` - Order fulfilled, reservation closed
- `CANCELLED` - Reservation cancelled, stock released
- `EXPIRED` - Reservation expired (TTL exceeded)
- `RELEASED` - Stock manually released back to available

#### 3.2.3 stock_movements Table

| Column          | Type         | Constraints                    | Description                          |
| --------------- | ------------ | ------------------------------ | ------------------------------------ |
| `id`            | INT          | PK, AUTO_INCREMENT             | Primary key                          |
| `sku`           | VARCHAR(50)  | NOT NULL, INDEX, FK            | References inventory_items.sku       |
| `movement_type` | ENUM         | NOT NULL, INDEX                | Type of stock movement               |
| `quantity`      | INT          | NOT NULL                       | Movement quantity (can be negative)  |
| `reference`     | VARCHAR(100) | INDEX                          | Order ID or adjustment reference     |
| `reason`        | VARCHAR(255) | DEFAULT NULL                   | Reason for movement                  |
| `created_by`    | VARCHAR(50)  | DEFAULT NULL                   | User or system that created movement |
| `created_at`    | DATETIME     | NOT NULL, DEFAULT NOW(), INDEX | Movement timestamp                   |

**StockMovementType Enum Values:**

- `INBOUND` - Stock received (purchase order, transfer in)
- `OUTBOUND` - Stock shipped (order fulfillment)
- `ADJUSTMENT` - Manual inventory adjustment
- `RESERVED` - Stock reserved for an order
- `RELEASED` - Reserved stock released back
- `DAMAGED` - Stock marked as damaged/lost
- `RETURNED` - Customer return processed

### 3.3 Indexes

| Table           | Index Name                      | Columns                               | Type   | Purpose                               |
| --------------- | ------------------------------- | ------------------------------------- | ------ | ------------------------------------- |
| inventory_items | `PRIMARY`                       | `id`                                  | B-tree | Primary key lookup                    |
| inventory_items | `ix_inventory_items_sku`        | `sku`                                 | B-tree | Unique SKU lookup (most common query) |
| inventory_items | `ix_inventory_items_reorder`    | `quantity_available`, `reorder_level` | B-tree | Low stock alert queries               |
| reservations    | `PRIMARY`                       | `id`                                  | B-tree | Primary key lookup                    |
| reservations    | `ix_reservations_order_id`      | `order_id`                            | B-tree | Unique order lookup                   |
| reservations    | `ix_reservations_sku`           | `sku`                                 | B-tree | SKU-based reservation queries         |
| reservations    | `ix_reservations_status`        | `status`                              | B-tree | Status-based filtering                |
| reservations    | `ix_reservations_expires_at`    | `expires_at`                          | B-tree | Expiration cleanup job                |
| reservations    | `ix_reservations_sku_status`    | `sku`, `status`                       | B-tree | Composite for active reservations     |
| stock_movements | `PRIMARY`                       | `id`                                  | B-tree | Primary key lookup                    |
| stock_movements | `ix_stock_movements_sku`        | `sku`                                 | B-tree | Movement history by SKU               |
| stock_movements | `ix_stock_movements_type`       | `movement_type`                       | B-tree | Movement type filtering               |
| stock_movements | `ix_stock_movements_created_at` | `created_at`                          | B-tree | Time-based queries and auditing       |

### 3.4 Caching Strategy

> **Current Status:** Caching is **not implemented** in the current codebase. Redis integration was previously removed.

| Aspect             | Current State           | Future Recommendation                    |
| ------------------ | ----------------------- | ---------------------------------------- |
| Cache Layer        | Not implemented         | Redis with Dapr State Store              |
| Stock Levels       | Direct database queries | Cache with 30s TTL, invalidate on update |
| Reservation Status | Direct database queries | Cache with 60s TTL                       |
| Low Stock Alerts   | Computed on demand      | Pre-computed, event-driven invalidation  |

**Database Query Optimization (Current Approach):**

- Indexed queries for all frequent access patterns
- Connection pooling via SQLAlchemy (pool_size=5, max_overflow=10)
- Read replicas not configured (single MySQL instance)

### 3.5 Database Configuration

Database connection is configured via the `DATABASE_URL` environment variable.

**Connection String Format:** `mysql+pymysql://{user}:{password}@{host}:{port}/{database}`

**Migration Management:**

| Aspect              | Value                   |
| ------------------- | ----------------------- |
| Tool                | Flask-Migrate (Alembic) |
| Migration Directory | `migrations/`           |

---

## 4. API Design

### 4.1 Endpoint Summary

| Method   | Endpoint                                   | Description                   | Auth          |
| -------- | ------------------------------------------ | ----------------------------- | ------------- |
| `GET`    | `/health`                                  | Basic health check            | None          |
| `GET`    | `/health/ready`                            | Readiness probe               | None          |
| `GET`    | `/health/live`                             | Liveness probe                | None          |
| `GET`    | `/metrics`                                 | Prometheus metrics            | None          |
| `GET`    | `/api/inventory/stock/{sku}`               | Query stock for single SKU    | Service Token |
| `POST`   | `/api/inventory/stock/batch`               | Query stock for multiple SKUs | Service Token |
| `GET`    | `/api/inventory/{sku}`                     | Get inventory by SKU          | Service Token |
| `PUT`    | `/api/inventory/{sku}`                     | Update inventory quantity     | Service Token |
| `POST`   | `/api/inventory/reservations`              | Create reservation            | Service Token |
| `GET`    | `/api/inventory/reservations/{id}`         | Get reservation by ID         | Service Token |
| `POST`   | `/api/inventory/reservations/{id}/confirm` | Confirm reservation           | Service Token |
| `POST`   | `/api/inventory/reservations/{id}/release` | Release reservation           | Service Token |
| `GET`    | `/api/admin/inventory`                     | List inventory records        | Admin JWT     |
| `POST`   | `/api/admin/inventory`                     | Create inventory record       | Admin JWT     |
| `DELETE` | `/api/admin/inventory/{sku}`               | Delete inventory record       | Admin JWT     |
| `POST`   | `/api/admin/inventory/{sku}/adjust`        | Adjust stock levels           | Admin JWT     |
| `GET`    | `/api/admin/inventory/reservations`        | List all reservations         | Admin JWT     |

**Authentication Types:**

- **None**: Public endpoints (health checks)
- **Service Token**: Internal service-to-service authentication using pre-shared tokens
- **Admin JWT**: Admin user authentication via JWT from auth-service

### 4.2 Request/Response Specifications

#### 4.2.1 Query Stock for Single SKU

**Endpoint:** `GET /api/inventory/stock/{sku}`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Product Service, Order Service, Cart Service
- **See:** Section 10.1.3 for token configuration

**Path Parameters:**

| Parameter | Type   | Required | Description |
| --------- | ------ | -------- | ----------- |
| `sku`     | string | Yes      | Product SKU |

**Response (200 OK):**

```json
{
  "sku": "SKU-12345",
  "quantity_available": 100,
  "quantity_reserved": 15,
  "in_stock": true
}
```

**Error Responses:**

| Status | Code            | Description          |
| ------ | --------------- | -------------------- |
| 404    | `SKU_NOT_FOUND` | SKU not in inventory |

---

#### 4.2.2 Query Stock for Multiple SKUs

**Endpoint:** `POST /api/inventory/stock/batch`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Product Service, Cart Service (bulk stock checks)
- **See:** Section 10.1.3 for token configuration

**Request Body:**

```json
{
  "skus": ["SKU-001", "SKU-002", "SKU-003"],
  "in_stock_only": false
}
```

| Field           | Type     | Required | Description                   |
| --------------- | -------- | -------- | ----------------------------- |
| `skus`          | string[] | Yes      | Array of SKUs (max 50)        |
| `in_stock_only` | boolean  | No       | Filter to only in-stock items |

**Response (200 OK):**

```json
{
  "items": [
    {
      "sku": "SKU-001",
      "quantity_available": 100,
      "quantity_reserved": 10,
      "in_stock": true
    },
    {
      "sku": "SKU-002",
      "quantity_available": 0,
      "quantity_reserved": 0,
      "in_stock": false
    }
  ],
  "not_found": ["SKU-003"]
}
```

---

#### 4.2.3 List Inventory Records

**Endpoint:** `GET /api/admin/inventory`

**Authentication:** Admin JWT

- **Header:** `Authorization: Bearer <admin-jwt>`
- **Required Claim:** `role: admin`
- **Callers:** Admin UI (inventory management dashboard)
- **See:** Section 10.1.4 for admin authentication

**Query Parameters:**

| Parameter | Type    | Required | Default | Description              |
| --------- | ------- | -------- | ------- | ------------------------ |
| `page`    | integer | No       | 1       | Page number              |
| `limit`   | integer | No       | 20      | Items per page (max 100) |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "sku": "SKU-12345",
      "quantity_available": 100,
      "quantity_reserved": 15,
      "reorder_level": 10,
      "max_stock": 500,
      "cost_per_unit": 25.99,
      "last_restocked": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-20T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

---

#### 4.2.4 Create Inventory Record

**Endpoint:** `POST /api/admin/inventory`

**Authentication:** Admin JWT

- **Header:** `Authorization: Bearer <admin-jwt>`
- **Required Claim:** `role: admin`
- **Callers:** Admin UI (manual inventory creation)
- **See:** Section 10.1.4 for admin authentication

**Request Body:**

```json
{
  "sku": "SKU-12345",
  "quantity_available": 100,
  "reorder_level": 10,
  "max_stock": 500,
  "cost_per_unit": 25.99
}
```

| Field                | Type    | Required | Description                                         |
| -------------------- | ------- | -------- | --------------------------------------------------- |
| `sku`                | string  | Yes      | Unique SKU - shared identifier with Product Service |
| `quantity_available` | integer | Yes      | Initial stock quantity                              |
| `reorder_level`      | integer | No       | Low stock threshold                                 |
| `max_stock`          | integer | No       | Maximum stock level                                 |
| `cost_per_unit`      | decimal | No       | Unit cost for valuation                             |

**Response (201 Created):**

```json
{
  "id": 1,
  "sku": "SKU-12345",
  "quantity_available": 100,
  "quantity_reserved": 0,
  "reorder_level": 10,
  "max_stock": 500,
  "cost_per_unit": 25.99,
  "created_at": "2025-01-20T15:00:00Z",
  "updated_at": "2025-01-20T15:00:00Z"
}
```

**Error Responses:**

| Status | Code                 | Description          |
| ------ | -------------------- | -------------------- |
| 400    | `VALIDATION_ERROR`   | Invalid request data |
| 409    | `SKU_ALREADY_EXISTS` | Duplicate SKU        |

---

#### 4.2.5 Update Inventory Quantity

**Endpoint:** `PUT /api/inventory/{sku}`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Internal services for stock adjustments
- **See:** Section 10.1.3 for token configuration

**Path Parameters:**

| Parameter | Type   | Required | Description |
| --------- | ------ | -------- | ----------- |
| `sku`     | string | Yes      | Product SKU |

**Request Body:**

```json
{
  "quantity_available": 150,
  "reorder_level": 20,
  "max_stock": 600,
  "cost_per_unit": 24.99
}
```

**Response (200 OK):** Returns updated inventory record.

**Error Responses:**

| Status | Code            | Description          |
| ------ | --------------- | -------------------- |
| 404    | `SKU_NOT_FOUND` | SKU not in inventory |

---

#### 4.2.6 Delete Inventory Record

**Endpoint:** `DELETE /api/admin/inventory/{sku}`

**Authentication:** Admin JWT

- **Header:** `Authorization: Bearer <admin-jwt>`
- **Required Claim:** `role: admin`
- **Callers:** Admin UI (inventory deletion)
- **See:** Section 10.1.4 for admin authentication

**Path Parameters:**

| Parameter | Type   | Required | Description |
| --------- | ------ | -------- | ----------- |
| `sku`     | string | Yes      | Product SKU |

**Response (204 No Content):** Empty body on success.

**Error Responses:**

| Status | Code                        | Description                            |
| ------ | --------------------------- | -------------------------------------- |
| 404    | `SKU_NOT_FOUND`             | SKU not in inventory                   |
| 409    | `ACTIVE_RESERVATIONS_EXIST` | Cannot delete with active reservations |

---

#### 4.2.7 List Reservations

**Endpoint:** `GET /api/admin/inventory/reservations`

**Authentication:** Admin JWT

- **Header:** `Authorization: Bearer <admin-jwt>`
- **Required Claim:** `role: admin`
- **Callers:** Admin UI (reservation monitoring dashboard)
- **See:** Section 10.1.4 for admin authentication

**Query Parameters:**

| Parameter  | Type    | Required | Default | Description                                          |
| ---------- | ------- | -------- | ------- | ---------------------------------------------------- |
| `page`     | integer | No       | 1       | Page number                                          |
| `limit`    | integer | No       | 20      | Items per page (max 100)                             |
| `status`   | string  | No       | all     | Filter by status: `PENDING`, `CONFIRMED`, `RELEASED` |
| `sku`      | string  | No       | -       | Filter by SKU                                        |
| `order_id` | string  | No       | -       | Filter by order ID                                   |

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "order_id": "ord-abc-123",
      "sku": "SKU-12345",
      "quantity": 2,
      "status": "PENDING",
      "expires_at": "2025-01-20T16:00:00Z",
      "created_at": "2025-01-20T15:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

---

#### 4.2.8 Get Reservation by ID

**Endpoint:** `GET /api/inventory/reservations/{id}`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Order Service (check reservation status)
- **See:** Section 10.1.3 for token configuration

**Path Parameters:**

| Parameter | Type    | Required | Description    |
| --------- | ------- | -------- | -------------- |
| `id`      | integer | Yes      | Reservation ID |

**Response (200 OK):**

```json
{
  "id": 1,
  "order_id": "ord-abc-123",
  "sku": "SKU-12345",
  "quantity": 2,
  "status": "PENDING",
  "expires_at": "2025-01-20T16:00:00Z",
  "created_at": "2025-01-20T15:00:00Z"
}
```

**Error Responses:**

| Status | Code                    | Description              |
| ------ | ----------------------- | ------------------------ |
| 404    | `RESERVATION_NOT_FOUND` | Reservation ID not found |

---

#### 4.2.9 Create Reservation

**Endpoint:** `POST /api/inventory/reservations`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Order Service (during checkout)
- **See:** Section 10.1.3 for token configuration

**Request Body:**

```json
{
  "order_id": "ord-abc-123",
  "sku": "SKU-12345",
  "quantity": 2
}
```

| Field      | Type    | Required | Description                |
| ---------- | ------- | -------- | -------------------------- |
| `order_id` | string  | Yes      | Order identifier           |
| `sku`      | string  | Yes      | Product SKU                |
| `quantity` | integer | Yes      | Quantity to reserve (>= 1) |

**Response (201 Created):**

```json
{
  "id": 1,
  "order_id": "ord-abc-123",
  "sku": "SKU-12345",
  "quantity": 2,
  "status": "PENDING",
  "expires_at": "2025-01-20T16:00:00Z",
  "created_at": "2025-01-20T15:00:00Z"
}
```

**Error Responses:**

| Status | Code                 | Description                   |
| ------ | -------------------- | ----------------------------- |
| 404    | `SKU_NOT_FOUND`      | SKU not in inventory          |
| 409    | `INSUFFICIENT_STOCK` | Requested qty > available qty |

---

#### 4.2.10 Confirm Reservation

**Endpoint:** `POST /api/inventory/reservations/{id}/confirm`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Order Service (after payment confirmed)
- **See:** Section 10.1.3 for token configuration

**Path Parameters:**

| Parameter | Type    | Required | Description    |
| --------- | ------- | -------- | -------------- |
| `id`      | integer | Yes      | Reservation ID |

**Response (200 OK):**

```json
{
  "id": 1,
  "order_id": "ord-abc-123",
  "sku": "SKU-12345",
  "quantity": 2,
  "status": "CONFIRMED",
  "confirmed_at": "2025-01-20T15:30:00Z"
}
```

**Error Responses:**

| Status | Code                        | Description                      |
| ------ | --------------------------- | -------------------------------- |
| 404    | `RESERVATION_NOT_FOUND`     | Reservation ID not found         |
| 409    | `INVALID_STATUS_TRANSITION` | Reservation not in PENDING state |

---

#### 4.2.11 Release Reservation

**Endpoint:** `POST /api/inventory/reservations/{id}/release`

**Authentication:** Service Token

- **Header:** `X-Service-Token: <token>`
- **Callers:** Order Service (order cancelled), scheduled job (expired reservations)
- **See:** Section 10.1.3 for token configuration

**Path Parameters:**

| Parameter | Type    | Required | Description    |
| --------- | ------- | -------- | -------------- |
| `id`      | integer | Yes      | Reservation ID |

**Response (200 OK):**

```json
{
  "id": 1,
  "order_id": "ord-abc-123",
  "sku": "SKU-12345",
  "quantity": 2,
  "status": "RELEASED",
  "released_at": "2025-01-20T15:45:00Z"
}
```

**Error Responses:**

| Status | Code                        | Description                          |
| ------ | --------------------------- | ------------------------------------ |
| 404    | `RESERVATION_NOT_FOUND`     | Reservation ID not found             |
| 409    | `INVALID_STATUS_TRANSITION` | Cannot release CONFIRMED reservation |

---

### 4.3 Error Response Format

All API errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
      "field": "sku",
      "reason": "SKU not found in inventory"
    }
  },
  "correlation_id": "req-abc-123-def-456",
  "timestamp": "2025-01-20T15:00:00Z"
}
```

### 4.4 Error Code Reference

| Code                        | HTTP Status | Description                                |
| --------------------------- | ----------- | ------------------------------------------ |
| `VALIDATION_ERROR`          | 400         | Request validation failed                  |
| `UNAUTHORIZED`              | 401         | Missing or invalid authentication          |
| `FORBIDDEN`                 | 403         | Insufficient permissions                   |
| `SKU_NOT_FOUND`             | 404         | SKU does not exist in inventory            |
| `RESERVATION_NOT_FOUND`     | 404         | Reservation ID does not exist              |
| `SKU_ALREADY_EXISTS`        | 409         | Duplicate SKU on create                    |
| `INSUFFICIENT_STOCK`        | 409         | Not enough stock for reservation           |
| `INVALID_STATUS_TRANSITION` | 409         | Invalid reservation status change          |
| `ACTIVE_RESERVATIONS_EXIST` | 409         | Cannot delete SKU with active reservations |
| `INTERNAL_ERROR`            | 500         | Unexpected server error                    |

### 4.5 Authentication

> **Complete Details:** See **Section 10 - Security** for comprehensive authentication documentation.

**Quick Reference:**

| Auth Type     | Header                        | Used By                                                       |
| ------------- | ----------------------------- | ------------------------------------------------------------- |
| Service Token | `X-Service-Token: <token>`    | Product Service, Order Service                                |
| Admin JWT     | `Authorization: Bearer <jwt>` | Admin UI                                                      |
| None          | -                             | Health endpoints (`/health`, `/health/ready`, `/health/live`) |

See Section 10.1.3 for service token configuration and Section 10.1.4 for admin JWT validation.

---

## 5. Event Architecture

Inventory Service participates in the xshopai event-driven architecture as both a **publisher** and **subscriber** via **Dapr Pub/Sub**.

> **Broker Abstraction:** Dapr Pub/Sub is broker-agnostic. The actual message broker (RabbitMQ, Azure Service Bus, Kafka, Redis Streams) is configured at deployment time via Dapr component YAML—no code changes required to switch brokers.

### 5.1 Event Summary

#### Published Events

| Event Name                 | Trigger                             | Primary Consumer(s)                   | Priority |
| -------------------------- | ----------------------------------- | ------------------------------------- | -------- |
| `inventory.stock.updated`  | Stock level changes                 | Product Service                       | High     |
| `inventory.stock.reserved` | Order placement creates reservation | Order Service, Audit Service          | High     |
| `inventory.stock.released` | Reservation cancelled/expired       | Order Service, Audit Service          | High     |
| `inventory.low.stock`      | Available quantity ≤ threshold      | Notification Service, Admin Dashboard | Medium   |
| `inventory.out.of.stock`   | Available quantity reaches zero     | Product Service, Notification Service | Critical |
| `inventory.created`        | New inventory record created        | Audit Service                         | Low      |

#### Subscribed Events

| Event Name        | Publisher       | Handler Endpoint               | Purpose                        |
| ----------------- | --------------- | ------------------------------ | ------------------------------ |
| `product.created` | Product Service | `POST /events/product-created` | Auto-create inventory record   |
| `product.deleted` | Product Service | `POST /events/product-deleted` | Soft-delete inventory, release |
| `order.cancelled` | Order Service   | `POST /events/order-cancelled` | Release reserved stock         |
| `order.completed` | Order Service   | `POST /events/order-completed` | Confirm reservations as sold   |

---

### 5.2 Published Events

All events use **CloudEvents 1.0** envelope with `source: "inventory-service"`. Only the `data` payload is shown below.

#### 5.2.1 inventory.stock.updated

**Trigger:** Stock level changes (admin updates, reservations, releases, confirmations)

| Consumer        | Purpose                          |
| --------------- | -------------------------------- |
| Product Service | Update denormalized availability |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "quantity": 100,
  "previousQuantity": 150,
  "reservedQuantity": 10,
  "availableQuantity": 90,
  "operation": "ADMIN_UPDATE",
  "timestamp": "2025-01-20T15:30:00Z"
}
```

**Operation Values:** `ADMIN_CREATE`, `ADMIN_UPDATE`, `ADMIN_DELETE`, `RESERVATION`, `RELEASE`, `CONFIRM`

---

#### 5.2.2 inventory.stock.reserved

**Trigger:** Stock successfully reserved for an order

| Consumer      | Purpose                     |
| ------------- | --------------------------- |
| Order Service | Confirm reservation created |
| Audit Service | Audit trail                 |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "quantity": 2,
  "orderId": "ord-xyz-789",
  "reservationId": "res-001",
  "expiresAt": "2025-01-20T15:50:00Z",
  "timestamp": "2025-01-20T15:35:00Z"
}
```

---

#### 5.2.3 inventory.stock.released

**Trigger:** Reservation cancelled or expired

| Consumer      | Purpose                    |
| ------------- | -------------------------- |
| Order Service | Handle reservation release |
| Audit Service | Audit trail                |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "quantity": 2,
  "orderId": "ord-xyz-789",
  "reservationId": "res-001",
  "reason": "ORDER_CANCELLED",
  "timestamp": "2025-01-20T16:00:00Z"
}
```

**Reason Values:** `ORDER_CANCELLED`, `RESERVATION_EXPIRED`, `MANUAL_RELEASE`

---

#### 5.2.4 inventory.low.stock

**Trigger:** Available quantity falls at or below threshold

| Consumer             | Purpose               |
| -------------------- | --------------------- |
| Notification Service | Send low stock alerts |
| Admin Dashboard      | Display warning in UI |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "currentQuantity": 5,
  "threshold": 10,
  "severity": "warning",
  "timestamp": "2025-01-20T16:15:00Z"
}
```

---

#### 5.2.5 inventory.out.of.stock

**Trigger:** Available quantity reaches zero

| Consumer             | Purpose                         |
| -------------------- | ------------------------------- |
| Product Service      | Mark product as out of stock    |
| Notification Service | Send out-of-stock notifications |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "severity": "critical",
  "timestamp": "2025-01-20T16:30:00Z"
}
```

---

#### 5.2.6 inventory.created

**Trigger:** New inventory record created

| Consumer      | Purpose     |
| ------------- | ----------- |
| Audit Service | Audit trail |

**Payload:**

```json
{
  "productId": "SKU-12345",
  "initialQuantity": 0,
  "lowStockThreshold": 10,
  "timestamp": "2025-01-20T14:00:00Z"
}
```

---

### 5.3 Subscribed Events

All handlers are **idempotent**—duplicate events are safely ignored.

#### 5.3.1 product.created

**Publisher:** Product Service  
**Handler Endpoint:** `POST /events/product-created`

**Behavior:**

1. Extract `sku` from event data
2. Check if inventory record already exists (idempotency)
3. Create new `InventoryItem` with zero initial stock
4. Publish `inventory.created` event

**Expected Payload:**

```json
{
  "productId": "prod-abc-123",
  "sku": "SKU-12345",
  "name": "Product Name"
}
```

> **Note:** Inventory Service uses `sku` as its primary identifier. The `productId` is stored for reference but `sku` is the lookup key.

---

#### 5.3.2 product.deleted

**Publisher:** Product Service  
**Handler Endpoint:** `POST /events/product-deleted`

**Behavior:**

1. Find inventory record by `sku`
2. Soft-delete the inventory record (set `is_active: false`)
3. Release any pending reservations

**Expected Payload:**

```json
{
  "productId": "prod-abc-123",
  "sku": "SKU-12345"
}
```

---

#### 5.3.3 order.cancelled

**Publisher:** Order Service  
**Handler Endpoint:** `POST /events/order-cancelled`

**Behavior:**

1. Find all PENDING reservations for the order
2. Release each reservation (restore available quantity)
3. Publish `inventory.stock.released` for each item

**Expected Payload:**

```json
{
  "orderId": "ord-xyz-789",
  "items": [
    { "sku": "SKU-12345", "quantity": 2 },
    { "sku": "SKU-67890", "quantity": 1 }
  ]
}
```

---

#### 5.3.4 order.completed

**Publisher:** Order Service  
**Handler Endpoint:** `POST /events/order-completed`

**Behavior:**

1. Find all PENDING reservations for the order
2. Confirm each reservation (convert reserved to sold)
3. Publish `inventory.stock.updated` with operation `CONFIRM`

**Expected Payload:**

```json
{
  "orderId": "ord-xyz-789",
  "items": [
    { "sku": "SKU-12345", "quantity": 2 },
    { "sku": "SKU-67890", "quantity": 1 }
  ]
}
```

---

### 5.4 Dapr Configuration

This section provides the Dapr component and subscription configurations needed for event-driven messaging.

#### 5.4.1 Pub/Sub Component (RabbitMQ)

File: `dapr/components/pubsub.yaml`

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: inventory-pubsub
  namespace: default
spec:
  type: pubsub.rabbitmq
  version: v1
  metadata:
    - name: host
      value: 'amqp://guest:guest@rabbitmq:5672'
    - name: durable
      value: 'true'
    - name: deletedWhenUnused
      value: 'false'
    - name: autoAck
      value: 'false'
    - name: deliveryMode
      value: '2' # Persistent messages
    - name: requeueInFailure
      value: 'true'
    - name: prefetchCount
      value: '10'
    - name: reconnectWait
      value: '5s'
    - name: maxReconnect
      value: '3'
scopes:
  - inventory-service
```

#### 5.4.2 Subscription Configuration

File: `dapr/components/subscription.yaml`

```yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: inventory-subscriptions
spec:
  pubsubname: inventory-pubsub
  topic: product.created
  routes:
    default: /events/product-created
  deadLetterTopic: inventory-events-dlq
scopes:
  - inventory-service
---
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: inventory-product-deleted
spec:
  pubsubname: inventory-pubsub
  topic: product.deleted
  routes:
    default: /events/product-deleted
  deadLetterTopic: inventory-events-dlq
scopes:
  - inventory-service
---
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: inventory-order-cancelled
spec:
  pubsubname: inventory-pubsub
  topic: order.cancelled
  routes:
    default: /events/order-cancelled
  deadLetterTopic: inventory-events-dlq
scopes:
  - inventory-service
---
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: inventory-order-completed
spec:
  pubsubname: inventory-pubsub
  topic: order.completed
  routes:
    default: /events/order-completed
  deadLetterTopic: inventory-events-dlq
scopes:
  - inventory-service
```

#### 5.4.3 CloudEvents Envelope

All published events use the **CloudEvents 1.0** specification:

```json
{
  "specversion": "1.0",
  "type": "inventory.stock.updated",
  "source": "inventory-service",
  "id": "evt-550e8400-e29b-41d4-a716-446655440000",
  "time": "2025-01-20T15:30:00Z",
  "datacontenttype": "application/json",
  "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
  "correlationid": "req-abc-123",
  "data": {
    "productId": "SKU-12345",
    "quantity": 100,
    "previousQuantity": 150,
    "reservedQuantity": 10,
    "availableQuantity": 90,
    "operation": "ADMIN_UPDATE",
    "timestamp": "2025-01-20T15:30:00Z"
  }
}
```

**CloudEvents Fields:**

| Field             | Description                                      | Source                       |
| ----------------- | ------------------------------------------------ | ---------------------------- |
| `specversion`     | CloudEvents spec version                         | Fixed: `"1.0"`               |
| `type`            | Event type (e.g., `inventory.stock.updated`)     | Application logic            |
| `source`          | Event producer identifier                        | Fixed: `"inventory-service"` |
| `id`              | Unique event ID                                  | UUID v4 generation           |
| `time`            | Event timestamp (ISO 8601)                       | System clock                 |
| `datacontenttype` | Content type of `data` field                     | Fixed: `"application/json"`  |
| `traceparent`     | W3C Trace Context for distributed tracing        | From incoming request        |
| `correlationid`   | Request correlation ID for cross-service tracing | From `X-Correlation-ID`      |
| `data`            | Event-specific payload (as shown in Section 5.1) | Application logic            |

#### 5.4.4 Event Handler Response Contract

Dapr expects specific response status codes from event handlers:

| Status Code | Meaning                       | Dapr Behavior                  |
| ----------- | ----------------------------- | ------------------------------ |
| `200`       | Success - event processed     | Acknowledge, remove from queue |
| `204`       | Success - no content          | Acknowledge, remove from queue |
| `400`       | Bad Request - malformed event | Drop event (no retry)          |
| `404`       | Handler not found             | Drop event (no retry)          |
| `500`       | Internal error - retriable    | Retry with backoff             |
| `503`       | Service unavailable           | Retry with backoff             |

---

### 5.5 Messaging Abstraction Layer

To support **deployment flexibility** across different Azure hosting options, the Inventory Service implements a **Messaging Abstraction Layer** that decouples business logic from specific messaging infrastructure.

#### 5.5.1 Why Abstraction?

| Deployment Target          | Dapr Available | Recommended Provider | Notes                    |
| -------------------------- | -------------- | -------------------- | ------------------------ |
| **Azure Container Apps**   | ✅ Yes         | `DaprProvider`       | Dapr sidecar built-in    |
| **Azure Kubernetes (AKS)** | ✅ Yes         | `DaprProvider`       | Dapr installed via Helm  |
| **Azure App Service**      | ❌ No          | `ServiceBusProvider` | Direct SDK required      |
| **Local Development**      | ✅ Optional    | `DaprProvider`       | Docker Compose with Dapr |
| **Local (No Dapr)**        | ❌ No          | `RabbitMQProvider`   | Direct RabbitMQ SDK      |

#### 5.5.2 Architecture Diagram

```mermaid
flowchart TB
    subgraph InventoryService["Inventory Service"]
        BL[Business Logic<br/>inventory_service.py]
        EP[Event Publisher<br/>event_publisher.py]
        MAL[Messaging Abstraction Layer<br/>messaging/]
    end

    subgraph Providers["Provider Implementations"]
        DP[DaprProvider]
        SBP[ServiceBusProvider]
        RMP[RabbitMQProvider]
    end

    subgraph Infrastructure["Messaging Infrastructure"]
        DS[Dapr Sidecar]
        SBSDK[Service Bus SDK]
        RMSDK[RabbitMQ SDK]
    end

    subgraph Backends["Message Brokers"]
        RMQ[RabbitMQ]
        ASB[Azure Service Bus]
        KAFKA[Kafka]
        REDIS[Redis Streams]
    end

    BL --> EP
    EP --> MAL
    MAL --> DP
    MAL --> SBP
    MAL --> RMP

    DP --> DS
    SBP --> SBSDK
    RMP --> RMSDK

    DS --> RMQ
    DS --> ASB
    DS --> KAFKA
    DS --> REDIS
    SBSDK --> ASB
    RMSDK --> RMQ

    style InventoryService fill:#4A90A4,stroke:#2C5F6E,color:#fff
    style MAL fill:#8B5CF6,stroke:#6D28D9,color:#fff
    style DP fill:#10B981,stroke:#059669,color:#fff
    style SBP fill:#3B82F6,stroke:#1D4ED8,color:#fff
    style RMP fill:#F59E0B,stroke:#D97706,color:#fff
    style DS fill:#10B981,stroke:#059669,color:#fff
```

#### 5.5.3 Deployment Configuration Matrix

| Environment Variable           | DaprProvider | ServiceBusProvider | RabbitMQProvider |
| ------------------------------ | ------------ | ------------------ | ---------------- |
| `MESSAGING_PROVIDER`           | `dapr`       | `servicebus`       | `rabbitmq`       |
| `DAPR_PUBSUB_NAME`             | ✅ Required  | ❌ Not used        | ❌ Not used      |
| `DAPR_HTTP_PORT`               | ✅ Required  | ❌ Not used        | ❌ Not used      |
| `SERVICEBUS_CONNECTION_STRING` | ❌ Not used  | ✅ Required        | ❌ Not used      |
| `SERVICEBUS_TOPIC_NAME`        | ❌ Not used  | ✅ Required        | ❌ Not used      |
| `RABBITMQ_URL`                 | ❌ Not used  | ❌ Not used        | ✅ Required      |
| `RABBITMQ_EXCHANGE`            | ❌ Not used  | ❌ Not used        | ⚪ Optional      |

#### 5.5.4 Benefits of Abstraction

| Benefit                    | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| **Deployment Flexibility** | Same codebase deploys to App Service, Container Apps, or AKS |
| **No Vendor Lock-in**      | Switch message brokers without code changes                  |
| **Testability**            | Mock provider for unit tests                                 |
| **Local Development**      | Run with or without Dapr sidecar                             |
| **Gradual Migration**      | Start with App Service, migrate to Container Apps when ready |
| **Cost Optimization**      | Choose broker based on pricing and requirements              |

---

## 6. Configuration

### 6.1 Environment Variables

| Variable              | Description                                | Required | Default       |
| --------------------- | ------------------------------------------ | -------- | ------------- |
| `PORT`                | Service port                               | No       | `8004`        |
| `FLASK_ENV`           | Flask environment                          | No       | `development` |
| `FLASK_DEBUG`         | Enable debug mode                          | No       | `false`       |
| `SECRET_KEY`          | Flask secret key                           | Yes      | -             |
| `DATABASE_URL`        | PostgreSQL connection string               | Yes      | -             |
| `REDIS_URL`           | Redis connection string                    | Yes      | -             |
| `JWT_SECRET_KEY`      | JWT validation secret                      | Yes      | -             |
| `JWT_ALGORITHM`       | JWT algorithm                              | No       | `HS256`       |
| `MESSAGING_PROVIDER`  | Provider: `dapr`, `servicebus`, `rabbitmq` | No       | `dapr`        |
| `LOG_LEVEL`           | Logging level                              | No       | `INFO`        |
| `LOW_STOCK_THRESHOLD` | Default low stock threshold                | No       | `10`          |
| `DAPR_HTTP_PORT`      | Dapr sidecar HTTP port                     | No       | `3500`        |
| `DAPR_GRPC_PORT`      | Dapr sidecar gRPC port                     | No       | `50001`       |
| `DAPR_PUBSUB_NAME`    | Dapr pub/sub component name                | No       | `pubsub`      |
| `CORS_ORIGINS`        | Allowed CORS origins (comma-separated)     | No       | `*`           |

#### Service Token Configuration

Service tokens for authenticating incoming service-to-service calls:

| Variable                | Description                     | Required | Format                         |
| ----------------------- | ------------------------------- | -------- | ------------------------------ |
| `PRODUCT_SERVICE_TOKEN` | Token for Product Service calls | Yes      | `svc-product-service-<random>` |
| `ORDER_SERVICE_TOKEN`   | Token for Order Service calls   | Yes      | `svc-order-service-<random>`   |
| `CART_SERVICE_TOKEN`    | Token for Cart Service calls    | Yes      | `svc-cart-service-<random>`    |
| `WEB_BFF_TOKEN`         | Token for Web BFF calls         | Yes      | `svc-web-bff-<random>`         |

> **Token Format**: `svc-{service-name}-{random-24-chars}` where random is cryptographically secure.
>
> **Generation**: Use `openssl rand -hex 12` to generate the 24-character random suffix.
>
> **Coordination**: Both the calling service and inventory-service must have matching tokens configured.

### 6.2 Messaging Provider Configuration

#### 6.2.1 Dapr Provider (Default - Local Development)

| Variable           | Description            | Required            |
| ------------------ | ---------------------- | ------------------- |
| `DAPR_HTTP_PORT`   | Dapr sidecar HTTP port | No (default: 3500)  |
| `DAPR_GRPC_PORT`   | Dapr sidecar gRPC port | No (default: 50001) |
| `DAPR_PUBSUB_NAME` | Pub/sub component name | Yes                 |

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

---

## 7. Deployment

### 7.1 Deployment Targets

| Target                 | Messaging Provider | Notes                           |
| ---------------------- | ------------------ | ------------------------------- |
| Local (Docker Compose) | `dapr`             | Uses Dapr sidecar with RabbitMQ |
| Azure App Service      | `servicebus`       | Direct SDK, no sidecar          |
| Azure Container Apps   | `dapr`             | Managed Dapr integration        |
| AKS                    | `dapr`             | Self-managed Dapr               |

---

## 8. Observability

This section covers logging, tracing, metrics, and error handling patterns that enable agent-driven implementation and debugging.

### 8.1 Distributed Tracing

#### 8.1.1 Correlation ID Propagation

Every request and event must carry a correlation ID for end-to-end tracing:

**Request Flow:**

1. API Gateway/BFF generates `X-Correlation-ID` header (UUID v4)
2. Inventory Service extracts header on incoming requests
3. All downstream calls (DB queries, event publishing) include correlation ID
4. Published events include `correlationid` in CloudEvents envelope
5. All log entries include correlation ID in structured metadata

#### 8.1.2 W3C Trace Context

For distributed tracing across services, W3C Trace Context headers are used:

| Header        | Description                             | Example                                                   |
| ------------- | --------------------------------------- | --------------------------------------------------------- |
| `traceparent` | Trace ID, parent span ID, sampling flag | `00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01` |
| `tracestate`  | Vendor-specific trace data              | `congo=t61rcWkgMzE`                                       |

Dapr automatically propagates these headers when publishing events and making service-to-service calls.

---

### 8.2 Structured Logging

#### 8.2.1 Log Format

All logs use JSON structured format for machine parseability:

```json
{
  "timestamp": "2025-01-20T15:30:00.123Z",
  "level": "INFO",
  "service": "inventory-service",
  "environment": "production",
  "correlation_id": "req-abc-123",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "message": "Inventory updated for SKU",
  "metadata": {
    "sku": "SKU-12345",
    "operation": "ADMIN_UPDATE",
    "previous_quantity": 150,
    "new_quantity": 100,
    "user_id": "admin-001"
  }
}
```

#### 8.2.2 Environment-Specific Logging

| Environment | Log Level | Destinations              | Additional Settings                   |
| ----------- | --------- | ------------------------- | ------------------------------------- |
| Development | `DEBUG`   | Console (pretty-printed)  | Full stack traces, SQL queries logged |
| Staging     | `INFO`    | Console + File            | Request/response bodies (sanitized)   |
| Production  | `WARNING` | Console + Centralized log | No sensitive data, no stack traces    |

#### 8.2.3 Required Log Events

| Event                    | Level   | When                         | Required Fields                               |
| ------------------------ | ------- | ---------------------------- | --------------------------------------------- |
| `inventory.created`      | INFO    | New inventory record         | `sku`, `quantity`, `user_id`                  |
| `inventory.updated`      | INFO    | Stock level changed          | `sku`, `prev_qty`, `new_qty`, `operation`     |
| `reservation.created`    | INFO    | New reservation              | `reservation_id`, `sku`, `quantity`           |
| `reservation.confirmed`  | INFO    | Reservation fulfilled        | `reservation_id`, `order_id`                  |
| `reservation.released`   | INFO    | Reservation cancelled        | `reservation_id`, `reason`                    |
| `event.published`        | DEBUG   | Event sent to broker         | `event_type`, `event_id`                      |
| `event.received`         | DEBUG   | Event handler invoked        | `event_type`, `event_id`                      |
| `event.processed`        | INFO    | Event successfully processed | `event_type`, `event_id`, `duration_ms`       |
| `event.failed`           | ERROR   | Event processing failed      | `event_type`, `event_id`, `error`, `retrying` |
| `low_stock.triggered`    | WARNING | Stock below threshold        | `sku`, `quantity`, `threshold`                |
| `out_of_stock.triggered` | WARNING | Stock reached zero           | `sku`                                         |
| `auth.failed`            | WARNING | Authentication failure       | `reason`, `ip_address`                        |
| `db.error`               | ERROR   | Database operation failed    | `operation`, `error`, `table`                 |

---

### 8.3 Metrics & Alerting

#### 8.3.1 Business Metrics

| Metric Name                     | Type    | Labels                 | Description                   |
| ------------------------------- | ------- | ---------------------- | ----------------------------- |
| `inventory_stock_level`         | Gauge   | `sku`, `warehouse`     | Current stock quantity        |
| `inventory_reservations_active` | Gauge   | `status`               | Active reservations count     |
| `inventory_operations_total`    | Counter | `operation`, `status`  | Total inventory operations    |
| `inventory_events_published`    | Counter | `event_type`, `status` | Events published to broker    |
| `inventory_events_consumed`     | Counter | `event_type`, `status` | Events consumed from broker   |
| `low_stock_alerts_total`        | Counter | `warehouse`            | Low stock alerts triggered    |
| `out_of_stock_events_total`     | Counter | `warehouse`            | Out of stock events triggered |

#### 8.3.2 Technical Metrics

| Metric Name                 | Type      | Labels                     | Description                   |
| --------------------------- | --------- | -------------------------- | ----------------------------- |
| `http_requests_total`       | Counter   | `method`, `path`, `status` | HTTP requests count           |
| `http_request_duration_ms`  | Histogram | `method`, `path`           | Request latency               |
| `db_query_duration_ms`      | Histogram | `operation`, `table`       | Database query latency        |
| `event_publish_duration_ms` | Histogram | `event_type`               | Event publishing latency      |
| `event_process_duration_ms` | Histogram | `event_type`               | Event handler processing time |

#### 8.3.3 Alerting Thresholds

| Alert                       | Condition                           | Severity | Action                        |
| --------------------------- | ----------------------------------- | -------- | ----------------------------- |
| High Error Rate             | Error rate > 5% for 5 minutes       | Critical | Page on-call engineer         |
| Elevated Latency            | p95 > 500ms for 5 minutes           | Warning  | Investigate slow queries      |
| Event Processing Backlog    | Consumer lag > 1000 messages        | Warning  | Scale consumers               |
| Low Stock Alert             | `inventory_stock_level` < threshold | Info     | Notify procurement team       |
| Database Connection Failure | DB pool exhausted                   | Critical | Page on-call, check DB health |

---

## 9. Error Handling

This section covers error response formats and resilience patterns for robust service operation.

### 9.1 Error Response Format

#### 9.1.1 Standard Error Structure

All API errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Not enough stock available for SKU-12345",
    "details": {
      "sku": "SKU-12345",
      "requested": 10,
      "available": 5
    },
    "correlation_id": "req-abc-123",
    "timestamp": "2025-01-20T15:30:00Z"
  }
}
```

#### 9.1.2 Error Code Catalog

| HTTP Status | Error Code              | Description                     | Retryable |
| ----------- | ----------------------- | ------------------------------- | --------- |
| 400         | `VALIDATION_ERROR`      | Invalid request payload         | No        |
| 400         | `INVALID_SKU`           | SKU format invalid              | No        |
| 400         | `INVALID_QUANTITY`      | Quantity must be non-negative   | No        |
| 401         | `UNAUTHORIZED`          | Missing or invalid auth token   | No        |
| 403         | `FORBIDDEN`             | Insufficient permissions        | No        |
| 404         | `SKU_NOT_FOUND`         | Inventory record not found      | No        |
| 404         | `RESERVATION_NOT_FOUND` | Reservation not found           | No        |
| 409         | `INSUFFICIENT_STOCK`    | Not enough stock for operation  | Yes       |
| 409         | `RESERVATION_CONFLICT`  | Conflicting reservation exists  | Yes       |
| 409         | `SKU_ALREADY_EXISTS`    | Duplicate SKU on creation       | No        |
| 422         | `RESERVATION_EXPIRED`   | Reservation TTL exceeded        | No        |
| 500         | `INTERNAL_ERROR`        | Unexpected server error         | Yes       |
| 503         | `SERVICE_UNAVAILABLE`   | Service temporarily unavailable | Yes       |
| 503         | `DATABASE_UNAVAILABLE`  | Database connection failed      | Yes       |

---

## 10. Security

### 10.1 Authentication

The Inventory Service uses a **layered authentication model** designed for deployment flexibility across different environments (App Service, Container Apps, AKS).

#### 10.1.1 Authentication Types

| Auth Type     | Purpose                          | Used By                |
| ------------- | -------------------------------- | ---------------------- |
| None          | Public endpoints (health checks) | Monitoring systems     |
| Service Token | Service-to-service communication | Order, Product Service |
| Admin JWT     | Admin user operations            | Admin UI, Admin BFF    |

#### 10.1.2 Layered Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Incoming Request                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Network Security (Optional)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dapr mTLS (when Dapr sidecar available)             │   │
│  │  • Automatic service identity                        │   │
│  │  • Encrypted service-to-service communication        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Service Token Validation (Required)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Pre-shared token validation                         │   │
│  │  • Always required for service endpoints             │   │
│  │  • Works on all deployment targets                   │   │
│  │  • Defense in depth                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Application Auth (Required for Admin)             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Admin JWT from auth-service                         │   │
│  │  • Required for admin CRUD operations                │   │
│  │  • Contains user claims (role, permissions)          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 10.1.3 Service Token Authentication

Service tokens are pre-shared secrets used for service-to-service authentication. This approach ensures the Inventory Service works consistently across all deployment targets.

**Design Principles:**

- **Deployment Flexibility**: Works on App Service (no Dapr), Container Apps, and AKS
- **Defense in Depth**: Additional security layer even when Dapr mTLS is available
- **Simplicity**: No token refresh logic required; tokens are long-lived secrets
- **Consistency**: Same authentication pattern across all environments

**Token Format Convention:**

`svc-{service-name}-{random-24-chars}`

Example: `svc-order-service-a1b2c3d4e5f6g7h8i9j0k1l2`

**Required Headers:**

| Header             | Value                    | Purpose             |
| ------------------ | ------------------------ | ------------------- |
| `X-Service-Token`  | Pre-shared service token | Authentication      |
| `X-Correlation-ID` | Request correlation ID   | Distributed tracing |
| `X-Service-Name`   | Calling service name     | Audit logging       |
| `Content-Type`     | `application/json`       | Request body format |

**Validation Flow:**

```
┌─────────────────┐    Request with    ┌─────────────────────┐
│  Order Service  │ ────────────────►  │  Inventory Service  │
│                 │   Authorization:   │                     │
│                 │   Bearer svc-...   │                     │
└─────────────────┘   X-Service-Name:  └─────────────────────┘
                      order-service              │
                                                 ▼
                                    ┌───────────────────────┐
                                    │ 1. Extract token      │
                                    │ 2. Lookup service     │
                                    │ 3. Get expected token │
                                    │ 4. Compare tokens     │
                                    │ 5. Allow/Deny         │
                                    └───────────────────────┘
```

**Deployment Target Compatibility:**

| Deployment Target      | Dapr mTLS | Service Token | Notes                                |
| ---------------------- | --------- | ------------- | ------------------------------------ |
| Azure App Service      | ❌ No     | ✅ Required   | No Dapr support                      |
| Azure Container Apps   | ✅ Yes    | ✅ Required   | Dapr + token for defense in depth    |
| Azure Kubernetes (AKS) | ✅ Yes    | ✅ Required   | Dapr + token for defense in depth    |
| Local Development      | Optional  | ✅ Required   | Can run with or without Dapr sidecar |

#### 10.1.4 Admin JWT Authentication

Admin endpoints require a valid JWT token issued by the auth-service with `role: admin`.

```
Authorization: Bearer <admin_jwt_token>
```

**Token Validation Process:**

1. Extract token from `Authorization: Bearer <token>` header
2. Validate token signature using `JWT_SECRET_KEY`
3. Verify token is not expired (`exp` claim)
4. Verify `role` claim equals `admin`
5. Extract user claims (`sub`, `role`, `permissions`)
6. Attach user context to request for authorization checks

### 10.2 Authorization

Authorization determines **what** an authenticated entity can do. After authentication validates identity, authorization checks permissions.

#### 10.2.1 Authorization Rules

| Auth Type     | Authorized Operations                                        |
| ------------- | ------------------------------------------------------------ |
| None          | Health endpoints (`/health`, `/health/ready`) and `/metrics` |
| Service Token | Stock queries and reservation operations                     |
| Admin JWT     | Full CRUD on inventory, adjustments, reporting               |
| Dapr Internal | Event subscription endpoints only                            |

### 10.3 Service-to-Service Communication

This section describes how other services call Inventory Service APIs.

#### 10.3.1 Direct HTTP with Service Token

For deployments without Dapr (e.g., Azure App Service), calling services make direct HTTP requests with:

| Header             | Value                    | Purpose             |
| ------------------ | ------------------------ | ------------------- |
| `X-Service-Token`  | Pre-shared service token | Authentication      |
| `X-Correlation-ID` | Request correlation ID   | Distributed tracing |
| `X-Service-Name`   | Calling service name     | Audit logging       |
| `Content-Type`     | `application/json`       | Request body format |

#### 10.3.2 Dapr Service Invocation with Service Token

For deployments with Dapr (Container Apps, AKS), use Dapr for service discovery while still including service token for defense in depth. The same headers are passed via Dapr's `http_headers` parameter.

#### 10.3.3 Why Service Token with Dapr?

Even when using Dapr's mTLS, we include service tokens for:

1. **Defense in Depth**: Multiple layers of security validation
2. **Caller Identification**: Know which specific service made the call
3. **Deployment Flexibility**: Same code works with or without Dapr
4. **Audit Trail**: Service name logged for all requests
5. **Consistency**: Uniform authentication pattern across all deployments

### 10.4 Input Validation

All input is validated using schema validation (Marshmallow) before processing. Validation rules include:

| Field                | Validation Rules                          |
| -------------------- | ----------------------------------------- |
| `sku`                | Required, 1-100 characters                |
| `quantity_available` | Required, non-negative integer            |
| `reorder_level`      | Optional, non-negative integer            |
| `max_stock`          | Optional, non-negative integer            |
| `cost_per_unit`      | Optional, non-negative decimal (2 places) |

### 10.5 CORS Configuration

Cross-Origin Resource Sharing is configured via the `CORS_ORIGINS` environment variable for frontend access.
