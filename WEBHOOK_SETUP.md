# Webhook Setup Guide

## Overview
Webhook mechanism ensures audio files are downloaded before RunPod pod shuts down.

## Architecture

```
RunPod Handler (TTS complete)
    ↓
Send webhook → Next.js /api/runpod-webhook
    ↓
Download audio immediately
    ↓
Save to disk + Update DB
    ↓
Send confirmation → Handler /confirm-download
    ↓
Handler receives confirmation → Return COMPLETED
    ↓
Pod shutdown (safe - audio already downloaded)
```

## Setup Steps

### 1. RunPod Environment Variables

Add to your RunPod template:

```bash
NEXTJS_WEBHOOK_URL=https://tts.n8nvn.io.vn/api/runpod-webhook
DOWNLOAD_CONFIRMATION_TIMEOUT=60
```

**Example for your domain:**
```bash
# Production
NEXTJS_WEBHOOK_URL=https://tts.n8nvn.io.vn/api/runpod-webhook

# Local testing with ngrok
NEXTJS_WEBHOOK_URL=https://abc123.ngrok.io/api/runpod-webhook
```

**Important:**
- Use your **production domain** (not localhost)
- Webhook URL must be publicly accessible
- Timeout is in seconds (60s recommended)

### 2. Next.js Webhook Endpoint

File already created at: `src/pages/api/runpod-webhook.ts`

**What it does:**
- Receives job completion notification
- Downloads audio from RunPod
- Saves to `public/audio-outputs/`
- Updates database
- Sends confirmation back to RunPod

### 3. Test Webhook

**Local Testing:**
```bash
# Use ngrok to expose local webhook
ngrok http 3000

# Set webhook URL in RunPod
NEXTJS_WEBHOOK_URL=https://abc123.ngrok.io/api/runpod-webhook
```

**Test Request:**
```bash
curl -X POST https://tts.n8nvn.io.vn/api/runpod-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_123",
    "download_url": "https://pod-id-8000.proxy.runpod.net/output/test.wav",
    "confirmation_url": "https://pod-id-8000.proxy.runpod.net/confirm-download/test_123",
    "filename": "test.wav"
  }'
```

Expected response:
```json
{
  "success": true,
  "job_id": "test_123",
  "audioUrl": "/audio-outputs/test.wav"
}
```

## How It Works

### 1. Handler Sends Webhook

When TTS completes, handler sends:
```python
requests.post(
    webhook_url,
    json={
        "job_id": job_id,
        "download_url": download_url,
        "confirmation_url": confirmation_url,
        "filename": filename,
    },
    timeout=5
)
```

### 2. Next.js Downloads Audio

Webhook endpoint:
```typescript
// Download from RunPod
const response = await axios.get(download_url, {
  responseType: 'arraybuffer',
  timeout: 60000,
});

// Save to disk
await fs.writeFile(localPath, response.data);

// Update DB
await prisma.audioJob.update({
  where: { id: job_id },
  data: { status: 'completed', audioUrl: publicUrl }
});
```

### 3. Send Confirmation

```typescript
await axios.post(confirmation_url, {
  job_id: job_id,
  status: 'downloaded',
  timestamp: Date.now(),
});
```

### 4. Handler Waits

```python
# Wait for confirmation (max 60s)
for i in range(60):
    check = requests.get(f"http://localhost:8000/check-download/{job_id}")
    if check.json().get("confirmed"):
        break
    time.sleep(1)

# Now safe to return COMPLETED
return {"status": "completed", ...}
```

## Troubleshooting

### Webhook Not Received

**Check:**
1. `NEXTJS_WEBHOOK_URL` is set correctly in RunPod
2. URL is publicly accessible (not localhost)
3. Next.js server is running
4. No firewall blocking requests

**Logs to check:**
- RunPod: `[RunPod Handler] 📤 Sending webhook...`
- Next.js: `[Webhook] 📥 Received notification for job...`

### Download Fails

**Check:**
1. RunPod pod is still alive when webhook sent
2. Download URL is valid
3. Network connectivity between Next.js and RunPod
4. Timeout (60s) is sufficient for file size

**Error:** `ECONNREFUSED`
- Pod already shutdown → Handler returned too early
- Should not happen with webhook (handler waits)

### Confirmation Timeout

**If handler logs:** `⚠️ No confirmation after 60s`

**Possible causes:**
1. Next.js webhook failed to download
2. Confirmation URL incorrect
3. Network issue

**Solution:**
- Check Next.js logs for errors
- Increase timeout if needed
- Verify confirmation URL format

## Monitoring

### Handler Logs
```
[RunPod Handler] ✅ TTS completed in 114.58s
[RunPod Handler] 📤 Sending webhook to Next.js...
[RunPod Handler] ✅ Webhook sent successfully
[RunPod Handler] ⏳ Waiting for download confirmation (max 60s)...
[RunPod Handler] ✅ Download confirmed after 6.2s!
```

### Next.js Logs
```
[Webhook] 📥 Received notification for job_xxx
[Webhook] 📥 Downloading audio for job_xxx...
[Webhook] ✅ Saved audio to /public/audio-outputs/...
[Webhook] ✅ Job marked as completed in DB
[Webhook] 📤 Sending confirmation to RunPod...
[Webhook] ✅ Confirmation sent to RunPod
```

## Performance

**Typical timing:**
- Webhook sent: ~0.5s after TTS complete
- Download: 1-5s (depends on file size)
- Confirmation received: Total 2-10s
- Handler waits: Only actual download time (not 90s)

**Benefits:**
- Fast: Instant notification vs 2s polling
- Reliable: No race condition
- Efficient: Pod shutdown only after download complete
- Handler waits: Only actual download time (not 60s)
