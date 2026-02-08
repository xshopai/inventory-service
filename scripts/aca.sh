#!/bin/bash
# ============================================================================
# Azure Container Apps Deployment Script for Inventory Service
# ============================================================================
# PREREQUISITE: Run infrastructure deployment first:
#   cd infrastructure/azure/aca/scripts && ./deploy.sh
# ============================================================================

set -e

# ============================================================================
# CONFIGURATION - Edit these variables as needed
# ============================================================================

# Service Configuration
SERVICE_NAME="inventory-service"
APP_PORT=8005
PROJECT_NAME="xshopai"

# Database Configuration
DB_NAME="inventory_service_db"
MYSQL_USERNAME="xshopaiadmin"

# Container Resources (Production-level)
CPU="1.0"
MEMORY="2.0Gi"
MIN_REPLICAS=2
MAX_REPLICAS=10

# Dapr Configuration (fixed for Azure Container Apps)
DAPR_HTTP_PORT=3500
DAPR_GRPC_PORT=50001

# ============================================================================
# COLORS & HELPER FUNCTIONS
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ $1${NC}"; }

# ============================================================================
# PREREQUISITES CHECK
# ============================================================================
print_header "Checking Prerequisites"

command -v az &>/dev/null || { print_error "Azure CLI not installed"; exit 1; }
print_success "Azure CLI installed"

command -v docker &>/dev/null || { print_error "Docker not installed"; exit 1; }
print_success "Docker installed"

az account show &>/dev/null || az login
print_success "Logged into Azure"

# Get script and service directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# USER INPUT - Environment & Suffix
# ============================================================================
print_header "Environment Selection"

echo "Available environments: dev, prod"
read -p "Enter environment [dev]: " ENVIRONMENT
ENVIRONMENT="${ENVIRONMENT:-dev}"

[[ "$ENVIRONMENT" =~ ^(dev|prod)$ ]] || { print_error "Invalid environment (dev/prod only)"; exit 1; }
print_success "Environment: $ENVIRONMENT"

echo ""
echo "Find your suffix by running:"
echo -e "  ${BLUE}az group list --query \"[?starts_with(name, 'rg-xshopai-$ENVIRONMENT')].name\" -o tsv${NC}"
echo ""
read -p "Enter infrastructure suffix: " SUFFIX

[[ "$SUFFIX" =~ ^[a-z0-9]{3,6}$ ]] || { print_error "Invalid suffix (3-6 lowercase alphanumeric)"; exit 1; }
print_success "Suffix: $SUFFIX"

# ============================================================================
# DERIVED RESOURCE NAMES (must match infrastructure deployment)
# ============================================================================
RESOURCE_GROUP="rg-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
ACR_NAME="${PROJECT_NAME}${ENVIRONMENT}${SUFFIX}"
CONTAINER_ENV="cae-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
CONTAINER_APP_NAME="ca-${SERVICE_NAME}-${ENVIRONMENT}-${SUFFIX}"
MYSQL_SERVER="mysql-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
KEY_VAULT="kv-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"
MANAGED_IDENTITY="id-${PROJECT_NAME}-${ENVIRONMENT}-${SUFFIX}"

# ============================================================================
# VERIFY INFRASTRUCTURE EXISTS
# ============================================================================
print_header "Verifying Infrastructure"

az group show --name "$RESOURCE_GROUP" &>/dev/null || { print_error "Resource group not found: $RESOURCE_GROUP"; exit 1; }
print_success "Resource Group: $RESOURCE_GROUP"

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv 2>/dev/null) || { print_error "ACR not found: $ACR_NAME"; exit 1; }
print_success "Container Registry: $ACR_LOGIN_SERVER"

az containerapp env show --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" &>/dev/null || { print_error "Container Env not found: $CONTAINER_ENV"; exit 1; }
print_success "Container Environment: $CONTAINER_ENV"

MYSQL_HOST=$(az mysql flexible-server show --name "$MYSQL_SERVER" --resource-group "$RESOURCE_GROUP" --query fullyQualifiedDomainName -o tsv 2>/dev/null) || { print_error "MySQL not found: $MYSQL_SERVER"; exit 1; }
print_success "MySQL Server: $MYSQL_HOST"

# Get Managed Identity (optional)
IDENTITY_ID=$(MSYS_NO_PATHCONV=1 az identity show --name "$MANAGED_IDENTITY" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
[ -n "$IDENTITY_ID" ] && print_success "Managed Identity: $MANAGED_IDENTITY" || print_warning "Managed Identity not found (optional)"

# ============================================================================
# DATABASE SETUP
# ============================================================================
print_header "Database Configuration"

# Create database if not exists
if az mysql flexible-server db show --resource-group "$RESOURCE_GROUP" --server-name "$MYSQL_SERVER" --database-name "$DB_NAME" &>/dev/null; then
    print_success "Database exists: $DB_NAME"
else
    print_info "Creating database: $DB_NAME"
    az mysql flexible-server db create --resource-group "$RESOURCE_GROUP" --server-name "$MYSQL_SERVER" --database-name "$DB_NAME" --output none
    print_success "Database created: $DB_NAME"
fi

print_success "Database configured"

# ============================================================================
# NETWORK CONFIGURATION - Add Container Apps IP to MySQL Firewall
# ============================================================================
print_header "Network Configuration"

CAE_STATIC_IP=$(az containerapp env show --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" --query "properties.staticIp" -o tsv 2>/dev/null)
if [ -n "$CAE_STATIC_IP" ]; then
    print_info "Container Apps Environment IP: $CAE_STATIC_IP"
    
    # Check if firewall rule exists
    if az mysql flexible-server firewall-rule show --resource-group "$RESOURCE_GROUP" --name "$MYSQL_SERVER" --rule-name AllowContainerApps &>/dev/null; then
        print_success "Firewall rule 'AllowContainerApps' already exists"
    else
        print_info "Adding Container Apps IP to MySQL firewall..."
        az mysql flexible-server firewall-rule create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$MYSQL_SERVER" \
            --rule-name AllowContainerApps \
            --start-ip-address "$CAE_STATIC_IP" \
            --end-ip-address "$CAE_STATIC_IP" \
            --output none
        print_success "Firewall rule 'AllowContainerApps' created"
    fi
else
    print_warning "Could not get Container Apps Environment IP - MySQL firewall may need manual configuration"
fi

# ============================================================================
# CONFIRMATION
# ============================================================================
print_header "Deployment Summary"

echo "Environment:        $ENVIRONMENT"
echo "Resource Group:     $RESOURCE_GROUP"
echo "Container App:      $CONTAINER_APP_NAME"
echo "Container Name:     $SERVICE_NAME"
echo "Image:              $ACR_LOGIN_SERVER/$SERVICE_NAME:latest"
echo "MySQL Server:       $MYSQL_HOST"
echo "Database:           $DB_NAME"
echo "CPU/Memory:         $CPU / $MEMORY"
echo "Replicas:           $MIN_REPLICAS - $MAX_REPLICAS"
echo ""

# ============================================================================
# BUILD & PUSH IMAGE
# ============================================================================
print_header "Building and Pushing Image"

az acr login --name "$ACR_NAME"
cd "$SERVICE_DIR"

IMAGE_TAG="$ACR_LOGIN_SERVER/$SERVICE_NAME:latest"
docker build -t "$SERVICE_NAME:latest" .
docker tag "$SERVICE_NAME:latest" "$IMAGE_TAG"
docker push "$IMAGE_TAG"
print_success "Image pushed: $IMAGE_TAG"

# ============================================================================
# DEPLOY CONTAINER APP
# ============================================================================
print_header "Deploying Container App"

ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Map environment to app config (dev->development, prod->production)
APP_CONFIG="development"
[ "$ENVIRONMENT" = "prod" ] && APP_CONFIG="production"

# Retrieve secrets from Key Vault
# All secrets are fetched at deployment time and set as env vars
# This avoids race conditions with Dapr sidecar startup
print_info "Retrieving secrets from Key Vault..."

# Per-service Application Insights (each service has its own App Insights resource)
APP_INSIGHTS_CONN=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "appinsights-inventory-service" --query "value" -o tsv 2>/dev/null || echo "")
[ -n "$APP_INSIGHTS_CONN" ] && print_success "  appinsights-inventory-service: retrieved" || print_warning "  appinsights-inventory-service: not configured (telemetry disabled)"

# JWT secret
JWT_SECRET=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "jwt-secret" --query "value" -o tsv 2>/dev/null || echo "")
[ -n "$JWT_SECRET" ] && print_success "  jwt-secret: retrieved" || print_error "  jwt-secret: NOT FOUND"

# MySQL connection
MYSQL_SERVER_CONNECTION=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "mysql-server-connection" --query "value" -o tsv 2>/dev/null || echo "")
[ -n "$MYSQL_SERVER_CONNECTION" ] && print_success "  mysql-server-connection: retrieved" || print_error "  mysql-server-connection: NOT FOUND"

# Service tokens
SVC_CART_TOKEN=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "service-cart-token" --query "value" -o tsv 2>/dev/null || echo "")
SVC_ORDER_TOKEN=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "service-order-token" --query "value" -o tsv 2>/dev/null || echo "")
SVC_PRODUCT_TOKEN=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "service-product-token" --query "value" -o tsv 2>/dev/null || echo "")
SVC_WEBBFF_TOKEN=$(az keyvault secret show --vault-name "$KEY_VAULT" --name "service-webbff-token" --query "value" -o tsv 2>/dev/null || echo "")
print_success "  service-*-token: retrieved"

# Environment variables for the container (sorted alphabetically)
# All secrets are set as env vars - no Dapr secretstore access needed at runtime
ENV_VARS=(
    "APPLICATIONINSIGHTS_CONNECTION_STRING=$APP_INSIGHTS_CONN"
    "DAPR_GRPC_PORT=50001"
    "DAPR_HTTP_PORT=3500"
    "DB_NAME=$DB_NAME"
    "ENVIRONMENT=$APP_CONFIG"
    "JWT_SECRET=$JWT_SECRET"
    "MESSAGING_PROVIDER=dapr"
    "MYSQL_SERVER_CONNECTION=$MYSQL_SERVER_CONNECTION"
    "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true"
    "OTEL_RESOURCE_ATTRIBUTES=service.version=1.0.0"
    "OTEL_SERVICE_NAME=$SERVICE_NAME"
    "PORT=$APP_PORT"
    "SERVICE_CART_TOKEN=$SVC_CART_TOKEN"
    "SERVICE_NAME=$SERVICE_NAME"
    "SERVICE_ORDER_TOKEN=$SVC_ORDER_TOKEN"
    "SERVICE_PRODUCT_TOKEN=$SVC_PRODUCT_TOKEN"
    "SERVICE_WEBBFF_TOKEN=$SVC_WEBBFF_TOKEN"
)

if az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    print_info "Updating existing container app..."
    az containerapp update \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$IMAGE_TAG" \
        --set-env-vars "${ENV_VARS[@]}" \
        --output none
else
    print_info "Creating new container app..."
    MSYS_NO_PATHCONV=1 az containerapp create \
        --name "$CONTAINER_APP_NAME" \
        --container-name "$SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$CONTAINER_ENV" \
        --image "$IMAGE_TAG" \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-username "$ACR_NAME" \
        --registry-password "$ACR_PASSWORD" \
        --target-port "$APP_PORT" \
        --ingress external \
        --min-replicas "$MIN_REPLICAS" \
        --max-replicas "$MAX_REPLICAS" \
        --cpu "$CPU" \
        --memory "$MEMORY" \
        --enable-dapr \
        --dapr-app-id "$SERVICE_NAME" \
        --dapr-app-port "$APP_PORT" \
        --env-vars "${ENV_VARS[@]}" \
        ${IDENTITY_ID:+--user-assigned "$IDENTITY_ID"} \
        --tags "project=$PROJECT_NAME" "environment=$ENVIRONMENT" "suffix=$SUFFIX" "service=$SERVICE_NAME" \
        --output none
fi
print_success "Container app deployed"

# ============================================================================
# VERIFY DEPLOYMENT
# ============================================================================
print_header "Verifying Deployment"

APP_URL=$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL${NC}"
echo ""
echo "Application URL:  https://$APP_URL"
echo "Health Check:     https://$APP_URL/health"
echo ""
echo "Useful commands:"
echo -e "  Logs:      ${BLUE}az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow${NC}"
echo -e "  Dapr logs: ${BLUE}az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --container daprd --follow${NC}"
echo -e "  Delete:    ${BLUE}az containerapp delete --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --yes${NC}"
echo ""

# Optional: Test health endpoint
print_info "Waiting 15s for app to start..."
sleep 15
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "https://$APP_URL/health" 2>/dev/null || echo "000")
[ "$HTTP_STATUS" = "200" ] && print_success "Health check passed!" || print_warning "Health check returned HTTP $HTTP_STATUS (app may still be starting)"
