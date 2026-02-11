#!/bin/bash

# Inventory Service - Run without Dapr (local development)

echo "Starting Inventory Service (without Dapr)..."
echo "Service will be available at: http://localhost:8005"
echo ""
echo "Note: Event publishing and service-to-service calls will fail without Dapr."
echo "This mode is suitable for isolated development and testing."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the service
python run.py
