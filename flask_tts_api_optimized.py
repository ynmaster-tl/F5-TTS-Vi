#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
F5-TTS Flask API - Optimized for RunPod Serverless
- Single job processing (1 at a time)
- GPU memory optimization
- Fast model loading
- Async job processing with progress tracking
"""

import os
import time
import random
import string
import json
import threading
from pathlib import Path
from datetime import datetime
from functools import lru_cache

from flask import Flask, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
from cached_path import cached_path
from f5_tts.api import F5TTS
from vinorm import TTSnorm


# ========== CONFIGURATION ==========
# Use relative paths for compatibility with both local and RunPod deployment
REF_VOICE_DIR = os.getenv("REF_VOICE_DIR", "./sample")
OUTPUT_AUDIO_DIR = os.getenv("OUTPUT_AUDIO_DIR", "./output")

BASE_DIR = Path.cwd()
SAMPLE_DIR = Path(REF_VOICE_DIR)
OUTPUT_DIR = Path(OUTPUT_AUDIO_DIR)

SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CKPT_HF_URI = "hf://hynt/F5-TTS-Vietnamese-ViVoice/model_last.pt"
VOCAB_HF_URI = "hf://hynt/F5-TTS-Vietnamese-ViVoice/config.json"


# ========== SINGLE JOB LOCK ==========
# Only 1 job can be processed at a time
job_lock = threading.Lock()
current_job_id = None
job_start_time = None
cancelled_jobs = set()  # Track cancelled job IDs


# ========== PROGRESS TRACKING ==========
def update_progress(job_id, progress, status=None, extra=None, batch_current=None, batch_total=None, filename=None):
    """Update progress for job tracking"""
    progress_file = OUTPUT_DIR / f"progress_{job_id}.json"
    
    data = {
        "progress": progress,
        "status": status,
        "extra": extra,
        "timestamp": time.time()
    }
    
    if batch_current is not None and batch_total is not None:
        data["batch_current"] = batch_current
        data["batch_total"] = batch_total
    
    if filename is not None:
        data["filename"] = filename
    
    with open(progress_file, "w") as f:
        json.dump(data, f)


# ========== TEXT CLEANING ==========
def post_process(text: str) -> str:
    """Clean text for TTS"""
    text = " " + text + " "
    text = text.replace(" . . ", " . ")
    text = " " + text + " "
    text = text.replace(" .. ", " . ")
    text = " " + text + " "
    text = text.replace(" , , ", " , ")
    text = " " + text + " "
    text = text.replace(" ,, ", " , ")
    text = " " + text + " "
    text = text.replace('"', "")
    return " ".join(text.split())


# ========== UTILITY ==========
def make_unique_filename(prefix: str = "", ext: str = "", text: str = "") -> str:
    """Generate unique filename with optional text preview"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    # If text provided, extract first 5 words and sanitize
    text_part = ""
    if text:
        words = text.split()[:5]
        text_preview = " ".join(words)
        # Sanitize filename (remove invalid characters)
        text_part = "_" + "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in text_preview).strip().replace(' ', ' ')
    
    return f"{prefix}_{timestamp}_{random_str}{text_part}{ext}"


# ========== DEVICE DETECTION ==========
def choose_device():
    """Choose best available device"""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ========== PHOWHISPER FOR TEXT_REF ==========
@lru_cache(maxsize=1)
def load_phowhisper():
    """Load PhoWhisper model (cached)"""
    import torch
    from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
    
    device = choose_device()
    print(f"[PhoWhisper] Using device: {device}")
    
    processor = AutoProcessor.from_pretrained("vinai/PhoWhisper-medium")
    model = AutoModelForSpeechSeq2Seq.from_pretrained("vinai/PhoWhisper-medium").to(device)
    model.eval()
    
    return processor, model, device


def get_text_ref(ref_basename: str) -> str:
    """Get text reference - generate if not exists"""
    import torch
    import soundfile as sf
    import torchaudio
    
    wav_path = SAMPLE_DIR / f"{ref_basename}.wav"
    txt_path = SAMPLE_DIR / f"{ref_basename}.txt"
    
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    print(f"[PhoWhisper] Generating text_ref for {ref_basename}.wav...")
    processor, model, device = load_phowhisper()
    
    try:
        # Use soundfile - works without torchcodec/FFmpeg
        audio, sr = sf.read(str(wav_path))
        waveform = torch.FloatTensor(audio).unsqueeze(0) if audio.ndim == 1 else torch.FloatTensor(audio).T
        if waveform.ndim > 1 and waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != 16000:
            print(f"[PhoWhisper] Resampling from {sr}Hz to 16000Hz...")
            waveform = torchaudio.functional.resample(waveform, sr, 16000)
            sr = 16000
        
        input_features = processor(
            waveform.squeeze(), sampling_rate=sr, return_tensors="pt"
        ).input_features.to(device)
        
        with torch.no_grad():
            predicted_ids = model.generate(input_features)
            transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        
        if not transcription.strip():
            raise ValueError("PhoWhisper returned empty transcription.")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(transcription.strip())
        
        print(f"[PhoWhisper] ✅ Saved text_ref to {txt_path}")
        return transcription.strip()
    
    except Exception as e:
        print(f"[PhoWhisper] ❌ Failed: {e}")
        raise RuntimeError(f"text_ref_failed: {e}")


# ========== F5-TTS MODEL (SINGLETON) ==========
tts_model = None
model_load_lock = threading.Lock()


def get_tts_model():
    """Get or load F5-TTS model (singleton, thread-safe)"""
    global tts_model
    
    if tts_model is not None:
        return tts_model
    
    with model_load_lock:
        # Double-check after acquiring lock
        if tts_model is not None:
            return tts_model
        
        device = choose_device()
        print(f"[F5-TTS] Loading model on {device}...")
        
        ckpt_file = str(cached_path(CKPT_HF_URI))
        vocab_file = str(cached_path(VOCAB_HF_URI))
        
        print(f"[F5-TTS] ckpt: {ckpt_file}")
        print(f"[F5-TTS] vocab: {vocab_file}")
        
        tts_model = F5TTS(
            model_type="F5-TTS",
            ckpt_file=ckpt_file,
            vocab_file=vocab_file,
            vocoder_name="vocos",
            device=device,
            use_ema=True,
        )
        
        print(f"[F5-TTS] ✅ Model loaded successfully")
        return tts_model


# ========== GPU CLEANUP ==========
def cleanup_gpu():
    """Clean up GPU memory"""
    try:
        import torch
        import gc
        
        if torch.cuda.is_available():
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            mem_allocated = torch.cuda.memory_allocated() / 1024**2
            mem_reserved = torch.cuda.memory_reserved() / 1024**2
            print(f"[GPU] Allocated: {mem_allocated:.2f} MB, Reserved: {mem_reserved:.2f} MB")
    except Exception as e:
        print(f"[GPU] Cleanup failed: {e}")


# ========== ASYNC JOB PROCESSOR ==========
def process_job_async(job_id, wav_path, text_ref, cleaned_text, speed, out_path, out_filename):
    """Process TTS job asynchronously"""
    global current_job_id, job_start_time, cancelled_jobs
    
    try:
        job_start_time = time.time()
        current_job_id = job_id
        
        print(f"[Job {job_id}] Starting processing...")
        
        # Check if cancelled before starting
        if job_id in cancelled_jobs:
            print(f"[Job {job_id}] Cancelled before start")
            update_progress(job_id, -1, "cancelled", "Job cancelled before start")
            return
        
        update_progress(job_id, 5, "init")
        
        # Get model
        update_progress(job_id, 10, "loading_model")
        
        # Check cancellation
        if job_id in cancelled_jobs:
            print(f"[Job {job_id}] Cancelled during model load")
            update_progress(job_id, -1, "cancelled", "Job cancelled")
            return
            
        tts = get_tts_model()
        
        # Progress callback for batches
        def batch_progress_callback(current, total):
            # Check if job was cancelled
            if job_id in cancelled_jobs:
                raise InterruptedError(f"Job {job_id} was cancelled")
            
            batch_progress = int(10 + (current / total) * 75)  # 10% -> 85%
            update_progress(job_id, batch_progress, "generating", 
                          f"Batch {current}/{total}", current, total)
        
        # Inference
        update_progress(job_id, 15, "generating_audio")
        print(f"[Job {job_id}] Calling TTS inference...")
        
        wav, sr, spect = tts.infer(
            ref_file=str(wav_path),
            ref_text=text_ref,
            gen_text=cleaned_text,
            speed=speed,
            progress_callback=batch_progress_callback
        )
        
        # Save audio
        update_progress(job_id, 90, "saving_audio")
        print(f"[Job {job_id}] Saving audio...")
        
        import torch
        import torchaudio
        
        if isinstance(wav, torch.Tensor):
            wav_tensor = wav
        else:
            wav_tensor = torch.from_numpy(wav)
        
        if wav_tensor.dim() == 1:
            wav_tensor = wav_tensor.unsqueeze(0)
        elif wav_tensor.dim() == 2 and wav_tensor.shape[0] != 1:
            wav_tensor = wav_tensor.unsqueeze(0)
        
        torchaudio.save(str(out_path), wav_tensor, sr)
        
        # Complete
        elapsed = time.time() - job_start_time
        update_progress(job_id, 100, "completed", f"Completed in {elapsed:.2f}s", filename=out_filename)
        
        print(f"[Job {job_id}] ✅ Completed in {elapsed:.2f}s")
        
        # Remove from cancelled set if it was there
        cancelled_jobs.discard(job_id)
        
        # Cleanup
        cleanup_gpu()
    
    except InterruptedError as e:
        # Job was cancelled
        print(f"[Job {job_id}] 🚫 Cancelled: {e}")
        update_progress(job_id, -1, "cancelled", str(e))
        cancelled_jobs.discard(job_id)
        cleanup_gpu()
        
    except Exception as e:
        print(f"[Job {job_id}] ❌ Failed: {e}")
        update_progress(job_id, -1, "failed", str(e))
        cancelled_jobs.discard(job_id)
        cleanup_gpu()
    
    finally:
        # Release lock
        current_job_id = None
        job_start_time = None
        job_lock.release()
        print(f"[Job {job_id}] Released job lock")


# ========== FLASK APP ==========
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "f5-tts"}), 200


@app.route("/status", methods=["GET"])
def get_status():
    """Get API status"""
    try:
        import torch
        
        is_busy = not job_lock.acquire(blocking=False)
        if not is_busy:
            job_lock.release()
        
        status = {
            "api_version": "3.0-optimized",
            "model_loaded": tts_model is not None,
            "busy": is_busy,
            "current_job": current_job_id,
            "job_duration": time.time() - job_start_time if job_start_time else None,
        }
        
        if torch.cuda.is_available():
            status["gpu_available"] = True
            status["gpu_memory_allocated_mb"] = torch.cuda.memory_allocated() / 1024**2
            status["gpu_memory_reserved_mb"] = torch.cuda.memory_reserved() / 1024**2
        else:
            status["gpu_available"] = False
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/voices", methods=["GET"])
def list_voices():
    """List available voice samples"""
    try:
        voices = []
        
        # Scan sample directory for .wav files
        if SAMPLE_DIR.exists():
            for wav_file in SAMPLE_DIR.glob("*.wav"):
                txt_file = wav_file.with_suffix(".txt")
                
                voice_info = {
                    "id": wav_file.stem,
                    "wav": wav_file.name,
                    "txt": txt_file.name if txt_file.exists() else None,
                    "path": f"sample/{wav_file.name}",
                    "size_mb": round(wav_file.stat().st_size / 1024 / 1024, 2)
                }
                
                # Try to read reference text if exists
                if txt_file.exists():
                    try:
                        with open(txt_file, "r", encoding="utf-8") as f:
                            voice_info["reference_text"] = f.read().strip()[:100]  # First 100 chars
                    except:
                        pass
                
                voices.append(voice_info)
        
        return jsonify({
            "voices": sorted(voices, key=lambda x: x["id"]),
            "count": len(voices),
            "sample_dir": str(SAMPLE_DIR)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tts", methods=["POST"])
def synthesize():
    """
    Main TTS endpoint
    
    JSON input:
    {
      "text": "Text to synthesize",
      "ref_name": "voice.wav",
      "speed": 0.9,
      "job_id": "optional_custom_id"
    }
    
    Returns 202 (Accepted) with job_id for async processing
    """
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "invalid_json", "message": str(e)}), 400
    
    # Parse parameters
    text = (payload or {}).get("text", "")
    ref_name = (payload or {}).get("ref_name", "")
    speed = (payload or {}).get("speed", 0.9)
    custom_job_id = (payload or {}).get("job_id")
    
    # Validation
    if not text.strip():
        return jsonify({"error": "missing_text"}), 400
    if not ref_name.strip():
        return jsonify({"error": "missing_ref_name"}), 400
    
    # Validate ref file exists
    # Handle paths like "sample/narrator.wav" or just "narrator.wav"
    ref_path = Path(ref_name)
    if ref_path.parent != Path('.'):
        # Has folder prefix like "sample/narrator.wav"
        ref_base = secure_filename(ref_path.stem)
        wav_path = BASE_DIR / ref_path.parent / f"{ref_base}.wav"
    else:
        # Just filename like "narrator.wav"
        ref_base = secure_filename(ref_path.stem)
        wav_path = SAMPLE_DIR / f"{ref_base}.wav"
    
    if not wav_path.exists():
        return jsonify({
            "error": "ref_not_found",
            "message": "Reference voice file not found for the given 'ref_name'.",
            "details": {
                "original_ref_name": ref_name,
                "sanitized_base_name": ref_base,
                "full_path_checked": str(wav_path)
            }
        }), 404
    
    # Validate speed
    try:
        speed = float(speed)
        if speed <= 0 or speed > 4:
            raise ValueError
    except Exception:
        return jsonify({"error": "invalid_speed"}), 400
    
    # Try to acquire job lock (non-blocking)
    if not job_lock.acquire(blocking=False):
        return jsonify({
            "error": "busy",
            "message": "Server is processing another job. Please try again later.",
            "current_job": current_job_id,
            "estimated_wait": int(time.time() - job_start_time) if job_start_time else None
        }), 503
    
    try:
        # Get text reference
        update_progress("temp", 2, "getting_text_ref")
        text_ref = get_text_ref(wav_path.stem)
        
        # Clean text
        try:
            cleaned_text = post_process(TTSnorm(text))
        except Exception:
            cleaned_text = post_process(text)
        
        # Generate output filename with text preview
        out_filename = make_unique_filename(prefix="f5tts", ext=".wav", text=text)
        out_path = OUTPUT_DIR / out_filename
        
        # Generate job ID
        if custom_job_id:
            job_id = custom_job_id
        else:
            job_id = make_unique_filename(prefix="job", ext="")
        
        print(f"[TTS] New job: {job_id}")
        
        # Initialize progress
        update_progress(job_id, 0, "pending")
        
        # Start async processing
        thread = threading.Thread(
            target=process_job_async,
            args=(job_id, wav_path, text_ref, cleaned_text, speed, out_path, out_filename),
            daemon=True
        )
        thread.start()
        
        # Return immediately
        wav_url = url_for("download_output", filename=out_filename, _external=True)
        
        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "message": "Job started. Poll /tts/progress/{job_id} for status",
            "wav_url": wav_url,
            "filename": out_filename,
            "sample_used": ref_base,
            "text_ref": text_ref
        }), 202
        
    except Exception as e:
        # Release lock on error
        job_lock.release()
        return jsonify({"error": "inference_failed", "message": str(e)}), 500


@app.route("/tts/progress/<job_id>", methods=["GET", "DELETE"])
def get_progress(job_id):
    """Get or delete progress for a job"""
    progress_file = OUTPUT_DIR / f"progress_{job_id}.json"
    
    if request.method == "DELETE":
        try:
            progress_file.unlink(missing_ok=True)
            return jsonify({"status": "deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # GET
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                data = json.load(f)
                return jsonify(data)
        except Exception as e:
            return jsonify({"progress": 0, "status": "error", "extra": str(e)})
    
    return jsonify({"progress": 0, "status": "pending"})


@app.route("/tts/kill/<job_id>", methods=["POST"])
def kill_job(job_id):
    """Kill a running job and release resources"""
    global current_job_id, job_lock, cancelled_jobs
    
    # Check if this job is currently running
    if current_job_id != job_id:
        return jsonify({
            "status": "not_running",
            "message": f"Job {job_id} is not currently running",
            "current_job": current_job_id
        }), 400
    
    try:
        print(f"[Kill] Attempting to kill job {job_id}...")
        
        # Add to cancelled set - worker thread will check this
        cancelled_jobs.add(job_id)
        
        # Update progress to cancelled
        update_progress(job_id, -1, "cancelled", "Job cancelled by user")
        
        # Force cleanup GPU
        cleanup_gpu()
        
        # Cleanup any partial output files
        output_file = OUTPUT_DIR / f"{job_id}.wav"
        if output_file.exists():
            try:
                output_file.unlink()
                print(f"[Kill] Deleted partial output: {output_file}")
            except:
                pass
        
        print(f"[Kill] ✅ Cancellation signal sent for job {job_id}")
        print(f"[Kill] Worker thread will stop at next checkpoint")
        
        return jsonify({
            "status": "cancelled",
            "job_id": job_id,
            "message": "Job cancelled. GPU memory released."
        }), 200
        
    except Exception as e:
        print(f"[Kill] ❌ Error killing job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/output/<path:filename>")
def download_output(filename):
    """Download output file"""
    return send_from_directory(str(OUTPUT_DIR), filename, as_attachment=False)


@app.route("/cleanup", methods=["POST"])
def force_cleanup():
    """Force GPU cleanup (admin endpoint)"""
    try:
        cleanup_gpu()
        return jsonify({"status": "cleaned"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tts/cleanup-file/<filename>", methods=["DELETE"])
def cleanup_file(filename):
    """Delete specific file from output directory after download"""
    try:
        file_path = OUTPUT_DIR / filename
        
        if not file_path.exists():
            return jsonify({
                "status": "not_found",
                "message": f"File {filename} not found"
            }), 404
        
        # Delete the audio file
        file_path.unlink()
        print(f"[Cleanup] 🗑️ Deleted audio: {filename}")
        
        # Find and delete corresponding progress file
        # Scan all progress files to find one with matching filename
        try:
            progress_files = list(OUTPUT_DIR.glob("progress_*.json"))
            for progress_file in progress_files:
                try:
                    with open(progress_file, 'r') as f:
                        data = json.load(f)
                        # Check if this progress file references our audio filename
                        if data.get('filename') == filename:
                            progress_file.unlink()
                            print(f"[Cleanup] 🗑️ Deleted progress: {progress_file.name}")
                            break
                except:
                    continue
        except Exception as progress_error:
            print(f"[Cleanup] ⚠️ Could not delete progress file: {progress_error}")
        
        return jsonify({
            "status": "deleted",
            "filename": filename
        }), 200
        
    except Exception as e:
        print(f"[Cleanup] ⚠️ Error deleting {filename}: {e}")
        return jsonify({"error": str(e)}), 500


# ========== PRELOAD MODEL ON STARTUP ==========
def preload_model():
    """Preload model on startup and ensure it's in VRAM"""
    try:
        import torch
        
        print("[Startup] Preloading F5-TTS model into VRAM...")
        print("[Startup] This may take 30-60 seconds...")
        
        # Load model into memory
        tts = get_tts_model()
        
        # Force model to VRAM by running a tiny dummy inference
        print("[Startup] Warming up model with dummy inference...")
        device = choose_device()
        
        if device == "cuda":
            # Get a sample voice file for dummy inference
            sample_wav = next(SAMPLE_DIR.glob("*.wav"), None)
            if sample_wav:
                sample_base = sample_wav.stem
                try:
                    # Get or generate text_ref
                    text_ref = get_text_ref(sample_base)
                    
                    # Run tiny inference to load model into VRAM
                    # Use default speed (0.9) for warmup - actual jobs will use their own speed
                    tts.infer(
                        ref_file=str(sample_wav),
                        ref_text=text_ref[:50],  # Use short text
                        gen_text="Khởi động hệ thống.",  # Short test sentence
                        speed=0.9,  # Default speed for warmup
                        progress_callback=None
                    )
                    
                    # Check VRAM usage
                    mem_allocated = torch.cuda.memory_allocated() / 1024**3
                    mem_reserved = torch.cuda.memory_reserved() / 1024**3
                    
                    print(f"[Startup] ✅ Model loaded into VRAM")
                    print(f"[Startup] VRAM Allocated: {mem_allocated:.2f} GB")
                    print(f"[Startup] VRAM Reserved: {mem_reserved:.2f} GB")
                    
                    # Cleanup after warmup
                    cleanup_gpu()
                    
                except Exception as warmup_error:
                    print(f"[Startup] ⚠️ Warmup inference failed: {warmup_error}")
                    print(f"[Startup] Model loaded but not warmed up")
            else:
                print("[Startup] ⚠️ No sample voice files found for warmup")
                print("[Startup] Model loaded but not warmed up")
        else:
            print(f"[Startup] ✅ Model loaded on {device}")
        
        print("[Startup] ✅ Server ready to process jobs")
        
    except Exception as e:
        print(f"[Startup] ⚠️ Failed to preload model: {e}")
        print("[Startup] Model will load on first request")


if __name__ == "__main__":
    # Preload model
    preload_model()
    
    # Start server with configurable port
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "7860"))
    
    print("=" * 60)
    print(f"[F5-TTS] Starting Flask API Server")
    print(f"[F5-TTS] Host: {host}:{port}")
    print(f"[F5-TTS] Mode: Single job processing")
    print(f"[F5-TTS] Sample Dir: {SAMPLE_DIR}")
    print(f"[F5-TTS] Output Dir: {OUTPUT_DIR}")
    print("=" * 60)
    print("")
    print("Available modes:")
    print("  1. Local Test:  FLASK_PORT=7860 python flask_tts_api_optimized.py")
    print("  2. Docker:      FLASK_PORT=8000 python flask_tts_api_optimized.py")
    print("  3. RunPod:      entrypoint.sh (auto-starts Flask + handler)")
    print("=" * 60)
    
    app.run(host=host, port=port, threaded=True)
