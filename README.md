# F5-TTS-Vi-Runpod: Hệ thống TTS Tiếng Việt Sẵn sàng Sản xuất

## 📖 Tổng quan Dự án

**F5-TTS-Vi-Runpod** là một hệ thống Text-to-Speech (TTS) tiếng Việt sẵn sàng sản xuất, được tối ưu hóa đặc biệt cho việc triển khai trên nền tảng RunPod Serverless. Dự án sử dụng mô hình F5-TTS tiên tiến để tạo ra âm thanh giọng nói tự nhiên từ văn bản tiếng Việt, với khả năng nhân bản giọng nói (voice cloning) dựa trên các mẫu âm thanh tham chiếu.

### 🎯 Mục đích
- Triển khai mô hình F5-TTS thành dịch vụ TTS đám mây có thể mở rộng cho tiếng Việt.
- Giải quyết các thách thức triển khai thực tế như quản lý tài nguyên GPU, xử lý bất đồng bộ và theo dõi tiến độ thời gian thực.
- Hỗ trợ các ứng dụng cần tạo âm thanh giọng nói tiếng Việt quy mô lớn, thời gian thực trên nền tảng serverless.  

## 🏗️ Cấu trúc Dự án

### Thư mục Gốc
- `README.md`: Tài liệu này (đang cập nhật).
- `runpod_handler_simple.py`: Bộ xử lý chính cho RunPod, điều phối các công việc.
- `flask_tts_api_optimized.py`: Máy chủ API Flask chính, xử lý logic TTS.
- `Dockerfile.optimized`: Cấu hình Docker tối ưu cho sản xuất.
- `entrypoint.sh`: Script khởi động container.
- `requirements.optimized.txt`: Các phụ thuộc Python tối thiểu.
- `Todo_F5_TTS_Runpod.md`: Danh sách các cải tiến cần thực hiện.

### Thư mục f5_tts/ (Mô-đun Cốt lõi)
- `api.py`: API suy luận mô hình F5-TTS chính.
- `socket_server.py`: Máy chủ streaming TTS thời gian thực qua socket.
- `eval/`: Scripts đánh giá hiệu suất mô hình.
- `infer/`: Tiện ích suy luận và các ví dụ sử dụng.
- `model/`: Kiến trúc mô hình cốt lõi (DiT, UNetT, CFM, v.v.).

### Thư mục Dữ liệu
- `sample/`: Mẫu giọng nói tham chiếu (file .wav với transcript .txt tương ứng).
- `output/`: File âm thanh được tạo và file JSON theo dõi tiến độ.

## ⚙️ Các Thành phần và Chức năng Chính

### 1. Máy chủ API Flask (`flask_tts_api_optimized.py`)
- **Xử lý Công việc Đơn**: Đảm bảo chỉ một công việc TTS được xử lý tại một thời điểm để tránh xung đột tài nguyên GPU.
- **Xử lý Bất đồng bộ**: Thực thi công việc không chặn với theo dõi tiến độ thời gian thực.
- **Quản lý Bộ nhớ GPU**: Tự động dọn dẹp và tối ưu hóa bộ nhớ.
- **Tích hợp PhoWhisper**: Tự động chuyển đổi văn bản từ âm thanh tham chiếu bằng mô hình PhoWhisper.
- **Endpoints chính**:
  - `/health`: Kiểm tra sức khỏe hệ thống.
  - `/status`: Trạng thái máy chủ và thông tin GPU.
  - `/voices`: Liệt kê các mẫu giọng nói khả dụng.
  - `/tts`: Tạo TTS chính (bất đồng bộ).
  - `/tts/progress/<job_id>`: Theo dõi tiến độ công việc.
  - `/tts/kill/<job_id>`: Hủy công việc đang chạy.
  - `/output/<filename>`: Tải file âm thanh đã tạo.
  - `/cleanup`: Dọn dẹp bộ nhớ GPU thủ công.
  - `/confirm-download/<job_id>`: Xác nhận client đã tải xuống âm thanh (POST).
  - `/check-download/<job_id>`: Kiểm tra trạng thái xác nhận tải xuống (GET).

### 2. Bộ xử lý RunPod (`runpod_handler_simple.py`)
- **Điều phối Công việc**: Nhận yêu cầu từ RunPod và chuyển tiếp đến Flask API.
- **Theo dõi Tiến độ**: Polling Flask API để cập nhật trạng thái công việc.
- **Trả về Kết quả**: Trả về URL tải xuống âm thanh khi hoàn thành.
- **Xác nhận Tải xuống**: Chờ client xác nhận đã tải xuống âm thanh trước khi tắt worker (tối đa 60 giây).
- **Xử lý Lỗi**: Quản lý các trường hợp lỗi và timeout.

### 3. Mô hình F5-TTS (`f5_tts/api.py`)
- **Loại Mô hình**: F5-TTS (dựa trên DiT) và E2-TTS (dựa trên UNetT).
- **Hỗ trợ Vocoder**: Vocos và BigVGAN để chuyển đổi spectrogram thành âm thanh.
- **Phát hiện Thiết bị**: Tự động chọn GPU/CPU phù hợp.
- **Xử lý Batch**: Suy luận hiệu quả với callback tiến độ.
- **Xử lý Văn bản**: Chuẩn hóa và làm sạch văn bản tiếng Việt.

### 4. Máy chủ Socket (`f5_tts/socket_server.py`)
- **Streaming Thời gian thực**: Tạo và truyền âm thanh theo chunk.
- **Tích hợp Client**: Hỗ trợ client tùy chỉnh cho TTS trực tiếp.

### 5. Cấu hình Đào tạo
- **Biến thể Mô hình**: Phiên bản Base và Small cho các yêu cầu tài nguyên khác nhau.
- **Hỗ trợ Dataset**: Dataset tiếng Việt (ViVoice 100h) và đa ngôn ngữ.
- **Tối ưu hóa**: Tích lũy gradient, lập lịch warmup và độ chính xác hỗn hợp.

## 🚀 Cách Hệ thống Hoạt động

### Luồng Triển khai trên RunPod
1. **Client (Next.js)** gửi yêu cầu công việc đến endpoint `/run` của RunPod (bất đồng bộ).
2. **RunPod** tạo worker và gọi handler với dữ liệu công việc.
3. **Handler** polling Flask API để theo dõi tiến độ mỗi 2 giây.
4. **Flask API** xử lý TTS (có thể mất 200-400 giây cho văn bản dài).
5. **Handler** nhận kết quả và sinh `confirmation_url` (URL webhook xác nhận).
6. **Handler** chờ xác nhận tải xuống từ client (polling mỗi 1 giây, tối đa 60 giây).
7. **Handler** trả về `download_url` và `confirmation_url` khi hoàn thành.
8. **Client** polling `/status` của RunPod mỗi 1 giây.
9. **Client** tải âm thanh xuống thành công.
10. **Client** gửi webhook POST đến `confirmation_url` để xác nhận.
11. **Handler** nhận xác nhận và kết thúc → **Worker tắt an toàn**.

**Lưu ý:** Nếu client không gửi xác nhận trong 60 giây, handler sẽ timeout và trả về cảnh báo, nhưng vẫn hoàn thành công việc. Timeout idle 10 giây của RunPod **không còn là vấn đề** nhờ cơ chế chờ xác nhận.

### Quy trình Tạo TTS
1. **Xác thực đầu vào**: Kiểm tra văn bản và file giọng nói tham chiếu.
2. **Tạo văn bản tham chiếu**: Sử dụng PhoWhisper để tạo transcript nếu chưa có.
3. **Làm sạch văn bản**: Chuẩn hóa tiếng Việt với Vinorm.
4. **Suy luận mô hình**: F5-TTS tạo mel spectrograms từ văn bản.
5. **Vocoder**: Chuyển spectrograms thành sóng âm thanh.
6. **Hậu xử lý**: Dọn dẹp âm thanh và lưu file.

### Webhook Confirmation (Tính năng Mới)
Để giải quyết vấn đề **worker RunPod tắt sớm trước khi client tải xuống âm thanh** (do timeout idle 10 giây), hệ thống triển khai cơ chế **xác nhận tải xuống qua webhook**:

#### Cách hoạt động
1. **Handler trả về ngay**: Sau khi TTS hoàn thành, handler **return response ngay lập tức** (không blocking).
2. **Background thread chờ**: Handler khởi động **background thread** (non-daemon) để chờ confirmation, giữ pod sống.
3. **Client nhận COMPLETED**: Scheduler nhận status=COMPLETED từ RunPod ngay lập tức (không bị deadlock).
4. **Client tải xuống**: Client download audio từ `download_url` (2-5 giây).
5. **Client xác nhận**: Sau khi tải thành công, client gửi POST request đến `confirmation_url`.
6. **Thread nhận confirmation**: Background thread detect confirmation → exit → pod tắt an toàn.

#### Endpoints xác nhận
- **POST `/confirm-download/<job_id>`**: Client gọi để xác nhận đã tải xuống thành công.
  ```bash
  curl -X POST http://localhost:8000/confirm-download/test_job_001
  # Response: {"confirmed": true, "job_id": "test_job_001"}
  ```

- **GET `/check-download/<job_id>`**: Handler polling để kiểm tra trạng thái xác nhận.
  ```bash
  curl http://localhost:8000/check-download/test_job_001
  # Response: {"confirmed": true, "timestamp": "2024-01-20T10:30:45.123456"}
  ```

#### Ví dụ luồng đầy đủ (Background Thread Pattern)
```python
# 1. Handler hoàn thành TTS
result = {
    "download_url": "http://api/output/audio.wav",
    "confirmation_url": f"{flask_api_url}/confirm-download/{job_id}"
}

# 2. Start background thread để chờ confirmation (non-blocking)
import threading

def wait_for_confirmation():
    for i in range(60):  # Max 60 giây
        resp = requests.get(f"{flask_api_url}/check-download/{job_id}")
        if resp.json().get("confirmed"):
            print("✓ Client confirmed download")
            return  # Exit thread → pod tắt
        time.sleep(1)
    print("⚠ Timeout - no confirmation received")

# Start thread (daemon=False để giữ pod sống)
threading.Thread(target=wait_for_confirmation, daemon=False).start()

# 3. Return NGAY LẬP TỨC (không chờ)
return result  # RunPod status = COMPLETED ngay
```

#### Lợi ích của Background Thread
- ✅ **Không deadlock**: Handler return ngay → Scheduler nhận COMPLETED ngay (không chờ 60s).
- ✅ **Pod vẫn sống**: Non-daemon thread giữ pod sống cho đến khi nhận confirmation.
- ✅ **Nhanh chóng**: Client download ngay khi thấy COMPLETED (thay vì chờ handler timeout).
- ✅ **Tiết kiệm**: Pod tắt ngay sau confirmation (không chờ hết 60s nếu client confirm sớm).
- ✅ **Backward compatible**: Client cũ không gửi confirmation → thread timeout 60s → pod vẫn tắt bình thường.

### Tính năng Serverless
- Khởi động lạnh: 30-60 giây cho lần yêu cầu đầu tiên.
- Xử lý ấm: 3-5 giây cho các yêu cầu tiếp theo.
- Bộ nhớ GPU: ~10GB VRAM sử dụng.
- Công việc đồng thời: 1 công việc mỗi worker (giới hạn GPU).
- **Timeout xác nhận**: 60 giây (handler chờ client xác nhận tải xuống).

## 🔧 Cài đặt và Triển khai

### Yêu cầu Hệ thống
- Python 3.10+
- Docker và Docker Compose
- GPU NVIDIA (khuyến nghị RTX 3090/4090 với 24GB VRAM)
- CUDA 11.8+

### Cài đặt Phụ thuộc
```bash
pip install -r requirements.optimized.txt
```

### Triển khai Local (Chế độ Kiểm tra)
```bash
cd /home/dtlong/F5-TTS-Vi-Runpod

# Khởi động Flask API trên port 7860
python3 flask_tts_api_optimized.py

# Hoặc sử dụng script
./start_local.sh
```

### Triển khai Docker (Sản xuất)
```bash
cd /home/dtlong/F5-TTS-Vi-Runpod

# Xây dựng image
docker build -f Dockerfile.optimized -t f5-tts-vi-runpod:latest .

# Chạy với GPU
docker run -d \
  --name f5-tts-runpod \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/sample:/app/sample \
  -v $(pwd)/output:/app/output \
  f5-tts-vi-runpod:latest
```

### Triển khai RunPod Serverless (Sản xuất)
1. **Tạo Endpoint Serverless** trên [RunPod Console](https://www.runpod.io/console/serverless):
   - **Container Image:** `tlong94/f5-tts-vi:optimized`
   - **GPU:** RTX 3090/4090 (24GB VRAM khuyến nghị)
   - **Container Disk:** 30GB tối thiểu
   - **Docker Command:** `python -u runpod_handler_simple.py`

2. **Cấu hình Scaling:**
   - **Min Workers:** 0 (tự động tắt để tiết kiệm chi phí)
   - **Max Workers:** 3-5 (tùy lưu lượng)
   - **Idle Timeout:** 10 giây
   - **Execution Timeout:** 600 giây

3. **Kết nối GitHub** để tự động rebuild khi push code.

## 📖 Sử dụng

### API Endpoints
- **POST /tts**: Gửi yêu cầu TTS
  ```json
  {
    "text": "Xin chào thế giới",
    "ref_name": "sample/3_Nu.wav",
    "speed": 0.9,
    "job_id": "unique_job_id"
  }
  ```
- **GET /tts/progress/{job_id}**: Kiểm tra tiến độ
- **GET /output/{filename}**: Tải âm thanh đã tạo

### Ví dụ Kiểm tra
```bash
# Gửi yêu cầu TTS
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào, đây là bản kiểm tra hệ thống F5-TTS tiếng Việt.",
    "ref_name": "3_Nu.wav",
    "speed": 0.8,
    "job_id": "test_job_001"
  }'

# Kiểm tra tiến độ
curl http://localhost:8000/tts/progress/test_job_001

# Tải âm thanh khi hoàn thành
curl -O http://localhost:8000/output/f5tts_20251121_120000_abc123.wav

# Xác nhận tải xuống thành công (để handler kết thúc sớm)
curl -X POST http://localhost:8000/confirm-download/test_job_001
```

### Kiểm tra Webhook Confirmation
```bash
# Chạy script test đầy đủ luồng webhook
cd /home/dtlong/F5-TTS-Vi-Runpod
python test_confirmation_flow.py

# Kết quả mong đợi:
# ✓ Health check: OK
# ✓ Status check: Available
# ✓ Voices check: 3 samples
# ✓ TTS submission: Job submitted
# ✓ TTS completion: Job completed
# ✓ Confirmation before: confirmed=False
# ✓ Download confirmation: Confirmed
# ✓ Confirmation after: confirmed=True
```

### Sử dụng với RunPod
```bash
# Gửi yêu cầu đến RunPod endpoint
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Xin chào Việt Nam",
      "ref_name": "3_Nu.wav",
      "speed": 0.9
    }
  }'

# Kiểm tra trạng thái
curl https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/status/JOB_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 📖 API Reference

### Input

```json
{
  "input": {
    "text": "Vietnamese text to synthesize",
    "ref_name": "main.wav",
    "speed": 0.9,
    "job_id": "optional_custom_id"
  }
}
```

**Parameters:**
- `text` (required): Vietnamese text to synthesize
- `ref_name` (optional): Voice sample file (default: `main.wav`)
- `speed` (optional): Speech speed 0.5-2.0 (default: 0.9)
- `job_id` (optional): Custom job identifier

### Output

```json
{
  "id": "job-id",
  "status": "COMPLETED",
  "output": {
    "audio_base64": "base64_encoded_wav_data",
    "filename": "output.wav",
    "download_url": "http://api/output/audio.wav",
    "confirmation_url": "http://api/confirm-download/job-id",
    "sample_used": "main.wav",
    "processing_time_seconds": 3.5,
    "job_id": "job-id"
  }
}
```

**Output Fields:**
- `audio_base64` (optional): Base64-encoded WAV audio data (for small files)
- `filename`: Generated audio filename
- `download_url`: URL to download audio file
- `confirmation_url` (**NEW**): Webhook URL for client to confirm download completion
- `sample_used`: Voice sample used for synthesis
- `processing_time_seconds`: Total processing time
- `job_id`: Unique job identifier

**Status Values:**
- `IN_QUEUE` - Waiting for worker
- `IN_PROGRESS` - Processing
- `COMPLETED` - Success
- `FAILED` - Error occurred

**Lưu ý về Confirmation URL:**
- Client **nên** gọi `confirmation_url` sau khi tải xuống thành công để handler biết và kết thúc sớm.
- Nếu không gọi, handler sẽ timeout sau 60 giây và vẫn hoàn thành (không lỗi).
- Format: `POST {confirmation_url}` (không cần body)

---

## 🔄 Switching Between Modes

### Architecture

All modes use the **same Flask API**, just different ports and startup methods:

```
┌─────────────────────────────────────────┐
│         Flask TTS API Server            │
│  (flask_tts_api_optimized.py)          │
│                                         │
│  - /health      - Health check         │
│  - /voices      - List voices          │
│  - /tts         - Submit job (POST)    │
│  - /tts/progress - Check progress      │
│  - /output/:id  - Download audio       │
└─────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
    Port 7860      Port 8000      Port 8000
    (Local)        (Docker)       (RunPod+Handler)
```

### Quick Switch Guide

```bash
# Local Testing (7860)
cd /home/dtlong/F5-TTS-Vi
./start_local.sh
# → Edit .env: F5_TTS_API_URL=http://localhost:7860

# Docker Production (8000)
./start_docker_mode.sh
# OR
docker run -p 8000:8000 f5-tts-local
# → Edit .env: F5_TTS_API_URL=http://localhost:8000

# RunPod Serverless
# Push to Docker Hub, deploy on RunPod
# → Edit .env: Enable RunPod in orchestrator.ts
```

---

## 🛠️ Build & Deploy

### Local Build

```bash
cd /home/dtlong/F5-TTS-Vi

# Ensure scripts are executable
chmod +x entrypoint.sh start_local.sh start_docker_mode.sh test_api.sh

# 3. Build Docker image
docker build -f Dockerfile.optimized -t f5-tts-vi:optimized .

# 4. Test locally
docker run --gpus all -p 8000:8000 f5-tts-vi:optimized

# 5. Test health check
curl http://localhost:8000/health
```

### Push to Docker Hub

```bash
# 1. Tag image
docker tag f5-tts-vi:optimized YOUR_USERNAME/f5-tts-vi:optimized

# 2. Login to Docker Hub
docker login

# 3. Push image
docker push YOUR_USERNAME/f5-tts-vi:optimized
```

---

## 🔧 Local Development

### Run Flask API Only

```bash
# Install dependencies
pip install -r requirements.optimized.txt

# Start Flask API
python3 flask_tts_api_optimized.py

# API available at http://localhost:8000
```

### Test TTS Generation

```bash
# Submit job
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Xin chào",
    "ref_name": "main.wav",
    "speed": 0.9,
    "job_id": "test_123"
  }'

# Check progress
curl http://localhost:8000/tts/progress/test_123

# Download audio
curl http://localhost:8000/output/test_123.wav -o output.wav
```

---

## 📁 Project Structure

```
F5-TTS-Vi-Runpod/
├── Dockerfile.optimized          # Production Docker build
├── entrypoint.sh                 # Container startup script
├── flask_tts_api_optimized.py    # Flask HTTP API server
├── runpod_handler_simple.py      # RunPod handler integration
├── requirements.optimized.txt    # Python dependencies
├── Todo_F5_TTS_Runpod.md         # Development roadmap
├── f5_tts/                       # F5-TTS source code
│   ├── api.py                    # Main F5-TTS inference API
│   ├── socket_server.py         # Real-time streaming TTS server
│   ├── eval/                     # Model evaluation scripts
│   ├── infer/                    # Inference utilities and examples
│   └── model/                    # Core model architecture (DiT, UNetT, CFM)
├── sample/                       # Voice reference samples
│   ├── 1_Nam_v1.1.wav           # Male voice v1.1 (improved quality)
│   ├── 3_Nam.wav                # Male voice 3
│   ├── 3_Nu.wav                 # Female voice 3
│   ├── 4_Nam_speed_1.1.wav      # Male voice 4 with speed adjustment
│   ├── 4_Nu_speed_1.wav         # Female voice 4 with speed adjustment
│   ├── 5_Nam_speed_1.wav        # Male voice 5 with speed adjustment
│   ├── Lat_Radio_v1.1.wav       # Radio-style voice v1.1
│   └── Ta_Hoi_Audio_v1.1.wav    # Conversational voice v1.1
└── output/                      # Generated audio files and progress tracking
```

### Voice Samples Description

**Available Voice References:**
- `1_Nam_v1.1`: Nam giọng nam nâng cấp (improved male voice)
- `3_Nam`: Nam giọng nam cơ bản (basic male voice)
- `3_Nu`: Nữ giọng nữ cơ bản (basic female voice)
- `4_Nam_speed_1.1`: Nam giọng nam với điều chỉnh tốc độ (male voice with speed tuning)
- `4_Nu_speed_1`: Nữ giọng nữ với điều chỉnh tốc độ (female voice with speed tuning)
- `5_Nam_speed_1`: Nam giọng nam tốc độ (male voice optimized for speed)
- `Lat_Radio_v1.1`: Giọng phát thanh radio nâng cấp (improved radio announcer voice)
- `Ta_Hoi_Audio_v1.1`: Giọng hội thoại nâng cấp (improved conversational voice)

**Usage:** Use the filename (without .wav extension) as the `ref_name` parameter in API calls.

---

## 🔍 Architecture

```
┌─────────────────────────────────────────┐
│   RunPod Serverless Platform            │
│   ┌─────────────────────────────────┐   │
│   │  Worker Container               │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  Flask API (port 8000)   │   │   │
│   │  │  • /tts - Submit job     │   │   │
│   │  │  • /tts/progress/{id}    │   │   │
│   │  │  • /output/{file}        │   │   │
│   │  │  • /health               │   │   │
│   │  └──────────────────────────┘   │   │
│   │            ↕                     │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  F5-TTS Model (GPU)      │   │   │
│   │  │  • Model inference       │   │   │
│   │  │  • Audio synthesis       │   │   │
│   │  └──────────────────────────┘   │   │
│   │            ↕                     │   │
│   │  ┌──────────────────────────┐   │   │
│   │  │  RunPod Handler          │   │   │
│   │  │  • Job orchestration     │   │   │
│   │  │  • Base64 encoding       │   │   │
│   │  └──────────────────────────┘   │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Flow:**
1. Client sends job to RunPod API
2. RunPod handler receives job
3. Handler calls Flask API (localhost:8000)
4. Flask processes TTS with F5-TTS model
5. Handler polls for completion
6. Handler downloads audio, encodes base64
7. Handler returns result to RunPod
8. Client retrieves result via RunPod API

---

## 📊 Performance

- **Cold Start:** 30-60 seconds (first request after worker start)
- **Warm Processing:** 3-5 seconds per request
- **GPU Memory:** ~10GB VRAM
- **Image Size:** 27GB
- **Concurrent Jobs:** 1 per worker (GPU limitation)

---

## 🐛 Troubleshooting

### Job Stays IN_QUEUE

**Problem:** Job never processes

**Solutions:**
- Check worker availability in RunPod console
- Verify GPU is enabled in endpoint settings
- Ensure workers are not at max limit
- Check RunPod logs for startup errors

### Worker Fails to Start

**Problem:** Container crashes on initialization

**Solutions:**
- Ensure GPU has 12GB+ VRAM
- Verify Docker image exists: `tlong94/f5-tts-vi:optimized`
- Check RunPod logs for error messages
- Increase container disk size to 30GB+

### Audio Quality Issues

**Problem:** Generated audio sounds wrong

**Solutions:**
- Adjust `speed` parameter (try 0.7-1.0)
- Use different voice sample (`ref_name`)
- Ensure input text is clean Vietnamese
- Check for special characters or formatting

### Health Check Fails

**Problem:** `/health` endpoint returns error

**Solutions:**
- Wait 30-60 seconds for initialization
- Check Flask API logs in container
- Verify port 8000 is not blocked
- Restart worker in RunPod console

---

## 🔗 Integration Examples

### Python Client

```python
import requests
import base64
import json

class RunPodTTS:
    def __init__(self, api_key, endpoint_id):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    
    def submit_job(self, text, voice="main", speed=0.9):
        response = requests.post(
            f"{self.base_url}/run",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": {
                    "text": text,
                    "ref_name": f"{voice}.wav",
                    "speed": speed
                }
            }
        )
        return response.json()["id"]
    
    def get_status(self, job_id):
        response = requests.get(
            f"{self.base_url}/status/{job_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    def download_audio(self, job_id, output_file):
        import time
        while True:
            status = self.get_status(job_id)
            if status["status"] == "COMPLETED":
                audio_data = base64.b64decode(status["output"]["audio_base64"])
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                return True
            elif status["status"] == "FAILED":
                raise Exception("Job failed")
            time.sleep(2)

# Usage
client = RunPodTTS("your_api_key", "your_endpoint_id")
job_id = client.submit_job("Xin chào Việt Nam")
client.download_audio(job_id, "output.wav")
```

### Node.js/TypeScript Client

```typescript
interface RunPodInput {
  text: string;
  ref_name?: string;
  speed?: number;
}

class RunPodTTSClient {
  private apiKey: string;
  private endpointId: string;
  private baseUrl: string;

  constructor(apiKey: string, endpointId: string) {
    this.apiKey = apiKey;
    this.endpointId = endpointId;
    this.baseUrl = `https://api.runpod.ai/v2/${endpointId}`;
  }

  async submitJob(input: RunPodInput): Promise<string> {
    const response = await fetch(`${this.baseUrl}/run`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input: {
          text: input.text,
          ref_name: input.ref_name || 'main.wav',
          speed: input.speed || 0.9
        }
      })
    });
    const data = await response.json();
    return data.id;
  }

  async getStatus(jobId: string) {
    const response = await fetch(`${this.baseUrl}/status/${jobId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });
    return await response.json();
  }

  async waitForCompletion(jobId: string, timeout = 300000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const status = await this.getStatus(jobId);
      if (status.status === 'COMPLETED') return status.output;
      if (status.status === 'FAILED') throw new Error('Job failed');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    throw new Error('Timeout');
  }
}

// Usage
const client = new RunPodTTSClient('your_api_key', 'your_endpoint_id');
const jobId = await client.submitJob({ text: 'Xin chào' });
const output = await client.waitForCompletion(jobId);
const audioBuffer = Buffer.from(output.audio_base64, 'base64');
```

---

## 🎯 Production Best Practices

### RunPod Configuration with Webhook

**Architecture:**
- RunPod handler sends **webhook notification** to Next.js when job completes
- Next.js downloads audio **immediately** upon receiving webhook
- Handler waits for **download confirmation** before returning COMPLETED
- Pod stays alive until confirmation received (max 90s)

**Why Webhook?**
- ✅ **Instant notification**: No polling delay
- ✅ **Guaranteed download**: Pod waits for confirmation
- ✅ **No race condition**: Download happens before pod shutdown
- ✅ **Reduced API calls**: No need to poll RunPod status API frequently

**Flow:**
1. Handler completes TTS → sends webhook to Next.js
2. Next.js receives webhook → downloads audio immediately
3. Next.js saves file → sends confirmation to handler
4. Handler receives confirmation → returns COMPLETED
5. RunPod removes job → pod shutdown

**Configuration:**
- **Idle Timeout:** 10 seconds (default)
- **Webhook URL:** Set `NEXTJS_WEBHOOK_URL` env var in RunPod
- **Confirmation Timeout:** 60 seconds (handler waits max 60s)
- **Webhook Endpoint:** `POST /api/runpod-webhook` in Next.js

**Max Concurrent Jobs:** Configure in Admin UI (default: 4)
- Limits total active jobs (waiting + processing)
- Prevents overwhelming RunPod with too many workers
- Jobs queue as `pending` when limit reached

### Status Flow

```
pending → waiting → processing → completed/failed
   ↓         ↓          ↓            ↓
Created   Sent to   RunPod      Download
          RunPod    accepted    success/error
```

**Timeout:** 60 minutes per job
- Jobs stuck in `processing` > 60 min auto-marked `failed`
- Prevents zombie jobs consuming slots

### Error Handling

**Idempotency:** Handler tracks processed job IDs in memory
- Prevents duplicate processing if job sent to multiple workers
- Returns `status: "duplicate"` for already-processed jobs

**Download Fallback:** Handler supports both formats
- Primary: `download_url` (preferred, smaller response)
- Fallback: `audio_base64` (if download_url fails)

**Retry Logic:** Failed jobs rollback to `pending`
- Temporary errors (503, network issues) → Retry
- Permanent errors (invalid input) → Marked `failed`

### Monitoring

**Health Check:** Every 5 minutes
```bash
curl -f http://localhost:8000/health || exit 1
```

**Logs:** Check RunPod console for:
- Worker initialization errors
- Job processing failures  
- Memory/GPU issues

**Metrics:**
- Average processing time: 200-400 seconds
- GPU utilization: 80-95% during processing
- Memory usage: ~8-10GB per worker

---

## 🐛 Known Issues & Solutions

### Issue: Worker tắt sớm trước khi client tải xuống (404 Error)

**Cause:** RunPod idle timeout 10s → worker tắt trước khi Next.js tải audio  
**Solution:** ✅ **Webhook confirmation mechanism** (implemented)
- Handler chờ client xác nhận tải xuống (tối đa 60s)
- Client gửi POST đến `confirmation_url` sau khi tải xong
- Worker chỉ tắt sau khi nhận confirmation hoặc timeout 60s

**Testing:**
```bash
python test_confirmation_flow.py
# Expected: All 7 tests pass, handler waits for confirmation
```

### Issue: "400 Bad Request" when returning job results

**Cause:** Response too large (base64 audio > 10MB)  
**Solution:** Switched to `download_url` instead of `audio_base64`

### Issue: Confirmation timeout (handler chờ 60s mà không có response)

**Cause:** Client không gọi `confirmation_url` (old client hoặc network issue)  
**Solution:** Backward compatible - handler timeout gracefully sau 60s và vẫn trả về success
- Không throw error
- Log warning: "Download confirmation not received, proceeding anyway"
- Client có thể retry nếu cần

**Debugging:**
```bash
# Kiểm tra trạng thái confirmation
curl http://localhost:8000/check-download/YOUR_JOB_ID

# Nếu confirmed=false sau khi tải xong → gọi lại confirm
curl -X POST http://localhost:8000/confirm-download/YOUR_JOB_ID
```

### Issue: One job triggers multiple workers

**Cause:** Race condition with fast polling (1s interval)  
**Solution:** Atomic lock - mark jobs as `waiting` before sending to RunPod

### Issue: Job marked `failed` but audio exists

**Cause:** Error after successful download overwrites `completed` status  
**Solution:** Check if job already `completed` before marking `failed`

### Issue: Download fails with 404

**Cause:** Worker terminated before Next.js downloaded audio  
**Solution:** Increased idle timeout to 10s + faster polling (1s)

---

## 📝 License

MIT License

## 🙏 Credits

- **F5-TTS:** [SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)
- **Vietnamese Model:** ViVoice Dataset (100h training data)
- **Platform:** [RunPod](https://runpod.io) Serverless GPU
- **Model Weights:** [hynt/F5-TTS-Vietnamese-ViVoice](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice)

---

## 📚 Related Projects

- **Next.js Frontend:** [Starter-Prisma-Pro](../Starter-Prisma-Pro)
- **Docker Hub:** [tlong94/f5-tts-vi](https://hub.docker.com/r/tlong94/f5-tts-vi)
- **GitHub:** [ynmaster-tl/F5-TTS-Vi](https://github.com/ynmaster-tl/F5-TTS-Vi)

---

## ⚙️ Cấu hình và Biến Môi trường

### Biến Môi trường Container
- `FLASK_HOST`, `FLASK_PORT`: Cấu hình máy chủ Flask (mặc định: 0.0.0.0:8000)
- `REF_VOICE_DIR`: Thư mục chứa mẫu giọng nói (mặc định: ./sample)
- `OUTPUT_AUDIO_DIR`: Thư mục lưu âm thanh đầu ra (mặc định: ./output)

### Cấu hình Mô hình
- **Checkpoint**: `hynt/F5-TTS-Vietnamese-ViVoice` (model_last.pt)
- **Vocoder**: Vocos (mặc định)
- **Tốc độ mẫu**: 24kHz
- **Thiết bị**: CUDA (tự động phát hiện GPU)

### Cấu hình RunPod
- **RUNPOD_POD_ID**: ID của pod RunPod (tự động)
- **RUNPOD_ENDPOINT_ID**: ID endpoint serverless

---

**Cập nhật lần cuối:** Tháng 11, 2025  
**Phiên bản:** 2.0.0 - Sẵn sàng sản xuất  
**Trạng thái:** ✅ Đã triển khai trên RunPod Serverless
