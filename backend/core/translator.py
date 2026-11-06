import re
import requests
from deep_translator import GoogleTranslator

# Mapping of Gnani regional Indic language codes to Google Translate codes
LANG_MAP = {
    "te-IN": "te",  # Telugu
    "hi-IN": "hi",  # Hindi
    "ta-IN": "ta",  # Tamil
    "kn-IN": "kn",  # Kannada
    "ml-IN": "ml",  # Malayalam
    "bn-IN": "bn",  # Bengali
    "mr-IN": "mr",  # Marathi
    "gu-IN": "gu",  # Gujarati
    "pa-IN": "pa",  # Punjabi
    "or-IN": "or",  # Odia
    "en-IN": "en"   # English
}

def translate_single_segment(text: str, target_code: str) -> str:
    """
    Translates a single segment of text into target_code using deep_translator's
    GoogleTranslator, with an automatic direct API fallback on rate-limit / timeout.
    """
    text = text.strip()
    if not text:
        return ""

    if target_code == "en":
        return text

    # Tier 1: deep_translator GoogleTranslator
    try:
        translator = GoogleTranslator(source="auto", target=target_code)
        translated = translator.translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception as e:
        print(f"[!] GoogleTranslator notice: {e}. Switching to direct translation fallback...")

    # Tier 2: Direct Google Translate Single API fallback
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_code,
            "dt": "t",
            "q": text
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                result_pieces = [item[0] for item in data[0] if item and isinstance(item, list) and item[0]]
                translated = "".join(result_pieces).strip()
                if translated:
                    return translated
    except Exception as e:
        print(f"[!] Direct API translation fallback notice: {e}")

    # Tier 3: Network / service failure fallback to original text
    print(f"[!] Translation fallback: retaining source text for target {target_code}")
    return text

def translate_text(text: str, target_lang: str) -> str:
    """
    Dynamic translation engine for IndicReel:
    Translates speech transcripts dynamically into any of the 11 supported Indic languages:
    te-IN, hi-IN, ta-IN, kn-IN, ml-IN, bn-IN, mr-IN, gu-IN, or-IN, pa-IN, en-IN.

    - Returns original text unchanged if target is English (en-IN).
    - Performs sentence-safe batching for long transcripts.
    - Uses deep_translator with high-resilience API fallback.
    """
    if not text or not text.strip():
        return ""

    target_code = LANG_MAP.get(target_lang, target_lang.split("-")[0] if "-" in target_lang else target_lang)

    # If target is English or already matches, return clean original text
    if target_code == "en" or target_lang == "en-IN":
        return text.strip()

    # If transcript is within safe limit, translate directly
    if len(text) <= 1500:
        return translate_single_segment(text, target_code)

    # Sentence-safe batching for long texts
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    batches = []
    current_batch = []
    current_len = 0

    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > 1200 and current_batch:
            batches.append(" ".join(current_batch))
            current_batch = [sentence]
            current_len = s_len
        else:
            current_batch.append(sentence)
            current_len += s_len + 1

    if current_batch:
        batches.append(" ".join(current_batch))

    translated_batches = []
    for batch in batches:
        t_batch = translate_single_segment(batch, target_code)
        translated_batches.append(t_batch)

    return " ".join(translated_batches)
