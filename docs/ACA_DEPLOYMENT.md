# Azure Container Apps Deployment Guide

This guide provides step-by-step instructions for deploying the Inventory Service to **Azure Container Apps** with built-in Dapr support.

---

## Prerequisites

- **Azure CLI** installed - [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Azure Subscription** with appropriate permissions
- **Docker** installed for building container images
- **Azure Container Registry** (or Docker Hub account)

---

## Step-by-Step Deployment

### Step 1: Login to Azure

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "<subscription-id>"

# Verify current subscription
az account show
```

### Step 2: Create Resource Group

```bash
# Set variables
RESOURCE_GROUP="rg-inventory-service"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 3: Create Azure Container Registry

```bash
# Set ACR name (must be globally unique)
ACR_NAME="acrinventoryservice"

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"
```

### Step 4: Build and Push Container Image

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build Docker image
docker build -t inventory-service:latest .

# Tag image for ACR
docker tag inventory-service:latest $ACR_LOGIN_SERVER/inventory-service:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/inventory-service:latest

# Verify image was pushed
az acr repository list --name $ACR_NAME --output table
```

### Step 5: Create Container Apps Environment

```bash
# Set environment name
ENVIRONMENT_NAME="env-inventory-service"

# Create Container Apps environment with Dapr enabled
az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --dapr-instrumentation-key "<app-insights-key>" \
  --enable-workload-profiles false
```

### Step 6: Create Azure Service Bus (for messaging)

```bash
# Set Service Bus namespace
SB_NAMESPACE="sb-inventory-service"

# Create Service Bus namespace
az servicebus namespace create \
  --name $SB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard

# Create topic for inventory events
az servicebus topic create \
  --name inventory-events \
  --namespace-name $SB_NAMESPACE \
  --resource-group $RESOURCE_GROUP

# Get connection string
SB_CONNECTION=$(az servicebus namespace authorization-rule keys list \
  --namespace-name $SB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv)
```

### Step 7: Create Azure Database for MySQL

```bash
# Set database server name
DB_SERVER="mysql-inventory-service"
DB_NAME="inventory_service_db"
DB_USERNAME="admin"
DB_PASSWORD="<secure-password>"

# Create MySQL server
az mysql flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --location $LOCATION \
  --admin-user $DB_USERNAME \
  --admin-password $DB_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 8.0 \
  --storage-size 32 \
  --public-access 0.0.0.0

# Create database
az mysql flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --database-name $DB_NAME

# Get connection string
DB_CONNECTION="mysql+pymysql://$DB_USERNAME:$DB_PASSWORD@$DB_SERVER.mysql.database.azure.com:3306/$DB_NAME"
```

### Step 8: Create Dapr Component for Service Bus

Create file `dapr-servicebus-component.yaml`:

```yaml
componentType: pubsub.azure.servicebus.topics
version: v1
metadata:
  - name: connectionString
    value: "<service-bus-connection-string>"
  - name: consumerID
    value: inventory-service
secrets: []
scopes:
  - inventory-service
```

### Step 9: Deploy Container App

```bash
# Set app name
APP_NAME="inventory-service"

# Get ACR credentials
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Create container app
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $ACR_LOGIN_SERVER/inventory-service:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8004 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --enable-dapr \
  --dapr-app-id inventory-service \
  --dapr-app-port 8004 \
  --env-vars \
    "FLASK_ENV=production" \
    "DATABASE_URL=$DB_CONNECTION" \
    "MESSAGING_PROVIDER=dapr" \
    "DAPR_PUBSUB_NAME=inventory-pubsub" \
    "PRODUCT_SERVICE_TOKEN=<token>" \
    "ORDER_SERVICE_TOKEN=<token>" \
    "CART_SERVICE_TOKEN=<token>" \
    "WEB_BFF_TOKEN=<token>"
```

### Step 10: Configure Dapr Component in Container Apps

```bash
# Create Dapr pub/sub component
az containerapp env dapr-component set \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --dapr-component-name inventory-pubsub \
  --yaml dapr-servicebus-component.yaml
```

### Step 11: Run Database Migrations

```bash
# Get container app URL
APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# SSH into container (if needed)
az containerapp exec \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --command "/bin/bash"

# Inside container, run migrations
flask db upgrade
```

**Alternative:** Run migrations as a Job before deploying the app.

### Step 12: Verify Deployment

```bash
# Check app status
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.runningStatus

# Get application URL
echo "Application URL: https://$APP_URL"

# Test health endpoint
curl https://$APP_URL/health
```

---

## Configure Secrets (Production)

### Using Azure Key Vault

```bash
# Create Key Vault
KV_NAME="kv-inventory-service"

az keyvault create \
  --name $KV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Store secrets
az keyvault secret set --vault-name $KV_NAME --name "database-url" --value "$DB_CONNECTION"
az keyvault secret set --vault-name $KV_NAME --name "jwt-secret" --value "<jwt-secret>"
az keyvault secret set --vault-name $KV_NAME --name "product-service-token" --value "<token>"

# Grant Container App access to Key Vault
# Enable managed identity first
az containerapp identity assign \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --system-assigned

# Get principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query principalId \
  --output tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name $KV_NAME \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

---

## Monitoring and Observability

### View Application Logs

```bash
# Stream logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# View Dapr sidecar logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --container daprd \
  --follow
```

### Application Insights Integration

```bash
# Create Application Insights
AI_NAME="ai-inventory-service"

az monitor app-insights component create \
  --app $AI_NAME \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
AI_KEY=$(az monitor app-insights component show \
  --app $AI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Update container app with App Insights
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=$AI_KEY"
```

---

## Scaling Configuration

### Manual Scaling

```bash
# Scale to specific replica count
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 10
```

### Auto-Scaling Rules

```bash
# Scale based on HTTP requests
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100

# Scale based on CPU
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --scale-rule-name cpu-scaling \
  --scale-rule-type cpu \
  --scale-rule-metadata "type=Utilization" "value=70"
```

---

## Update Deployment

### Deploy New Version

```bash
# Build new image with version tag
VERSION="1.1.0"
docker build -t inventory-service:$VERSION .
docker tag inventory-service:$VERSION $ACR_LOGIN_SERVER/inventory-service:$VERSION
docker push $ACR_LOGIN_SERVER/inventory-service:$VERSION

# Update container app
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/inventory-service:$VERSION

# Verify deployment
az containerapp revision list \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

### Blue-Green Deployment

```bash
# Create new revision without traffic
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/inventory-service:$VERSION \
  --revision-suffix v2

# Split traffic (90% old, 10% new)
az containerapp ingress traffic set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --revision-weight latest=10 previous=90

# After validation, shift all traffic to new version
az containerapp ingress traffic set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --revision-weight latest=100
```

---

## Cleanup Resources

```bash
# Delete container app
az containerapp delete \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --yes

# Delete entire resource group (WARNING: deletes everything)
az group delete \
  --name $RESOURCE_GROUP \
  --yes
```

---

## Quick Reference

```bash
# Check app status
az containerapp show --name inventory-service --resource-group rg-inventory-service

# View logs
az containerapp logs show --name inventory-service --resource-group rg-inventory-service --follow

# Update environment variable
az containerapp update --name inventory-service --resource-group rg-inventory-service \
  --set-env-vars "LOG_LEVEL=INFO"

# Scale replicas
az containerapp update --name inventory-service --resource-group rg-inventory-service \
  --min-replicas 2 --max-replicas 10

# Get app URL
az containerapp show --name inventory-service --resource-group rg-inventory-service \
  --query properties.configuration.ingress.fqdn --output tsv
```

---

## Best Practices

✅ **Use Azure Key Vault** for secrets (database passwords, JWT secrets, service tokens)  
✅ **Enable Application Insights** for monitoring and diagnostics  
✅ **Configure health probes** for automatic restart of unhealthy containers  
✅ **Use managed identity** instead of connection strings where possible  
✅ **Enable auto-scaling** based on HTTP traffic and CPU metrics  
✅ **Use revision labels** for blue-green deployments  
✅ **Configure dead letter queues** in Dapr components  
✅ **Set up alerts** for errors and performance issues  

---

## Next Steps

- **Kubernetes Deployment**: See [AKS_DEPLOYMENT.md](AKS_DEPLOYMENT.md)
- **Local Development**: See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
