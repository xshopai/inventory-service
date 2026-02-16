#!/bin/bash

# Inventory Service - Run with direct RabbitMQ (local development)

echo "Starting Inventory Service (Direct RabbitMQ)..."
echo "Service will be available at: http://localhost:8005"
echo ""

# Kill any process using port 8005 (prevents "address already in use" errors)
PORT=8005
for pid in $(netstat -ano 2>/dev/null | grep ":$PORT" | grep LISTENING | awk '{print $5}' | sort -u); do
    echo "Killing process $pid on port $PORT..."
    taskkill //F //PID $pid 2>/dev/null
done

# Copy .env.dev to .env for local development
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SERVICE_DIR"

if [ -f ".env.dev" ]; then
    cp ".env.dev" ".env"
    echo "✅ Copied .env.dev → .env"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Install dependencies if needed
if [ ! -f "venv/.deps_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt -q
    touch venv/.deps_installed
fi

# Run the service with hot reload
export FLASK_DEBUG=1
export FLASK_ENV=development
export USE_RELOADER=true
python run.py
