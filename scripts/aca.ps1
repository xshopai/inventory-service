# ============================================================================
# Azure Container Apps Deployment Script for Inventory Service
# ============================================================================
# This script deploys the Inventory Service to Azure Container Apps.
# 
# PREREQUISITE: Run the infrastructure deployment script first:
#   cd infrastructure/azure/aca/scripts
#   ./deploy-infra.ps1
#
# The infrastructure script creates all shared resources:
#   - Resource Group, ACR, Container Apps Environment
#   - Service Bus, Redis, Cosmos DB, MySQL, Key Vault
#   - Dapr components (pubsub, statestore, secretstore)
# ============================================================================

#Requires -Version 5.1

param(
    [string]$Environment,
    [string]$Suffix,
    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
function Write-Header {
    param([string]$Message)
    Write-Host "`n==============================================================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "==============================================================================`n" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

# ============================================================================
# Prerequisites Check
# ============================================================================
Write-Header "Checking Prerequisites"

# Check Azure CLI
try {
    $null = az --version 2>$null
    Write-Success "Azure CLI is installed"
}
catch {
    Write-ErrorMsg "Azure CLI is not installed. Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check Docker
try {
    $null = docker --version 2>$null
    Write-Success "Docker is installed"
}
catch {
    Write-ErrorMsg "Docker is not installed. Please install Docker first."
    exit 1
}

# Check if logged into Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Warning "Not logged into Azure. Initiating login..."
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Success "Logged into Azure"

# ============================================================================
# Configuration
# ============================================================================
Write-Header "Configuration"

# Service-specific configuration
$ServiceName = "inventory-service"
$AppPort = 8005
$ProjectName = "xshopai"

# Get script and service directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceDir = Split-Path -Parent $ScriptDir

# ============================================================================
# Environment Selection
# ============================================================================
if (-not $Environment) {
    Write-Host "Available Environments:" -ForegroundColor Cyan
    Write-Host "   dev     - Development environment"
    Write-Host "   staging - Staging/QA environment"
    Write-Host "   prod    - Production environment"
    Write-Host ""
    
    $Environment = Read-Host "Enter environment (dev/staging/prod) [dev]"
    if ([string]::IsNullOrWhiteSpace($Environment)) {
        $Environment = "dev"
    }
}

if ($Environment -notmatch "^(dev|staging|prod)$") {
    Write-ErrorMsg "Invalid environment: $Environment"
    Write-Host "   Valid values: dev, staging, prod"
    exit 1
}
Write-Success "Environment: $Environment"

# ============================================================================
# Suffix Configuration
# ============================================================================
Write-Header "Infrastructure Configuration"

if (-not $Suffix) {
    Write-Host "The suffix was set during infrastructure deployment." -ForegroundColor Cyan
    Write-Host "You can find it by running:"
    Write-Host "   az group list --query `"[?starts_with(name, 'rg-xshopai-$Environment')].{Name:name, Suffix:tags.suffix}`" -o table" -ForegroundColor Blue
    Write-Host ""
    
    $Suffix = Read-Host "Enter the infrastructure suffix"
}

if ([string]::IsNullOrWhiteSpace($Suffix)) {
    Write-ErrorMsg "Suffix is required. Please run the infrastructure deployment first."
    exit 1
}

if ($Suffix -notmatch "^[a-z0-9]{3,6}$") {
    Write-ErrorMsg "Invalid suffix format: $Suffix"
    Write-Host "   Suffix must be 3-6 lowercase alphanumeric characters."
    exit 1
}
Write-Success "Using suffix: $Suffix"

# ============================================================================
# Derive Resource Names from Infrastructure
# ============================================================================
$ResourceGroup = "rg-$ProjectName-$Environment-$Suffix"
$AcrName = "$ProjectName$Environment$Suffix"
$ContainerEnv = "cae-$ProjectName-$Environment-$Suffix"
$MysqlServer = "mysql-$ProjectName-$Environment-$Suffix"
$KeyVault = "kv-$ProjectName-$Environment-$Suffix"
$ManagedIdentity = "id-$ProjectName-$Environment-$Suffix"

Write-Info "Derived resource names:"
Write-Host "   Resource Group:      $ResourceGroup"
Write-Host "   Container Registry:  $AcrName"
Write-Host "   Container Env:       $ContainerEnv"
Write-Host "   MySQL Server:        $MysqlServer"
Write-Host "   Key Vault:           $KeyVault"
Write-Host ""

# ============================================================================
# Verify Infrastructure Exists
# ============================================================================
Write-Header "Verifying Infrastructure"

# Check Resource Group
$rgExists = az group show --name $ResourceGroup 2>$null
if (-not $rgExists) {
    Write-ErrorMsg "Resource group '$ResourceGroup' does not exist."
    Write-Host ""
    Write-Host "Please run the infrastructure deployment first:"
    Write-Host "   cd infrastructure/azure/aca/scripts" -ForegroundColor Blue
    Write-Host "   ./deploy-infra.ps1" -ForegroundColor Blue
    exit 1
}
Write-Success "Resource Group exists: $ResourceGroup"

# Check ACR
$acrExists = az acr show --name $AcrName 2>$null
if (-not $acrExists) {
    Write-ErrorMsg "Container Registry '$AcrName' does not exist."
    exit 1
}
$AcrLoginServer = (az acr show --name $AcrName --query loginServer -o tsv)
Write-Success "Container Registry exists: $AcrLoginServer"

# Check Container Apps Environment
$caeExists = az containerapp env show --name $ContainerEnv --resource-group $ResourceGroup 2>$null
if (-not $caeExists) {
    Write-ErrorMsg "Container Apps Environment '$ContainerEnv' does not exist."
    exit 1
}
Write-Success "Container Apps Environment exists: $ContainerEnv"

# Check MySQL Server
$mysqlExists = az mysql flexible-server show --name $MysqlServer --resource-group $ResourceGroup 2>$null
if (-not $mysqlExists) {
    Write-ErrorMsg "MySQL Server '$MysqlServer' does not exist."
    exit 1
}
$MysqlHost = (az mysql flexible-server show --name $MysqlServer --resource-group $ResourceGroup --query fullyQualifiedDomainName -o tsv)
Write-Success "MySQL Server exists: $MysqlHost"

# Get Managed Identity ID
$IdentityId = az identity show --name $ManagedIdentity --resource-group $ResourceGroup --query id -o tsv 2>$null
if ($IdentityId) {
    Write-Success "Managed Identity exists: $ManagedIdentity"
} else {
    Write-Warning "Managed Identity not found, will deploy without it"
}

# ============================================================================
# Database Configuration
# ============================================================================
Write-Header "Database Configuration"

$DbName = "inventory_db"
Write-Info "Database name: $DbName"

# Check if database exists, create if not
$dbExists = az mysql flexible-server db show --resource-group $ResourceGroup --server-name $MysqlServer --database-name $DbName 2>$null
if ($dbExists) {
    Write-Success "Database '$DbName' already exists"
} else {
    Write-Info "Creating database '$DbName'..."
    az mysql flexible-server db create `
        --resource-group $ResourceGroup `
        --server-name $MysqlServer `
        --database-name $DbName `
        --output none
    Write-Success "Database '$DbName' created"
}

# Get MySQL credentials from Key Vault
Write-Info "Retrieving MySQL credentials from Key Vault..."
$MysqlPassword = az keyvault secret show --vault-name $KeyVault --name "mysql-password" --query value -o tsv 2>$null

if ([string]::IsNullOrWhiteSpace($MysqlPassword)) {
    Write-Warning "Could not retrieve MySQL password from Key Vault"
    $securePassword = Read-Host "Enter MySQL admin password" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $MysqlPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

$MysqlUsername = "xshopaiadmin"

# URL-encode the password
$DbPasswordEncoded = [System.Uri]::EscapeDataString($MysqlPassword)
$DbConnection = "mysql+pymysql://${MysqlUsername}:${DbPasswordEncoded}@${MysqlHost}:3306/${DbName}?ssl_verify_cert=false&ssl_verify_identity=false"

Write-Success "Database connection configured"

# ============================================================================
# Confirmation
# ============================================================================
Write-Header "Deployment Configuration Summary"

Write-Host "Environment:          $Environment" -ForegroundColor Cyan
Write-Host "Suffix:               $Suffix" -ForegroundColor Cyan
Write-Host "Resource Group:       $ResourceGroup" -ForegroundColor Cyan
Write-Host "Container Registry:   $AcrLoginServer" -ForegroundColor Cyan
Write-Host "Container Env:        $ContainerEnv" -ForegroundColor Cyan
Write-Host "MySQL Server:         $MysqlHost" -ForegroundColor Cyan
Write-Host "Database:             $DbName" -ForegroundColor Cyan
Write-Host "Service:              $ServiceName" -ForegroundColor Cyan
Write-Host "Port:                 $AppPort" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipConfirmation) {
    $confirm = Read-Host "Do you want to proceed with deployment? (y/N)"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Warning "Deployment cancelled by user"
        exit 0
    }
}

# ============================================================================
# Step 1: Build and Push Container Image
# ============================================================================
Write-Header "Step 1: Building and Pushing Container Image"

# Login to ACR
Write-Info "Logging into ACR..."
az acr login --name $AcrName
Write-Success "Logged into ACR"

# Navigate to service directory
Push-Location $ServiceDir

try {
    # Build Docker image
    Write-Info "Building Docker image..."
    docker build -t "${ServiceName}:latest" .
    Write-Success "Docker image built"

    # Tag and push
    $ImageTag = "$AcrLoginServer/${ServiceName}:latest"
    docker tag "${ServiceName}:latest" $ImageTag
    Write-Info "Pushing image to ACR..."
    docker push $ImageTag
    Write-Success "Image pushed: $ImageTag"
}
finally {
    Pop-Location
}

# ============================================================================
# Step 2: Deploy Container App
# ============================================================================
Write-Header "Step 2: Deploying Container App"

# Get ACR credentials
$AcrPassword = (az acr credential show --name $AcrName --query "passwords[0].value" -o tsv)

# Check if container app exists
$appExists = az containerapp show --name $ServiceName --resource-group $ResourceGroup 2>$null

if ($appExists) {
    Write-Info "Container app '$ServiceName' exists, updating..."
    az containerapp update `
        --name $ServiceName `
        --resource-group $ResourceGroup `
        --image $ImageTag `
        --set-env-vars "FLASK_ENV=production" "DATABASE_URL=$DbConnection" "MESSAGING_PROVIDER=dapr" "DAPR_PUBSUB_NAME=pubsub" `
        --output none
    Write-Success "Container app updated"
} else {
    Write-Info "Creating container app '$ServiceName'..."
    
    $createArgs = @(
        "containerapp", "create",
        "--name", $ServiceName,
        "--resource-group", $ResourceGroup,
        "--environment", $ContainerEnv,
        "--image", $ImageTag,
        "--registry-server", $AcrLoginServer,
        "--registry-username", $AcrName,
        "--registry-password", $AcrPassword,
        "--target-port", $AppPort,
        "--ingress", "external",
        "--min-replicas", "1",
        "--max-replicas", "5",
        "--cpu", "0.5",
        "--memory", "1.0Gi",
        "--enable-dapr",
        "--dapr-app-id", $ServiceName,
        "--dapr-app-port", $AppPort,
        "--env-vars", "FLASK_ENV=production", "DATABASE_URL=$DbConnection", "MESSAGING_PROVIDER=dapr", "DAPR_PUBSUB_NAME=pubsub",
        "--output", "none"
    )
    
    if ($IdentityId) {
        $createArgs += @("--user-assigned", $IdentityId)
    }
    
    & az @createArgs
    Write-Success "Container app created"
}

# ============================================================================
# Step 3: Verify Deployment
# ============================================================================
Write-Header "Step 3: Verifying Deployment"

$AppUrl = (az containerapp show `
    --name $ServiceName `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn `
    -o tsv)

Write-Success "Deployment completed!"
Write-Host ""
Write-Info "Application URL: https://$AppUrl"
Write-Info "Health Check:    https://$AppUrl/health"
Write-Host ""

# Test health endpoint
Write-Info "Waiting for app to start (30s)..."
Start-Sleep -Seconds 30

Write-Info "Testing health endpoint..."
try {
    $response = Invoke-WebRequest -Uri "https://$AppUrl/health" -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    Write-Success "Health check passed! (HTTP $($response.StatusCode))"
}
catch {
    Write-Warning "Health check failed or timed out. The app may still be starting."
}

# ============================================================================
# Summary
# ============================================================================
Write-Header "Deployment Summary"

Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "   ✅ $ServiceName DEPLOYED SUCCESSFULLY" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application:" -ForegroundColor Cyan
Write-Host "   URL:              https://$AppUrl"
Write-Host "   Health:           https://$AppUrl/health"
Write-Host ""
Write-Host "Infrastructure:" -ForegroundColor Cyan
Write-Host "   Resource Group:   $ResourceGroup"
Write-Host "   Environment:      $ContainerEnv"
Write-Host "   Registry:         $AcrLoginServer"
Write-Host ""
Write-Host "Database:" -ForegroundColor Cyan
Write-Host "   Server:           $MysqlHost"
Write-Host "   Database:         $DbName"
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs:        az containerapp logs show --name $ServiceName --resource-group $ResourceGroup --follow" -ForegroundColor Blue
Write-Host "   View Dapr logs:   az containerapp logs show --name $ServiceName --resource-group $ResourceGroup --container daprd --follow" -ForegroundColor Blue
Write-Host "   Delete app:       az containerapp delete --name $ServiceName --resource-group $ResourceGroup --yes" -ForegroundColor Blue
Write-Host ""
