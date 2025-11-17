# A unified script for inference process
# Make adjustments inside functions, and consider both gradio and cli scripts if need to change func output format
import os
import sys

os.environ["PYTOCH_ENABLE_MPS_FALLBACK"] = "1"  # for MPS device compatibility
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../third_party/BigVGAN/")

import hashlib
import re
import tempfile
from importlib.resources import files

import matplotlib

matplotlib.use("Agg")

import matplotlib.pylab as plt
import numpy as np
import torch
import torchaudio
import tqdm
from huggingface_hub import snapshot_download, hf_hub_download
from pydub import AudioSegment, silence
from transformers import pipeline
from vocos import Vocos

from f5_tts.model import CFM
from f5_tts.model.utils import (
    get_tokenizer,
    convert_char_to_pinyin,
)

# Global cache for ASR transcriptions
_ref_audio_cache = {}

def choose_device_dynamic(gpu_memory_threshold_gb=2.0, gpu_utilization_threshold=80):
    """
    Chọn device động dựa trên load của GPU.
    Nếu GPU available, kiểm tra memory free và utilization.
    Nếu memory free < threshold hoặc utilization > threshold, dùng CPU.
    """
    if torch.cuda.is_available():
        try:
            # Kiểm tra memory free
            free, total = torch.cuda.mem_get_info()
            free_gb = free / (1024**3)
            if free_gb < gpu_memory_threshold_gb:
                print(f"GPU memory low ({free_gb:.2f}GB free), falling back to CPU")
                return "cpu"
            
            # Nếu có pynvml, kiểm tra utilization
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                if util.gpu > gpu_utilization_threshold:
                    print(f"GPU utilization high ({util.gpu}%), falling back to CPU")
                    pynvml.nvmlShutdown()
                    return "cpu"
                pynvml.nvmlShutdown()
            except ImportError:
                print("pynvml not installed, skipping utilization check")
            except Exception as e:
                print(f"Error checking GPU utilization: {e}")
            
            return "cuda"
        except Exception as e:
            print(f"Error checking GPU memory: {e}, falling back to CPU")
            return "cpu"
    elif torch.xpu.is_available():
        return "xpu"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"

device = choose_device_dynamic()

# -----------------------------------------

target_sample_rate = 24000
n_mel_channels = 100
hop_length = 256
win_length = 1024
n_fft = 1024
mel_spec_type = "vocos"
target_rms = 0.1
cross_fade_duration = 0.15
ode_method = "euler"
nfe_step = 32  # 16, 32
cfg_strength = 2.0
sway_sampling_coef = -1.0
speed = 1.0
fix_duration = None

# -----------------------------------------


# chunk text into smaller pieces


def chunk_text(text: str, max_chars: int = 370, min_chars: int = 40):
    """
    Chia nhỏ văn bản dựa trên dấu câu, ưu tiên ngắt thành từng câu riêng biệt.
    Chỉ ghép câu ngắn (dưới min_chars) với câu tiếp theo nếu kết quả ghép không vượt max_chars.
    
    Tham số:
    - text (str): Văn bản đầu vào.
    - max_chars (int): Chiều dài ký tự tối đa cho mỗi đoạn.
    - min_chars (int): Chiều dài ký tự tối thiểu cho một đoạn trước khi cố gắng ghép.
    """
    
    # Bước 1: Tách văn bản thành các câu/mệnh đề dựa trên dấu câu mạnh.
    # [.] [?] [!] [:] [\n] là ranh giới câu.
    sentences = re.split(r'([.?!:\n])', text)
    full_sentences = []
    current_sentence = ""

    for part in sentences:
        if not part.strip() and part != '\n':
            continue
        
        # Nếu là dấu câu mạnh (kết thúc câu)
        if re.match(r'[.?!:\n]', part):
            if current_sentence:
                current_sentence += part
                # Làm sạch khoảng trắng dư thừa
                full_sentences.append(" ".join(current_sentence.strip().split())) 
            current_sentence = ""
        else:
            # Nối phần tiếp theo, thêm khoảng trắng nếu cần
            # Kiểm tra nếu câu hiện tại không kết thúc bằng dấu đóng ngoặc kép/ngăn cách, thêm khoảng trắng.
            if current_sentence and not current_sentence.endswith(tuple('”)"')) and not current_sentence.endswith(tuple(' \t\n')):
                current_sentence += " "
            current_sentence += part.strip()
            
    if current_sentence:
        # Làm sạch khoảng trắng dư thừa
        full_sentences.append(" ".join(current_sentence.strip().split()))
    
    # Nếu không có câu nào, trả về rỗng
    if not full_sentences:
        return []

    # --- Bước 2: Ghép các câu nhỏ và Tách các câu quá dài ---
    final_chunks = []
    i = 0
    while i < len(full_sentences):
        sentence = full_sentences[i]
        
        # 1. Xử lý câu quá dài (> max_chars)
        if len(sentence) > max_chars:
            
            # Cắt câu quá dài thành nhiều đoạn, ưu tiên ngắt nghỉ tại dấu câu yếu (nếu có)
            start = 0
            while start < len(sentence):
                segment = sentence[start:start + max_chars]
                split_point = len(segment) 
                
                # Tìm điểm ngắt tốt nhất trong 70 ký tự cuối
                for j in range(len(segment) - 1, max(0, len(segment) - 70), -1):
                    char = segment[j]
                    if char in [',', ';']: # Ưu tiên phẩy, chấm phẩy
                        split_point = j + 1
                        break
                    # Sau đó là khoảng trắng
                    elif char.isspace() and (len(segment) - j) < 50: 
                        split_point = j + 1
                        break
                    
                final_chunks.append(segment[:split_point].strip())
                start += split_point
            i += 1
            
        # 2. Xử lý câu ngắn (< min_chars) và cố gắng ghép
        elif len(sentence) < min_chars and i < len(full_sentences) - 1:
            next_sentence = full_sentences[i+1]
            merged_sentence = sentence + " " + next_sentence
            
            # Nếu ghép không vượt quá max_chars
            if len(merged_sentence) <= max_chars:
                # Thực hiện ghép và tiếp tục kiểm tra câu ghép này ở vòng lặp sau
                full_sentences[i+1] = merged_sentence
                i += 1 
            else:
                # Nếu ghép vượt quá max_chars, không ghép (giữ nguyên câu ngắn)
                final_chunks.append(sentence)
                i += 1
            
        # 3. Câu có độ dài hợp lệ hoặc câu cuối cùng
        else:
            final_chunks.append(sentence)
            i += 1

    return final_chunks


# load vocoder
def load_vocoder(vocoder_name="vocos", is_local=False, local_path="", device=device, hf_cache_dir=None):
    if vocoder_name == "vocos":
        # vocoder = Vocos.from_pretrained("charactr/vocos-mel-24khz").to(device)
        if is_local:
            print(f"Load vocos from local path {local_path}")
            config_path = f"{local_path}/config.yaml"
            model_path = f"{local_path}/pytorch_model.bin"
        else:
            print("Download Vocos from huggingface charactr/vocos-mel-24khz")
            repo_id = "charactr/vocos-mel-24khz"
            config_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="config.yaml")
            model_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="pytorch_model.bin")
        # print("Download Vocos from huggingface charactr/vocos-mel-24khz")
        # repo_id = "charactr/vocos-mel-24khz"
        # config_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="config.yaml")
        # model_path = hf_hub_download(repo_id=repo_id, cache_dir=hf_cache_dir, filename="pytorch_model.bin")
        vocoder = Vocos.from_hparams(config_path)
        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
        # print(state_dict)
        from vocos.feature_extractors import EncodecFeatures

        if isinstance(vocoder.feature_extractor, EncodecFeatures):
            encodec_parameters = {
                "feature_extractor.encodec." + key: value
                for key, value in vocoder.feature_extractor.encodec.state_dict().items()
            }
            state_dict.update(encodec_parameters)
        vocoder.load_state_dict(state_dict)
        vocoder = vocoder.eval().to(device)
    elif vocoder_name == "bigvgan":
        try:
            from third_party.BigVGAN import bigvgan
        except ImportError:
            print("You need to follow the README to init submodule and change the BigVGAN source code.")
        if is_local:
            """download from https://huggingface.co/nvidia/bigvgan_v2_24khz_100band_256x/tree/main"""
            vocoder = bigvgan.BigVGAN.from_pretrained(local_path, use_cuda_kernel=False)
        else:
            local_path = snapshot_download(repo_id="nvidia/bigvgan_v2_24khz_100band_256x", cache_dir=hf_cache_dir)
            vocoder = bigvgan.BigVGAN.from_pretrained(local_path, use_cuda_kernel=False)

        vocoder.remove_weight_norm()
        vocoder = vocoder.eval().to(device)
    return vocoder


# load asr pipeline

asr_pipe = None


def initialize_asr_pipeline(device: str = device, dtype=None):
    if dtype is None:
        dtype = (
            torch.float16
            if "cuda" in device
            and torch.cuda.get_device_properties(device).major >= 6
            and not torch.cuda.get_device_name().endswith("[ZLUDA]")
            else torch.float32
        )
    global asr_pipe
    asr_pipe = pipeline(
        "automatic-speech-recognition",
        model="vinai/PhoWhisper-medium",
        torch_dtype=dtype,
        device=device,
    )


# transcribe


def transcribe(ref_audio, language=None):
    global asr_pipe
    if asr_pipe is None:
        initialize_asr_pipeline(device=device)
    return asr_pipe(
        ref_audio,
        chunk_length_s=30,
        batch_size=128,
        generate_kwargs={"task": "transcribe", "language": language} if language else {"task": "transcribe"},
        return_timestamps=False,
    )["text"].strip()


# load model checkpoint for inference


def load_checkpoint(model, ckpt_path, device: str, dtype=None, use_ema=True):
    if dtype is None:
        dtype = (
            torch.float16
            if "cuda" in device
            and torch.cuda.get_device_properties(device).major >= 6
            and not torch.cuda.get_device_name().endswith("[ZLUDA]")
            else torch.float32
        )
    model = model.to(dtype)

    ckpt_type = ckpt_path.split(".")[-1]
    if ckpt_type == "safetensors":
        from safetensors.torch import load_file

        checkpoint = load_file(ckpt_path, device=device)
    else:
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)

    if use_ema:
        if ckpt_type == "safetensors":
            checkpoint = {"ema_model_state_dict": checkpoint}
        checkpoint["model_state_dict"] = {
            k.replace("ema_model.", ""): v
            for k, v in checkpoint["ema_model_state_dict"].items()
            if k not in ["initted", "step"]
        }

        # patch for backward compatibility, 305e3ea
        for key in ["mel_spec.mel_stft.mel_scale.fb", "mel_spec.mel_stft.spectrogram.window"]:
            if key in checkpoint["model_state_dict"]:
                del checkpoint["model_state_dict"][key]

        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        if ckpt_type == "safetensors":
            checkpoint = {"model_state_dict": checkpoint}
        model.load_state_dict(checkpoint["model_state_dict"])

    del checkpoint
    torch.cuda.empty_cache()

    return model.to(device)


# load model for inference


def load_model(
    model_cls,
    model_cfg,
    ckpt_path,
    mel_spec_type=mel_spec_type,
    vocab_file="",
    ode_method=ode_method,
    use_ema=True,
    device=device,
):
    if vocab_file == "":
        vocab_file = str(files("f5_tts").joinpath("infer/examples/vocab.txt"))
    tokenizer = "custom"

    print("\nvocab : ", vocab_file)
    print("token : ", tokenizer)
    print("model : ", ckpt_path, "\n")

    vocab_char_map, vocab_size = get_tokenizer(vocab_file, tokenizer)
    model = CFM(
        transformer=model_cls(**model_cfg, text_num_embeds=vocab_size, mel_dim=n_mel_channels),
        mel_spec_kwargs=dict(
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length,
            n_mel_channels=n_mel_channels,
            target_sample_rate=target_sample_rate,
            mel_spec_type=mel_spec_type,
        ),
        odeint_kwargs=dict(
            method=ode_method,
        ),
        vocab_char_map=vocab_char_map,
    ).to(device)

    dtype = torch.float32 if mel_spec_type == "bigvgan" else None
    model = load_checkpoint(model, ckpt_path, device, dtype=dtype, use_ema=use_ema)

    return model


def remove_silence_edges(audio, silence_threshold=-42):
    # Remove silence from the start
    non_silent_start_idx = silence.detect_leading_silence(audio, silence_threshold=silence_threshold)
    audio = audio[non_silent_start_idx:]

    # Remove silence from the end
    non_silent_end_duration = audio.duration_seconds
    for ms in reversed(audio):
        if ms.dBFS > silence_threshold:
            break
        non_silent_end_duration -= 0.001
    trimmed_audio = audio[: int(non_silent_end_duration * 1000)]

    return trimmed_audio


# preprocess reference audio and text


def preprocess_ref_audio_text(ref_audio_orig, ref_text, clip_short=True, show_info=print, device=device):
    show_info("Converting audio...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        aseg = AudioSegment.from_file(ref_audio_orig)

        if clip_short:
            # 1. try to find long silence for clipping
            non_silent_segs = silence.split_on_silence(
                aseg, min_silence_len=1000, silence_thresh=-50, keep_silence=1000, seek_step=10
            )
            non_silent_wave = AudioSegment.silent(duration=0)
            for non_silent_seg in non_silent_segs:
                if len(non_silent_wave) > 6000 and len(non_silent_wave + non_silent_seg) > 15000:
                    show_info("Audio is over 15s, clipping short. (1)")
                    break
                non_silent_wave += non_silent_seg

            # 2. try to find short silence for clipping if 1. failed
            if len(non_silent_wave) > 15000:
                non_silent_segs = silence.split_on_silence(
                    aseg, min_silence_len=100, silence_thresh=-40, keep_silence=1000, seek_step=10
                )
                non_silent_wave = AudioSegment.silent(duration=0)
                for non_silent_seg in non_silent_segs:
                    if len(non_silent_wave) > 6000 and len(non_silent_wave + non_silent_seg) > 15000:
                        show_info("Audio is over 15s, clipping short. (2)")
                        break
                    non_silent_wave += non_silent_seg

            aseg = non_silent_wave

            # 3. if no proper silence found for clipping
            if len(aseg) > 15000:
                aseg = aseg[:15000]
                show_info("Audio is over 15s, clipping short. (3)")

        aseg = remove_silence_edges(aseg) + AudioSegment.silent(duration=50)
        aseg.export(f.name, format="wav")
        ref_audio = f.name

    # Compute a hash of the reference audio file
    with open(ref_audio, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_hash = hashlib.md5(audio_data).hexdigest()

    if not ref_text.strip():
        global _ref_audio_cache
        if audio_hash in _ref_audio_cache:
            # Use cached asr transcription
            show_info("Using cached reference text...")
            ref_text = _ref_audio_cache[audio_hash]
        else:
            show_info("No reference text provided, transcribing reference audio...")
            ref_text = transcribe(ref_audio)
            # Cache the transcribed text (not caching custom ref_text, enabling users to do manual tweak)
            _ref_audio_cache[audio_hash] = ref_text
    else:
        show_info("Using custom reference text...")

    # Ensure ref_text ends with a proper sentence-ending punctuation
    if not ref_text.endswith(". ") and not ref_text.endswith("。"):
        if ref_text.endswith("."):
            ref_text += " "
        else:
            ref_text += ". "

    print("\nref_text  ", ref_text)

    return ref_audio, ref_text


# infer process: chunk text -> infer batches [i.e. infer_batch_process()]


def infer_process(
    ref_audio,
    ref_text,
    gen_text,
    model_obj,
    vocoder,
    mel_spec_type=mel_spec_type,
    show_info=print,
    progress=tqdm,
    target_rms=target_rms,
    cross_fade_duration=cross_fade_duration,
    nfe_step=nfe_step,
    cfg_strength=cfg_strength,
    sway_sampling_coef=sway_sampling_coef,
    speed=speed,
    fix_duration=fix_duration,
    device=device,
    progress_callback=None,  # <-- thêm dòng này
):
    # Split the input text into batches
    audio, sr = torchaudio.load(ref_audio)
    max_chars = int(len(ref_text.encode("utf-8")) / (audio.shape[-1] / sr) * (25 - audio.shape[-1] / sr))
    gen_text_batches = chunk_text(gen_text, max_chars=max_chars)
    for i, gen_text in enumerate(gen_text_batches):
        print(f"gen_text {i}", gen_text)
    print("\n")

    show_info(f"Generating audio in {len(gen_text_batches)} batches...")
    return infer_batch_process(
        (audio, sr),
        ref_text,
        gen_text_batches,
        model_obj,
        vocoder,
        mel_spec_type=mel_spec_type,
        progress=progress,
        target_rms=target_rms,
        cross_fade_duration=cross_fade_duration,
        nfe_step=nfe_step,
        cfg_strength=cfg_strength,
        sway_sampling_coef=sway_sampling_coef,
        speed=speed,
        fix_duration=fix_duration,
        device=device,
        progress_callback=progress_callback,  # <-- thêm dòng này
    )


# infer batches


def infer_batch_process(
    ref_audio,
    ref_text,
    gen_text_batches,
    model_obj,
    vocoder,
    mel_spec_type="vocos",
    progress=tqdm,
    target_rms=0.1,
    cross_fade_duration=0.15,
    nfe_step=32,
    cfg_strength=2.0,
    sway_sampling_coef=-1,
    speed=1,
    fix_duration=None,
    device=None,
    progress_callback=None,  # <-- thêm dòng này
):
    audio, sr = ref_audio
    if audio.shape[0] > 1:
        audio = torch.mean(audio, dim=0, keepdim=True)

    rms = torch.sqrt(torch.mean(torch.square(audio)))
    if rms < target_rms:
        audio = audio * target_rms / rms
    if sr != target_sample_rate:
        resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
        audio = resampler(audio)
    audio = audio.to(device)

    generated_waves = []
    spectrograms = []

    if len(ref_text[-1].encode("utf-8")) == 1:
        ref_text = ref_text + " "
    for i, gen_text in enumerate(gen_text_batches, start=1):
        # Realtime progress
        if progress_callback:
            progress_callback(i, len(gen_text_batches))
        else:
            print(f"Processing batch {i}/{len(gen_text_batches)}", end="\r")
        
        # Chuẩn bị text
        text_list = [ref_text + gen_text]
        final_text_list = convert_char_to_pinyin(text_list)

        ref_audio_len = audio.shape[-1] // hop_length
        if fix_duration is not None:
            duration = int(fix_duration * target_sample_rate / hop_length)
        else:
            # Calculate duration
            ref_text_len = len(ref_text.encode("utf-8"))
            gen_text_len = len(gen_text.encode("utf-8"))
            duration = ref_audio_len + int(ref_audio_len / ref_text_len * gen_text_len / speed)

        # inference
        with torch.inference_mode():
            generated, _ = model_obj.sample(
                cond=audio,
                text=final_text_list,
                duration=duration,
                steps=nfe_step,
                cfg_strength=cfg_strength,
                sway_sampling_coef=sway_sampling_coef,
            )

            generated = generated.to(torch.float32)
            generated = generated[:, ref_audio_len:, :]
            generated_mel_spec = generated.permute(0, 2, 1)
            if mel_spec_type == "vocos":
                generated_wave = vocoder.decode(generated_mel_spec)
            elif mel_spec_type == "bigvgan":
                generated_wave = vocoder(generated_mel_spec)
            if rms < target_rms:
                generated_wave = generated_wave * rms / target_rms

            # wav -> numpy
            generated_wave = generated_wave.squeeze().cpu().numpy()

            generated_waves.append(generated_wave)
            spectrograms.append(generated_mel_spec[0].cpu().numpy())

    # --- START: LOGIC NÂNG CẤP TẠO KHOẢNG LẶNG GIỮA CÁC BATCH ---
    
    # Đặt thời gian khoảng lặng mong muốn (0.3 giây)
    SILENCE_DURATION = 0.25 
    
    # Chỉ chèn khoảng lặng nếu có nhiều hơn một batch
    if len(generated_waves) > 1:
        # Tần số mẫu được định nghĩa là target_sample_rate (thường là 24000)
        silence_samples = int(SILENCE_DURATION * target_sample_rate)
        
        # Tạo mảng silence (giá trị 0.0)
        silence_array = np.zeros(silence_samples, dtype=generated_waves[0].dtype)
        
        combined_waves = []
        combined_spectrograms = [] # Cần một mảng spectrograms mới nếu bạn muốn chèn silence vào đây
        
        for i in range(len(generated_waves)):
            # Thêm sóng âm của batch hiện tại
            combined_waves.append(generated_waves[i])
            
            # Thêm spectrogram của batch hiện tại
            combined_spectrograms.append(spectrograms[i]) 
            
            # Chèn silence sau mỗi batch, trừ batch cuối cùng
            if i < len(generated_waves) - 1:
                combined_waves.append(silence_array)
                
                # CHÚ Ý: Nếu bạn muốn spectrogram khớp với sóng âm,
                # bạn cũng cần chèn một cột (hoặc nhiều cột) 'silence' vào spectrograms.
                # Tuy nhiên, việc này phức tạp và thường không cần thiết trừ khi bạn 
                # hiển thị spectrogram đã kết hợp. Ta sẽ bỏ qua việc chèn silence
                # vào spectrograms để giữ code đơn giản, và chỉ nối spectrograms.

        # Kết hợp tất cả các sóng âm (bao gồm cả silence)
        final_wave = np.concatenate(combined_waves)
        
        # Kết hợp các spectrogram như ban đầu (không chèn silence vào spectrogram)
        combined_spectrogram = np.concatenate(combined_spectrograms, axis=1)
        
    else:
        # Nếu chỉ có một batch, sử dụng kết quả ban đầu
        final_wave = generated_waves[0]
        combined_spectrogram = spectrograms[0]

    # --- END: LOGIC NÂNG CẤP TẠO KHOẢNG LẶNG GIỮA CÁC BATCH ---
    
    # ❗️ LƯU Ý: ĐOẠN CODE CROSS-FADING BỊ XÓA BỎ HOÀN TOÀN
    # vì nó mâu thuẫn với mục tiêu chèn khoảng lặng rõ ràng.

    return final_wave, target_sample_rate, combined_spectrogram


# remove silence from generated wav


def remove_silence_for_generated_wav(filename):
    aseg = AudioSegment.from_file(filename)
    non_silent_segs = silence.split_on_silence(
        aseg, min_silence_len=1000, silence_thresh=-50, keep_silence=500, seek_step=10
    )
    non_silent_wave = AudioSegment.silent(duration=0)
    for non_silent_seg in non_silent_segs:
        non_silent_wave += non_silent_seg
    aseg = non_silent_wave
    aseg.export(filename, format="wav")


# save spectrogram


def save_spectrogram(spectrogram, path):
    plt.figure(figsize=(12, 4))
    plt.imshow(spectrogram, origin="lower", aspect="auto")
    plt.colorbar()
    plt.savefig(path)
    plt.close()
