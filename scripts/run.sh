#!/bin/bash

# Inventory Service - Run with Dapr
echo "Starting Inventory Service with Dapr..."
echo "Service will be available at: http://localhost:8004"
echo "Dapr HTTP endpoint: http://localhost:3500"
echo "Dapr gRPC endpoint: localhost:50001"
echo ""

dapr run \
  --app-id inventory-service \
  --app-port 8004 \
  --dapr-http-port 3500 \
  --dapr-grpc-port 50001 \
  --log-level warn \
  --config ./.dapr/config.yaml \
  --resources-path ./.dapr/components \
  -- python run.py
