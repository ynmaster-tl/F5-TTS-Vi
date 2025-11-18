#!/bin/bash
# Quick commands for F5-TTS deployment

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================"
echo "F5-TTS Quick Commands"
echo -e "========================================${NC}"
echo ""

# Check if container is running
if docker ps | grep -q f5-tts-api; then
    echo -e "${GREEN}✅ Container is running${NC}"
    CONTAINER_NAME="f5-tts-api"
elif docker ps | grep -q f5-tts-runpod; then
    echo -e "${GREEN}✅ Container is running${NC}"
    CONTAINER_NAME="f5-tts-runpod"
else
    echo -e "${RED}❌ Container is not running${NC}"
    CONTAINER_NAME=""
fi

echo ""
echo "Available commands:"
echo ""
echo "1. Start container:"
echo "   ./quick-commands.sh start"
echo ""
echo "2. Stop container:"
echo "   ./quick-commands.sh stop"
echo ""
echo "3. Restart container:"
echo "   ./quick-commands.sh restart"
echo ""
echo "4. View logs:"
echo "   ./quick-commands.sh logs"
echo ""
echo "5. Check health:"
echo "   ./quick-commands.sh health"
echo ""
echo "6. Submit test job:"
echo "   ./quick-commands.sh test"
echo ""
echo "7. GPU status:"
echo "   ./quick-commands.sh gpu"
echo ""
echo "8. Clean old containers:"
echo "   ./quick-commands.sh clean"
echo ""
echo "9. Update image:"
echo "   ./quick-commands.sh update"
echo ""

# Execute command if provided
case "$1" in
    start)
        echo -e "${YELLOW}Starting F5-TTS container...${NC}"
        docker run -d \
          --name f5-tts-api \
          --gpus all \
          -p 8000:8000 \
          -v ~/f5-tts-data/sample:/app/sample \
          -v ~/f5-tts-data/output:/app/output \
          -e RUNPOD_MODE=false \
          --restart unless-stopped \
          tlong94/f5-tts-vi:optimized
        echo -e "${GREEN}✅ Container started${NC}"
        echo "Waiting for health check..."
        sleep 30
        curl -s http://localhost:8000/health | jq '.'
        ;;
        
    stop)
        if [ -n "$CONTAINER_NAME" ]; then
            echo -e "${YELLOW}Stopping container...${NC}"
            docker stop $CONTAINER_NAME
            echo -e "${GREEN}✅ Container stopped${NC}"
        else
            echo -e "${RED}No container running${NC}"
        fi
        ;;
        
    restart)
        if [ -n "$CONTAINER_NAME" ]; then
            echo -e "${YELLOW}Restarting container...${NC}"
            docker restart $CONTAINER_NAME
            echo -e "${GREEN}✅ Container restarted${NC}"
            echo "Waiting for health check..."
            sleep 30
            curl -s http://localhost:8000/health | jq '.'
        else
            echo -e "${RED}No container running${NC}"
        fi
        ;;
        
    logs)
        if [ -n "$CONTAINER_NAME" ]; then
            docker logs -f $CONTAINER_NAME
        else
            echo -e "${RED}No container running${NC}"
        fi
        ;;
        
    health)
        echo -e "${YELLOW}Checking health...${NC}"
        RESPONSE=$(curl -s http://localhost:8000/health)
        if echo "$RESPONSE" | jq -e '.status == "ok"' > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is healthy${NC}"
            echo "$RESPONSE" | jq '.'
        else
            echo -e "${RED}❌ API is not responding${NC}"
            echo "$RESPONSE"
        fi
        ;;
        
    test)
        echo -e "${YELLOW}Submitting test job...${NC}"
        JOB_ID="test_$(date +%s)"
        RESPONSE=$(curl -s -X POST http://localhost:8000/tts \
          -H "Content-Type: application/json" \
          -d "{
            \"text\": \"Xin chào, đây là bản kiểm tra hệ thống.\",
            \"ref_name\": \"main.wav\",
            \"speed\": 0.9,
            \"job_id\": \"$JOB_ID\"
          }")
        
        if echo "$RESPONSE" | grep -q "accepted"; then
            echo -e "${GREEN}✅ Job submitted: $JOB_ID${NC}"
            echo "Checking progress..."
            sleep 5
            curl -s http://localhost:8000/tts/progress/$JOB_ID | jq '.'
            echo ""
            echo "To check progress:"
            echo "  curl http://localhost:8000/tts/progress/$JOB_ID"
            echo "To download when completed:"
            echo "  curl http://localhost:8000/output/${JOB_ID}.wav -o test.wav"
        else
            echo -e "${RED}❌ Job submission failed${NC}"
            echo "$RESPONSE"
        fi
        ;;
        
    gpu)
        echo -e "${YELLOW}GPU Status:${NC}"
        nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader
        ;;
        
    clean)
        echo -e "${YELLOW}Cleaning old containers...${NC}"
        docker container prune -f
        echo -e "${GREEN}✅ Cleaned${NC}"
        ;;
        
    update)
        echo -e "${YELLOW}Updating to latest image...${NC}"
        if [ -n "$CONTAINER_NAME" ]; then
            echo "Stopping current container..."
            docker stop $CONTAINER_NAME
            docker rm $CONTAINER_NAME
        fi
        echo "Pulling latest image..."
        docker pull tlong94/f5-tts-vi:optimized
        echo "Starting new container..."
        docker run -d \
          --name f5-tts-api \
          --gpus all \
          -p 8000:8000 \
          -v ~/f5-tts-data/sample:/app/sample \
          -v ~/f5-tts-data/output:/app/output \
          -e RUNPOD_MODE=false \
          --restart unless-stopped \
          tlong94/f5-tts-vi:optimized
        echo -e "${GREEN}✅ Updated to latest version${NC}"
        ;;
        
    *)
        if [ -n "$1" ]; then
            echo -e "${RED}Unknown command: $1${NC}"
        fi
        ;;
esac
