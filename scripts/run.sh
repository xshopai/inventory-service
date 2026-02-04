#!/bin/bash

# Inventory Service - Run with Dapr
# Change to project root directory
cd "$(dirname "$0")/.." || exit 1

echo "Starting Inventory Service with Dapr..."
echo "Working directory: $(pwd)"
echo "Service will be available at: http://localhost:8005"
echo "Dapr HTTP endpoint: http://localhost:3500"
echo "Dapr gRPC endpoint: localhost:50001"
echo ""

dapr run \
  --app-id inventory-service \
  --app-port 8005 \
  --dapr-http-port 3500 \
  --dapr-grpc-port 50001 \
  --log-level info \
  --config ./.dapr/config.yaml \
  --resources-path ./.dapr/components \
  -- python run.py
