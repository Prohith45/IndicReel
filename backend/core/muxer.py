import subprocess
import os
import datetime

def get_audio_duration(file_path: str) -> float:
    """Returns duration of an audio or video file in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dur = float(result.stdout.strip())
        return max(dur, 2.0)
    except Exception:
        return 10.0

def format_timestamp_srt(seconds: float) -> str:
    """Converts seconds into SRT timestamp format: HH:MM:SS,mmm"""
    total_millis = int(round(seconds * 1000))
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_dynamic_srt(text: str, audio_duration: float, srt_path: str, words_per_card: int = 4) -> str:
    """
    Generates dynamically timed .srt subtitle cards (3-5 words per card)
    evenly synchronized across the synthesized audio duration so text changes
    in real-time as the cloned voice speaks.
    """
    os.makedirs(os.path.dirname(os.path.abspath(srt_path)), exist_ok=True)
    
    words = text.strip().split()
    if not words:
        words = ["..."]

    # Group words into small cards (3-5 words per card)
    cards = []
    current_chunk = []
    for w in words:
        current_chunk.append(w)
        if len(current_chunk) >= words_per_card:
            cards.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        if cards and len(current_chunk) <= 2:
            cards[-1] += " " + " ".join(current_chunk)
        else:
            cards.append(" ".join(current_chunk))

    total_cards = len(cards)
    total_chars = sum(len(c) for c in cards)
    
    # Calculate time slots proportional to character weight
    current_time = 0.0
    srt_entries = []

    for idx, card in enumerate(cards, start=1):
        # Character-weighted duration allocation
        ratio = len(card) / total_chars if total_chars > 0 else (1.0 / total_cards)
        card_dur = max(0.8, audio_duration * ratio)
        
        start_time = current_time
        end_time = min(audio_duration, current_time + card_dur)
        if idx == total_cards:
            end_time = max(end_time, audio_duration)

        current_time = end_time

        srt_entries.append(
            f"{idx}\n{format_timestamp_srt(start_time)} --> {format_timestamp_srt(end_time)}\n{card}\n"
        )

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries) + "\n")

    print(f"[+] Generated {len(cards)} dynamic SRT cards synchronized over {audio_duration:.2f}s.")
    return srt_path

def generate_global_srt(chunk_segments: list, srt_path: str, words_per_card: int = 4) -> str:
    """
    Builds the master subtitle track by offsetting each chunk's subtitles
    by its cumulative timestamp (chunk_start_time).
    Subdivides chunk text into readable mobile cards (3-5 words) and writes
    a unified SRT covering the full video timeline.
    """
    os.makedirs(os.path.dirname(os.path.abspath(srt_path)), exist_ok=True)
    srt_entries = []
    card_index = 1

    for seg in chunk_segments:
        chunk_start = float(seg.get("start", 0.0))
        chunk_end = float(seg.get("end", chunk_start + 1.0))
        chunk_dur = max(0.5, chunk_end - chunk_start)
        text = seg.get("text", "").strip()
        if not text:
            continue

        words = text.split()
        cards = []
        current_chunk = []
        for w in words:
            current_chunk.append(w)
            if len(current_chunk) >= words_per_card:
                cards.append(" ".join(current_chunk))
                current_chunk = []
        if current_chunk:
            if cards and len(current_chunk) <= 2:
                cards[-1] += " " + " ".join(current_chunk)
            else:
                cards.append(" ".join(current_chunk))

        if not cards:
            continue

        total_cards = len(cards)
        total_chars = sum(len(c) for c in cards)
        current_time = chunk_start

        for idx, card in enumerate(cards, start=1):
            ratio = len(card) / total_chars if total_chars > 0 else (1.0 / total_cards)
            card_dur = max(0.6, chunk_dur * ratio)

            start_t = current_time
            end_t = min(chunk_end, current_time + card_dur)
            if idx == total_cards:
                end_t = chunk_end

            current_time = end_t

            srt_entries.append(
                f"{card_index}\n{format_timestamp_srt(start_t)} --> {format_timestamp_srt(end_t)}\n{card}\n"
            )
            card_index += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries) + "\n")

    print(f"[+] Generated global master SRT ({card_index - 1} cards) saved to {srt_path}")
    return srt_path

def get_video_dimensions(file_path: str) -> tuple:
    """Returns (width, height) of the video using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = res.stdout.strip().split("x")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 720, 1280

def mux_final_video(video_path: str, dubbed_audio_path: str, srt_path: str, final_output: str):
    """
    Muxes the original video track with the newly synthesized cloned audio track,
    burning dynamic yellow subtitles into the video via FFmpeg.
    Automatically adapts subtitle sizing & margins for both 16:9 YouTube widescreen
    and 9:16 vertical reels/shorts.
    """
    os.makedirs(os.path.dirname(os.path.abspath(final_output)), exist_ok=True)
    
    # Detect video aspect ratio for optimal subtitle readability
    width, height = get_video_dimensions(video_path)
    is_widescreen = width > height
    
    # Windows-safe path escaping for ffmpeg subtitle filter
    formatted_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    
    if is_widescreen:
        # 16:9 YouTube Widescreen styling (larger readable text, bottom margin)
        style_str = "FontSize=24,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2.5,Alignment=2,MarginV=30"
        print(f"[+] Burning subtitles for 16:9 Widescreen YouTube format ({width}x{height})")
    else:
        # 9:16 Vertical Reel/Shorts styling (lifted above mobile gesture bar)
        style_str = "FontSize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=40"
        print(f"[+] Burning subtitles for 9:16 Vertical Reel format ({width}x{height})")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", dubbed_audio_path,
        "-vf", f"subtitles='{formatted_srt}':force_style='{style_str}'",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(final_output) and os.path.getsize(final_output) > 0:
            print(f"[+] Final dubbing complete with burned dynamic subtitles! Saved to {final_output}")
            return final_output
    except Exception as e:
        print(f"[!] Subtitle burning filter warning: {e}")

    # Fallback to direct mux if libass filter has platform issues
    fallback_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", dubbed_audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]
    subprocess.run(fallback_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[+] Final dubbing complete (fallback mux)! Saved to {final_output}")
    return final_output
