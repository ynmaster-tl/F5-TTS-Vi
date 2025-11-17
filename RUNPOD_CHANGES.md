# RunPod Implementation - Changes Summary

## ✅ Changes Made Based on Official RunPod Documentation

### 1. **Request Format** (Already Correct ✓)
```typescript
// Using /run async endpoint
POST https://api.runpod.ai/v2/{endpoint_id}/run
Body: {
  "input": {
    "text": "...",
    "ref_name": "sample/narrator.wav",
    "speed": 0.9,
    "job_id": "..."
  }
}
```

### 2. **Handler Return Format** (✨ IMPROVED)

**Before:**
```python
# Raised exceptions on error
raise Exception("Error message")
```

**After:**
```python
# Returns proper error format
return {
  "error": "error_code",
  "message": "Error description"
}

# Success format
return {
  "status": "completed",
  "audio_base64": "...",
  "filename": "...",
  "processing_time_seconds": 3.5,
  "job_id": "..."
}
```

### 3. **Error Handling** (✨ IMPROVED)

**Handler now returns errors instead of raising:**
- `{"error": "Server busy"}` - When Flask API busy (503)
- `{"error": "flask_api_error"}` - When Flask returns error
- `{"error": "tts_failed"}` - When TTS processing fails
- `{"error": "timeout"}` - When job exceeds max_wait (10 min)
- `{"error": "handler_exception"}` - Unexpected errors

**Orchestrator now handles both formats:**
```typescript
if (status.output.status === 'completed' && status.output.audio_base64) {
  // Process success
} else if (status.output.error) {
  // Handle error from handler
}
```

### 4. **Voice File Path** (✨ FIXED)

**Before:**
```typescript
ref_name: `${voiceId}.wav`  // Missing folder prefix
```

**After:**
```typescript
ref_name: `sample/${voiceId}.wav`  // Correct path with folder
```

### 5. **Progress Cleanup** (✨ ADDED)

Handler now cleans up progress file after completion:
```python
try:
    requests.delete(f"http://localhost:8000/tts/progress/{job_id}", timeout=2)
except:
    pass
```

### 6. **TypeScript Interfaces** (✨ UPDATED)

```typescript
export interface RunPodJobResponse {
  id: string;
  status: string;
  output?: {
    status?: string;           // ✨ NEW: Handler status
    audio_base64?: string;     // ✨ NEW: Base64 audio
    filename?: string;
    sample_used?: string;
    processing_time_seconds?: number;
    job_id?: string;
    error?: string;            // ✨ NEW: Error code
    message?: string;          // ✨ NEW: Error message
  };
  error?: string;
}
```

## 📋 Testing Checklist

Before deploying to RunPod:

- [ ] Test local Flask API on port 7860
- [ ] Test Docker container on port 8000
- [ ] Build Docker image: `docker build -t f5-tts-vi:optimized -f Dockerfile.optimized .`
- [ ] Test Docker image locally
- [ ] Push to Docker Hub: `docker push tlong94/f5-tts-vi:optimized`
- [ ] Create RunPod endpoint with correct image
- [ ] Test RunPod `/health` endpoint
- [ ] Submit test job via RunPod
- [ ] Verify base64 audio in response
- [ ] Test error scenarios (busy, timeout, invalid input)

## 🔧 Configuration

### Environment Variables:

**Local/Docker:**
```env
FLASK_PORT=7860  # or 8000
FLASK_HOST=0.0.0.0
REF_VOICE_DIR=./sample
OUTPUT_AUDIO_DIR=./output
```

**Next.js (.env):**
```env
# For local/Docker
F5_TTS_API_URL=http://localhost:7860

# For RunPod
RUNPOD_API_KEY=rpa_xxxxx
RUNPOD_ENDPOINT_ID=xxxxx
MAX_CONCURRENT_JOBS=6
```

## 🚀 Deployment Commands

### Build & Push to Docker Hub:
```bash
cd /home/dtlong/F5-TTS-Vi

# Build
docker build -t tlong94/f5-tts-vi:optimized -f Dockerfile.optimized .

# Test locally
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/sample:/app/sample \
  -v $(pwd)/output:/app/output \
  tlong94/f5-tts-vi:optimized

# Push
docker push tlong94/f5-tts-vi:optimized
```

### RunPod Endpoint Settings:
- **Container Image:** `tlong94/f5-tts-vi:optimized`
- **GPU:** RTX 3090/4090 (12GB+ VRAM)
- **Container Disk:** 30GB
- **Workers:** Min 0, Max 3
- **Execution Timeout:** 600000ms (10 min)

## 📝 Key Differences from Previous Version

| Aspect | Before | After |
|--------|--------|-------|
| Error Handling | Raised exceptions | Returns error objects |
| Return Format | Inconsistent | Standardized with `status` field |
| Voice Path | `narrator.wav` | `sample/narrator.wav` |
| Progress Cleanup | Not cleaned | Auto-cleanup after completion |
| TypeScript Types | Incomplete | Full interface with all fields |

## ✅ No Rebuild Needed If:

- ✅ Only changed orchestrator.ts (TypeScript)
- ✅ Only changed runpodClient.ts (TypeScript)
- ✅ Only changed .env configuration

## 🔄 Rebuild Required If:

- ❌ Changed flask_tts_api_optimized.py
- ❌ Changed runpod_handler_simple.py
- ❌ Changed Dockerfile.optimized
- ❌ Changed requirements.optimized.txt
- ❌ Changed entrypoint.sh

**Current status: Need rebuild because we changed `runpod_handler_simple.py`**

## 🎯 Next Steps

1. Test locally with `./start_local.sh`
2. Build new Docker image
3. Test Docker locally
4. Push to Docker Hub
5. Update RunPod endpoint (or wait for auto-pull)
6. Test full flow from Next.js UI

## 📚 References

- [RunPod Send Requests Documentation](https://docs.runpod.io/serverless/endpoints/send-requests)
- Flask API: http://localhost:7860 or http://localhost:8000
- RunPod API: https://api.runpod.ai/v2/{endpoint_id}
