import argparse
import os
import sys
from pathlib import Path

# Configure stdout encoding on Windows for Indic characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from backend.core.extractor import extract_audio_and_reference
    from backend.core.stt import transcribe_single_chunk
    from backend.core.voice_clone import generate_voice_embedding, synthesize_cloned_voice
    from backend.core.translator import translate_text
    from backend.core.muxer import generate_dynamic_srt, mux_final_video, get_audio_duration
    USE_BACKEND_CORE = True
except ImportError:
    from core.extractor import extract_audio_and_reference
    from core.stt import transcribe_audio
    from core.voice_clone import generate_voice_embedding, synthesize_cloned_voice
    from core.translator import translate_text
    from core.muxer import create_srt_file, mux_final_video
    USE_BACKEND_CORE = False

def main():
    parser = argparse.ArgumentParser(description="IndicReel CLI Dubbing Pipeline")
    parser.add_argument("--video", required=True, help="Path to input .mp4 video file")
    parser.add_argument("--lang", default="te-IN", help="Target language code (e.g., te-IN, hi-IN, ta-IN)")
    parser.add_argument("--output", default="output_dubbed.mp4", help="Path for final output video")
    
    args = parser.parse_args()
    
    os.makedirs("temp", exist_ok=True)
    audio_path = "temp/extracted.wav"
    ref_path = "temp/reference.wav"
    dubbed_audio_path = "temp/dubbed.wav"
    srt_path = "temp/subtitles.srt"
    
    print(f"[*] Starting IndicReel CLI Pipeline for video: {args.video}")
    
    extract_audio_and_reference(args.video, audio_path, ref_path)
    
    if USE_BACKEND_CORE:
        stt_res, _ = transcribe_single_chunk(audio_path)
    else:
        stt_res = transcribe_audio(audio_path)
    original_text = stt_res.get("transcript", "Hello world")
    
    if USE_BACKEND_CORE:
        embedding_data, _ = generate_voice_embedding(ref_path)
    else:
        embedding_data = generate_voice_embedding(ref_path)
        
    translated_text = translate_text(original_text, args.lang)
    print(f"[+] Translated text: {translated_text}")
    
    speaker_emb = {
        "embedding": embedding_data["embedding"],
        "shape": embedding_data["shape"],
        "dtype": embedding_data["dtype"]
    }
    
    if USE_BACKEND_CORE:
        synthesize_cloned_voice(
            text=translated_text,
            speaker_embedding=speaker_emb,
            output_path=dubbed_audio_path,
            language=args.lang,
            voice_mode="clone"
        )
        audio_dur = get_audio_duration(dubbed_audio_path)
        generate_dynamic_srt(translated_text, audio_dur, srt_path)
    else:
        synthesize_cloned_voice(
            text=translated_text,
            speaker_embedding=speaker_emb,
            output_path=dubbed_audio_path,
            language=args.lang
        )
        create_srt_file(translated_text, srt_path)
        
    mux_final_video(args.video, dubbed_audio_path, srt_path, args.output)
    print("[+] Pipeline executed successfully!")

if __name__ == "__main__":
    main()

