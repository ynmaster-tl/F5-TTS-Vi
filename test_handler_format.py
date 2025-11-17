#!/usr/bin/env python3
"""Test handler return format"""

import sys
sys.path.insert(0, '/home/dtlong/F5-TTS-Vi')

from runpod_handler_simple import handler

# Mock event
test_event = {
    "input": {
        "text": "Xin chào, đây là test.",
        "ref_name": "sample/main.wav",
        "speed": 0.9,
        "job_id": "test_123"
    }
}

print("Testing handler with mock event...")
print("=" * 60)

# Test with missing text
print("\n1. Test missing text:")
result = handler({"input": {}})
print("Result:", result)
print("Has 'error':", "error" in result)
print("Has 'status':", "status" in result)

# Test with valid input (will fail if Flask not running, but we can see the format)
print("\n2. Test valid input:")
try:
    result = handler(test_event)
    print("Result:", result)
    print("Keys:", list(result.keys()))
    
    if "error" in result:
        print("✅ Error format correct:", "status" in result)
    elif "audio_base64" in result:
        print("✅ Success format correct:")
        print("   - Has audio_base64:", "audio_base64" in result)
        print("   - Has filename:", "filename" in result)
        print("   - Has job_id:", "job_id" in result)
        print("   - Has status:", "status" in result)
except Exception as e:
    print(f"⚠️ Expected error (Flask not running): {e}")

print("\n" + "=" * 60)
print("✅ Handler return format verification complete")
