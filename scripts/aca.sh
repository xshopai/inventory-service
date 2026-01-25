#!/bin/bash

# ============================================================================
# Azure Container Apps Deployment Script for Inventory Service
# ============================================================================
# This script automates the deployment of Inventory Service to Azure Container Apps
# with Dapr support, Azure Service Bus, and Azure MySQL Flexible Server.
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================================================
# Prerequisites Check
# ============================================================================
print_header "Checking Prerequisites"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    print_error "Azure CLI is not installed. Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi
print_success "Azure CLI is installed"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

# Check if logged into Azure
if ! az account show &> /dev/null; then
    print_warning "Not logged into Azure. Initiating login..."
    az login
fi
print_success "Logged into Azure"

# ============================================================================
# User Input Collection
# ============================================================================
print_header "Azure Configuration"

# Function to prompt with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local varname="$3"
    
    read -p "$prompt [$default]: " input
    eval "$varname=\"${input:-$default}\""
}

# Function to prompt for password (hidden input)
prompt_password() {
    local prompt="$1"
    local varname="$2"
    
    read -sp "$prompt: " input
    echo ""
    eval "$varname=\"$input\""
}

# List available subscriptions
echo -e "\n${BLUE}Available Azure Subscriptions:${NC}"
az account list --query "[].{Name:name, SubscriptionId:id, IsDefault:isDefault}" --output table

echo ""
prompt_with_default "Enter Azure Subscription ID (leave empty for default)" "" SUBSCRIPTION_ID

if [ -n "$SUBSCRIPTION_ID" ]; then
    az account set --subscription "$SUBSCRIPTION_ID"
    print_success "Subscription set to: $SUBSCRIPTION_ID"
else
    SUBSCRIPTION_ID=$(az account show --query id --output tsv)
    print_info "Using default subscription: $SUBSCRIPTION_ID"
fi

# Resource Group
echo ""
prompt_with_default "Enter Resource Group name" "rg-xshopai-aca" RESOURCE_GROUP

# Location
echo ""
echo -e "${BLUE}Common Azure Locations:${NC}"
echo "  - swedencentral (Sweden Central)"
echo "  - eastus (East US)"
echo "  - westus2 (West US 2)"
echo "  - westeurope (West Europe)"
echo "  - northeurope (North Europe)"
prompt_with_default "Enter Azure Location" "swedencentral" LOCATION

# Azure Container Registry
echo ""
prompt_with_default "Enter Azure Container Registry name (must be globally unique)" "acrxshopaiaca" ACR_NAME

# Container Apps Environment
echo ""
prompt_with_default "Enter Container Apps Environment name" "cae-xshopai-aca" ENVIRONMENT_NAME

# Application Insights
echo ""
prompt_with_default "Enter Application Insights name" "ai-xshopai-aca" AI_NAME

# Log Analytics Workspace
echo ""
prompt_with_default "Enter Log Analytics Workspace name" "law-xshopai-aca" LOG_ANALYTICS_WORKSPACE

# Service Bus
echo ""
prompt_with_default "Enter Service Bus namespace name (must be globally unique)" "sb-xshopai-aca" SB_NAMESPACE

# MySQL Configuration
echo ""
prompt_with_default "Enter MySQL Server name (must be globally unique)" "mysql-xshopai-aca" DB_SERVER
prompt_with_default "Enter MySQL Database name" "inventory_service_db" DB_NAME
prompt_with_default "Enter MySQL Admin Username" "xshopaiadmin" DB_USERNAME
echo ""
print_warning "Password must be at least 8 characters and include: uppercase, lowercase, number, and special character"
prompt_password "Enter MySQL Admin Password" DB_PASSWORD

# Service Tokens (optional)
echo ""
print_info "Service tokens are used for inter-service authentication (optional for initial deployment)"
prompt_with_default "Enter Product Service Token" "" PRODUCT_SERVICE_TOKEN
prompt_with_default "Enter Order Service Token" "" ORDER_SERVICE_TOKEN
prompt_with_default "Enter Cart Service Token" "" CART_SERVICE_TOKEN
prompt_with_default "Enter Web BFF Token" "" WEB_BFF_TOKEN

# App name
APP_NAME="inventory-service"

# ============================================================================
# Confirmation
# ============================================================================
print_header "Deployment Configuration Summary"

echo "Resource Group:           $RESOURCE_GROUP"
echo "Location:                 $LOCATION"
echo "Container Registry:       $ACR_NAME"
echo "Environment:              $ENVIRONMENT_NAME"
echo "Application Insights:     $AI_NAME"
echo "Log Analytics:            $LOG_ANALYTICS_WORKSPACE"
echo "Service Bus:              $SB_NAMESPACE"
echo "MySQL Server:             $DB_SERVER"
echo "MySQL Database:           $DB_NAME"
echo "MySQL Username:           $DB_USERNAME"
echo "App Name:                 $APP_NAME"
echo ""

read -p "Do you want to proceed with deployment? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled by user"
    exit 0
fi

# ============================================================================
# Step 1: Create Resource Group
# ============================================================================
print_header "Step 1: Creating Resource Group"

az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

print_success "Resource group '$RESOURCE_GROUP' created/verified"

# ============================================================================
# Step 2: Create Azure Container Registry
# ============================================================================
print_header "Step 2: Creating Azure Container Registry"

if az acr show --name "$ACR_NAME" &> /dev/null; then
    print_info "ACR '$ACR_NAME' already exists, skipping creation"
else
    az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --admin-enabled true \
        --output none
    print_success "ACR '$ACR_NAME' created"
fi

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)
print_info "ACR Login Server: $ACR_LOGIN_SERVER"

# ============================================================================
# Step 3: Build and Push Container Image
# ============================================================================
print_header "Step 3: Building and Pushing Container Image"

# Login to ACR
az acr login --name "$ACR_NAME"
print_success "Logged into ACR"

# Navigate to service directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SERVICE_DIR"

# Build Docker image
print_info "Building Docker image..."
docker build -t inventory-service:latest .
print_success "Docker image built"

# Tag and push
docker tag inventory-service:latest "$ACR_LOGIN_SERVER/inventory-service:latest"
docker push "$ACR_LOGIN_SERVER/inventory-service:latest"
print_success "Image pushed to ACR"

# ============================================================================
# Step 4: Register Resource Providers
# ============================================================================
print_header "Step 4: Registering Resource Providers"

print_info "Registering microsoft.operationalinsights..."
az provider register --namespace microsoft.operationalinsights --wait

print_info "Registering microsoft.insights..."
az provider register --namespace microsoft.insights --wait

print_info "Registering Microsoft.App..."
az provider register --namespace Microsoft.App --wait

print_info "Registering Microsoft.ServiceBus..."
az provider register --namespace Microsoft.ServiceBus --wait

print_success "All resource providers registered"

# ============================================================================
# Step 5: Create Application Insights
# ============================================================================
print_header "Step 5: Creating Application Insights"

if az monitor app-insights component show --app "$AI_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "Application Insights '$AI_NAME' already exists"
else
    az monitor app-insights component create \
        --app "$AI_NAME" \
        --location "$LOCATION" \
        --resource-group "$RESOURCE_GROUP" \
        --output none
    print_success "Application Insights '$AI_NAME' created"
fi

AI_KEY=$(az monitor app-insights component show \
    --app "$AI_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query instrumentationKey \
    --output tsv)
print_info "App Insights Key: $AI_KEY"

# ============================================================================
# Step 6: Create Log Analytics Workspace
# ============================================================================
print_header "Step 6: Creating Log Analytics Workspace"

if az monitor log-analytics workspace show --resource-group "$RESOURCE_GROUP" --workspace-name "$LOG_ANALYTICS_WORKSPACE" &> /dev/null; then
    print_info "Log Analytics Workspace '$LOG_ANALYTICS_WORKSPACE' already exists"
else
    az monitor log-analytics workspace create \
        --resource-group "$RESOURCE_GROUP" \
        --workspace-name "$LOG_ANALYTICS_WORKSPACE" \
        --location "$LOCATION" \
        --output none
    print_success "Log Analytics Workspace '$LOG_ANALYTICS_WORKSPACE' created"
fi

LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_WORKSPACE" \
    --query customerId \
    --output tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group "$RESOURCE_GROUP" \
    --workspace-name "$LOG_ANALYTICS_WORKSPACE" \
    --query primarySharedKey \
    --output tsv)

print_info "Log Analytics Workspace ID: $LOG_ANALYTICS_WORKSPACE_ID"

# ============================================================================
# Step 7: Create Container Apps Environment
# ============================================================================
print_header "Step 7: Creating Container Apps Environment"

if az containerapp env show --name "$ENVIRONMENT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "Container Apps Environment '$ENVIRONMENT_NAME' already exists"
else
    az containerapp env create \
        --name "$ENVIRONMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --dapr-instrumentation-key "$AI_KEY" \
        --logs-workspace-id "$LOG_ANALYTICS_WORKSPACE_ID" \
        --logs-workspace-key "$LOG_ANALYTICS_KEY" \
        --enable-workload-profiles false \
        --output none
    print_success "Container Apps Environment '$ENVIRONMENT_NAME' created"
fi

# ============================================================================
# Step 8: Create Azure Service Bus
# ============================================================================
print_header "Step 8: Creating Azure Service Bus"

if az servicebus namespace show --name "$SB_NAMESPACE" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "Service Bus namespace '$SB_NAMESPACE' already exists"
else
    az servicebus namespace create \
        --name "$SB_NAMESPACE" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard \
        --output none
    print_success "Service Bus namespace '$SB_NAMESPACE' created"
fi

# Create topic
if az servicebus topic show --name inventory-events --namespace-name "$SB_NAMESPACE" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "Service Bus topic 'inventory-events' already exists"
else
    az servicebus topic create \
        --name inventory-events \
        --namespace-name "$SB_NAMESPACE" \
        --resource-group "$RESOURCE_GROUP" \
        --output none
    print_success "Service Bus topic 'inventory-events' created"
fi

SB_CONNECTION=$(az servicebus namespace authorization-rule keys list \
    --namespace-name "$SB_NAMESPACE" \
    --resource-group "$RESOURCE_GROUP" \
    --name RootManageSharedAccessKey \
    --query primaryConnectionString \
    --output tsv)

print_info "Service Bus connection string retrieved"

# ============================================================================
# Step 9: Create Azure MySQL Flexible Server
# ============================================================================
print_header "Step 9: Creating Azure MySQL Flexible Server"

if az mysql flexible-server show --name "$DB_SERVER" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "MySQL server '$DB_SERVER' already exists"
else
    az mysql flexible-server create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DB_SERVER" \
        --location "$LOCATION" \
        --admin-user "$DB_USERNAME" \
        --admin-password "$DB_PASSWORD" \
        --sku-name Standard_B1ms \
        --tier Burstable \
        --version 8.0.21 \
        --storage-size 32 \
        --public-access 0.0.0.0 \
        --output none
    print_success "MySQL server '$DB_SERVER' created"
fi

# Configure firewall
print_info "Configuring firewall rules..."

MY_IP=$(curl -s ifconfig.me)
print_info "Your public IP: $MY_IP"

az mysql flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DB_SERVER" \
    --rule-name AllowMyIP \
    --start-ip-address "$MY_IP" \
    --end-ip-address "$MY_IP" \
    --output none 2>/dev/null || true

az mysql flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DB_SERVER" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    --output none 2>/dev/null || true

print_success "Firewall rules configured"

# Create database
if az mysql flexible-server db show --resource-group "$RESOURCE_GROUP" --server-name "$DB_SERVER" --database-name "$DB_NAME" &> /dev/null; then
    print_info "Database '$DB_NAME' already exists"
else
    az mysql flexible-server db create \
        --resource-group "$RESOURCE_GROUP" \
        --server-name "$DB_SERVER" \
        --database-name "$DB_NAME" \
        --output none
    print_success "Database '$DB_NAME' created"
fi

# URL-encode the password
DB_PASSWORD_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$DB_PASSWORD', safe=''))")
DB_CONNECTION="mysql+pymysql://$DB_USERNAME:$DB_PASSWORD_ENCODED@$DB_SERVER.mysql.database.azure.com:3306/$DB_NAME?ssl_ca=/etc/ssl/certs/DigiCertGlobalRootG2.crt.pem"

print_info "Database connection string prepared"

# ============================================================================
# Step 10: Create Dapr Component File
# ============================================================================
print_header "Step 10: Creating Dapr Component File"

mkdir -p "$SERVICE_DIR/.dapr/components"

cat > "$SERVICE_DIR/.dapr/components/dapr-servicebus-component.yaml" << EOF
componentType: pubsub.azure.servicebus.topics
version: v1
metadata:
  - name: connectionString
    value: '$SB_CONNECTION'
  - name: consumerID
    value: inventory-service
scopes:
  - inventory-service
EOF

print_success "Dapr Service Bus component file created"

# ============================================================================
# Step 11: Deploy Container App
# ============================================================================
print_header "Step 11: Deploying Container App"

ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" --output tsv)

# Build env-vars string
ENV_VARS="FLASK_ENV=production DATABASE_URL=$DB_CONNECTION MESSAGING_PROVIDER=dapr DAPR_PUBSUB_NAME=inventory-pubsub"

if [ -n "$PRODUCT_SERVICE_TOKEN" ]; then
    ENV_VARS="$ENV_VARS PRODUCT_SERVICE_TOKEN=$PRODUCT_SERVICE_TOKEN"
fi
if [ -n "$ORDER_SERVICE_TOKEN" ]; then
    ENV_VARS="$ENV_VARS ORDER_SERVICE_TOKEN=$ORDER_SERVICE_TOKEN"
fi
if [ -n "$CART_SERVICE_TOKEN" ]; then
    ENV_VARS="$ENV_VARS CART_SERVICE_TOKEN=$CART_SERVICE_TOKEN"
fi
if [ -n "$WEB_BFF_TOKEN" ]; then
    ENV_VARS="$ENV_VARS WEB_BFF_TOKEN=$WEB_BFF_TOKEN"
fi

if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    print_info "Container app '$APP_NAME' already exists, updating..."
    az containerapp update \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_LOGIN_SERVER/inventory-service:latest" \
        --set-env-vars $ENV_VARS \
        --output none
else
    az containerapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$ENVIRONMENT_NAME" \
        --image "$ACR_LOGIN_SERVER/inventory-service:latest" \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-username "$ACR_NAME" \
        --registry-password "$ACR_PASSWORD" \
        --target-port 8004 \
        --ingress external \
        --min-replicas 1 \
        --max-replicas 5 \
        --cpu 0.5 \
        --memory 1.0Gi \
        --enable-dapr \
        --dapr-app-id inventory-service \
        --dapr-app-port 8004 \
        --env-vars $ENV_VARS \
        --output none
fi

print_success "Container app '$APP_NAME' deployed"

# ============================================================================
# Step 12: Configure Dapr Component
# ============================================================================
print_header "Step 12: Configuring Dapr Component"

az containerapp env dapr-component set \
    --name "$ENVIRONMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --dapr-component-name inventory-pubsub \
    --yaml "$SERVICE_DIR/.dapr/components/dapr-servicebus-component.yaml" \
    --output none

print_success "Dapr component configured"

# ============================================================================
# Step 13: Verify Deployment
# ============================================================================
print_header "Step 13: Verifying Deployment"

APP_URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv)

print_success "Deployment completed successfully!"
echo ""
print_info "Application URL: https://$APP_URL"
print_info "Health Check: https://$APP_URL/health"
echo ""

# Test health endpoint
print_info "Testing health endpoint..."
sleep 10  # Wait for app to start

if curl -s --max-time 30 "https://$APP_URL/health" > /dev/null; then
    print_success "Health check passed!"
else
    print_warning "Health check failed or timed out. The app may still be starting."
fi

# ============================================================================
# Summary
# ============================================================================
print_header "Deployment Summary"

echo "Resource Group:       $RESOURCE_GROUP"
echo "Location:             $LOCATION"
echo "Container Registry:   $ACR_LOGIN_SERVER"
echo "Environment:          $ENVIRONMENT_NAME"
echo "Application URL:      https://$APP_URL"
echo ""
echo "MySQL Server:         $DB_SERVER.mysql.database.azure.com"
echo "MySQL Database:       $DB_NAME"
echo "MySQL Username:       $DB_USERNAME"
echo ""
echo "Service Bus:          $SB_NAMESPACE.servicebus.windows.net"
echo ""
print_info "To view logs: az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
print_info "To delete: az containerapp delete --name $APP_NAME --resource-group $RESOURCE_GROUP --yes"
