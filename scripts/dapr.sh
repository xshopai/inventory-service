#!/bin/bash

# Inventory Service - Run with Dapr Pub/Sub

echo "Starting Inventory Service (Dapr Pub/Sub)..."
echo "Service will be available at: http://localhost:8005"
echo "Dapr HTTP endpoint: http://localhost:3505"
echo "Dapr gRPC endpoint: localhost:50005"
echo ""

# Kill any processes using required ports (prevents "address already in use" errors)
for PORT in 8005 3505 50005; do
    for pid in $(netstat -ano 2>/dev/null | grep ":$PORT" | grep LISTENING | awk '{print $5}' | sort -u); do
        echo "Killing process $pid on port $PORT..."
        taskkill //F //PID $pid 2>/dev/null
    done
done

dapr run \
  --app-id inventory-service \
  --app-port 8005 \
  --dapr-http-port 3505 \
  --dapr-grpc-port 50005 \
  --log-level info \
  --config ./.dapr/config.yaml \
  --resources-path ./.dapr/components \
  -- python run.py
