#!/bin/bash
# Push F5-TTS-Vi image to Docker Hub

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Push F5-TTS-Vi to Docker Hub                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
LOCAL_IMAGE="f5-tts-api:latest"
DOCKER_HUB_USER="tlong94"
DOCKER_HUB_REPO="f5-tts-vi"
TAG="latest"

echo "📦 Local image:  $LOCAL_IMAGE"
echo "🚀 Target:       $DOCKER_HUB_USER/$DOCKER_HUB_REPO:$TAG"
echo ""

# Check if local image exists
if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${LOCAL_IMAGE}$"; then
    echo "❌ Error: Local image $LOCAL_IMAGE not found"
    echo ""
    echo "Available images:"
    docker images | grep -E "f5-tts|REPOSITORY"
    echo ""
    echo "Please build it first: docker build -t $LOCAL_IMAGE -f Dockerfile.optimized ."
    exit 1
fi

echo "✅ Local image found"

# Login to Docker Hub (if not already logged in)
echo "🔐 Checking Docker Hub authentication..."
if ! docker info | grep -q "Username"; then
    echo "Please login to Docker Hub:"
    docker login
else
    echo "✅ Already logged in to Docker Hub"
fi

echo ""
echo "🏷️  Tagging image..."
docker tag $LOCAL_IMAGE $DOCKER_HUB_USER/$DOCKER_HUB_REPO:$TAG

echo "📤 Pushing to Docker Hub..."
docker push $DOCKER_HUB_USER/$DOCKER_HUB_REPO:$TAG

echo ""
echo "✅ Successfully pushed!"
echo ""
echo "Image URL: $DOCKER_HUB_USER/$DOCKER_HUB_REPO:$TAG"
echo ""
echo "Next steps:"
echo "1. Go to RunPod: https://www.runpod.io/console/serverless"
echo "2. Create new endpoint"
echo "3. Use image: $DOCKER_HUB_USER/$DOCKER_HUB_REPO:$TAG"
echo "4. Set GPU: RTX 3090/4090 (12GB+)"
echo "5. Workers: Min 0, Max 3+"
echo ""
