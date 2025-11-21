#!/bin/bash

echo "[F5-TTS] Starting Flask API Server in background..."
python3 flask_tts_api_optimized.py &
FLASK_PID=$!

echo "[F5-TTS] Waiting 5 seconds for Flask to initialize..."
sleep 5

echo "[F5-TTS] Starting RunPod Handler..."
python3 runpod_handler_simple.py &
RUNPOD_PID=$!

echo "[F5-TTS] Both services started. Flask PID: $FLASK_PID, RunPod PID: $RUNPOD_PID"

# Wait for both processes
wait $FLASK_PID $RUNPOD_PID