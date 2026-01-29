# Azure Container Apps Deployment Guide

This guide provides step-by-step instructions for deploying the **Inventory Service** to **Azure Container Apps** with built-in Dapr support.

---

## Prerequisites

### 1. Infrastructure Deployment (Required First)

Before deploying any service, you must deploy the shared infrastructure using the centralized deployment script:

```bash
cd infrastructure/azure/aca/scripts
./deploy-infra.sh
```

This script creates all shared resources:

- **Resource Group** - Container for all resources
- **Azure Container Registry (ACR)** - Docker image storage
- **Container Apps Environment** - Serverless container runtime with Dapr
- **Azure Service Bus** - Event messaging (Dapr pub/sub)
- **Azure Cache for Redis** - Caching and state store
- **Azure Cosmos DB** - Document database
- **Azure MySQL Flexible Server** - Relational database
- **Azure Key Vault** - Secrets management
- **Azure Storage Account** - Blob storage
- **Managed Identity** - Secure access to Azure resources
- **Dapr Components** - Pre-configured pubsub, statestore, secretstore

**Important**: Note the **suffix** used during infrastructure deployment. You'll need it for service deployments.

### 2. Local Tools

- **Azure CLI** - [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Docker** - For building container images
- **Python 3** - For URL encoding (used in connection strings)

---

## Quick Start (Automated)

The fastest way to deploy is using the automated script:

```bash
cd inventory-service/scripts
./aca.sh
```

The script will:

1. Prompt for environment (dev/prod) and infrastructure suffix
2. Verify infrastructure exists
3. Build and push the Docker image
4. Create/update the Container App
5. Configure environment variables and Dapr integration

---

## Manual Deployment Steps

### Step 1: Login to Azure

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "<subscription-id>"

# Verify current subscription
az account show
```

### Step 2: Set Variables

```bash
# Environment and suffix (must match infrastructure deployment)
ENVIRONMENT="dev"
SUFFIX="abc1"  # Your infrastructure suffix
PROJECT_NAME="xshopai"

# Derived resource names
RESOURCE_GROUP="rg-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
ACR_NAME="${PROJECT_NAME}${ENVIRONMENT}${SUFFIX}"
CONTAINER_ENV="cae-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
MYSQL_SERVER="mysql-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
KEY_VAULT="kv-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"

# Service-specific
SERVICE_NAME="inventory-service"
APP_PORT=8005
DB_NAME="inventory_db"
```

### Step 3: Verify Infrastructure Exists

```bash
# Check resource group
az group show --name $RESOURCE_GROUP

# Check ACR
az acr show --name $ACR_NAME
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Check Container Apps Environment
az containerapp env show --name $CONTAINER_ENV --resource-group $RESOURCE_GROUP

# Check MySQL Server
az mysql flexible-server show --name $MYSQL_SERVER --resource-group $RESOURCE_GROUP
MYSQL_HOST=$(az mysql flexible-server show --name $MYSQL_SERVER --resource-group $RESOURCE_GROUP --query fullyQualifiedDomainName -o tsv)
```

### Step 4: Create Service Database

```bash
# Create inventory database (if not exists)
az mysql flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $MYSQL_SERVER \
  --database-name $DB_NAME
```

### Step 5: Build and Push Container Image

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build Docker image (from inventory-service directory)
docker build -t $SERVICE_NAME:latest .

# Tag and push
docker tag $SERVICE_NAME:latest $ACR_LOGIN_SERVER/$SERVICE_NAME:latest
docker push $ACR_LOGIN_SERVER/$SERVICE_NAME:latest

# Verify
az acr repository list --name $ACR_NAME --output table
```

### Step 6: Configure Database Connection

```bash
# Get MySQL password from Key Vault
MYSQL_PASSWORD=$(az keyvault secret show --vault-name $KEY_VAULT --name "mysql-password" --query value -o tsv)
MYSQL_USERNAME="xshopaiadmin"

# URL-encode password (handles special characters)
DB_PASSWORD_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$MYSQL_PASSWORD', safe=''))")

# Build connection string with SSL (Azure MySQL requires secure transport)
DB_CONNECTION="mysql+pymysql://$MYSQL_USERNAME:$DB_PASSWORD_ENCODED@$MYSQL_HOST:3306/$DB_NAME?ssl_ca=/etc/ssl/certs/ca-certificates.crt"
```

### Step 7: Deploy Container App

```bash
# Get ACR credentials
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Deploy container app
az containerapp create \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_LOGIN_SERVER/$SERVICE_NAME:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port $APP_PORT \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --enable-dapr \
  --dapr-app-id $SERVICE_NAME \
  --dapr-app-port $APP_PORT \
  --env-vars \
    "FLASK_ENV=production" \
    "DATABASE_URL=$DB_CONNECTION" \
    "MESSAGING_PROVIDER=dapr"
```

> **Note:** The pubsub component name (`pubsub`) is hardcoded in the application code, not passed as an environment variable.

### Step 8: Verify Deployment

```bash
# Get application URL
APP_URL=$(az containerapp show \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

echo "Application URL: https://$APP_URL"

# Test health endpoint
curl https://$APP_URL/health
```

---

## Dapr Integration

The infrastructure deployment pre-configures Dapr components that are available to all services:

### Available Dapr Components

| Component    | Name          | Type                           | Backend               |
| ------------ | ------------- | ------------------------------ | --------------------- |
| Pub/Sub      | `pubsub`      | pubsub.azure.servicebus.queues | Azure Service Bus     |
| State Store  | `statestore`  | state.redis                    | Azure Cache for Redis |
| Secret Store | `secretstore` | secretstores.azure.keyvault    | Azure Key Vault       |

### Using Dapr in Inventory Service

The service is pre-configured to use Dapr for messaging:

```python
# The pubsub name 'pubsub' is hardcoded in the application code
# No environment variable needed

# Publishing events
dapr_client.publish_event(
    pubsub_name="pubsub",  # Hardcoded in src/messaging/factory.py
    topic_name="inventory.updated",
    data={"sku": "ABC123", "quantity": 50}
)

# Subscribing to events (via HTTP endpoint)
@app.route('/dapr/subscribe', methods=['GET'])
def subscribe():
    return jsonify([
        {"pubsubname": "pubsub", "topic": "order.created", "route": "/events/order-created"}
    ])
```

---

## Environment Variables

| Variable             | Description             | Example               |
| -------------------- | ----------------------- | --------------------- |
| `FLASK_ENV`          | Flask environment       | `production`          |
| `DATABASE_URL`       | MySQL connection string | `mysql+pymysql://...` |
| `MESSAGING_PROVIDER` | Messaging backend       | `dapr`                |

> **Note:** The pubsub component name (`pubsub`) is hardcoded in the application code. Secrets like `JWT_SECRET`, `FLASK_SECRET_KEY`, and service tokens should be stored in Azure Key Vault and accessed via Dapr Secret Store in production.

---

## Updating the Service

To deploy a new version:

```bash
# Build and push new image
docker build -t $SERVICE_NAME:latest .
docker tag $SERVICE_NAME:latest $ACR_LOGIN_SERVER/$SERVICE_NAME:latest
docker push $ACR_LOGIN_SERVER/$SERVICE_NAME:latest

# Update container app (pulls latest image)
az containerapp update \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/$SERVICE_NAME:latest
```

---

## Monitoring

### View Logs

```bash
# Application logs
az containerapp logs show \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Dapr sidecar logs
az containerapp logs show \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --container daprd \
  --follow
```

### Application Insights

Application Insights is configured at the Container Apps Environment level. Traces, metrics, and logs are automatically collected.

View in Azure Portal:

1. Navigate to the Resource Group
2. Open the Log Analytics Workspace (`law-xshopai-{env}-{suffix}`)
3. Query container app logs using KQL

---

## Scaling

### Manual Scaling

```bash
# Scale to specific replica count
az containerapp update \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 10
```

### Auto-scaling Rules

The default configuration scales based on HTTP traffic (1-5 replicas). Custom rules can be added:

```bash
az containerapp update \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100
```

---

## Cleanup

### Delete Service Only

```bash
# Remove inventory-service (keeps infrastructure)
az containerapp delete \
  --name $SERVICE_NAME \
  --resource-group $RESOURCE_GROUP \
  --yes
```

### Delete All Infrastructure

```bash
# WARNING: Deletes ALL xshopai resources in this environment
az group delete --name $RESOURCE_GROUP --yes
```

---

## Troubleshooting

### Container Won't Start

1. Check container logs:

   ```bash
   az containerapp logs show --name $SERVICE_NAME --resource-group $RESOURCE_GROUP
   ```

2. Verify image exists in ACR:

   ```bash
   az acr repository show-tags --name $ACR_NAME --repository $SERVICE_NAME
   ```

3. Check environment variables are set correctly

### Database Connection Fails

1. Verify MySQL firewall allows Azure services:

   ```bash
   az mysql flexible-server firewall-rule list --name $MYSQL_SERVER --resource-group $RESOURCE_GROUP -o table
   ```

2. Check connection string format (special characters must be URL-encoded)

3. Verify SSL settings match Azure MySQL requirements

### Dapr Component Not Found

1. Verify component exists:

   ```bash
   az containerapp env dapr-component list --name $CONTAINER_ENV --resource-group $RESOURCE_GROUP -o table
   ```

2. Check component scopes include the service

---

## Related Documentation

- [Infrastructure Deployment](../../../../infrastructure/azure/aca/docs/README.md)
- [Local Development](./LOCAL_DEVELOPMENT.md)
- [Local Development with Dapr](./LOCAL_DEVELOPMENT_DAPR.md)
- [Architecture](./ARCHITECTURE.md)
