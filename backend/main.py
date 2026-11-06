import os
import sys
import uuid
import shutil
import subprocess
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response

# Ensure proper sys.path resolution
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from backend.config import (
    OUTPUTS_DIR, TEMP_DIR, FRONTEND_DIR,
    GNANI_API_KEY, SUPPORTED_LANGUAGES, GNANI_BASE_URL
)
from backend.core import (
    extract_audio_and_reference,
    prepare_custom_voice_reference,
    trim_video,
    get_video_duration,
    split_audio_on_silence,
    align_and_pad_chunk,
    concatenate_audio_chunks,
    transcribe_single_chunk,
    generate_voice_embedding,
    synthesize_cloned_voice,
    translate_text,
    generate_dynamic_srt,
    generate_global_srt,
    mux_final_video,
    get_audio_duration,
    get_video_dimensions,
    list_voices,
    get_voice_embedding,
    save_voice_profile,
    delete_voice_profile
)

app = FastAPI(
    title="IndicReel AI Dubbing Studio",
    description="Full-stack AI video dubber with Gnani Prisma STT, multi-chunk long-form dubbing, and zero-shot voice cloning",
    version="2.2.0"
)

# In-memory asynchronous job store for long-form video dubbing
jobs: dict[str, dict] = {}

# Enable CORS for external/dev clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    """Serves studio favicon to prevent browser 404 logs."""
    fav_path = FRONTEND_DIR / "favicon.ico"
    if fav_path.exists():
        return FileResponse(str(fav_path), media_type="image/x-icon")
    svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="#6C62ED"/><polygon points="40,30 70,50 40,70" fill="#FFFFFF"/></svg>"""
    return Response(content=svg_icon, media_type="image/svg+xml")

@app.get("/api/status")
async def get_status():
    """Returns the backend configuration, credit cache status, and API key readiness."""
    has_api_key = bool(GNANI_API_KEY and GNANI_API_KEY != "your_actual_api_key_here")
    return {
        "status": "ready",
        "api_configured": has_api_key,
        "gnani_base_url": GNANI_BASE_URL,
        "models": {
            "stt": "prisma-v3.0 (silence-aware chunking <=24s)",
            "voice_cloning": "vachana-vc-v1",
            "stock_voices": "timbre-v2.5"
        },
        "supported_languages": SUPPORTED_LANGUAGES,
        "active_jobs": len([j for j in jobs.values() if j.get("status") == "processing"])
    }

@app.get("/api/languages")
async def get_languages():
    """Returns the 11 supported regional Indian languages."""
    return SUPPORTED_LANGUAGES

@app.get("/api/sample-reel")
async def get_sample_reel(name: str = Query("test_reel_45s.mp4")):
    """Returns a sample video for quick browser demo/testing."""
    sample_path = PROJECT_ROOT / "samples" / name
    if not sample_path.exists():
        sample_path = PROJECT_ROOT / "samples" / "test_reel_45s.mp4"
    if not sample_path.exists():
        sample_path = PROJECT_ROOT / "samples" / "sample_reel.mp4"
    if not sample_path.exists():
        sample_path = PROJECT_ROOT / "samples" / "sample reel.mp4"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample video not found")
    return FileResponse(str(sample_path), media_type="video/mp4", filename=os.path.basename(sample_path))

def run_long_form_dub(
    job_id: str,
    raw_video_path: Path,
    target_dub_lang: str,
    target_sub_lang: str,
    voice_mode: str,
    stock_voice: Optional[str],
    trim_start: float,
    trim_end: Optional[float],
    custom_voice_path: Optional[Path] = None,
    saved_voice_id: Optional[str] = None,
    save_as_name: Optional[str] = None
) -> dict:
    """
    Executes the scalable long-form video dubbing architecture:
    1. Video Trimming (optional)
    2. Mono Audio Extraction & Reference Slice
    3. Global Speaker Voice Embedding (Single API call, or instant load from voices.json)
    4. VAD & Silence-Aware Chunking (Chunks strictly <= 24s to satisfy Prisma STT limit)
    5. Sequential Chunk Processing: Prisma STT -> Dual Translation -> VC Synthesis -> Tempo Alignment/Padding
    6. Audio Concatenation into unified master track
    7. Global Subtitle Assembly with cumulative time offsets
    8. Final FFmpeg Remux with dynamic subtitles burned
    """
    task_id = job_id
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["step"] = 1
    jobs[job_id]["progress"] = 10
    jobs[job_id]["message"] = "Trimming video and extracting reference audio..."

    try:
        # 1. Video Trimming (if requested)
        active_video_path = raw_video_path
        if (trim_start and trim_start > 0) or (trim_end is not None and trim_end > 0):
            print(f"[{task_id}] Trimming video from {trim_start}s to {trim_end}s...")
            trimmed_path = TEMP_DIR / f"{task_id}_trimmed.mp4"
            try:
                trim_video(str(raw_video_path), str(trimmed_path), start_sec=trim_start, end_sec=trim_end)
                if trimmed_path.exists() and os.path.getsize(trimmed_path) > 0:
                    active_video_path = trimmed_path
                    print(f"[{task_id}] Video trimmed successfully.")
            except Exception as e:
                print(f"[{task_id}] Trimming warning, using original video: {e}")

        # 2. Extract full audio and reference slice
        audio_out = TEMP_DIR / f"{task_id}_full_audio.wav"
        ref_out = TEMP_DIR / f"{task_id}_ref10s.wav"

        # 3. Global Speaker Embedding Resolution
        jobs[job_id]["step"] = 2
        jobs[job_id]["progress"] = 15
        jobs[job_id]["message"] = "Resolving speaker voice profile..."

        global_speaker_embedding = None
        emb_cached = True

        # Case 1: Saved Voice Profile from voices.json (Zero Gnani embedding API credits!)
        if voice_mode == "saved_voice" or (saved_voice_id and saved_voice_id.strip()):
            voice_key = saved_voice_id.strip() if saved_voice_id else None
            if not voice_key:
                raise ValueError("No saved voice profile selected from voices.json.")
            print(f"[{task_id}] Loading saved voice profile '{voice_key}' from voices.json...")
            global_speaker_embedding = get_voice_embedding(voice_key)
            emb_cached = True
            voice_mode = "saved_voice"
            print(f"[{task_id}] Successfully retrieved saved embedding tensor (0 Gnani API credits used)!")
            # Extract video audio for STT
            dummy_ref = TEMP_DIR / f"{task_id}_dummy_ref.wav"
            extract_audio_and_reference(str(active_video_path), str(audio_out), str(dummy_ref), max_audio_duration=None)

        # Case 2: Custom audio file uploaded
        elif voice_mode == "clone_custom" and custom_voice_path and os.path.exists(custom_voice_path):
            print(f"[{task_id}] Preparing custom voice reference from: {custom_voice_path.name}")
            prepare_custom_voice_reference(str(custom_voice_path), str(ref_out))
            dummy_ref = TEMP_DIR / f"{task_id}_dummy_ref.wav"
            extract_audio_and_reference(str(active_video_path), str(audio_out), str(dummy_ref), max_audio_duration=None)
            print(f"[{task_id}] Generating speaker embedding for custom uploaded voice...")
            global_speaker_embedding, emb_cached = generate_voice_embedding(str(ref_out))
            if save_as_name and save_as_name.strip():
                try:
                    save_voice_profile(name=save_as_name.strip(), embedding_dict=global_speaker_embedding)
                    print(f"[{task_id}] Automatically saved voice as '{save_as_name.strip()}' in voices.json!")
                except Exception as ex:
                    print(f"[{task_id}] Warning saving voice profile: {ex}")

        # Case 3: Stock Studio Voice
        elif voice_mode == "stock_voice":
            print(f"[{task_id}] Stock Voice selected ({stock_voice}); using pre-trained studio voice.")
            global_speaker_embedding = None
            extract_audio_and_reference(str(active_video_path), str(audio_out), str(ref_out), max_audio_duration=None)

        # Case 4: Clone Video Voice (default)
        else:
            print(f"[{task_id}] Extracting full audio track and 10s reference slice from video...")
            extract_audio_and_reference(str(active_video_path), str(audio_out), str(ref_out), max_audio_duration=None)
            print(f"[{task_id}] Generating global speaker embedding from video voice...")
            global_speaker_embedding, emb_cached = generate_voice_embedding(str(ref_out))

        # 4. Silence-aware audio chunking (<= 24.0s)
        jobs[job_id]["step"] = 3
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Splitting audio on natural speech pauses (<=24s)..."
        chunks_dir = TEMP_DIR / f"{task_id}_chunks"
        chunks = split_audio_on_silence(str(audio_out), str(chunks_dir), max_chunk_len=24.0)
        total_chunks = len(chunks)
        jobs[job_id]["total_chunks"] = total_chunks
        print(f"[{task_id}] Total silence-aware chunks to process: {total_chunks}")

        # 5. Sequential Chunk Processing Loop
        jobs[job_id]["step"] = 4
        aligned_audio_files = []
        chunk_segments = []
        original_transcripts = []
        dub_transcripts = []
        sub_transcripts = []
        all_stt_cached = True
        all_tts_cached = True

        for i, chunk in enumerate(chunks):
            chunk_num = i + 1
            chunk_dur = chunk["duration"]
            chunk_file = chunk["file"]

            jobs[job_id]["current_chunk"] = chunk_num
            chunk_prog = 20 + int(65 * (i / total_chunks))
            jobs[job_id]["progress"] = chunk_prog
            jobs[job_id]["message"] = f"Processing chunk {chunk_num} of {total_chunks} ({chunk_dur:.1f}s)..."

            print(f"[{task_id}] Chunk {chunk_num}/{total_chunks} [{chunk['start']:.2f}s - {chunk['end']:.2f}s, dur={chunk_dur:.2f}s]...")

            # 5a. Prisma STT
            stt_res, c_stt_cached = transcribe_single_chunk(chunk_file, language_code="indic-auto")
            if not c_stt_cached:
                all_stt_cached = False
            c_orig_text = stt_res.get("transcript", "").strip()
            original_transcripts.append(c_orig_text)

            # 5b. Dual Translation & Language Routing
            if c_orig_text:
                c_dub_text = translate_text(c_orig_text, target_dub_lang)
                if target_sub_lang in ["en-IN", "en"]:
                    c_sub_text = c_orig_text
                elif target_sub_lang == target_dub_lang:
                    c_sub_text = c_dub_text
                else:
                    c_sub_text = translate_text(c_orig_text, target_sub_lang)
            else:
                c_dub_text = ""
                c_sub_text = ""
            dub_transcripts.append(c_dub_text)
            sub_transcripts.append(c_sub_text)

            # 5c. Cloned / Stock Voice Synthesis
            chunk_synth_wav = str(TEMP_DIR / f"{task_id}_chunk_{i:04d}_synth.wav")
            chunk_aligned_wav = str(TEMP_DIR / f"{task_id}_chunk_{i:04d}_aligned.wav")

            if c_dub_text:
                _, c_tts_cached = synthesize_cloned_voice(
                    text=c_dub_text,
                    speaker_embedding=global_speaker_embedding,
                    output_path=chunk_synth_wav,
                    language=target_dub_lang,
                    voice_mode=voice_mode,
                    stock_voice=stock_voice or "Nalini"
                )
                if not c_tts_cached:
                    all_tts_cached = False
                # 5d. Audio Synchronization & Time-Drift Correction (atempo / apad)
                align_and_pad_chunk(chunk_synth_wav, chunk_dur, chunk_aligned_wav)
            else:
                # Silence fallback for audio segments without speech
                cmd_silence = [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", f"{chunk_dur:.3f}", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
                    chunk_aligned_wav
                ]
                subprocess.run(cmd_silence, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            aligned_audio_files.append(chunk_aligned_wav)
            chunk_segments.append({
                "index": i,
                "start": chunk["start"],
                "end": chunk["end"],
                "text": c_sub_text
            })

        # 6. Concatenate all aligned audio chunks into master track
        jobs[job_id]["step"] = 5
        jobs[job_id]["progress"] = 88
        jobs[job_id]["message"] = "Concatenating aligned audio segments into master track..."
        master_dubbed_wav = str(TEMP_DIR / f"{task_id}_master_dubbed.wav")
        concat_list_file = str(TEMP_DIR / f"{task_id}_concat_list.txt")
        concatenate_audio_chunks(aligned_audio_files, master_dubbed_wav, concat_list_path=concat_list_file)

        # 7. Generate global SRT with cumulative time offsets
        vid_w, vid_h = get_video_dimensions(str(active_video_path))
        is_widescreen = vid_w > vid_h
        aspect_ratio_label = "16:9" if is_widescreen else "9:16"
        words_per_card = 6 if is_widescreen else 4

        jobs[job_id]["progress"] = 92
        jobs[job_id]["message"] = f"Generating global dynamic subtitles ({aspect_ratio_label} format, {words_per_card} words/card)..."
        master_srt_file = str(TEMP_DIR / f"{task_id}_master_subs_{target_sub_lang}.srt")
        generate_global_srt(chunk_segments, master_srt_file, words_per_card=words_per_card)

        # 8. Final FFmpeg Remux with dynamic subtitles burned
        jobs[job_id]["step"] = 6
        jobs[job_id]["progress"] = 95
        jobs[job_id]["message"] = f"Burning synchronized subtitles into {aspect_ratio_label} video..."
        final_video_filename = f"{task_id}_dubbed_{target_dub_lang}.mp4"
        final_video_out = OUTPUTS_DIR / final_video_filename
        mux_final_video(str(active_video_path), master_dubbed_wav, master_srt_file, str(final_video_out))

        # 9. Completion telemetry & results
        final_duration = get_audio_duration(str(master_dubbed_wav))
        overall_cached = bool(all_stt_cached and (emb_cached if voice_mode != "stock_voice" else True) and all_tts_cached)
        video_url = f"/outputs/{final_video_filename}"
        full_orig = " ".join([t for t in original_transcripts if t])
        full_dub = " ".join([t for t in dub_transcripts if t])
        full_sub = " ".join([t for t in sub_transcripts if t])

        result_data = {
            "success": True,
            "task_id": task_id,
            "job_id": job_id,
            "original_transcript": full_orig,
            "translated_dub_text": full_dub,
            "translated_sub_text": full_sub,
            "video_url": video_url,
            "dub_lang": target_dub_lang,
            "sub_lang": target_sub_lang,
            "dub_lang_name": SUPPORTED_LANGUAGES[target_dub_lang]["name"],
            "sub_lang_name": SUPPORTED_LANGUAGES[target_sub_lang]["name"],
            "voice_mode": voice_mode,
            "duration": round(final_duration, 2),
            "total_chunks": total_chunks,
            "aspect_ratio": aspect_ratio_label,
            "resolution": f"{vid_w}x{vid_h}",
            "cached": overall_cached
        }

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Dubbing completed successfully!"
        jobs[job_id]["result"] = result_data
        print(f"[{task_id}] Long-form dubbing pipeline completed successfully! Result: {video_url}")
        return result_data

    except Exception as e:
        print(f"[{task_id}] Long-form dubbing error: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Pipeline error: {str(e)}"
        raise e

@app.post("/api/dub/long")
async def dub_video_long(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    custom_voice: Optional[UploadFile] = File(None),
    dub_lang: Optional[str] = Form(None),
    sub_lang: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    voice_mode: str = Form("clone_video"),
    stock_voice: Optional[str] = Form("Nalini"),
    trim_start: float = Form(0.0),
    trim_end: Optional[float] = Form(None),
    saved_voice_id: Optional[str] = Form(None),
    save_as_name: Optional[str] = Form(None)
):
    """
    Asynchronous initiation endpoint for long-form video dubbing:
    Accepts video, queues background worker, and immediately returns a job_id for polling.
    Supports saved voice profiles (zero-credit inference) and custom audio uploads.
    """
    target_dub_lang = dub_lang or lang or "te-IN"
    target_sub_lang = sub_lang or target_dub_lang
    if target_dub_lang not in SUPPORTED_LANGUAGES:
        target_dub_lang = "te-IN"
    if target_sub_lang not in SUPPORTED_LANGUAGES:
        target_sub_lang = target_dub_lang

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    raw_video_filename = f"{job_id}_{video.filename or 'input.mp4'}"
    raw_video_path = TEMP_DIR / raw_video_filename

    try:
        with open(raw_video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    custom_voice_path = None
    if voice_mode == "clone_custom" and custom_voice and custom_voice.filename:
        custom_voice_filename = f"{job_id}_custom_{custom_voice.filename}"
        custom_voice_path = TEMP_DIR / custom_voice_filename
        with open(custom_voice_path, "wb") as buffer:
            shutil.copyfileobj(custom_voice.file, buffer)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 5,
        "step": 1,
        "current_chunk": 0,
        "total_chunks": 0,
        "message": "Video queued for long-form dubbing pipeline...",
        "result": None,
        "error": None
    }

    background_tasks.add_task(
        run_long_form_dub,
        job_id,
        raw_video_path,
        target_dub_lang,
        target_sub_lang,
        voice_mode,
        stock_voice,
        trim_start,
        trim_end,
        custom_voice_path,
        saved_voice_id,
        save_as_name
    )

    return {"success": True, "job_id": job_id}

@app.get("/api/dub/status/{job_id}")
async def get_dub_status(job_id: str):
    """
    Polls status and live progress of an asynchronous long-form dubbing job.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.post("/api/dub")
async def dub_video(
    video: UploadFile = File(...),
    custom_voice: Optional[UploadFile] = File(None),
    dub_lang: Optional[str] = Form(None),
    sub_lang: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    voice_mode: str = Form("clone_video"),
    stock_voice: Optional[str] = Form("Nalini"),
    trim_start: float = Form(0.0),
    trim_end: Optional[float] = Form(None),
    saved_voice_id: Optional[str] = Form(None),
    save_as_name: Optional[str] = Form(None)
):
    """
    Synchronous fallback endpoint: executes the complete chunked dubbing pipeline
    and returns when the video is finalized.
    """
    target_dub_lang = dub_lang or lang or "te-IN"
    target_sub_lang = sub_lang or target_dub_lang
    if target_dub_lang not in SUPPORTED_LANGUAGES:
        target_dub_lang = "te-IN"
    if target_sub_lang not in SUPPORTED_LANGUAGES:
        target_sub_lang = target_dub_lang

    job_id = f"reel_{uuid.uuid4().hex[:8]}"
    raw_video_filename = f"{job_id}_{video.filename or 'input.mp4'}"
    raw_video_path = TEMP_DIR / raw_video_filename

    try:
        with open(raw_video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    custom_voice_path = None
    if voice_mode == "clone_custom" and custom_voice and custom_voice.filename:
        custom_voice_filename = f"{job_id}_custom_{custom_voice.filename}"
        custom_voice_path = TEMP_DIR / custom_voice_filename
        with open(custom_voice_path, "wb") as buffer:
            shutil.copyfileobj(custom_voice.file, buffer)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "progress": 5,
        "step": 1,
        "current_chunk": 0,
        "total_chunks": 0,
        "message": "Starting synchronous dubbing pipeline...",
        "result": None,
        "error": None
    }

    try:
        result = run_long_form_dub(
            job_id,
            raw_video_path,
            target_dub_lang,
            target_sub_lang,
            voice_mode,
            stock_voice,
            trim_start,
            trim_end,
            custom_voice_path,
            saved_voice_id,
            save_as_name
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# Persistent Voice Profiles Management API (voices.json)
# ==============================================================================

@app.get("/api/voices")
async def get_saved_voices():
    """Returns list of saved voice profiles from voices.json."""
    return list_voices()

@app.post("/api/voices")
async def create_saved_voice(
    name: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    Registers a new voice profile:
    Extracts a 10s audio slice, computes the speaker embedding tensor via Gnani AI,
    and persists it into backend/data/voices.json for zero-credit future runs.
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Voice profile name is required.")

    voice_task_id = f"vreg_{uuid.uuid4().hex[:6]}"
    temp_audio = TEMP_DIR / f"{voice_task_id}_{audio_file.filename or 'voice.wav'}"
    ref_10s = TEMP_DIR / f"{voice_task_id}_ref10s.wav"

    try:
        with open(temp_audio, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # Slice 10-second reference audio sample
        prepare_custom_voice_reference(str(temp_audio), str(ref_10s))

        # Generate embedding tensor via Gnani AI endpoint
        emb_dict, is_cached = generate_voice_embedding(str(ref_10s))

        # Save to voices.json
        profile = save_voice_profile(name=name.strip(), embedding_dict=emb_dict)

        return {
            "success": True,
            "voice": {
                "id": profile["id"],
                "name": profile["name"],
                "created_at": profile["created_at"]
            },
            "cached": is_cached
        }
    except Exception as e:
        print(f"[!] Error registering voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Voice registration failed: {str(e)}")
    finally:
        # Clean up temporary voice registration files
        for p in [temp_audio, ref_10s]:
            if p.exists():
                try: os.remove(p)
                except: pass

@app.delete("/api/voices/{voice_id}")
async def delete_saved_voice(voice_id: str):
    """Deletes a voice profile by ID from voices.json."""
    success = delete_voice_profile(voice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    return {"success": True, "deleted_id": voice_id}

# Mount static outputs folder so generated videos can be downloaded and played
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Mount frontend directory for static UI assets
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
