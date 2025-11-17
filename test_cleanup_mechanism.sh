#!/bin/bash

echo "=== Testing Cleanup Mechanism ==="
echo ""
echo "Progress files before:"
ls -1 output/progress_*.json 2>/dev/null | wc -l

# Pick a random progress file
PROGRESS_FILE=$(ls output/progress_*.json 2>/dev/null | head -1)
if [ -n "$PROGRESS_FILE" ]; then
    echo "Sample progress file: $PROGRESS_FILE"
    cat "$PROGRESS_FILE"
    echo ""
    
    # Extract filename from progress JSON
    AUDIO_FILE=$(cat "$PROGRESS_FILE" | grep -o '"filename":[^,}]*' | cut -d'"' -f4)
    echo "Associated audio: $AUDIO_FILE"
    
    if [ -n "$AUDIO_FILE" ]; then
        # Test cleanup API
        echo "Testing cleanup..."
        curl -X DELETE "http://localhost:7860/tts/cleanup-file/$AUDIO_FILE"
        echo ""
    fi
fi

echo ""
echo "Progress files after:"
ls -1 output/progress_*.json 2>/dev/null | wc -l
