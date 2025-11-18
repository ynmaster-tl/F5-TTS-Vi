# F5-TTS Vietnamese - Production-Ready Voice Cloning

Production-ready F5-TTS text-to-speech with Vietnamese language support optimized for RunPod Serverless deployment.

**Docker Image:** `tlong94/f5-tts-vi:optimized` (27GB)  
**RunPod Endpoint:** `vmv08jygfi62i6`  
**GitHub:** https://github.com/ynmaster-tl/F5-TTS-Vi

---

## 🎯 Key Features

✅ **RunPod Serverless v2** - Async processing with `/run` and `/status` polling  
✅ **Vietnamese Voice Cloning** - F5-TTS model trained on 100h ViVoice dataset  
✅ **Idempotency** - Prevents duplicate processing with in-memory job tracking  
✅ **Download URL** - Returns public URL for audio download (worker terminates after job)  
✅ **Health Check** - Curl-based healthcheck for container monitoring  
✅ **Progress Tracking** - Real-time progress via JSON files  
✅ **Auto Cleanup** - Progress files deleted after audio download  

---

## 🏗️ Architecture

### RunPod Serverless Flow
1. **Next.js** submits job to RunPod `/run` endpoint (async)
2. **RunPod** spawns worker, calls handler with job data
3. **Handler** polls Flask API for progress every 2 seconds
4. **Flask API** processes TTS (200-400s for long text)
5. **Handler** returns `download_url` when complete
6. **Next.js** polls RunPod `/status` every 1 second
7. **Next.js** downloads audio before worker terminates (10s idle timeout)

### Components
- **Flask API** (Port 8000): TTS processing, progress tracking, file serving
- **RunPod Handler**: Orchestrates Flask API, returns results to RunPod
- **Next.js Orchestrator**: Job queue management, status polling, audio download

---

## 🚀 Deployment Modes

This project supports **3 deployment modes** with the same codebase:

| Mode | Port | Use Case | Command |
|------|------|----------|---------|
| **Local Test** | 7860 | Quick testing & development | `./start_local.sh` |
| **Docker** | 8000 | Production on your server | `docker run -p 8000:8000 ...` |
| **RunPod** | 8000 | Cloud serverless (PRODUCTION) | RunPod Console |

All modes use the same Flask API - just different configurations.

---

## 🚀 Mode 1: Local Testing (Port 7860)

### Quick Start

```bash
cd /home/dtlong/F5-TTS-Vi

# Start Flask API on port 7860
./start_local.sh

# Or manually:
conda activate F5-TTS-Vi-100h
FLASK_PORT=7860 python flask_tts_api_optimized.py
```

### Test API

```bash
# Test with sample request
./test_api.sh 7860

# Or manual curl:
curl http://localhost:7860/health
```

### Update Next.js Config

```bash
# Edit Starter-Prisma-Pro/.env
F5_TTS_API_URL=http://localhost:7860
```

---

## 🐳 Mode 2: Docker Production (Port 8000)

### Build & Run

```bash
cd /home/dtlong/F5-TTS-Vi

# Build image
docker build -t f5-tts-local:latest -f Dockerfile.optimized .

# Run with GPU
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/sample:/app/sample \
  -v $(pwd)/output:/app/output \
  f5-tts-local:latest

# Check logs
docker logs -f f5-tts-api
```

### Test API

```bash
./test_api.sh 8000
```

### Update Next.js Config

```bash
# Edit Starter-Prisma-Pro/.env
F5_TTS_API_URL=http://localhost:8000
```

---

## ☁️ Mode 3: RunPod Serverless (PRODUCTION)

### 1. Create Serverless Endpoint

Go to [RunPod Console](https://www.runpod.io/console/serverless) and create endpoint:

**Container Configuration:**
- **Container Image:** `tlong94/f5-tts-vi:optimized`
- **GPU:** RTX 3090/4090 (24GB VRAM recommended)
- **Container Disk:** 30GB minimum
- **Docker Command:** `python -u runpod_handler_simple.py` (or leave empty - uses CMD from Dockerfile)

**Scaling Configuration:**
- **Min Workers:** 0 (auto-scale down to save cost)
- **Max Workers:** 3-5 (based on traffic)
- **Idle Timeout:** 10 seconds (keep worker alive after job completion for download)
- **Execution Timeout:** 600 seconds (10 minutes max per job)

**Environment Variables:**
- None required (all configured in image)

**Network Configuration:**
- **FlashBoot:** Enabled (faster cold start)

### 2. GitHub Integration (Auto-Deploy)

Connect RunPod to GitHub for automatic rebuilds:

1. Go to Endpoint Settings → GitHub Integration
2. Connect repository: `https://github.com/ynmaster-tl/F5-TTS-Vi`
3. Branch: `main`
4. Auto-deploy on push: **Enabled**

Now any commit to `main` branch will trigger automatic rebuild in RunPod.

### 3. Get Credentials

- **API Key:** Settings → API Keys
- **Endpoint ID:** Copy from endpoint overview (e.g., `vmv08jygfi62i6`)

### 4. Configure Next.js

```bash
# Edit Starter-Prisma-Pro/.env
RUNPOD_API_KEY=rpa_YOUR_API_KEY
RUNPOD_ENDPOINT_ID=your_endpoint_id
```

### 5. Test Endpoint

```bash
export RUNPOD_API_KEY="your_api_key"
export ENDPOINT_ID="your_endpoint_id"

curl -X POST https://api.runpod.ai/v2/$ENDPOINT_ID/run \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Xin chào Việt Nam",
      "ref_name": "main.wav",
      "speed": 0.9
    }
  }'
```

### 4. Check Job Status

```bash
# Get job ID from step 3 response
curl https://api.runpod.ai/v2/$ENDPOINT_ID/status/YOUR_JOB_ID \
  -H "Authorization: Bearer $RUNPOD_API_KEY"
```

---

## 📖 API Reference

### Input

```json
{
  "input": {
    "text": "Vietnamese text to synthesize",
    "ref_name": "main.wav",
    "speed": 0.9,
    "job_id": "optional_custom_id"
  }
}
```

**Parameters:**
- `text` (required): Vietnamese text to synthesize
- `ref_name` (optional): Voice sample file (default: `main.wav`)
- `speed` (optional): Speech speed 0.5-2.0 (default: 0.9)
- `job_id` (optional): Custom job identifier

### Output

```json
{
  "id": "job-id",
  "status": "COMPLETED",
  "output": {
    "audio_base64": "base64_encoded_wav_data",
    "filename": "output.wav",
    "sample_used": "main.wav",
    "processing_time_seconds": 3.5,
    "job_id": "job-id"
  }
}
```

**Status Values:**
- `IN_QUEUE` - Waiting for worker
- `IN_PROGRESS` - Processing
- `COMPLETED` - Success
- `FAILED` - Error occurred

---

## 🔄 Switching Between Modes

### Architecture

All modes use the **same Flask API**, just different ports and startup methods:

```
┌─────────────────────────────────────────┐
│         Flask TTS API Server            │
│  (flask_tts_api_optimized.py)          │
│                                         │
│  - /health      - Health check         │
│  - /voices      - List voices          │
│  - /tts         - Submit job (POST)    │
│  - /tts/progress - Check progress      │
│  - /output/:id  - Download audio       │
└─────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
    Port 7860      Port 8000      Port 8000
    (Local)        (Docker)       (RunPod+Handler)
```

### Quick Switch Guide

```bash
# Local Testing (7860)
cd /home/dtlong/F5-TTS-Vi
./start_local.sh
# → Edit .env: F5_TTS_API_URL=http://localhost:7860

# Docker Production (8000)
./start_docker_mode.sh
# OR
docker run -p 8000:8000 f5-tts-local
# → Edit .env: F5_TTS_API_URL=http://localhost:8000

# RunPod Serverless
# Push to Docker Hub, deploy on RunPod
# → Edit .env: Enable RunPod in orchestrator.ts
```

---

## 🛠️ Build & Deploy

### Local Build

```bash
cd /home/dtlong/F5-TTS-Vi

# Ensure scripts are executable
chmod +x entrypoint.sh start_local.sh start_docker_mode.sh test_api.sh

# 3. Build Docker image
docker build -f Dockerfile.optimized -t f5-tts-vi:optimized .

# 4. Test locally
docker run --gpus all -p 8000:8000 f5-tts-vi:optimized

# 5. Test health check
curl http://localhost:8000/health
```

### Push to Docker Hub

```bash
# 1. Tag image
docker tag f5-tts-vi:optimized YOUR_USERNAME/f5-tts-vi:optimized

# 2. Login to Docker Hub
docker login

# 3. Push image
docker push YOUR_USERNAME/f5-tts-vi:optimized
```

---

## 🔧 Local Development

### Run Flask API Only

```bash
# Install dependencies
pip install -r requirements.optimized.txt

# Start Flask API
python3 flask_tts_api_optimized.py

# API available at http://localhost:8000
```

### Test TTS Generation

```bash
# Submit job
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào",
    "ref_name": "main.wav",
    "speed": 0.9,
    "job_id": "test_123"
  }'

# Check progress
curl http://localhost:8000/tts/progress/test_123

# Download audio
curl http://localhost:8000/output/test_123.wav -o output.wav
```

---

## 📁 Project Structure

```
F5-TTS-Vi/
├── Dockerfile.optimized          # Production Docker build
├── entrypoint.sh                 # Container startup script
├── flask_tts_api_optimized.py    # Flask HTTP API server
├── runpod_handler_simple.py      # RunPod handler integration
├── requirements.optimized.txt    # Python dependencies
├── f5_tts/                       # F5-TTS source code
│   ├── model/                    # Model architecture
│   └── infer/                    # Inference code
└── sample/                       # Voice sample files
    ├── main.wav
    ├── female.wav
    └── male.wav
```

### File Descriptions

- **Dockerfile.optimized**: Multi-stage Docker build, optimized for size (27GB)
- **entrypoint.sh**: Starts Flask API, then RunPod handler
- **flask_tts_api_optimized.py**: HTTP server with endpoints: `/tts`, `/tts/progress/{id}`, `/output/{file}`, `/health`
- **runpod_handler_simple.py**: Orchestrates jobs between RunPod and Flask API
- **requirements.optimized.txt**: Minimal production dependencies

---

## 🔍 Architecture

```
┌─────────────────────────────────────────┐
│   RunPod Serverless Platform            │
│   ┌─────────────────────────────────┐   │
│   │  Worker Container               │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  Flask API (port 8000)   │   │   │
│   │  │  • /tts - Submit job     │   │   │
│   │  │  • /tts/progress/{id}    │   │   │
│   │  │  • /output/{file}        │   │   │
│   │  │  • /health               │   │   │
│   │  └──────────────────────────┘   │   │
│   │            ↕                     │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  F5-TTS Model (GPU)      │   │   │
│   │  │  • Model inference       │   │   │
│   │  │  • Audio synthesis       │   │   │
│   │  └──────────────────────────┘   │   │
│   │            ↕                     │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  RunPod Handler          │   │   │
│   │  │  • Job orchestration     │   │   │
│   │  │  • Base64 encoding       │   │   │
│   │  └──────────────────────────┘   │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Flow:**
1. Client sends job to RunPod API
2. RunPod handler receives job
3. Handler calls Flask API (localhost:8000)
4. Flask processes TTS with F5-TTS model
5. Handler polls for completion
6. Handler downloads audio, encodes base64
7. Handler returns result to RunPod
8. Client retrieves result via RunPod API

---

## 📊 Performance

- **Cold Start:** 30-60 seconds (first request after worker start)
- **Warm Processing:** 3-5 seconds per request
- **GPU Memory:** ~10GB VRAM
- **Image Size:** 27GB
- **Concurrent Jobs:** 1 per worker (GPU limitation)

---

## 🐛 Troubleshooting

### Job Stays IN_QUEUE

**Problem:** Job never processes

**Solutions:**
- Check worker availability in RunPod console
- Verify GPU is enabled in endpoint settings
- Ensure workers are not at max limit
- Check RunPod logs for startup errors

### Worker Fails to Start

**Problem:** Container crashes on initialization

**Solutions:**
- Ensure GPU has 12GB+ VRAM
- Verify Docker image exists: `tlong94/f5-tts-vi:optimized`
- Check RunPod logs for error messages
- Increase container disk size to 30GB+

### Audio Quality Issues

**Problem:** Generated audio sounds wrong

**Solutions:**
- Adjust `speed` parameter (try 0.7-1.0)
- Use different voice sample (`ref_name`)
- Ensure input text is clean Vietnamese
- Check for special characters or formatting

### Health Check Fails

**Problem:** `/health` endpoint returns error

**Solutions:**
- Wait 30-60 seconds for initialization
- Check Flask API logs in container
- Verify port 8000 is not blocked
- Restart worker in RunPod console

---

## 🔗 Integration Examples

### Python Client

```python
import requests
import base64
import json

class RunPodTTS:
    def __init__(self, api_key, endpoint_id):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    
    def submit_job(self, text, voice="main", speed=0.9):
        response = requests.post(
            f"{self.base_url}/run",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": {
                    "text": text,
                    "ref_name": f"{voice}.wav",
                    "speed": speed
                }
            }
        )
        return response.json()["id"]
    
    def get_status(self, job_id):
        response = requests.get(
            f"{self.base_url}/status/{job_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    def download_audio(self, job_id, output_file):
        import time
        while True:
            status = self.get_status(job_id)
            if status["status"] == "COMPLETED":
                audio_data = base64.b64decode(status["output"]["audio_base64"])
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                return True
            elif status["status"] == "FAILED":
                raise Exception("Job failed")
            time.sleep(2)

# Usage
client = RunPodTTS("your_api_key", "your_endpoint_id")
job_id = client.submit_job("Xin chào Việt Nam")
client.download_audio(job_id, "output.wav")
```

### Node.js/TypeScript Client

```typescript
interface RunPodInput {
  text: string;
  ref_name?: string;
  speed?: number;
}

class RunPodTTSClient {
  private apiKey: string;
  private endpointId: string;
  private baseUrl: string;

  constructor(apiKey: string, endpointId: string) {
    this.apiKey = apiKey;
    this.endpointId = endpointId;
    this.baseUrl = `https://api.runpod.ai/v2/${endpointId}`;
  }

  async submitJob(input: RunPodInput): Promise<string> {
    const response = await fetch(`${this.baseUrl}/run`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input: {
          text: input.text,
          ref_name: input.ref_name || 'main.wav',
          speed: input.speed || 0.9
        }
      })
    });
    const data = await response.json();
    return data.id;
  }

  async getStatus(jobId: string) {
    const response = await fetch(`${this.baseUrl}/status/${jobId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });
    return await response.json();
  }

  async waitForCompletion(jobId: string, timeout = 300000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const status = await this.getStatus(jobId);
      if (status.status === 'COMPLETED') return status.output;
      if (status.status === 'FAILED') throw new Error('Job failed');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    throw new Error('Timeout');
  }
}

// Usage
const client = new RunPodTTSClient('your_api_key', 'your_endpoint_id');
const jobId = await client.submitJob({ text: 'Xin chào' });
const output = await client.waitForCompletion(jobId);
const audioBuffer = Buffer.from(output.audio_base64, 'base64');
```

---

## 🎯 Production Best Practices

### RunPod Configuration

**Idle Timeout:** Set to **10 seconds**
- Keeps worker alive long enough for Next.js to download audio
- Worker terminates ~5-10s after returning COMPLETED status
- Must download within this window or get 404

**Polling Interval:** Next.js polls every **1 second**
- RunPod allows 2000 req/10s for `/status` endpoint
- Fast polling ensures catching COMPLETED before worker terminates
- Timeout set to 15s for download to prevent hanging

**Max Concurrent Jobs:** Configure in Admin UI (default: 4)
- Limits total active jobs (waiting + processing)
- Prevents overwhelming RunPod with too many workers
- Jobs queue as `pending` when limit reached

### Status Flow

```
pending → waiting → processing → completed/failed
   ↓         ↓          ↓            ↓
Created   Sent to   RunPod      Download
          RunPod    accepted    success/error
```

**Timeout:** 60 minutes per job
- Jobs stuck in `processing` > 60 min auto-marked `failed`
- Prevents zombie jobs consuming slots

### Error Handling

**Idempotency:** Handler tracks processed job IDs in memory
- Prevents duplicate processing if job sent to multiple workers
- Returns `status: "duplicate"` for already-processed jobs

**Download Fallback:** Handler supports both formats
- Primary: `download_url` (preferred, smaller response)
- Fallback: `audio_base64` (if download_url fails)

**Retry Logic:** Failed jobs rollback to `pending`
- Temporary errors (503, network issues) → Retry
- Permanent errors (invalid input) → Marked `failed`

### Monitoring

**Health Check:** Every 5 minutes
```bash
curl -f http://localhost:8000/health || exit 1
```

**Logs:** Check RunPod console for:
- Worker initialization errors
- Job processing failures  
- Memory/GPU issues

**Metrics:**
- Average processing time: 200-400 seconds
- GPU utilization: 80-95% during processing
- Memory usage: ~8-10GB per worker

---

## 🐛 Known Issues & Solutions

### Issue: "400 Bad Request" when returning job results

**Cause:** Response too large (base64 audio > 10MB)  
**Solution:** Switched to `download_url` instead of `audio_base64`

### Issue: One job triggers multiple workers

**Cause:** Race condition with fast polling (1s interval)  
**Solution:** Atomic lock - mark jobs as `waiting` before sending to RunPod

### Issue: Job marked `failed` but audio exists

**Cause:** Error after successful download overwrites `completed` status  
**Solution:** Check if job already `completed` before marking `failed`

### Issue: Download fails with 404

**Cause:** Worker terminated before Next.js downloaded audio  
**Solution:** Increased idle timeout to 10s + faster polling (1s)

---

## 📝 License

MIT License

## 🙏 Credits

- **F5-TTS:** [SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)
- **Vietnamese Model:** ViVoice Dataset (100h training data)
- **Platform:** [RunPod](https://runpod.io) Serverless GPU
- **Model Weights:** [hynt/F5-TTS-Vietnamese-ViVoice](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice)

---

## 📚 Related Projects

- **Next.js Frontend:** [Starter-Prisma-Pro](../Starter-Prisma-Pro)
- **Docker Hub:** [tlong94/f5-tts-vi](https://hub.docker.com/r/tlong94/f5-tts-vi)
- **GitHub:** [ynmaster-tl/F5-TTS-Vi](https://github.com/ynmaster-tl/F5-TTS-Vi)

---

**Last Updated:** November 18, 2025  
**Version:** 2.0.0 - Production Stable  
**Status:** ✅ Deployed on RunPod Serverless
