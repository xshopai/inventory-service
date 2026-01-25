# ============================================================================
# Azure Container Apps Deployment Script for Inventory Service
# ============================================================================
# This script automates the deployment of Inventory Service to Azure Container Apps
# with Dapr support, Azure Service Bus, and Azure MySQL Flexible Server.
# ============================================================================

#Requires -Version 5.1

param(
    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Header {
    param([string]$Message)
    Write-Host "`n============================================================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "============================================================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Blue
}

function Get-UserInput {
    param(
        [string]$Prompt,
        [string]$Default
    )
    
    if ($Default) {
        $input = Read-Host "$Prompt [$Default]"
        if ([string]::IsNullOrWhiteSpace($input)) {
            return $Default
        }
        return $input
    }
    else {
        return Read-Host $Prompt
    }
}

function Get-SecureUserInput {
    param([string]$Prompt)
    
    $secureString = Read-Host $Prompt -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureString)
    return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# ============================================================================
# Prerequisites Check
# ============================================================================
Write-Header "Checking Prerequisites"

# Check Azure CLI
try {
    $null = az --version
    Write-Success "Azure CLI is installed"
}
catch {
    Write-Error "Azure CLI is not installed. Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check Docker
try {
    $null = docker --version
    Write-Success "Docker is installed"
}
catch {
    Write-Error "Docker is not installed. Please install Docker first."
    exit 1
}

# Check if logged into Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Warning "Not logged into Azure. Initiating login..."
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Success "Logged into Azure as: $($account.user.name)"

# ============================================================================
# User Input Collection
# ============================================================================
Write-Header "Azure Configuration"

# List available subscriptions
Write-Host "`nAvailable Azure Subscriptions:" -ForegroundColor Blue
az account list --query "[].{Name:name, SubscriptionId:id, IsDefault:isDefault}" --output table

Write-Host ""
$SubscriptionId = Get-UserInput -Prompt "Enter Azure Subscription ID (leave empty for default)" -Default ""

if ($SubscriptionId) {
    az account set --subscription $SubscriptionId
    Write-Success "Subscription set to: $SubscriptionId"
}
else {
    $SubscriptionId = (az account show --query id --output tsv)
    Write-Info "Using default subscription: $SubscriptionId"
}

# Resource Group
Write-Host ""
$ResourceGroup = Get-UserInput -Prompt "Enter Resource Group name" -Default "rg-xshopai-aca"

# Location
Write-Host ""
Write-Host "Common Azure Locations:" -ForegroundColor Blue
Write-Host "  - swedencentral (Sweden Central)"
Write-Host "  - eastus (East US)"
Write-Host "  - westus2 (West US 2)"
Write-Host "  - westeurope (West Europe)"
Write-Host "  - northeurope (North Europe)"
$Location = Get-UserInput -Prompt "Enter Azure Location" -Default "swedencentral"

# Azure Container Registry
Write-Host ""
$AcrName = Get-UserInput -Prompt "Enter Azure Container Registry name (must be globally unique)" -Default "acrxshopaiaca"

# Container Apps Environment
Write-Host ""
$EnvironmentName = Get-UserInput -Prompt "Enter Container Apps Environment name" -Default "cae-xshopai-aca"

# Application Insights
Write-Host ""
$AiName = Get-UserInput -Prompt "Enter Application Insights name" -Default "ai-xshopai-aca"

# Log Analytics Workspace
Write-Host ""
$LogAnalyticsWorkspace = Get-UserInput -Prompt "Enter Log Analytics Workspace name" -Default "law-xshopai-aca"

# Service Bus
Write-Host ""
$SbNamespace = Get-UserInput -Prompt "Enter Service Bus namespace name (must be globally unique)" -Default "sb-xshopai-aca"

# MySQL Configuration
Write-Host ""
$DbServer = Get-UserInput -Prompt "Enter MySQL Server name (must be globally unique)" -Default "mysql-xshopai-aca"
$DbName = Get-UserInput -Prompt "Enter MySQL Database name" -Default "inventory_service_db"
$DbUsername = Get-UserInput -Prompt "Enter MySQL Admin Username" -Default "xshopaiadmin"
Write-Host ""
Write-Warning "Password must be at least 8 characters and include: uppercase, lowercase, number, and special character"
$DbPassword = Get-SecureUserInput -Prompt "Enter MySQL Admin Password"

# Service Tokens (optional)
Write-Host ""
Write-Info "Service tokens are used for inter-service authentication (optional for initial deployment)"
$ProductServiceToken = Get-UserInput -Prompt "Enter Product Service Token (optional)" -Default ""
$OrderServiceToken = Get-UserInput -Prompt "Enter Order Service Token (optional)" -Default ""
$CartServiceToken = Get-UserInput -Prompt "Enter Cart Service Token (optional)" -Default ""
$WebBffToken = Get-UserInput -Prompt "Enter Web BFF Token (optional)" -Default ""

# App name
$AppName = "inventory-service"

# ============================================================================
# Confirmation
# ============================================================================
Write-Header "Deployment Configuration Summary"

Write-Host "Resource Group:           $ResourceGroup"
Write-Host "Location:                 $Location"
Write-Host "Container Registry:       $AcrName"
Write-Host "Environment:              $EnvironmentName"
Write-Host "Application Insights:     $AiName"
Write-Host "Log Analytics:            $LogAnalyticsWorkspace"
Write-Host "Service Bus:              $SbNamespace"
Write-Host "MySQL Server:             $DbServer"
Write-Host "MySQL Database:           $DbName"
Write-Host "MySQL Username:           $DbUsername"
Write-Host "App Name:                 $AppName"
Write-Host ""

if (-not $SkipConfirmation) {
    $confirm = Read-Host "Do you want to proceed with deployment? (y/N)"
    if ($confirm -notmatch '^[Yy]$') {
        Write-Warning "Deployment cancelled by user"
        exit 0
    }
}

# ============================================================================
# Step 1: Create Resource Group
# ============================================================================
Write-Header "Step 1: Creating Resource Group"

az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

Write-Success "Resource group '$ResourceGroup' created/verified"

# ============================================================================
# Step 2: Create Azure Container Registry
# ============================================================================
Write-Header "Step 2: Creating Azure Container Registry"

$acrExists = az acr show --name $AcrName 2>$null
if ($acrExists) {
    Write-Info "ACR '$AcrName' already exists, skipping creation"
}
else {
    az acr create `
        --resource-group $ResourceGroup `
        --name $AcrName `
        --sku Basic `
        --admin-enabled true `
        --output none
    Write-Success "ACR '$AcrName' created"
}

$AcrLoginServer = (az acr show --name $AcrName --query loginServer --output tsv)
Write-Info "ACR Login Server: $AcrLoginServer"

# ============================================================================
# Step 3: Build and Push Container Image
# ============================================================================
Write-Header "Step 3: Building and Pushing Container Image"

# Login to ACR
az acr login --name $AcrName
Write-Success "Logged into ACR"

# Navigate to service directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceDir = Split-Path -Parent $ScriptDir
Push-Location $ServiceDir

try {
    # Build Docker image
    Write-Info "Building Docker image..."
    docker build -t inventory-service:latest .
    Write-Success "Docker image built"

    # Tag and push
    docker tag inventory-service:latest "$AcrLoginServer/inventory-service:latest"
    docker push "$AcrLoginServer/inventory-service:latest"
    Write-Success "Image pushed to ACR"
}
finally {
    Pop-Location
}

# ============================================================================
# Step 4: Register Resource Providers
# ============================================================================
Write-Header "Step 4: Registering Resource Providers"

Write-Info "Registering microsoft.operationalinsights..."
az provider register --namespace microsoft.operationalinsights --wait

Write-Info "Registering microsoft.insights..."
az provider register --namespace microsoft.insights --wait

Write-Info "Registering Microsoft.App..."
az provider register --namespace Microsoft.App --wait

Write-Info "Registering Microsoft.ServiceBus..."
az provider register --namespace Microsoft.ServiceBus --wait

Write-Success "All resource providers registered"

# ============================================================================
# Step 5: Create Application Insights
# ============================================================================
Write-Header "Step 5: Creating Application Insights"

$aiExists = az monitor app-insights component show --app $AiName --resource-group $ResourceGroup 2>$null
if ($aiExists) {
    Write-Info "Application Insights '$AiName' already exists"
}
else {
    az monitor app-insights component create `
        --app $AiName `
        --location $Location `
        --resource-group $ResourceGroup `
        --output none
    Write-Success "Application Insights '$AiName' created"
}

$AiKey = (az monitor app-insights component show `
    --app $AiName `
    --resource-group $ResourceGroup `
    --query instrumentationKey `
    --output tsv)
Write-Info "App Insights Key: $AiKey"

# ============================================================================
# Step 6: Create Log Analytics Workspace
# ============================================================================
Write-Header "Step 6: Creating Log Analytics Workspace"

$lawExists = az monitor log-analytics workspace show --resource-group $ResourceGroup --workspace-name $LogAnalyticsWorkspace 2>$null
if ($lawExists) {
    Write-Info "Log Analytics Workspace '$LogAnalyticsWorkspace' already exists"
}
else {
    az monitor log-analytics workspace create `
        --resource-group $ResourceGroup `
        --workspace-name $LogAnalyticsWorkspace `
        --location $Location `
        --output none
    Write-Success "Log Analytics Workspace '$LogAnalyticsWorkspace' created"
}

$LogAnalyticsWorkspaceId = (az monitor log-analytics workspace show `
    --resource-group $ResourceGroup `
    --workspace-name $LogAnalyticsWorkspace `
    --query customerId `
    --output tsv)

$LogAnalyticsKey = (az monitor log-analytics workspace get-shared-keys `
    --resource-group $ResourceGroup `
    --workspace-name $LogAnalyticsWorkspace `
    --query primarySharedKey `
    --output tsv)

Write-Info "Log Analytics Workspace ID: $LogAnalyticsWorkspaceId"

# ============================================================================
# Step 7: Create Container Apps Environment
# ============================================================================
Write-Header "Step 7: Creating Container Apps Environment"

$envExists = az containerapp env show --name $EnvironmentName --resource-group $ResourceGroup 2>$null
if ($envExists) {
    Write-Info "Container Apps Environment '$EnvironmentName' already exists"
}
else {
    az containerapp env create `
        --name $EnvironmentName `
        --resource-group $ResourceGroup `
        --location $Location `
        --dapr-instrumentation-key $AiKey `
        --logs-workspace-id $LogAnalyticsWorkspaceId `
        --logs-workspace-key $LogAnalyticsKey `
        --enable-workload-profiles false `
        --output none
    Write-Success "Container Apps Environment '$EnvironmentName' created"
}

# ============================================================================
# Step 8: Create Azure Service Bus
# ============================================================================
Write-Header "Step 8: Creating Azure Service Bus"

$sbExists = az servicebus namespace show --name $SbNamespace --resource-group $ResourceGroup 2>$null
if ($sbExists) {
    Write-Info "Service Bus namespace '$SbNamespace' already exists"
}
else {
    az servicebus namespace create `
        --name $SbNamespace `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard `
        --output none
    Write-Success "Service Bus namespace '$SbNamespace' created"
}

# Create topic
$topicExists = az servicebus topic show --name inventory-events --namespace-name $SbNamespace --resource-group $ResourceGroup 2>$null
if ($topicExists) {
    Write-Info "Service Bus topic 'inventory-events' already exists"
}
else {
    az servicebus topic create `
        --name inventory-events `
        --namespace-name $SbNamespace `
        --resource-group $ResourceGroup `
        --output none
    Write-Success "Service Bus topic 'inventory-events' created"
}

$SbConnection = (az servicebus namespace authorization-rule keys list `
    --namespace-name $SbNamespace `
    --resource-group $ResourceGroup `
    --name RootManageSharedAccessKey `
    --query primaryConnectionString `
    --output tsv)

Write-Info "Service Bus connection string retrieved"

# ============================================================================
# Step 9: Create Azure MySQL Flexible Server
# ============================================================================
Write-Header "Step 9: Creating Azure MySQL Flexible Server"

$dbExists = az mysql flexible-server show --name $DbServer --resource-group $ResourceGroup 2>$null
if ($dbExists) {
    Write-Info "MySQL server '$DbServer' already exists"
}
else {
    az mysql flexible-server create `
        --resource-group $ResourceGroup `
        --name $DbServer `
        --location $Location `
        --admin-user $DbUsername `
        --admin-password $DbPassword `
        --sku-name Standard_B1ms `
        --tier Burstable `
        --version 8.0.21 `
        --storage-size 32 `
        --public-access 0.0.0.0 `
        --output none
    Write-Success "MySQL server '$DbServer' created"
}

# Configure firewall
Write-Info "Configuring firewall rules..."

$MyIp = (Invoke-RestMethod -Uri "https://ifconfig.me/ip" -UseBasicParsing).Trim()
Write-Info "Your public IP: $MyIp"

try {
    az mysql flexible-server firewall-rule create `
        --resource-group $ResourceGroup `
        --name $DbServer `
        --rule-name AllowMyIP `
        --start-ip-address $MyIp `
        --end-ip-address $MyIp `
        --output none 2>$null
}
catch {
    # Ignore error if rule already exists
}

try {
    az mysql flexible-server firewall-rule create `
        --resource-group $ResourceGroup `
        --name $DbServer `
        --rule-name AllowAzureServices `
        --start-ip-address 0.0.0.0 `
        --end-ip-address 0.0.0.0 `
        --output none 2>$null
}
catch {
    # Ignore error if rule already exists
}

Write-Success "Firewall rules configured"

# Create database
$dbDatabaseExists = az mysql flexible-server db show --resource-group $ResourceGroup --server-name $DbServer --database-name $DbName 2>$null
if ($dbDatabaseExists) {
    Write-Info "Database '$DbName' already exists"
}
else {
    az mysql flexible-server db create `
        --resource-group $ResourceGroup `
        --server-name $DbServer `
        --database-name $DbName `
        --output none
    Write-Success "Database '$DbName' created"
}

# URL-encode the password
Add-Type -AssemblyName System.Web
$DbPasswordEncoded = [System.Web.HttpUtility]::UrlEncode($DbPassword)
$DbConnection = "mysql+pymysql://${DbUsername}:${DbPasswordEncoded}@${DbServer}.mysql.database.azure.com:3306/${DbName}?ssl_ca=/etc/ssl/certs/DigiCertGlobalRootG2.crt.pem"

Write-Info "Database connection string prepared"

# ============================================================================
# Step 10: Create Dapr Component File
# ============================================================================
Write-Header "Step 10: Creating Dapr Component File"

$daprComponentsDir = Join-Path $ServiceDir ".dapr\components"
if (-not (Test-Path $daprComponentsDir)) {
    New-Item -ItemType Directory -Path $daprComponentsDir -Force | Out-Null
}

$daprComponentContent = @"
componentType: pubsub.azure.servicebus.topics
version: v1
metadata:
  - name: connectionString
    value: '$SbConnection'
  - name: consumerID
    value: inventory-service
scopes:
  - inventory-service
"@

$daprComponentFile = Join-Path $daprComponentsDir "dapr-servicebus-component.yaml"
Set-Content -Path $daprComponentFile -Value $daprComponentContent -Encoding UTF8

Write-Success "Dapr Service Bus component file created"

# ============================================================================
# Step 11: Deploy Container App
# ============================================================================
Write-Header "Step 11: Deploying Container App"

$AcrPassword = (az acr credential show --name $AcrName --query "passwords[0].value" --output tsv)

# Build env-vars array
$envVars = @(
    "FLASK_ENV=production",
    "DATABASE_URL=$DbConnection",
    "MESSAGING_PROVIDER=dapr",
    "DAPR_PUBSUB_NAME=inventory-pubsub"
)

if ($ProductServiceToken) { $envVars += "PRODUCT_SERVICE_TOKEN=$ProductServiceToken" }
if ($OrderServiceToken) { $envVars += "ORDER_SERVICE_TOKEN=$OrderServiceToken" }
if ($CartServiceToken) { $envVars += "CART_SERVICE_TOKEN=$CartServiceToken" }
if ($WebBffToken) { $envVars += "WEB_BFF_TOKEN=$WebBffToken" }

$envVarsString = $envVars -join " "

$appExists = az containerapp show --name $AppName --resource-group $ResourceGroup 2>$null
if ($appExists) {
    Write-Info "Container app '$AppName' already exists, updating..."
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --image "$AcrLoginServer/inventory-service:latest" `
        --set-env-vars $envVarsString `
        --output none
}
else {
    az containerapp create `
        --name $AppName `
        --resource-group $ResourceGroup `
        --environment $EnvironmentName `
        --image "$AcrLoginServer/inventory-service:latest" `
        --registry-server $AcrLoginServer `
        --registry-username $AcrName `
        --registry-password $AcrPassword `
        --target-port 8004 `
        --ingress external `
        --min-replicas 1 `
        --max-replicas 5 `
        --cpu 0.5 `
        --memory 1.0Gi `
        --enable-dapr `
        --dapr-app-id inventory-service `
        --dapr-app-port 8004 `
        --env-vars $envVarsString `
        --output none
}

Write-Success "Container app '$AppName' deployed"

# ============================================================================
# Step 12: Configure Dapr Component
# ============================================================================
Write-Header "Step 12: Configuring Dapr Component"

az containerapp env dapr-component set `
    --name $EnvironmentName `
    --resource-group $ResourceGroup `
    --dapr-component-name inventory-pubsub `
    --yaml $daprComponentFile `
    --output none

Write-Success "Dapr component configured"

# ============================================================================
# Step 13: Verify Deployment
# ============================================================================
Write-Header "Step 13: Verifying Deployment"

$AppUrl = (az containerapp show `
    --name $AppName `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn `
    --output tsv)

Write-Success "Deployment completed successfully!"
Write-Host ""
Write-Info "Application URL: https://$AppUrl"
Write-Info "Health Check: https://$AppUrl/health"
Write-Host ""

# Test health endpoint
Write-Info "Testing health endpoint..."
Start-Sleep -Seconds 10  # Wait for app to start

try {
    $response = Invoke-WebRequest -Uri "https://$AppUrl/health" -TimeoutSec 30 -UseBasicParsing
    Write-Success "Health check passed!"
}
catch {
    Write-Warning "Health check failed or timed out. The app may still be starting."
}

# ============================================================================
# Summary
# ============================================================================
Write-Header "Deployment Summary"

Write-Host "Resource Group:       $ResourceGroup"
Write-Host "Location:             $Location"
Write-Host "Container Registry:   $AcrLoginServer"
Write-Host "Environment:          $EnvironmentName"
Write-Host "Application URL:      https://$AppUrl"
Write-Host ""
Write-Host "MySQL Server:         $DbServer.mysql.database.azure.com"
Write-Host "MySQL Database:       $DbName"
Write-Host "MySQL Username:       $DbUsername"
Write-Host ""
Write-Host "Service Bus:          $SbNamespace.servicebus.windows.net"
Write-Host ""
Write-Info "To view logs: az containerapp logs show --name $AppName --resource-group $ResourceGroup --follow"
Write-Info "To delete: az containerapp delete --name $AppName --resource-group $ResourceGroup --yes"
