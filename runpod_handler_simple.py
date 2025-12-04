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
        
        # Double-check Flask is still alive before submitting
        if flask_started and flask_process.poll() is not None:
            print("[RunPod Handler] ❌ Flask process died before job submission")
            return {
                "error": "Flask API process died",
                "status": "failed",
                "job_id": job_id
            }
        
        try:
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
            print(f"[RunPod Handler] Flask response status: {response.status_code}")
            print(f"[RunPod Handler] Flask response: {response.text[:200]}...")
        except requests.RequestException as e:
            print(f"[RunPod Handler] ❌ Request to Flask failed: {e}")
            return {
                "error": f"Cannot connect to Flask API: {str(e)}",
                "status": "failed",
                "job_id": job_id
            }
        
        if response.status_code == 503:
            return {
                "error": "Flask API is processing another job",
                "status": "failed",
                "job_id": job_id
            }
        
        if response.status_code != 202:
            error_details = response.text
            print(f"[RunPod Handler] ❌ Flask API returned non-202 status: {response.status_code}")
            print(f"[RunPod Handler] ❌ Error details: {error_details}")
            return {
                "error": f"Flask API error: {error_details}",
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
                        confirmation_url = f"https://{pod_id}-8000.proxy.runpod.net/confirm-download/{job_id}"
                    else:
                        download_url = f"http://localhost:8000/output/{filename}"
                        confirmation_url = f"http://localhost:8000/confirm-download/{job_id}"
                    
                    print(f"[RunPod Handler] ✅ TTS completed in {time.time() - start_time:.2f}s")
                    print(f"[RunPod Handler] Download URL: {download_url}")
                    print(f"[RunPod Handler] Confirmation URL: {confirmation_url}")
                    
                    # Mark job as processed
                    processed_jobs.add(job_id)
                    
                    # Cleanup progress file
                    try:
                        requests.delete(f"http://localhost:8000/tts/progress/{job_id}", timeout=2)
                    except:
                        pass
                    
                    # ========== SEND WEBHOOK TO NEXT.JS ==========
                    webhook_url = os.getenv('NEXTJS_WEBHOOK_URL')
                    webhook_api_key = os.getenv('RUNPOD_WEBHOOK_API_KEY')
                    
                    if webhook_url:
                        print(f"[RunPod Handler] 📤 Sending webhook to Next.js: {webhook_url}")
                        
                        # Prepare headers with API key authentication
                        webhook_headers = {
                            'Content-Type': 'application/json'
                        }
                        if webhook_api_key:
                            webhook_headers['X-API-Key'] = webhook_api_key
                            print(f"[RunPod Handler] 🔐 Using API key authentication")
                        else:
                            print(f"[RunPod Handler] ⚠️ RUNPOD_WEBHOOK_API_KEY not set, sending without auth")
                        
                        try:
                            webhook_resp = requests.post(
                                webhook_url,
                                json={
                                    "job_id": job_id,
                                    "download_url": download_url,
                                    "confirmation_url": confirmation_url,
                                    "filename": filename,
                                },
                                headers=webhook_headers,
                                timeout=10
                            )
                            if webhook_resp.status_code == 200:
                                print(f"[RunPod Handler] ✅ Webhook sent successfully")
                            elif webhook_resp.status_code == 401:
                                print(f"[RunPod Handler] 🚫 Webhook authentication failed - check API key")
                            else:
                                print(f"[RunPod Handler] ⚠️ Webhook returned {webhook_resp.status_code}")
                        except Exception as webhook_err:
                            print(f"[RunPod Handler] ⚠️ Webhook failed: {webhook_err}")
                    else:
                        print(f"[RunPod Handler] ⚠️ NEXTJS_WEBHOOK_URL not set, skipping webhook")
                    
                    # ========== WAIT FOR DOWNLOAD CONFIRMATION ==========
                    # Handler MUST wait for confirmation to keep pod alive
                    print(f"[RunPod Handler] ⏳ Waiting for download confirmation (max 60s)...")
                    confirmation_timeout = int(os.getenv('DOWNLOAD_CONFIRMATION_TIMEOUT', '60'))
                    confirmation_start = time.time()
                    confirmed = False
                    
                    for i in range(confirmation_timeout):
                        try:
                            check_resp = requests.get(
                                f"http://localhost:8000/check-download/{job_id}",
                                timeout=2
                            )
                            
                            if check_resp.status_code == 200:
                                check_data = check_resp.json()
                                if check_data.get("confirmed"):
                                    elapsed = time.time() - confirmation_start
                                    print(f"[RunPod Handler] ✅ Download confirmed after {elapsed:.1f}s!")
                                    confirmed = True
                                    break
                        except Exception as e:
                            pass  # Ignore polling errors
                        
                        time.sleep(1)
                    
                    if not confirmed:
                        elapsed = time.time() - confirmation_start
                        print(f"[RunPod Handler] ⚠️ No confirmation after {elapsed:.1f}s - returning anyway")
                    
                    # Return result - job will be removed from RunPod queue
                    return {
                        "download_url": download_url,
                        "confirmation_url": confirmation_url,
                        "filename": filename,
                        "job_id": job_id,
                        "status": "completed",
                        "confirmed": confirmed,
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
        import os
        
        # Pass environment variables to Flask subprocess
        env = os.environ.copy()
        env['FLASK_HOST'] = '0.0.0.0'
        env['FLASK_PORT'] = '8000'
        
        flask_process = subprocess.Popen(
            ["python3", "flask_tts_api_optimized.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        flask_started = True

        # Wait for Flask to be ready (increased timeout for model loading)
        for i in range(60):  # 60 attempts = 60 seconds
            try:
                resp = requests.get("http://localhost:8000/health", timeout=2)
                if resp.status_code == 200:
                    print("[RunPod Handler] ✅ Flask API started successfully")
                    break
            except:
                # Check if Flask process is still alive
                if flask_process.poll() is not None:
                    print("[RunPod Handler] ❌ Flask process died")
                    stdout, stderr = flask_process.communicate()
                    print(f"[RunPod Handler] Flask stdout: {stdout.decode()}")
                    print(f"[RunPod Handler] Flask stderr: {stderr.decode()}")
                    exit(1)
                time.sleep(1)
        else:
            print("[RunPod Handler] ❌ Failed to start Flask API after 60 seconds")
            flask_process.terminate()
            stdout, stderr = flask_process.communicate()
            print(f"[RunPod Handler] Flask stdout: {stdout.decode()}")
            print(f"[RunPod Handler] Flask stderr: {stderr.decode()}")
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