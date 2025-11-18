#!/bin/bash
# Build and push F5-TTS Docker image
# Usage: ./build_and_push.sh [tag_version]

set -e

# Configuration
DOCKER_USERNAME="tlong94"
IMAGE_NAME="f5-tts-vi"
TAG_VERSION="${1:-latest}"
FULL_TAG="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG_VERSION}"

echo "========================================"
echo "Building F5-TTS Docker Image"
echo "========================================"
echo "Image: $FULL_TAG"
echo "Base: nvidia/cuda:11.8.0-cudnn8"
echo "Size: ~27GB (optimized)"
echo ""

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username: ${DOCKER_USERNAME}"; then
    echo "⚠️  Not logged in to Docker Hub"
    echo "Running: docker login"
    docker login
fi

# Build image
echo ""
echo "Step 1: Building Docker image..."
echo "This will take 10-15 minutes..."
docker build \
    -f Dockerfile.optimized \
    -t ${FULL_TAG} \
    -t ${DOCKER_USERNAME}/${IMAGE_NAME}:latest \
    .

echo ""
echo "✅ Build completed!"
echo ""
echo "Image info:"
docker images ${DOCKER_USERNAME}/${IMAGE_NAME}

# Test image locally
echo ""
echo "========================================"
echo "Testing image locally..."
echo "========================================"
echo "Running health check test..."

# Start container for testing
CONTAINER_ID=$(docker run -d --rm \
    --gpus all \
    -p 8000:8000 \
    --name f5-tts-test \
    ${FULL_TAG})

echo "Container started: $CONTAINER_ID"
echo "Waiting for API to be ready (max 5 minutes)..."

# Wait for health check
for i in {1..60}; do
    if docker ps | grep -q f5-tts-test; then
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Health check passed!"
            break
        fi
    else
        echo "❌ Container stopped unexpectedly"
        docker logs f5-tts-test
        exit 1
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ Health check timeout"
        docker logs f5-tts-test
        docker stop f5-tts-test
        exit 1
    fi
    
    echo "  Waiting... ($i/60)"
    sleep 5
done

# Test TTS endpoint
echo ""
echo "Testing TTS endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8000/tts \
    -H "Content-Type: application/json" \
    -d '{
        "text": "Test Docker image",
        "ref_name": "main.wav",
        "speed": 0.9,
        "job_id": "docker_test"
    }')

if echo "$RESPONSE" | grep -q "accepted"; then
    echo "✅ TTS endpoint working!"
else
    echo "❌ TTS endpoint failed"
    echo "$RESPONSE"
    docker stop f5-tts-test
    exit 1
fi

# Stop test container
echo ""
echo "Stopping test container..."
docker stop f5-tts-test

echo ""
echo "✅ All tests passed!"

# Push to Docker Hub
echo ""
echo "========================================"
echo "Pushing to Docker Hub..."
echo "========================================"
echo "This will take 10-20 minutes (27GB upload)..."
echo ""

# Push both tags
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG_VERSION}
if [ "$TAG_VERSION" != "latest" ]; then
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
fi

echo ""
echo "✅ Push completed!"
echo ""
echo "========================================"
echo "Deployment URLs:"
echo "========================================"
echo "Docker Hub: https://hub.docker.com/r/${DOCKER_USERNAME}/${IMAGE_NAME}"
echo "Pull command: docker pull ${FULL_TAG}"
echo ""
echo "To deploy on another machine:"
echo "  docker pull ${FULL_TAG}"
echo "  docker run -d --gpus all -p 8000:8000 ${FULL_TAG}"
echo ""
echo "To deploy on RunPod:"
echo "  1. Go to RunPod Console"
echo "  2. Update endpoint with image: ${FULL_TAG}"
echo "  3. RunPod will auto-pull new image"
echo ""
echo "✅ Done!"
