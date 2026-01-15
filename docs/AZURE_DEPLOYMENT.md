# Azure Container Apps Deployment Guide

## Overview

This document describes the Azure Container Apps deployment setup for the Inventory Service.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Azure Container Apps Environment                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Inventory Service                                │  │
│  │                                                  │  │
│  │  ┌─────────────┐      ┌──────────────────────┐ │  │
│  │  │   App       │◄────►│   Dapr Sidecar       │ │  │
│  │  │   Port 8005 │      │   HTTP: 3500         │ │  │
│  │  │             │      │   gRPC: 50005        │ │  │
│  │  └─────────────┘      └──────────────────────┘ │  │
│  │                                                  │  │
│  │  External Ingress: https://inventory-...        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Dependencies:                                           │
│  ├─ Azure MySQL Flexible Server (inventory_service_db)  │
│  ├─ Azure Service Bus (Dapr pub/sub)                   │
│  ├─ Azure Redis (Dapr state store)                     │
│  ├─ Azure Key Vault (secrets)                          │
│  └─ Azure Container Registry (Docker images)           │
└─────────────────────────────────────────────────────────┘
```

## Infrastructure Configuration

### Bicep Templates

The inventory-service Container App is defined in:
```
infrastructure/azure/container-apps/bicep/layers/layer4-container-apps.bicep
```

Key configuration:
- **Service Name**: `inventory-service`
- **Port**: 8005
- **Dapr App ID**: `inventory-service`
- **Dapr HTTP Port**: 3500 (standard sidecar)
- **Dapr gRPC Port**: 50005 (unique to inventory-service)
- **Database**: Azure MySQL Flexible Server (`inventory_service_db`)
- **Resources**: 
  - CPU: 0.5-1 cores (environment dependent)
  - Memory: 1-2Gi (environment dependent)
- **Scaling**: 1-5/10 replicas (environment dependent)
- **Health Probes**:
  - Liveness: `/liveness`
  - Readiness: `/readiness`
  - Startup: `/readiness`

### Environment Variables

The Container App is configured with these environment variables:

```yaml
ENVIRONMENT: production
DEBUG: false
NAME: inventory-service
VERSION: 1.0.0
PORT: 8005
LOG_LEVEL: INFO/WARNING (env dependent)
LOG_FORMAT: json
LOG_TO_CONSOLE: true
LOG_TO_FILE: false

# Dapr Configuration
DAPR_HOST: localhost
DAPR_HTTP_PORT: 3500
DAPR_GRPC_PORT: 50005
DAPR_APP_ID: inventory-service
DAPR_PUBSUB_NAME: event-bus

# Database Configuration
MYSQL_DATABASE: inventory_service_db
MYSQL_HOST: <from Key Vault: inventory-service-mysql-host>
MYSQL_PORT: <from Key Vault: inventory-service-mysql-port>
MYSQL_USER: <from Key Vault: inventory-service-mysql-username>
MYSQL_PASSWORD: <from Key Vault: inventory-service-mysql-password>

# Application Configuration
WORKERS: 2-4 (env dependent)
```

## Deployment Process

### Prerequisites

1. **Infrastructure Deployment** (must be done first):
   ```bash
   # Deploy all infrastructure layers
   cd infrastructure/azure/container-apps
   
   # Deploy Layer 0-3 (foundation, platform, data, Dapr)
   az deployment group create \
     --resource-group rg-xshopai-dev \
     --template-file bicep/main.bicep \
     --parameters @bicep/parameters/dev.bicepparam
   
   # Deploy Layer 4 (Container Apps)
   az deployment group create \
     --resource-group rg-xshopai-dev \
     --template-file bicep/layers/layer4-container-apps.bicep \
     --parameters @bicep/parameters/dev.bicepparam
   ```

   **Note**: Ensure Key Vault secrets are created:
   ```bash
   # Example: Add secrets to Key Vault (after Key Vault is deployed in Layer 0)
   KEY_VAULT_NAME="kv-xshopai-dev-unique"
   
   az keyvault secret set --vault-name $KEY_VAULT_NAME \
     --name "mysql-host" --value "<mysql-server-fqdn>"
   
   az keyvault secret set --vault-name $KEY_VAULT_NAME \
     --name "mysql-port" --value "3306"
   
   az keyvault secret set --vault-name $KEY_VAULT_NAME \
     --name "mysql-username" --value "<admin-username>"
   
   az keyvault secret set --vault-name $KEY_VAULT_NAME \
     --name "mysql-password" --value "<secure-password>"
   ```

2. **GitHub Secrets Configuration**:
   - `AZURE_CLIENT_ID`: Service principal client ID
   - `AZURE_TENANT_ID`: Azure AD tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
   - MySQL credentials stored in Azure Key Vault:
     - `mysql-host`
     - `mysql-port`
     - `mysql-username`
     - `mysql-password`

### Manual Deployment

Trigger deployment via GitHub Actions:

1. Navigate to: https://github.com/xshopai/inventory-service/actions/workflows/deploy-container-app.yml
2. Click "Run workflow"
3. Select environment (dev/staging/prod)
4. Click "Run workflow"

### Automatic Deployment

The workflow automatically triggers on:
- Push to `main` branch (when code changes)
- Changes to:
  - `src/**`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `Dockerfile`
  - `.dockerignore`
  - `main.py`
  - `run.py`

## Deployment Workflow

### Stage 1: Build & Push Image

1. **Checkout code** from repository
2. **Azure login** using federated credentials
3. **Discover resources** (ACR, resource group)
4. **Build Docker image** using multi-stage Dockerfile
5. **Push to ACR** with tags:
   - Short SHA (e.g., `a1b2c3d`)
   - Environment-latest (e.g., `dev-latest`)
   - `latest` (prod only)

### Stage 2: Deploy to Container Apps

1. **Update Container App** with new image
   - Existing app configuration is preserved
   - Only the container image is updated
2. **Wait for deployment** to complete
3. **Run health checks** to verify deployment

### Stage 3: Post-Deployment Verification

1. **Health Check**: Verify `/health` endpoint returns 200
2. **API Tests**: Test version and readiness endpoints
3. **Dapr Verification**: Confirm Dapr sidecar is enabled
4. **MySQL Check**: Verify database configuration

## Monitoring & Troubleshooting

### View Container App Logs

```bash
# Stream logs
az containerapp logs show \
  --name inventory-service \
  --resource-group rg-xshopai-dev \
  --follow

# View recent logs
az containerapp logs show \
  --name inventory-service \
  --resource-group rg-xshopai-dev \
  --tail 100
```

### View Dapr Logs

```bash
# View Dapr sidecar logs
az containerapp logs show \
  --name inventory-service \
  --resource-group rg-xshopai-dev \
  --container daprd \
  --tail 100
```

### Check Revision Status

```bash
# List all revisions
az containerapp revision list \
  --name inventory-service \
  --resource-group rg-xshopai-dev \
  --output table

# Show specific revision
az containerapp revision show \
  --name <revision-name> \
  --app inventory-service \
  --resource-group rg-xshopai-dev
```

### Health Check Endpoints

- **Health**: `https://inventory-service-<env>.azurecontainerapps.io/health` (basic status)
- **Liveness**: `https://inventory-service-<env>.azurecontainerapps.io/liveness` (service alive)
- **Readiness**: `https://inventory-service-<env>.azurecontainerapps.io/readiness` (ready for traffic)
- **Metrics**: `https://inventory-service-<env>.azurecontainerapps.io/metrics` (system metrics)

### Common Issues

#### 1. Container App Not Found

**Error**: Container App 'inventory-service' does not exist

**Solution**: Deploy infrastructure Layer 4 first:
```bash
cd infrastructure/azure/container-apps
az deployment group create \
  --resource-group rg-xshopai-dev \
  --template-file bicep/layers/layer4-container-apps.bicep \
  --parameters @bicep/parameters/dev.bicepparam
```

#### 2. MySQL Connection Failed

**Error**: Can't connect to MySQL server

**Solution**: 
1. Verify MySQL Flexible Server is running
2. Check Key Vault has MySQL credentials
3. Verify managed identity has Key Vault access
4. Check MySQL firewall rules allow Azure services

#### 3. Health Check Failing

**Error**: Health check returns 503

**Solution**:
1. Check application logs for errors
2. Verify MySQL connection is working
3. Check all required environment variables are set
4. Verify port 8005 is correct in health probe configuration

## Scale Configuration

### Auto-Scaling Rules

The service automatically scales based on HTTP traffic:

```yaml
# Development
min_replicas: 1
max_replicas: 5
scale_rule: 100 concurrent requests per replica

# Production
min_replicas: 1
max_replicas: 10
scale_rule: 100 concurrent requests per replica
```

### Manual Scaling

```bash
# Scale to specific replica count
az containerapp update \
  --name inventory-service \
  --resource-group rg-xshopai-dev \
  --min-replicas 2 \
  --max-replicas 5
```

## Security

### Managed Identity

The Container App uses Azure Managed Identity for:
- **Azure Container Registry**: Pull Docker images
- **Azure Key Vault**: Access secrets (MySQL credentials)
- **Azure Service Bus**: Dapr pub/sub
- **Azure Redis**: Dapr state store

### Network Security

- **Ingress**: External HTTPS (TLS 1.2+)
- **Transport**: HTTP to container (internal network)
- **Dapr**: HTTP communication between app and sidecar
- **Database**: Private connection via Azure backbone

### Secrets Management

All sensitive configuration is stored in Azure Key Vault:
- MySQL connection string
- MySQL username
- MySQL password
- Application Insights connection string

## Performance Tuning

### Resource Allocation

Current configuration:
```yaml
CPU: 0.5-1 cores
Memory: 1-2Gi
Workers: 2-4 (Gunicorn workers)
```

### Optimization Tips

1. **Workers**: Set to `(2 × CPU cores) + 1`
   - Dev (0.5 CPU): 2 workers
   - Prod (1 CPU): 4 workers

2. **Connection Pooling**: Configure in `config.py`
   ```python
   MYSQL_POOL_SIZE = 10
   MYSQL_MAX_OVERFLOW = 20
   ```

3. **Caching**: Implement Redis caching for frequent queries

4. **Monitoring**: Use Application Insights for performance metrics

## Related Documentation

- [Infrastructure README](../../../infrastructure/README.md)
- [Main Infrastructure Bicep](../../../infrastructure/azure/container-apps/bicep/main.bicep)
- [Layer 4 Container Apps](../../../infrastructure/azure/container-apps/bicep/layers/layer4-container-apps.bicep)
- [Reusable Workflow](../../../infrastructure/.github/workflows/reusable-deploy-container-app.yml)
- [Product Service Deployment](../../../product-service/.github/workflows/deploy.yml) (similar pattern)
- [User Service Deployment](../../../user-service/.github/workflows/deploy-container-app.yml) (similar pattern)

## Support

For deployment issues:
1. Check Azure Portal Container Apps logs
2. Review GitHub Actions workflow run logs
3. Verify infrastructure deployment completed successfully
4. Contact DevOps team for assistance
