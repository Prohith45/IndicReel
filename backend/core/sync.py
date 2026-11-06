import subprocess
import os
from .chunker import get_audio_duration

def align_and_pad_chunk(synthesized_wav: str, target_duration: float, output_wav: str) -> str:
    """
    Adjusts tempo and pads chunk to fit target duration perfectly.
    - If synthesized audio is longer than original window (T_syn > T_orig),
      uses ffmpeg atempo filter to compress speech duration up to 1.25x without pitch distortion.
    - If synthesized audio is shorter than original window (T_syn < T_orig),
      pads with trailing silence so subsequent speech chunks remain time-synchronized.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    syn_duration = get_audio_duration(synthesized_wav)
    if syn_duration <= 0.0 or target_duration <= 0.0:
        return synthesized_wav
        
    ratio = syn_duration / target_duration
    
    # If audio is too long, speed it up (clamp at 1.25x max speed)
    if ratio > 1.05:
        speed = min(ratio, 1.25)
        cmd = [
            "ffmpeg", "-y", "-i", synthesized_wav,
            "-filter:a", f"atempo={speed:.3f}",
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            "-t", f"{target_duration:.3f}",
            output_wav
        ]
    # If audio is shorter, pad with silence to prevent desync
    elif ratio < 0.95:
        pad_sec = max(0.05, target_duration - syn_duration)
        cmd = [
            "ffmpeg", "-y", "-i", synthesized_wav,
            "-af", f"apad=pad_dur={pad_sec:.3f}",
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            "-t", f"{target_duration:.3f}",
            output_wav
        ]
    else:
        # Minor variation within 5%: keep as is, strictly bounded to target_duration
        cmd = [
            "ffmpeg", "-y", "-i", synthesized_wav,
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
            "-t", f"{target_duration:.3f}",
            output_wav
        ]
        
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_wav

def concatenate_audio_chunks(aligned_files: list, output_master_wav: str, concat_list_path: str = "temp/concat_list.txt") -> str:
    """
    Concatenates all aligned audio segments into a single unified master audio track.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_master_wav)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(concat_list_path)), exist_ok=True)
    
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for path in aligned_files:
            safe_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
            
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        output_master_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_master_wav
