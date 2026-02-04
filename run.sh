#!/bin/bash

# Inventory Service - Run with Dapr

echo "Starting Inventory Service with Dapr..."
echo "Service will be available at: http://localhost:8005"
echo "Dapr HTTP endpoint: http://localhost:3505"
echo "Dapr gRPC endpoint: localhost:50005"
echo ""

dapr run \
  --app-id inventory-service \
  --app-port 8005 \
  --dapr-http-port 3505 \
  --dapr-grpc-port 50005 \
  --log-level info \
  --config ./.dapr/config.yaml \
  --resources-path ./.dapr/components \
  -- python run.py
