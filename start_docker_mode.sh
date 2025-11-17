#!/bin/bash
# Start Flask API on port 8000 (Docker production mode)

export FLASK_HOST=0.0.0.0
export FLASK_PORT=8000
export REF_VOICE_DIR=./sample
export OUTPUT_AUDIO_DIR=./output

echo "========================================"
echo "F5-TTS Docker Mode (Port 8000)"
echo "========================================"
echo ""

# Check if conda environment exists
if conda env list | grep -q "F5-TTS-Vi-100h"; then
    echo "Using conda environment: F5-TTS-Vi-100h"
    conda run -n F5-TTS-Vi-100h python flask_tts_api_optimized.py
else
    echo "Conda environment not found, using system Python"
    python3 flask_tts_api_optimized.py
fi
