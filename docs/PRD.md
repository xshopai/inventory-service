# Inventory Service - Product Requirements Document

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope](#2-scope)
3. [User Stories](#3-user-stories)
4. [Functional Requirements](#4-functional-requirements)
5. [Traceability Matrix](#5-traceability-matrix)
6. [Non-Functional Requirements](#6-non-functional-requirements)

---

## 1. Executive Summary

### 1.1 Purpose

The Inventory Service is a core microservice within the xshopai e-commerce platform responsible for tracking stock levels and managing inventory reservations. It serves as the single source of truth for product availability across the platform.

### 1.2 Business Objectives

| Objective                     | Description                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| **Prevent Overselling**       | Ensure customers cannot purchase more items than available in stock                |
| **Real-time Availability**    | Provide accurate stock information to Product Service for customer-facing displays |
| **Support Order Fulfillment** | Enable Order Service to reserve and confirm inventory during checkout              |
| **Enable Stock Management**   | Allow administrators to view and adjust inventory levels                           |

### 1.3 Success Metrics

| Metric                   | Target  | Description                                           |
| ------------------------ | ------- | ----------------------------------------------------- |
| Oversell Rate            | < 0.1%  | Percentage of orders that exceed available stock      |
| API Response Time (p95)  | < 100ms | 95th percentile response time for stock queries       |
| Reservation Success Rate | > 99.5% | Percentage of valid reservation requests that succeed |
| Service Availability     | 99.9%   | Uptime during business hours                          |

### 1.4 Target Users

| User                | Interaction                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------- |
| **Product Service** | Queries stock availability to display on product pages and filter out-of-stock items        |
| **Order Service**   | Creates reservations during checkout, confirms on payment success, releases on cancellation |
| **Admin Users**     | View inventory levels, manually adjust stock quantities via Admin UI                        |

---

## 2. Scope

### 2.1 In Scope

- Stock level tracking per SKU
- Stock availability query API
- Admin CRUD operations for inventory
- Inventory reservations (create, confirm, release)
- Stock update event publishing
- Audit event publishing (consumed by audit-service)

### 2.2 Out of Scope

- Bulk import/export operations
- Low stock alerts and notifications
- Event-driven inventory initialization from Product Service
- Built-in audit trail (delegated to audit-service)
- Multi-warehouse support
- Automatic reservation expiration

---

## 3. User Stories

### 3.1 Query Stock Availability

**As a** Product Service  
**I want to** query current stock levels for one or more SKUs  
**So that** I can display accurate availability information to customers

**Acceptance Criteria:**

- [ ] API accepts a single SKU or list of SKUs
- [ ] Returns available quantity for each requested SKU
- [ ] Returns "SKU not found" error for SKUs that don't exist in inventory
- [ ] Response time < 100ms for up to 50 SKUs
- [ ] Supports filtering to return only in-stock items (available quantity > 0)

---

### 3.2 Reserve Inventory for Order

**As a** Order Service  
**I want to** reserve, confirm, and release inventory for orders  
**So that** customers cannot purchase more items than available during checkout

**Acceptance Criteria:**

- [ ] Reserve API decrements available quantity and creates a reservation record
- [ ] Reserve API fails if requested quantity exceeds available stock
- [ ] Confirm API converts reservation to permanent stock deduction
- [ ] Release API restores reserved quantity back to available stock
- [ ] Each reservation is linked to an order ID for traceability
- [ ] Publishes `inventory.stock.updated` event after successful reserve/confirm/release

---

### 3.3 Manage Inventory Records

**As an** Admin User  
**I want to** create, view, update, and delete inventory records  
**So that** I can maintain accurate stock levels in the system

**Acceptance Criteria:**

- [ ] View paginated list of all inventory records with SKU and quantity
- [ ] Create new inventory record with SKU and initial quantity
- [ ] Update quantity for an existing inventory record
- [ ] Delete an inventory record by SKU
- [ ] Prevent duplicate SKU creation (returns error if SKU already exists)
- [ ] Publishes `inventory.stock.updated` event after create/update/delete
- [ ] All operations require admin authentication

---

## 4. Functional Requirements

### 4.1 Query Stock for Single SKU

**Description:**  
The system shall provide an API endpoint to query stock availability for a single SKU.

**Functional Details:**

| Aspect   | Specification                                    |
| -------- | ------------------------------------------------ |
| Endpoint | `GET /api/inventory/{sku}`                       |
| Input    | SKU path parameter (string)                      |
| Output   | Inventory record with SKU and available quantity |
| Auth     | None (public read access for stock levels)       |

**Acceptance Criteria:**

- [ ] API accepts SKU as path parameter
- [ ] Returns inventory record with available quantity
- [ ] Response time < 100ms

**Notes:** This is the primary endpoint for Product Service to check individual product availability.

---

### 4.2 Query Stock for Multiple SKUs

**Description:**  
The system shall provide an API endpoint to query stock availability for multiple SKUs in a single request.

**Functional Details:**

| Aspect   | Specification                                        |
| -------- | ---------------------------------------------------- |
| Endpoint | `POST /api/inventory/batch`                          |
| Input    | Array of SKUs in request body                        |
| Output   | Array of inventory records with available quantities |
| Auth     | None (public read access)                            |
| Limit    | Maximum 50 SKUs per request                          |

**Acceptance Criteria:**

- [ ] API accepts array of SKUs in request body
- [ ] Returns inventory records for all requested SKUs
- [ ] Response time < 100ms for up to 50 SKUs

**Notes:** Batch endpoint optimizes performance for product listing pages.

---

### 4.3 Handle Unknown SKU in Query

**Description:**  
The system shall return an HTTP 404 error with "SKU not found" message for SKUs that do not exist in the inventory database.

**Functional Details:**

| Aspect    | Specification                                                           |
| --------- | ----------------------------------------------------------------------- |
| Behavior  | Return HTTP 404 with `{ error: "SKU not found", sku }` for unknown SKUs |
| Rationale | Clearly indicates SKU doesn't exist vs. being out of stock              |

**Acceptance Criteria:**

- [ ] Returns HTTP 404 "SKU not found" error for non-existent SKU
- [ ] Error response includes the requested SKU for debugging

**Notes:** This behavior clearly distinguishes between "SKU not in inventory system" and "SKU exists but quantity is 0".

---

### 4.4 Filter In-Stock Items

**Description:**  
The system shall support filtering batch query results to return only in-stock items (available quantity > 0).

**Functional Details:**

| Aspect    | Specification                               |
| --------- | ------------------------------------------- |
| Parameter | `?inStockOnly=true` query parameter         |
| Behavior  | Excludes items with available quantity <= 0 |

**Acceptance Criteria:**

- [ ] Filter parameter excludes out-of-stock items
- [ ] Default behavior returns all items regardless of stock

**Notes:** Useful for Product Service to efficiently load only available products.

---

### 4.5 Create Inventory Reservation

**Description:**  
The system shall provide an API to create inventory reservation for an order.

**Functional Details:**

| Aspect   | Specification                              |
| -------- | ------------------------------------------ |
| Endpoint | `POST /api/inventory/reservations`         |
| Auth     | Service-to-service authentication required |

**Inputs:**

| Field    | Type    | Required | Description                               |
| -------- | ------- | -------- | ----------------------------------------- |
| orderId  | string  | Yes      | Unique identifier of the order            |
| sku      | string  | Yes      | Product SKU to reserve                    |
| quantity | integer | Yes      | Number of units to reserve (must be >= 1) |

**Outputs:**

| Field         | Type    | Description                       |
| ------------- | ------- | --------------------------------- |
| reservationId | string  | Unique identifier for reservation |
| orderId       | string  | Order ID associated               |
| sku           | string  | Reserved SKU                      |
| quantity      | integer | Reserved quantity                 |
| status        | string  | Reservation status ("reserved")   |
| createdAt     | string  | ISO 8601 timestamp                |

**Acceptance Criteria:**

- [ ] Creates reservation record with provided details
- [ ] Returns reservation ID for tracking
- [ ] Reservation status is "reserved"

**Notes:** Called by Order Service during checkout flow.

---

### 4.6 Decrement Stock on Reservation

**Description:**  
The system shall decrement available quantity when a reservation is created.

**Functional Details:**

| Aspect    | Specification                                   |
| --------- | ----------------------------------------------- |
| Operation | Atomic increment of reserved_quantity field     |
| Effect    | Available quantity decreases by reserved amount |

**Acceptance Criteria:**

- [ ] Reserved quantity increases by requested amount
- [ ] Available quantity decreases accordingly
- [ ] Operation is atomic (no partial updates)

**Notes:** Ensures stock is held for the order during payment processing.

---

### 4.7 Reject Insufficient Stock Reservation

**Description:**  
The system shall reject reservation requests if the requested quantity exceeds available stock.

**Functional Details:**

| Aspect    | Specification                                     |
| --------- | ------------------------------------------------- |
| Condition | `requested_quantity > available_quantity`         |
| Response  | HTTP 409 Conflict with "Insufficient stock" error |

**Acceptance Criteria:**

- [ ] Rejects reservation when stock is insufficient
- [ ] Returns clear error message with available quantity
- [ ] Does not create partial reservation

**Notes:** Prevents overselling by enforcing stock limits at reservation time.

---

### 4.8 Confirm Reservation

**Description:**  
The system shall provide an API to confirm a reservation, converting it to a permanent stock deduction.

**Functional Details:**

| Aspect   | Specification                                           |
| -------- | ------------------------------------------------------- |
| Endpoint | `POST /api/inventory/reservations/{id}/confirm`         |
| Effect   | Changes reservation status to "confirmed"               |
| Stock    | Decrements total_quantity, decrements reserved_quantity |

**Acceptance Criteria:**

- [ ] Updates reservation status to "confirmed"
- [ ] Permanently deducts quantity from total stock
- [ ] Decreases reserved quantity accordingly

**Notes:** Called by Order Service after successful payment.

---

### 4.9 Release Reservation

**Description:**  
The system shall provide an API to release a reservation, restoring the reserved quantity back to available stock.

**Functional Details:**

| Aspect   | Specification                                        |
| -------- | ---------------------------------------------------- |
| Endpoint | `POST /api/inventory/reservations/{id}/release`      |
| Effect   | Changes reservation status to "released"             |
| Stock    | Decrements reserved_quantity (restores availability) |

**Acceptance Criteria:**

- [ ] Updates reservation status to "released"
- [ ] Restores reserved quantity to available pool
- [ ] Cannot release already confirmed reservation

**Notes:** Called by Order Service on order cancellation or payment failure.

---

### 4.10 Associate Reservation with Order

**Description:**  
The system shall associate each reservation with an order ID for traceability.

**Functional Details:**

| Aspect     | Specification                              |
| ---------- | ------------------------------------------ |
| Field      | `orderId` stored with reservation record   |
| Constraint | Order ID is required and must be non-empty |

**Acceptance Criteria:**

- [ ] Every reservation has an associated order ID
- [ ] Can query reservations by order ID

**Notes:** Enables Order Service to track all reservations for a given order.

---

### 4.11 Publish Stock Updated Event on Reservation

**Description:**  
The system shall publish `inventory.stock.updated` event after successful reserve, confirm, or release operations.

**Functional Details:**

| Aspect  | Specification                           |
| ------- | --------------------------------------- |
| Event   | `inventory.stock.updated`               |
| Trigger | After reserve, confirm, or release      |
| Payload | SKU, available quantity, operation type |

**Acceptance Criteria:**

- [ ] Event published after successful reservation create
- [ ] Event published after successful confirmation
- [ ] Event published after successful release

**Notes:** Product Service subscribes to update cached availability display.

---

### 4.12 List Inventory Records

**Description:**  
The system shall provide an API to list all inventory records with pagination.

**Functional Details:**

| Aspect     | Specification                 |
| ---------- | ----------------------------- |
| Endpoint   | `GET /api/admin/inventory`    |
| Pagination | Query params: `page`, `limit` |
| Default    | page=1, limit=20              |
| Auth       | Admin authentication required |

**Acceptance Criteria:**

- [ ] Returns paginated list of inventory records
- [ ] Includes total count for pagination UI
- [ ] Supports configurable page size

**Notes:** Used by Admin UI to display inventory management dashboard.

---

### 4.13 Create Inventory Record

**Description:**  
The system shall provide an API to create a new inventory record with SKU and initial quantity.

**Functional Details:**

| Aspect   | Specification                        |
| -------- | ------------------------------------ |
| Endpoint | `POST /api/admin/inventory`          |
| Input    | `{ sku: string, quantity: integer }` |
| Auth     | Admin authentication required        |

**Acceptance Criteria:**

- [ ] Creates inventory record with provided SKU and quantity
- [ ] Returns created record with generated ID
- [ ] Initial reserved_quantity is 0

**Notes:** Used when adding new products to the platform.

---

### 4.14 Get Inventory Record by SKU

**Description:**  
The system shall provide an API to retrieve a single inventory record by SKU with full details.

**Functional Details:**

| Aspect   | Specification                                |
| -------- | -------------------------------------------- |
| Endpoint | `GET /api/admin/inventory/{sku}`             |
| Output   | Full inventory record including reserved qty |
| Auth     | Admin authentication required                |

**Acceptance Criteria:**

- [ ] Returns complete inventory record for given SKU
- [ ] Returns 404 if SKU not found

**Notes:** Provides detailed view for admin inventory management.

---

### 4.15 Update Inventory Quantity

**Description:**  
The system shall provide an API to update quantity for an existing inventory record.

**Functional Details:**

| Aspect   | Specification                    |
| -------- | -------------------------------- |
| Endpoint | `PUT /api/admin/inventory/{sku}` |
| Input    | `{ quantity: integer }`          |
| Auth     | Admin authentication required    |

**Acceptance Criteria:**

- [ ] Updates total quantity for specified SKU
- [ ] Returns updated inventory record
- [ ] Returns 404 if SKU not found

**Notes:** Used for stock replenishment or manual corrections.

---

### 4.16 Delete Inventory Record

**Description:**  
The system shall provide an API to delete an inventory record by SKU.

**Functional Details:**

| Aspect   | Specification                            |
| -------- | ---------------------------------------- |
| Endpoint | `DELETE /api/admin/inventory/{sku}`      |
| Auth     | Admin authentication required            |
| Safety   | Should warn if active reservations exist |

**Acceptance Criteria:**

- [ ] Deletes inventory record for specified SKU
- [ ] Returns 404 if SKU not found
- [ ] Returns 204 No Content on success

**Notes:** Used when discontinuing products.

---

### 4.17 Prevent Duplicate SKU Creation

**Description:**  
The system shall reject creation of inventory records with duplicate SKUs.

**Functional Details:**

| Aspect   | Specification                               |
| -------- | ------------------------------------------- |
| Auth     | Admin authentication required               |
| Check    | SKU uniqueness constraint in database       |
| Response | HTTP 409 Conflict with "SKU already exists" |

**Acceptance Criteria:**

- [ ] Rejects duplicate SKU with clear error message
- [ ] Does not modify existing record

**Notes:** Ensures data integrity; each SKU has exactly one inventory record.

---

### 4.18 Publish Stock Updated Event on Admin Operations

**Description:**  
The system shall publish `inventory.stock.updated` event after admin create, update, or delete operations.

**Functional Details:**

| Aspect  | Specification                     |
| ------- | --------------------------------- |
| Event   | `inventory.stock.updated`         |
| Trigger | After create, update, or delete   |
| Payload | SKU, new quantity, operation type |

**Acceptance Criteria:**

- [ ] Event published after successful create
- [ ] Event published after successful update
- [ ] Event published after successful delete

**Notes:** Enables real-time sync with Product Service availability display.

---

## 5. Traceability Matrix

> **Purpose:** This matrix provides a single snapshot view linking User Stories to their implementing requirements. Use this to verify coverage and track implementation status.

| User Story                             | Story Title                 | Requirements                                                                                                                                                                                                                                                                                                 |
| -------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [3.1](#31-query-stock-availability)    | Query Stock Availability    | [4.1](#41-query-stock-for-single-sku), [4.2](#42-query-stock-for-multiple-skus), [4.3](#43-handle-unknown-sku-in-query), [4.4](#44-filter-in-stock-items)                                                                                                                                                    |
| [3.2](#32-reserve-inventory-for-order) | Reserve Inventory for Order | [4.5](#45-create-inventory-reservation), [4.6](#46-decrement-stock-on-reservation), [4.7](#47-reject-insufficient-stock-reservation), [4.8](#48-confirm-reservation), [4.9](#49-release-reservation), [4.10](#410-associate-reservation-with-order), [4.11](#411-publish-stock-updated-event-on-reservation) |
| [3.3](#33-manage-inventory-records)    | Manage Inventory Records    | [4.12](#412-list-inventory-records), [4.13](#413-create-inventory-record), [4.14](#414-get-inventory-record-by-sku), [4.15](#415-update-inventory-quantity), [4.16](#416-delete-inventory-record), [4.17](#417-prevent-duplicate-sku-creation), [4.18](#418-publish-stock-updated-event-on-admin-operations) |

**Coverage Summary:**

- Total User Stories: 3
- Total Requirements: 18
- Requirements without User Story: 0
- User Stories without Requirements: 0

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric                  | Target    | Description                              |
| ----------------------- | --------- | ---------------------------------------- |
| API Response Time (p95) | < 100ms   | Stock queries and reservation operations |
| Throughput              | 500 req/s | Sustained load during normal operations  |

### 6.2 Reliability

| Metric                   | Target  | Description                               |
| ------------------------ | ------- | ----------------------------------------- |
| Service Availability     | 99.9%   | Uptime during business hours              |
| Reservation Success Rate | > 99.5% | Valid requests that complete successfully |
| Oversell Rate            | < 0.1%  | Orders exceeding available stock          |

### 6.3 Security

| Requirement                                 | Priority |
| ------------------------------------------- | -------- |
| Admin endpoints require JWT with admin role | Critical |
| Input validation on all endpoints           | Critical |
| No sensitive data in logs                   | High     |

### 6.4 Observability

| Requirement                                                         | Priority |
| ------------------------------------------------------------------- | -------- |
| Health check endpoints (`/health`, `/health/ready`, `/health/live`) | Critical |
| Structured JSON logging with correlation IDs                        | High     |
| Log stock changes with before/after values                          | High     |
| Prometheus metrics endpoint (`/metrics`)                            | High     |

---
