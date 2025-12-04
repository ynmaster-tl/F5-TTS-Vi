#!/usr/bin/env python3
"""
Test script for download confirmation flow
Simulates: Job submit → Process → Complete → Wait for confirmation
"""

import requests
import time
import json

BASE_URL = "http://localhost:7860"

def test_confirmation_flow():
    print("=" * 60)
    print("Testing Download Confirmation Flow")
    print("=" * 60)
    
    # Step 1: Submit a small TTS job
    print("\n[Step 1] Submitting TTS job...")
    job_id = f"test_conf_{int(time.time())}"
    
    tts_payload = {
        "text": "Xin chào",
        "ref_name": "3_Nam.wav",
        "speed": 0.9,
        "job_id": job_id
    }
    
    response = requests.post(f"{BASE_URL}/tts", json=tts_payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 202:
        print("❌ Failed to submit job")
        return False
    
    # Step 2: Poll for completion
    print(f"\n[Step 2] Polling job {job_id} for completion...")
    max_wait = 120  # 2 minutes max
    start = time.time()
    
    while time.time() - start < max_wait:
        time.sleep(2)
        
        prog_resp = requests.get(f"{BASE_URL}/tts/progress/{job_id}")
        if prog_resp.status_code != 200:
            continue
        
        data = prog_resp.json()
        progress = data.get("progress", 0)
        status = data.get("status", "unknown")
        
        print(f"  Progress: {progress}% - {status}")
        
        if progress == 100 and status == "completed":
            print("✅ Job completed!")
            filename = data.get("filename")
            print(f"  Filename: {filename}")
            break
        
        if progress == -1 or status == "failed":
            print(f"❌ Job failed: {data.get('extra')}")
            return False
    else:
        print("❌ Job timeout")
        return False
    
    # Step 3: Check confirmation status BEFORE confirming
    print(f"\n[Step 3] Check confirmation status (should be False)...")
    check_resp = requests.get(f"{BASE_URL}/check-download/{job_id}")
    check_data = check_resp.json()
    print(f"  Confirmed: {check_data.get('confirmed')}")
    
    if check_data.get('confirmed'):
        print("❌ Already confirmed (unexpected)")
        return False
    
    # Step 4: Simulate Next.js downloading file (wait 2s)
    print(f"\n[Step 4] Simulating download (2 seconds)...")
    time.sleep(2)
    
    # Step 5: Send confirmation
    print(f"\n[Step 5] Sending download confirmation...")
    conf_resp = requests.post(
        f"{BASE_URL}/confirm-download/{job_id}",
        json={"job_id": job_id, "status": "downloaded"}
    )
    conf_data = conf_resp.json()
    print(f"  Status: {conf_data.get('status')}")
    print(f"  Response: {conf_data}")
    
    if conf_data.get('status') != 'confirmed':
        print("❌ Confirmation failed")
        return False
    
    # Step 6: Verify confirmation
    print(f"\n[Step 6] Verify confirmation (should be True)...")
    check_resp2 = requests.get(f"{BASE_URL}/check-download/{job_id}")
    check_data2 = check_resp2.json()
    print(f"  Confirmed: {check_data2.get('confirmed')}")
    
    if not check_data2.get('confirmed'):
        print("❌ Not confirmed after confirmation")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_confirmation_flow()
    exit(0 if success else 1)
