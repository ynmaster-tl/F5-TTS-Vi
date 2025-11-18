# DEPLOYMENT GUIDE - F5-TTS Vietnamese

Guide triển khai F5-TTS trên máy khác sử dụng Docker.

---

## 📋 Yêu Cầu Hệ Thống

### Phần cứng
- **GPU:** NVIDIA GPU với 12GB+ VRAM (RTX 3090/4090 khuyến nghích)
- **RAM:** 16GB+ 
- **Disk:** 40GB+ trống
- **CUDA:** 11.8 hoặc mới hơn

### Phần mềm
- **OS:** Ubuntu 20.04/22.04 hoặc compatible Linux
- **Docker:** 20.10+ với GPU support
- **NVIDIA Driver:** 525+ (hỗ trợ CUDA 11.8)
- **nvidia-docker2:** Đã cài đặt

---

## 🚀 Hướng Dẫn Triển Khai

### Bước 1: Kiểm tra GPU

```bash
# Kiểm tra driver NVIDIA
nvidia-smi

# Kiểm tra Docker có nhận GPU không
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

Nếu lỗi, cài đặt nvidia-docker2:

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Bước 2: Pull Docker Image

```bash
# Pull image từ Docker Hub (27GB, cần 10-20 phút)
docker pull tlong94/f5-tts-vi:optimized

# Hoặc pull version cụ thể
docker pull tlong94/f5-tts-vi:v2.0.0

# Kiểm tra image
docker images tlong94/f5-tts-vi
```

### Bước 3: Tạo Thư Mục Dữ Liệu

```bash
# Tạo thư mục cho sample và output
mkdir -p ~/f5-tts-data/{sample,output}

# Copy file voice sample (nếu có)
# Hoặc tải từ repository
cd ~/f5-tts-data/sample
wget https://github.com/ynmaster-tl/F5-TTS-Vi/raw/main/sample/main.wav
wget https://github.com/ynmaster-tl/F5-TTS-Vi/raw/main/sample/female.wav
wget https://github.com/ynmaster-tl/F5-TTS-Vi/raw/main/sample/male.wav
```

### Bước 4: Chạy Container

#### Mode 1: Flask API Only (cho Local Use)

```bash
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 8000:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  -e RUNPOD_MODE=false \
  --restart unless-stopped \
  tlong94/f5-tts-vi:optimized
```

#### Mode 2: RunPod Handler Mode

```bash
docker run -d \
  --name f5-tts-runpod \
  --gpus all \
  -p 8000:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  -e RUNPOD_MODE=true \
  -e RUNPOD_API_KEY=your_api_key \
  -e RUNPOD_ENDPOINT_ID=your_endpoint_id \
  --restart unless-stopped \
  tlong94/f5-tts-vi:optimized
```

### Bước 5: Kiểm Tra Health

```bash
# Đợi 30-60 giây để model load
sleep 60

# Kiểm tra health
curl http://localhost:8000/health

# Xem logs
docker logs -f f5-tts-api

# Kiểm tra GPU usage
nvidia-smi
```

### Bước 6: Test TTS

```bash
# Submit job
JOB_ID="test_$(date +%s)"
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d "{
    \"text\": \"Xin chào, đây là bản kiểm tra hệ thống F5-TTS tiếng Việt.\",
    \"ref_name\": \"main.wav\",
    \"speed\": 0.9,
    \"job_id\": \"$JOB_ID\"
  }"

# Kiểm tra progress
curl http://localhost:8000/tts/progress/$JOB_ID

# Download audio khi completed
curl http://localhost:8000/output/${JOB_ID}.wav -o test_output.wav
```

---

## 🔧 Cấu Hình Nâng Cao

### Thay Đổi Port

```bash
# Chạy trên port khác (ví dụ 7860)
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 7860:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  tlong94/f5-tts-vi:optimized

# Test
curl http://localhost:7860/health
```

### Resource Limits

```bash
# Giới hạn GPU memory và CPU
docker run -d \
  --name f5-tts-api \
  --gpus '"device=0"' \
  --memory="16g" \
  --cpus="4" \
  -p 8000:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  tlong94/f5-tts-vi:optimized
```

### Auto-restart on Boot

```bash
# Container sẽ tự động start khi khởi động lại máy
docker update --restart=always f5-tts-api
```

---

## 🐛 Troubleshooting

### Container không start

```bash
# Xem logs
docker logs f5-tts-api

# Common issues:
# 1. GPU không available → Cài nvidia-docker2
# 2. Port 8000 đã dùng → Đổi port: -p 8001:8000
# 3. Out of memory → Tắt app khác, hoặc giảm GPU usage
```

### Health check fail

```bash
# Vào trong container check
docker exec -it f5-tts-api bash

# Test Flask từ bên trong
curl localhost:8000/health

# Kiểm tra process
ps aux | grep flask
ps aux | grep python

# Kiểm tra port
netstat -tuln | grep 8000
```

### Model load chậm

```bash
# Model cần 30-60s để load lần đầu
# Xem progress trong logs
docker logs -f f5-tts-api

# Nếu thấy "Model loaded successfully" → OK
# Nếu không thấy sau 5 phút → Restart container
```

### Out of GPU memory

```bash
# Kiểm tra GPU usage
nvidia-smi

# Nếu >20GB → Có thể có process khác đang dùng GPU
# Kill process hoặc restart container:
docker restart f5-tts-api
```

---

## 📊 Monitoring

### Check Container Status

```bash
# Container status
docker ps -f name=f5-tts-api

# Resource usage
docker stats f5-tts-api

# GPU usage
watch -n 1 nvidia-smi
```

### Log Monitoring

```bash
# Real-time logs
docker logs -f f5-tts-api

# Last 100 lines
docker logs --tail 100 f5-tts-api

# Search for errors
docker logs f5-tts-api 2>&1 | grep -i error
```

---

## 🔄 Update Image

### Pull New Version

```bash
# Stop container
docker stop f5-tts-api
docker rm f5-tts-api

# Pull new image
docker pull tlong94/f5-tts-vi:optimized

# Start with new image
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 8000:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  --restart unless-stopped \
  tlong94/f5-tts-vi:optimized
```

---

## 🔐 Security

### Firewall Configuration

```bash
# Chỉ cho phép truy cập từ localhost
# Dùng nginx/caddy làm reverse proxy nếu cần expose ra ngoài

# Example với ufw:
sudo ufw allow 8000/tcp
sudo ufw enable
```

### API Key Protection

Nếu expose ra internet, nên thêm API key authentication:
- Sử dụng nginx với basic auth
- Hoặc thêm middleware vào Flask API
- Hoặc dùng Cloudflare Tunnel

---

## 📈 Performance Tuning

### Optimize for Speed

```bash
# Tăng số worker threads (nếu có nhiều GPU)
docker run -d \
  --name f5-tts-api \
  --gpus all \
  -p 8000:8000 \
  -v ~/f5-tts-data/sample:/app/sample \
  -v ~/f5-tts-data/output:/app/output \
  -e WORKERS=2 \
  tlong94/f5-tts-vi:optimized
```

### Benchmark

```bash
# Test processing time
time curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test performance",
    "job_id": "bench_'$(date +%s)'"
  }'

# Expected: 3-5s for short text, 200-400s for long text
```

---

## 📞 Support

- **GitHub Issues:** https://github.com/ynmaster-tl/F5-TTS-Vi/issues
- **Docker Hub:** https://hub.docker.com/r/tlong94/f5-tts-vi
- **Documentation:** https://github.com/ynmaster-tl/F5-TTS-Vi/blob/main/README.md

---

**Last Updated:** November 18, 2025  
**Version:** 2.0.0  
**Docker Image:** tlong94/f5-tts-vi:optimized (27GB)
