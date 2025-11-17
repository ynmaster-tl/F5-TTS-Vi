# F5-TTS-Vi Quick Reference

## 📁 Project Structure

```
F5-TTS-Vi/
├── flask_tts_api_optimized.py   # Main Flask API (all modes use this)
├── runpod_handler_simple.py     # RunPod wrapper (calls Flask API)
├── entrypoint.sh                # Docker/RunPod startup script
├── Dockerfile.optimized         # Docker build config
├── requirements.optimized.txt   # Python dependencies
│
├── start_local.sh               # Start on port 7860 (testing)
├── start_docker_mode.sh         # Start on port 8000 (production)
├── test_api.sh                  # Test API endpoints
├── DEPLOYMENT_GUIDE.sh          # Full deployment guide
│
├── f5_tts/                      # F5-TTS source code
├── sample/                      # Voice reference files
│   ├── narrator.wav
│   ├── main.wav
│   └── ...
└── output/                      # Generated audio files
```

## 🚀 Quick Start

### 1️⃣ Local Testing (Port 7860)
```bash
cd /home/dtlong/F5-TTS-Vi
./start_local.sh

# In another terminal, test:
./test_api.sh 7860

# Update Next.js .env:
# F5_TTS_API_URL=http://localhost:7860
```

### 2️⃣ Docker Production (Port 8000)
```bash
cd /home/dtlong/F5-TTS-Vi

# Build
docker build -t f5-tts-local:latest -f Dockerfile.optimized .

# Run
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/sample:/app/sample \
  -v $(pwd)/output:/app/output \
  f5-tts-local:latest

# Test
./test_api.sh 8000

# Update Next.js .env:
# F5_TTS_API_URL=http://localhost:8000
```

### 3️⃣ RunPod Serverless
```bash
# 1. Push to Docker Hub
docker tag f5-tts-local:latest tlong94/f5-tts-vi:optimized
docker push tlong94/f5-tts-vi:optimized

# 2. Create RunPod endpoint via console
# - Image: tlong94/f5-tts-vi:optimized
# - GPU: RTX 3090/4090
# - Workers: 0-3

# 3. Update Next.js .env:
# RUNPOD_API_KEY=rpa_xxxxx
# RUNPOD_ENDPOINT_ID=xxxxx
```

## 🔧 API Endpoints

All modes expose the same Flask API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/voices` | GET | List available voices |
| `/tts` | POST | Submit TTS job |
| `/tts/progress/:id` | GET | Check job progress |
| `/tts/cancel/:id` | POST | Cancel job |
| `/output/:filename` | GET | Download audio |

## 📝 API Usage Example

```bash
# Submit job
curl -X POST http://localhost:7860/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, đây là test.",
    "ref_name": "sample/narrator.wav",
    "speed": 1.0,
    "job_id": "test_123"
  }'

# Check progress
curl http://localhost:7860/tts/progress/test_123

# Download audio (when completed)
curl -O http://localhost:7860/output/test_123.wav
```

## 🎯 Integration with Next.js

The Next.js app (`Starter-Prisma-Pro`) automatically routes jobs to:
- **Local GPU** (if available) → `F5_TTS_API_URL`
- **RunPod** (if configured) → RunPod API

Edit `.env` to switch between modes:

```env
# Mode 1: Local Testing
F5_TTS_API_URL=http://localhost:7860
MAX_CONCURRENT_JOBS=1

# Mode 2: Docker Production  
F5_TTS_API_URL=http://localhost:8000
MAX_CONCURRENT_JOBS=1

# Mode 3: RunPod (+ optional local fallback)
F5_TTS_API_URL=http://localhost:8000
RUNPOD_API_KEY=rpa_xxxxx
RUNPOD_ENDPOINT_ID=xxxxx
MAX_CONCURRENT_JOBS=6
```

## 🐛 Troubleshooting

### Voice file not found
Error: `sample/narrator.wav not found`

**Fix:** Ensure orchestrator sends correct path:
- ✅ `sample/narrator.wav` (with folder prefix)
- ❌ `narrator.wav` (will fail if Flask expects folder)

### Port already in use
Error: `Address already in use`

**Fix:**
```bash
# Find process using port
lsof -i :7860
# Kill it
kill -9 <PID>
```

### GPU out of memory
Error: `CUDA out of memory`

**Fix:**
- Only 1 job at a time (already enforced)
- Reduce text length
- Restart Flask API to clear GPU memory

## 📚 Full Documentation

- `README.md` - Complete deployment guide
- `DEPLOYMENT_GUIDE.sh` - Quick reference (run it to see)
- Source code comments for implementation details

## 🔄 Switching Modes

**No code changes needed!** Just change:
1. Port number (7860 or 8000)
2. `.env` configuration
3. Restart API/Next.js

The same Flask API code runs in all 3 modes.
