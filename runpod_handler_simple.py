#!/usr/bin/env python3
"""
RunPod Handler for F5-TTS - SIMPLIFIED VERSION
Flask API runs separately, handler just orchestrates
Updated: 2025-11-18 - Added idempotency and download_url support
"""

import os
import json
import time
import requests
import base64
import runpod

# Track processed jobs (in-memory for this worker)
processed_jobs = set()

def handler(event):
    """
    RunPod handler - calls Flask API running on localhost:8000
    
    Input: {"input": {"text": "...", "ref_name": "sample/narrator.wav", "speed": 0.9, "job_id": "..."}}
    Output: {"audio_base64": "...", "filename": "...", "status": "completed"}
    """
    try:
        print("[RunPod Handler] Received:", json.dumps(event.get("input", {}), indent=2))
        
        input_data = event.get("input", {})
        text = input_data.get("text")
        ref_name = input_data.get("ref_name", "sample/main.wav")
        speed = input_data.get("speed", 0.9)
        job_id = input_data.get("job_id", f"runpod_{int(time.time())}")
        
        # Idempotency check - if this worker already processed this job, return cached result
        if job_id in processed_jobs:
            print(f"[RunPod Handler] ⚠️ Job {job_id} already processed by this worker, skipping")
            return {
                "error": "Job already processed by this worker",
                "status": "duplicate",
                "job_id": job_id
            }
        
        if not text:
            return {
                "error": "Missing 'text' in input",
                "status": "failed"
            }
        
        print(f"[RunPod Handler] Job {job_id}: {len(text)} chars")
        start_time = time.time()
        
        # Submit to Flask API
        print("[RunPod Handler] Submitting to Flask API...")
        response = requests.post(
            "http://localhost:8000/tts",
            json={
                "text": text,
                "ref_name": ref_name,
                "speed": speed,
                "job_id": job_id
            },
            timeout=10
        )
        
        if response.status_code == 503:
            return {
                "error": "Flask API is processing another job",
                "status": "failed",
                "job_id": job_id
            }
        
        if response.status_code != 202:
            return {
                "error": f"Flask API error: {response.text}",
                "status_code": response.status_code,
                "status": "failed",
                "job_id": job_id
            }
        
        print(f"[RunPod Handler] Job accepted, polling for completion...")
        
        # Poll for completion
        max_wait = 600  # 10 minutes
        poll_interval = 2
        
        while time.time() - start_time < max_wait:
            time.sleep(poll_interval)
            
            try:
                prog_resp = requests.get(f"http://localhost:8000/tts/progress/{job_id}", timeout=5)
                if prog_resp.status_code != 200:
                    continue
                
                progress_data = prog_resp.json()
                progress = progress_data.get("progress", 0)
                status = progress_data.get("status", "unknown")
                
                print(f"[RunPod Handler] Progress: {progress}% - {status}")
                
                if progress == 100 and status == "completed":
                    # Get filename
                    filename = progress_data.get("filename", f"{job_id}.wav")
                    
                    # Generate public URL (RunPod pod URL)
                    # Format: https://{pod_id}-8000.proxy.runpod.net/output/{filename}
                    pod_id = os.getenv('RUNPOD_POD_ID', 'localhost')
                    if pod_id != 'localhost':
                        download_url = f"https://{pod_id}-8000.proxy.runpod.net/output/{filename}"
                    else:
                        download_url = f"http://localhost:8000/output/{filename}"
                    
                    print(f"[RunPod Handler] ✅ Completed in {time.time() - start_time:.2f}s")
                    print(f"[RunPod Handler] Download URL: {download_url}")
                    
                    # Mark job as processed
                    processed_jobs.add(job_id)
                    
                    # Cleanup progress file
                    try:
                        requests.delete(f"http://localhost:8000/tts/progress/{job_id}", timeout=2)
                    except:
                        pass
                    
                    # Return result - MUST be flat dict at top level
                    # Return download URL instead of base64 to avoid 400 Bad Request
                    return {
                        "download_url": download_url,
                        "filename": filename,
                        "job_id": job_id,
                        "status": "completed",
                        "sample_used": ref_name,
                        "processing_time_seconds": round(time.time() - start_time, 2)
                    }
                
                if progress == -1 or status in ["failed", "cancelled"]:
                    error_msg = progress_data.get("extra", "Unknown error")
                    # Return error in flat structure
                    return {
                        "error": f"TTS processing failed: {error_msg}",
                        "job_id": job_id,
                        "status": "failed"
                    }
            
            except requests.RequestException as e:
                print(f"[RunPod Handler] Poll error: {e}")
                continue
        
        # Timeout
        return {
            "error": f"Processing timeout after {max_wait} seconds",
            "status": "failed",
            "job_id": job_id
        }
    
    except Exception as e:
        print(f"[RunPod Handler] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "failed",
            "traceback": traceback.format_exc()
        }


# Start RunPod handler
if __name__ == "__main__":
    print("[RunPod Handler] ========================================")
    print("[RunPod Handler] F5-TTS RunPod Serverless Handler")
    print("[RunPod Handler] ========================================")

    # Auto-start Flask API if not running
    flask_started = False
    try:
        resp = requests.get("http://localhost:8000/health", timeout=2)
        if resp.status_code == 200:
            print("[RunPod Handler] ✅ Flask API already running")
        else:
            raise Exception("Flask not healthy")
    except:
        print("[RunPod Handler] 🔄 Flask API not running, starting it...")
        import subprocess
        flask_process = subprocess.Popen(
            ["python3", "flask_tts_api_optimized.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        flask_started = True

        # Wait for Flask to be ready
        for i in range(30):
            try:
                resp = requests.get("http://localhost:8000/health", timeout=2)
                if resp.status_code == 200:
                    print("[RunPod Handler] ✅ Flask API started successfully")
                    break
            except:
                time.sleep(1)
        else:
            print("[RunPod Handler] ❌ Failed to start Flask API")
            flask_process.terminate()
            exit(1)

    print("[RunPod Handler] Starting RunPod serverless handler...")
    try:
        runpod.serverless.start({"handler": handler})
    finally:
        # Cleanup Flask if we started it
        if flask_started:
            print("[RunPod Handler] Cleaning up Flask process...")
            try:
                flask_process.terminate()
                flask_process.wait(timeout=5)
            except:
                flask_process.kill()