#!/bin/bash
# Entrypoint script for RunPod deployment
# Starts both Flask API and RunPod handler

set -e

echo "========================================"
echo "F5-TTS RunPod Serverless - Starting"
echo "========================================"

# GPU check
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Info:"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
else
    echo "⚠️  No GPU detected"
fi

# Create directories
mkdir -p /app/sample /app/output

# Start Flask API in background
echo "Starting Flask TTS API on port 8000..."
python3 /app/flask_tts_api_optimized.py &
FLASK_PID=$!
echo "Flask PID: $FLASK_PID"

# Wait for Flask to be ready
echo "Waiting for Flask API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Flask API is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Check if running in RunPod or Docker standalone mode
# Auto-detect RunPod environment or check explicit flag
if [ "$RUNPOD_MODE" = "true" ] || [ -n "$RUNPOD_POD_ID" ] || [ -n "$RUNPOD_ENDPOINT_ID" ]; then
    # Start RunPod handler (this will block)
    echo "=========================================="
    echo "Running in RunPod Serverless mode"
    echo "Starting RunPod handler..."
    echo "=========================================="
    exec python3 -u /app/runpod_handler_simple.py
else
    # Docker standalone mode - just keep Flask running
    echo "=========================================="
    echo "[RunPod Handler] ✅ Flask API is ready"
    echo "=========================================="
    echo "Running in Docker standalone mode (Flask only)"
    echo "To enable RunPod mode, set RUNPOD_MODE=true"
    echo "=========================================="
    # Keep container alive by waiting on Flask process
    wait $FLASK_PID
fi
