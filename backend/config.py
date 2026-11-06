import os
from pathlib import Path
from dotenv import load_dotenv

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OUTPUTS_DIR = BACKEND_DIR / "outputs"
DATA_DIR = BACKEND_DIR / "data"
VOICES_FILE = DATA_DIR / "voices.json"
TEMP_DIR = ROOT_DIR / "temp"
CACHE_DIR = TEMP_DIR / "cache"

# Ensure output, data, temp, and cache directories exist
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

if not VOICES_FILE.exists():
    with open(VOICES_FILE, "w", encoding="utf-8") as f:
        f.write("[]")

# Load environment variables securely from root .env
load_dotenv(dotenv_path=ROOT_DIR / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
if not GNANI_API_KEY or GNANI_API_KEY == "your_actual_api_key_here":
    print("[!] Warning: GNANI_API_KEY is not set or using placeholder in .env file.")

# Strict API URL: target only official API, never touch app.gnani.ai web dashboard
GNANI_BASE_URL = "https://api.vachana.ai"

HEADERS_REST = {
    "X-API-Key-ID": GNANI_API_KEY,
}

HEADERS_JSON = {
    "X-API-Key-ID": GNANI_API_KEY,
    "Content-Type": "application/json"
}

# Regional language mappings (11 Gnani-supported languages)
SUPPORTED_LANGUAGES = {
    "te-IN": {"name": "Telugu", "native": "తెలుగు"},
    "hi-IN": {"name": "Hindi", "native": "हिन्दी"},
    "ta-IN": {"name": "Tamil", "native": "தமிழ்"},
    "kn-IN": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    "ml-IN": {"name": "Malayalam", "native": "മലയാളം"},
    "bn-IN": {"name": "Bengali", "native": "বাংলা"},
    "mr-IN": {"name": "Marathi", "native": "मराठी"},
    "gu-IN": {"name": "Gujarati", "native": "ગુજરાતી"},
    "or-IN": {"name": "Odia", "native": "ଓଡ଼ିଆ"},
    "pa-IN": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
    "en-IN": {"name": "English (India)", "native": "English"}
}
