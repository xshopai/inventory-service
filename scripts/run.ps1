# Inventory Service - Run with Dapr

#!/usr/bin/env pwsh
# Run Inventory Service with Dapr sidecar
# Usage: .\run.ps1

$Host.UI.RawUI.WindowTitle = "Inventory Service"

Write-Host "Starting Inventory Service with Dapr..." -ForegroundColor Green
Write-Host "Service will be available at: http://localhost:8004"
Write-Host "Dapr HTTP endpoint: http://localhost:3504"
Write-Host "Dapr gRPC endpoint: localhost:50004"
Write-Host ""

dapr run `
  --app-id inventory-service `
  --app-port 8004 `
  --dapr-http-port 3504 `
  --dapr-grpc-port 50004 `
  --log-level warn `
  --config ./.dapr/config.yaml `
  --resources-path ./.dapr/components `
  -- python run.py
