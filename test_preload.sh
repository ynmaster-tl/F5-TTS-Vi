#!/bin/bash
# Test preload mechanism - check if model loads into VRAM on startup

echo "========================================"
echo "Testing Model Preload into VRAM"
echo "========================================"
echo ""

echo "1. Checking GPU status before starting..."
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
echo ""

echo "2. Starting Flask API (will preload model)..."
echo "   Watch for 'Model loaded into VRAM' message"
echo "   This should take 30-60 seconds"
echo ""

cd /home/dtlong/F5-TTS-Vi

# Start server and capture output
FLASK_PORT=7860 timeout 120 conda run -n F5-TTS-Vi-100h python flask_tts_api_optimized.py &
FLASK_PID=$!

echo "Flask PID: $FLASK_PID"
echo ""

# Wait for startup
echo "3. Waiting for server to be ready..."
for i in {1..60}; do
  if curl -s http://localhost:7860/health > /dev/null 2>&1; then
    echo "   ✅ Server is ready!"
    break
  fi
  sleep 2
done

echo ""
echo "4. Checking GPU memory after preload..."
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
echo ""

echo "5. Checking API status..."
curl -s http://localhost:7860/status | jq '.'
echo ""

echo "6. Cleaning up..."
kill $FLASK_PID 2>/dev/null
wait $FLASK_PID 2>/dev/null

echo ""
echo "✅ Test completed!"
echo ""
echo "Expected results:"
echo "  - GPU memory usage should increase after startup"
echo "  - API status should show: model_loaded: true"
echo "  - First job should start immediately (no model load wait)"
