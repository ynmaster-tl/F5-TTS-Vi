#!/bin/bash
# Test Flask API with sample request

PORT=${1:-7860}
API_URL="http://localhost:${PORT}"

echo "========================================"
echo "Testing F5-TTS API on port $PORT"
echo "========================================"
echo ""

# 1. Health check
echo "1. Health Check:"
curl -s "${API_URL}/health" | jq '.'
echo ""

# 2. List voices
echo "2. Available Voices:"
curl -s "${API_URL}/voices" | jq '.'
echo ""

# 3. Submit TTS job
echo "3. Submit TTS Job:"
JOB_RESPONSE=$(curl -s -X POST "${API_URL}/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, đây là bài test hệ thống.",
    "ref_name": "sample/narrator.wav",
    "speed": 1.0,
    "job_id": "test_'$(date +%s)'"
  }')

echo "$JOB_RESPONSE" | jq '.'
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id // empty')

if [ -z "$JOB_ID" ]; then
  echo "Failed to get job ID"
  exit 1
fi

echo ""
echo "Job ID: $JOB_ID"
echo "Polling for completion..."
echo ""

# 4. Poll for completion
for i in {1..60}; do
  sleep 2
  PROGRESS=$(curl -s "${API_URL}/tts/progress/${JOB_ID}")
  STATUS=$(echo "$PROGRESS" | jq -r '.status // "unknown"')
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress // 0')
  
  echo "[$i] Progress: ${PERCENT}% - Status: ${STATUS}"
  
  if [ "$STATUS" = "completed" ]; then
    echo ""
    echo "✅ Job completed!"
    echo "$PROGRESS" | jq '.'
    
    FILENAME=$(echo "$PROGRESS" | jq -r '.filename // empty')
    if [ -n "$FILENAME" ]; then
      echo ""
      echo "Audio available at: ${API_URL}/output/${FILENAME}"
      echo "Download: curl -O ${API_URL}/output/${FILENAME}"
    fi
    exit 0
  fi
  
  if [ "$STATUS" = "failed" ]; then
    echo ""
    echo "❌ Job failed!"
    echo "$PROGRESS" | jq '.'
    exit 1
  fi
done

echo ""
echo "⚠️ Timeout waiting for job completion"
exit 1
