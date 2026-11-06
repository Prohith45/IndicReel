import os
import subprocess
import shutil

from typing import Optional

def get_video_duration(file_path: str) -> float:
    """Returns duration of an audio or video file in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def trim_video(video_path: str, output_path: str, start_sec: float = 0.0, end_sec: float = None) -> str:
    """
    Trims input video from start_sec to end_sec using FFmpeg.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video not found: {video_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cmd = ["ffmpeg", "-y"]
    if start_sec and start_sec > 0:
        cmd.extend(["-ss", str(start_sec)])
    cmd.extend(["-i", video_path])
    if end_sec is not None and end_sec > start_sec:
        duration = end_sec - start_sec
        cmd.extend(["-t", str(duration)])
    cmd.extend(["-c", "copy", output_path])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def extract_audio_and_reference(video_path: str, audio_out: str, ref_out: str, max_audio_duration: Optional[float] = None):
    """
    Extracts mono WAV audio (44.1kHz pcm_s16le).
    If max_audio_duration is specified, extracts up to max_audio_duration (None = full length).
    Extracts a 10s reference voice sample starting at 00:00:01 for voice clone embeddings.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video not found: {video_path}")
        
    os.makedirs(os.path.dirname(os.path.abspath(audio_out)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(ref_out)), exist_ok=True)

    # 1. Extract audio
    extract_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1"
    ]
    if max_audio_duration and max_audio_duration > 0:
        extract_cmd.extend(["-t", str(max_audio_duration)])
    extract_cmd.append(audio_out)
    subprocess.run(extract_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Extract 10-second reference clip for voice cloning embedding
    ref_cmd = [
        "ffmpeg", "-y", "-ss", "00:00:01", "-i", audio_out,
        "-t", "00:00:10",
        ref_out
    ]
    subprocess.run(ref_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # If reference extraction produces an empty file (e.g., short input clip), fallback to audio_out
    if not os.path.exists(ref_out) or os.path.getsize(ref_out) == 0:
        shutil.copyfile(audio_out, ref_out)

    print("[+] Audio extracted and 10s reference voice sample prepared.")

def prepare_custom_voice_reference(custom_audio_path: str, ref_out: str) -> str:
    """
    Converts custom audio (.wav/.mp3/.mpa) into a 10s mono 44.1kHz WAV reference sample.
    FFmpeg automatically handles PCM WAV, MPEG Layer-3 (.mp3), and MPEG-1/2 Audio (.mpa).
    """
    if not os.path.exists(custom_audio_path):
        raise FileNotFoundError(f"Custom audio not found: {custom_audio_path}")

    os.makedirs(os.path.dirname(os.path.abspath(ref_out)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", custom_audio_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        "-t", "00:00:10",
        ref_out
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ref_out

def split_audio_chunks(audio_path: str, chunk_duration: float = 28.0) -> list:
    """
    Inspects audio duration. If > chunk_duration (e.g. 28s), splits into
    consecutive chunks of max 28s each so Prisma STT 30s limit is never exceeded.
    Returns list of chunk file paths.
    """
    dur = get_video_duration(audio_path)
    if dur <= chunk_duration:
        return [audio_path]
    
    chunks = []
    base, ext = os.path.splitext(audio_path)
    current_start = 0.0
    idx = 1
    while current_start < dur:
        chunk_out = f"{base}_chunk{idx}{ext}"
        chunk_cmd = [
            "ffmpeg", "-y", "-ss", str(current_start), "-i", audio_path,
            "-t", str(chunk_duration),
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            chunk_out
        ]
        subprocess.run(chunk_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(chunk_out) and os.path.getsize(chunk_out) > 0:
            chunks.append(chunk_out)
        current_start += chunk_duration
        idx += 1
    print(f"[+] Audio duration ({dur:.2f}s) split into {len(chunks)} chunks for STT.")
    return chunks
