#!/bin/bash
# Quick deployment guide for F5-TTS-Vi

cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║         F5-TTS Vietnamese - Deployment Guide                 ║
║         One Codebase, Three Deployment Modes                 ║
╚══════════════════════════════════════════════════════════════╝

📋 AVAILABLE MODES:

┌──────────────────────────────────────────────────────────────┐
│ MODE 1: Local Testing (Port 7860)                           │
│ Best for: Quick testing, development                         │
├──────────────────────────────────────────────────────────────┤
│ Start:  ./start_local.sh                                     │
│ Test:   ./test_api.sh 7860                                   │
│ Config: F5_TTS_API_URL=http://localhost:7860                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ MODE 2: Docker Production (Port 8000)                        │
│ Best for: Production on your own server                      │
├──────────────────────────────────────────────────────────────┤
│ Build:  docker build -t f5-tts-api:latest -f Dockerfile.optimized --network=host . │
│ Run:    docker run -d --name f5-tts-api \
            --gpus all \
            -p 8000:8000 \
            -v $(pwd)/sample:/workspace/sample \
            -v $(pwd)/output:/workspace/output \
            --restart unless-stopped \
              f5-tts-api:latest                             
│ Test:   ./test_api.sh 8000                                   │
│ Config: F5_TTS_API_URL=http://localhost:8000                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ MODE 3: RunPod Serverless (Cloud)                           │
│ Best for: Scalable cloud deployment, pay-per-use            │
├──────────────────────────────────────────────────────────────┤
│ 1. Push to Docker Hub:                                       │
│    docker tag f5-tts-api tlong94/f5-tts-vi:optimized      │
│    docker push tlong94/f5-tts-vi:optimized                  │
│                                                              │
│ 2. Create RunPod Endpoint:                                   │
│    - Image: tlong94/f5-tts-vi:optimized                     │
│    - GPU: RTX 3090/4090 (12GB+)                             │
│    - Workers: Min 0, Max 3+ (scale as needed)               │
│    - Note: Max workers can be 10, 50, 100+ depending on    │
│      your traffic and budget. Start with 3 for testing.    │
│                                                              │
│ 3. Configure Next.js:                                        │
│    RUNPOD_API_KEY=your_key                                   │
│    RUNPOD_ENDPOINT_ID=your_endpoint_id                       │
└──────────────────────────────────────────────────────────────┘

🔧 QUICK SETUP:

1. Start API (choose one):
   ./start_local.sh              # Port 7860 (testing)
   ./start_docker_mode.sh        # Port 8000 (production)

2. Test API:
   ./test_api.sh 7860            # Test local
   ./test_api.sh 8000            # Test docker

3. Update Next.js config:
   cd /home/dtlong/Starter-Prisma-Pro
   
   # For local/docker (edit .env):
   F5_TTS_API_URL=http://localhost:7860  # or 8000
   
   # For RunPod (edit .env):
   RUNPOD_API_KEY=rpa_xxxxx
   RUNPOD_ENDPOINT_ID=xxxxx

4. Restart Next.js:
   npm run dev

📝 ARCHITECTURE:

All modes share the same Flask API (flask_tts_api_optimized.py):
- Handles TTS processing
- Single job queue
- Progress tracking
- GPU optimization

Differences:
- Local/Docker: Direct API calls
- RunPod: API + Handler wrapper (returns base64 audio)

🎯 RECOMMENDED WORKFLOW:

Development:
  1. Use MODE 1 (port 7860) for quick testing
  2. Test changes with ./test_api.sh 7860

Production (Own Server):
  1. Build Docker image
  2. Run on port 8000
  3. Deploy to production server

Production (Cloud):
  1. Push to Docker Hub
  2. Deploy on RunPod
  3. Enable RunPod in orchestrator

📚 FULL DOCUMENTATION: README.md

EOF
