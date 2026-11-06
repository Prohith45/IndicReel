import os
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from backend.config import VOICES_FILE

def _read_voices() -> list:
    """Reads all voice profiles from JSON file safely."""
    if not VOICES_FILE.exists():
        return []
    try:
        with open(VOICES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[!] Warning reading voices.json: {e}")
        return []

def _write_voices(voices: list):
    """Writes all voice profiles to JSON file with atomic safety."""
    VOICES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = VOICES_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(voices, f, indent=2, ensure_ascii=False)
    temp_file.replace(VOICES_FILE)

def list_voices() -> list:
    """
    Returns lightweight summaries of saved voice profiles,
    omitting large raw embedding arrays for efficient transmission.
    """
    voices = _read_voices()
    return [
        {
            "id": v.get("id"),
            "name": v.get("name", "Untitled Voice"),
            "created_at": v.get("created_at", "")
        }
        for v in voices
        if isinstance(v, dict) and "id" in v
    ]

def get_voice_embedding(voice_id: str) -> dict:
    """
    Retrieves the exact speaker embedding tensor dict for a saved voice profile.
    Raises ValueError if voice_id is not found.
    """
    voices = _read_voices()
    for v in voices:
        if isinstance(v, dict) and v.get("id") == voice_id:
            emb = v.get("embedding")
            if not emb:
                raise ValueError(f"Voice profile '{voice_id}' has no embedding tensor.")
            return emb
    raise ValueError(f"Voice profile '{voice_id}' not found.")

def save_voice_profile(name: str, embedding_dict: dict) -> dict:
    """
    Appends a new voice profile with unique ID and timestamp,
    persisting the embedding tensor to backend/data/voices.json.
    """
    voices = _read_voices()
    voice_id = f"voice_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    
    new_entry = {
        "id": voice_id,
        "name": (name or "My Cloned Voice").strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding": embedding_dict
    }
    
    voices.append(new_entry)
    _write_voices(voices)
    print(f"[+] Saved voice profile '{new_entry['name']}' ({voice_id}) to voices.json")
    return new_entry

def delete_voice_profile(voice_id: str) -> bool:
    """
    Deletes a voice profile by ID from voices.json.
    Returns True if removed, False if not found.
    """
    voices = _read_voices()
    initial_count = len(voices)
    voices = [v for v in voices if not (isinstance(v, dict) and v.get("id") == voice_id)]
    
    if len(voices) < initial_count:
        _write_voices(voices)
        print(f"[+] Deleted voice profile '{voice_id}' from voices.json")
        return True
    return False
