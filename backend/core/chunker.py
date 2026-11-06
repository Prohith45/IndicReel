import subprocess
import re
import os

def get_audio_duration(file_path: str) -> float:
    """Returns duration of an audio or video file in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def split_audio_on_silence(input_wav: str, output_dir: str, max_chunk_len: float = 24.0) -> list:
    """
    Splits long audio into chunks <= max_chunk_len using silence cues.
    Prevents words from being cut off mid-syllable by snapping split points
    to natural breath and sentence pauses detected via ffmpeg silencedetect.
    """
    os.makedirs(output_dir, exist_ok=True)
    total_len = get_audio_duration(input_wav)
    if total_len <= 0.0:
        raise ValueError(f"Invalid or empty audio file: {input_wav}")

    # If the total length is already <= max_chunk_len, return as a single chunk
    if total_len <= max_chunk_len:
        single_chunk_file = os.path.join(output_dir, "chunk_0000.wav")
        cmd = [
            "ffmpeg", "-y", "-i", input_wav,
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            single_chunk_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return [{
            "index": 0,
            "start": 0.0,
            "end": total_len,
            "duration": total_len,
            "file": single_chunk_file
        }]

    # Run FFmpeg silencedetect filter across the input audio
    cmd = [
        "ffmpeg", "-i", input_wav,
        "-af", "silencedetect=noise=-30dB:d=0.35",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Parse silence end points (and start points)
    silence_ends = [float(m.group(1)) for m in re.finditer(r"silence_end:\s*(\d+\.?\d*)", res.stderr)]
    if not silence_ends:
        # Fallback to silence_start if silence_end wasn't explicitly formatted
        silence_ends = [float(m.group(1)) for m in re.finditer(r"silence_start:\s*(\d+\.?\d*)", res.stderr)]

    chunks = []
    current_start = 0.0
    idx = 0

    while current_start < total_len:
        target_end = min(current_start + max_chunk_len, total_len)
        if target_end >= total_len:
            split_point = total_len
        else:
            # Find best silence pause in the [current_start + 15s, target_end] window
            candidates = [t for t in silence_ends if (current_start + 15.0) <= t <= target_end]
            if candidates:
                split_point = candidates[-1]
            else:
                # Secondary search in [current_start + 10s, target_end]
                secondary = [t for t in silence_ends if (current_start + 10.0) <= t <= target_end]
                split_point = secondary[-1] if secondary else target_end

        chunk_file = os.path.join(output_dir, f"chunk_{idx:04d}.wav")
        duration = split_point - current_start
        if duration <= 0.1:
            break

        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{current_start:.3f}", "-t", f"{duration:.3f}",
            "-i", input_wav, "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            chunk_file
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chunks.append({
            "index": idx,
            "start": current_start,
            "end": split_point,
            "duration": duration,
            "file": chunk_file
        })
        current_start = split_point
        idx += 1

    print(f"[+] Audio ({total_len:.2f}s) split into {len(chunks)} silence-aware chunks (max {max_chunk_len}s).")
    return chunks
