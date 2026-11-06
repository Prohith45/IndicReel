import requests
import os
import json
import hashlib
from ..config import GNANI_BASE_URL, HEADERS_REST, GNANI_API_KEY, CACHE_DIR
from .extractor import split_audio_chunks

def compute_file_sha256(file_path: str) -> str:
    """Computes SHA256 hex digest for a file to enable deterministic caching."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def transcribe_single_chunk(chunk_path: str, language_code: str = "indic-auto") -> tuple:
    """
    Transcribes a single audio chunk (<= 28s) using Gnani Prisma v3.0,
    checking cache first. Returns (response_dict, is_cached).
    """
    chunk_hash = compute_file_sha256(chunk_path)
    cache_file = CACHE_DIR / f"stt_{chunk_hash}.json"

    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            print(f"[+] STT Cache Hit ({chunk_hash[:8]}). Transcript: {cached_data.get('transcript', '')[:50]}...")
            return cached_data, True
        except Exception as e:
            print(f"[!] Cache read warning: {e}")

    url = f"{GNANI_BASE_URL}/stt/v3"

    # Safe guard: avoid unauthenticated hits if API key is not configured
    if not GNANI_API_KEY or GNANI_API_KEY == "your_actual_api_key_here":
        print("[*] GNANI_API_KEY not configured in .env. Returning simulation transcript.")
        res_json = {
            "transcript": "How does one gigabyte folder get compressed to four hundred megabyte zip file, and when you unzip it, you get back the complete folder? So, where did those six hundred megabytes go?",
            "status": "success",
            "model": "prisma-v3.0"
        }
        return res_json, False

    with open(chunk_path, "rb") as f:
        files = {"audio_file": ("audio.wav", f, "audio/wav")}
        data = {"model": "prisma-v3.0", "language_code": language_code}
        response = requests.post(url, headers=HEADERS_REST, files=files, data=data, timeout=60)

    if response.status_code == 200:
        res_json = response.json()
        print(f"[+] Prisma STT Success. Transcript: {res_json.get('transcript', '')[:60]}...")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(res_json, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[!] Cache write warning: {e}")
        return res_json, False
    else:
        raise Exception(f"STT Error {response.status_code}: {response.text}")

def transcribe_audio(audio_path: str, language_code: str = "indic-auto") -> tuple:
    """
    Transcribes audio using Gnani Prisma v3.0 REST API endpoint.
    If audio is > 28s, automatically splits into chunks <= 28s,
    transcribes each chunk, and concatenates transcriptions with a space.
    Returns (result_dict, is_cached).
    """
    # Check overall audio hash cache
    audio_hash = compute_file_sha256(audio_path)
    full_cache_file = CACHE_DIR / f"stt_full_{audio_hash}.json"
    if full_cache_file.exists():
        try:
            with open(full_cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            print(f"[+] Full STT Cache Hit ({audio_hash[:8]}). Transcript: {cached_data.get('transcript', '')[:50]}...")
            return cached_data, True
        except Exception:
            pass

    chunks = split_audio_chunks(audio_path, chunk_duration=28.0)
    transcripts = []
    all_cached = True

    for idx, chunk_file in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f"[+] Transcribing chunk {idx}/{len(chunks)} ({os.path.basename(chunk_file)})...")
        res, was_cached = transcribe_single_chunk(chunk_file, language_code)
        if not was_cached:
            all_cached = False
        t = res.get("transcript", "").strip()
        if t:
            transcripts.append(t)

    combined_transcript = " ".join(transcripts)
    result = {
        "transcript": combined_transcript,
        "status": "success",
        "model": "prisma-v3.0",
        "chunks_processed": len(chunks)
    }

    try:
        with open(full_cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return result, all_cached
