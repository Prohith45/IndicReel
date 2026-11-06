<div align="center">

# 🎙️✨ IndicReel
### **Production-Grade Multilingual Voice-Cloned Video Dubbing & Dynamic Subtitling Studio**

*Zero-shot neural voice cloning across 11 Indic languages with natural timbre preservation, silence-aware chunking, tempo-adaptive synchronization, and word-paced subtitling.*

---

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gnani AI](https://img.shields.io/badge/Powered%20By-Gnani.ai-FF6F00?style=for-the-badge)](https://gnani.ai/)
[![FFmpeg](https://img.shields.io/badge/Media%20Engine-FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](https://github.com/Prohith45/IndicReel/pulls)

[Key Features](#-key-features) • [Architecture](#-system-architecture) • [Supported Languages](#-supported-indic-languages) • [Quickstart](#-quickstart) • [REST API](#-rest-api-documentation) • [Directory Structure](#-repository-structure)

</div>

---

## 📌 Problem Statement

Over 90% of India's internet population consumes content in their regional native languages, yet content creators and educators are bottlenecked by language barriers:
- **Traditional Dubbing is Prohibitive**: Hiring regional voice actors is slow, costly, and unscalable for high-frequency video output.
- **Generic Robotic TTS Fails**: Standard text-to-speech models strip away the creator's personality, vocal timbre, emotional warmth, and pacing.
- **Length & Audio Pacing Mismatches**: Regional translations vary drastically in word count and cadence (e.g., Telugu often requires 20–35% more syllable time than English), causing dubbing de-sync.

**IndicReel** solves this end-to-end. By combining **Gnani AI's proprietary speech models** (`prisma-v3.0` & `vachana-vc-v1`), **dynamic neural translation**, and **hardware-accelerated FFmpeg processing**, IndicReel automatically extracts speaker timbre from a 10-second reference, transcribes the speech, translates it into 11 Indic languages, synthesizes cloned speech in the creator's exact voice, adjusts audio tempo dynamically, and burns word-synced subtitles directly into the video.

---

## ⚡ Key Features

<table>
  <tr>
    <td width="50%">
      <h3>🧬 Zero-Shot Voice Cloning</h3>
      <p>Clones the creator's authentic vocal tract, pitch, and cadence using <b>Gnani <code>vachana-vc-v1</code></b> from a single 10-second audio slice. No dataset training, fine-tuning, or speaker enrollment required.</p>
    </td>
    <td width="50%">
      <h3>⏱️ Arbitrary Length & 16:9 / 9:16 Support</h3>
      <p>Handles both short-form vertical reels (9:16) and full-length YouTube videos / lectures (16:9). Uses silence-aware VAD chunking (≤ 24s) to bypass API duration limits with zero audio clipping.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>💾 Persistent Voice Profile Manager</h3>
      <p>Save speaker embedding tensors locally (<code>backend/data/voices.json</code>) with custom names. Re-dub new videos in one click from the <b>Saved Voices</b> dropdown—saving API credits and network latency.</p>
    </td>
    <td width="50%">
      <h3>🎯 Dynamic Word-Paced Subtitling</h3>
      <p>Eliminates cluttered, wall-of-text subtitles. Slices translated sentences into dynamic 3–5 word cards mapped proportionally across speech duration, with custom placement for reels vs. widescreen.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🌐 11 Indic Languages Supported</h3>
      <p>Comprehensive localization across Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, Odia, Punjabi, and Indian English with independent subtitle language routing.</p>
    </td>
    <td width="50%">
      <h3>🎛️ Dual Studio Interface & CLI</h3>
      <p>Includes a reactive browser-based <b>Web Studio</b> with live real-time terminal logs, audio wave meters, sample loaders, and a headless <b>CLI Pipeline</b> (<code>cli.py</code>) for automated batch processing.</p>
    </td>
  </tr>
</table>

---

## 🏗️ System Architecture

```text
                                  ┌────────────────────────┐
                                  │   Input Video (.mp4)   │
                                  │  (9:16 Reel / 16:9 YT) │
                                  └───────────┬────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │  Aspect Ratio Detector  │                       │  FFmpeg Audio Extractor │
        │ (Resolution & Layout)   │                       │ (44.1kHz Mono PCM WAV)  │
        └────────────┬────────────┘                       └────────────┬────────────┘
                     │                                                 │
                     │                 ┌───────────────────────────────┴───────────────────────────────┐
                     │                 ▼                                                               ▼
                     │   ┌───────────────────────────┐                                   ┌───────────────────────────┐
                     │   │   10s Reference Audio     │                                   │   Silence-Aware Chunker   │
                     │   │ (Video or Custom .wav/.mp3│                                   │   (VAD Splits <= 24s)     │
                     │   └─────────────┬─────────────┘                                   └─────────────┬─────────────┘
                     │                 ▼                                                               │
                     │   ┌───────────────────────────┐                                                 ▼
                     │   │   Gnani Voice Embedding   │                                   ┌───────────────────────────┐
                     │   │ (Cached in voices.json)   │                                   │  Prisma v3.0 STT Engine   │
                     │   └─────────────┬─────────────┘                                   │  (Concurrent Multi-Chunk) │
                     │                 │                                                 └─────────────┬─────────────┘
                     │                 │                                                               │
                     │                 │   [Speaker Embedding Tensor]                        [English Transcript]
                     │                 │                                                               │
                     │                 │                                                               ▼
                     │                 │                                                 ┌───────────────────────────┐
                     │                 │                                                 │ Dynamic Translation Engine│
                     │                 │                                                 │ (deep-translator + gtx)   │
                     │                 │                                                 └─────────────┬─────────────┘
                     │                 │                                                               │
                     │                 │                                                               ▼
                     │                 │                                                 ┌───────────────────────────┐
                     │                 │                                                 │ Subtitle Language Router  │
                     │                 │                                                 │ (en-IN clean vs regional) │
                     │                 │                                                 └─────────────┬─────────────┘
                     │                 │                                                               │
                     │                 └───────────────────────┬───────────────────────────────────────┘
                     │                                         ▼
                     │                       ┌───────────────────────────────────┐
                     │                       │    Gnani Neural Voice Cloning     │
                     │                       │       (vachana-vc-v1 Model)       │
                     │                       └─────────────────┬─────────────────┘
                     │                                         │
                     │                                         ▼
                     │                       ┌───────────────────────────────────┐
                     │                       │   Dynamic Audio Tempo Alignment   │
                     │                       │    (FFmpeg atempo / pad / sync)   │
                     │                       └─────────────────┬─────────────────┘
                     │                                         │
                     │                                         ▼
                     │                       ┌───────────────────────────────────┐
                     │                       │  Dynamic SRT Subtitle Generator   │
                     │                       │   (3-5 words/card, time-aligned)  │
                     │                       └─────────────────┬─────────────────┘
                     │                                         │
                     ▼                                         ▼
        ┌────────────────────────────────────────────────────────────────────────┐
        │             FFmpeg Hardware/Software Muxer & Subtitle Burner           │
        │   (Smart subtitle placement: MarginV=85 for 9:16 | MarginV=35 for 16:9) │
        └───────────────────────────────────┬────────────────────────────────────┘
                                            │
                                            ▼
                        ┌────────────────────────────────────────┐
                        │       Final Dubbed Video (.mp4)        │
                        │ (Native Timbre + Synchronized Subs)    │
                        └────────────────────────────────────────┘
```

---

## 🌐 Supported Indic Languages

IndicReel supports 11 major Indic languages across Speech-to-Text, Neural Voice Cloning, and Subtitle Localization:

| Language | Native Name | Code | Speech-to-Text | Voice Cloning (`vachana-vc-v1`) | Stock Voice (`timbre-v2.5`) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Telugu** | తెలుగు | `te-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Hindi** | हिन्दी | `hi-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Tamil** | தமிழ் | `ta-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Kannada** | ಕನ್ನಡ | `kn-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Malayalam** | മലയാളം | `ml-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Bengali** | বাংলা | `bn-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Marathi** | मराठी | `mr-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Gujarati** | ગુજરાતી | `gu-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Odia** | ଓଡ଼ିଆ | `or-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Punjabi** | ਪੰਜਾਬੀ | `pa-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |
| **Indian English** | English (India) | `en-IN` | ✅ Prisma v3.0 | ✅ Full Timbre Clone | ✅ Available |

---

## 🚀 Quickstart

### Prerequisites

1. **Python 3.10+** installed.
2. **FFmpeg** installed and accessible via system `PATH` ([Download FFmpeg](https://ffmpeg.org/download.html)).
3. **Gnani AI API Key** ([Sign up at Gnani.ai](https://gnani.ai/)).

---

### Method 1: Windows 1-Click Launch (Easiest)

If you are on Windows, simply double-click:
```bat
run_studio.bat
```
This automatically activates the virtual environment and launches the studio at `http://127.0.0.1:8000`.

---

### Method 2: Manual Setup (Cross-Platform)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Prohith45/IndicReel.git
   cd IndicReel
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your environment variables**:
   ```bash
   # Copy example environment configuration
   cp .env.example .env
   ```
   Edit `.env` with your API credentials:
   ```ini
   GNANI_API_KEY="your_gnani_api_key_here"
   GNANI_BASE_URL="https://api.vachana.ai"
   ```

5. **Start the Web Studio**:
   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Open **`http://localhost:8000`** in any modern web browser.

---

## 💻 Headless CLI Pipeline

For automated workflows, batch rendering, or CI/CD pipelines, use `cli.py`:

```bash
# Dub a video into Telugu with default voice cloning from video audio
python cli.py --video "samples/sample_reel.mp4" --lang "te-IN" --output "output_telugu.mp4"

# Dub into Hindi
python cli.py --video "samples/sample_reel.mp4" --lang "hi-IN" --output "output_hindi.mp4"

# Dub into Tamil
python cli.py --video "samples/sample_reel.mp4" --lang "ta-IN" --output "output_tamil.mp4"
```

---

## 📡 REST API Documentation

The backend exposes a production-ready asynchronous REST API:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Health check, API credentials status, and supported languages list. |
| `GET` | `/api/voices` | Returns all locally saved voice profiles and metadata. |
| `POST` | `/api/voices` | Registers a new custom voice profile from an uploaded `.wav`/`.mp3`/`.mpa` sample. |
| `DELETE` | `/api/voices/{voice_id}` | Deletes a saved voice profile. |
| `POST` | `/api/dub` | Synchronous dubbing pipeline (optimized for short clips $\le 30$s). |
| `POST` | `/api/dub/long` | **Asynchronous chunked pipeline** for arbitrary length videos. Returns `{ job_id }`. |
| `GET` | `/api/jobs/{job_id}` | Polls real-time progress, status percentage, and output download URL. |
| `GET` | `/api/sample-reel` | Streams bundled sample reels for 1-click UI testing. |

### Example: Initiating an Asynchronous Dubbing Job
```bash
curl -X POST "http://127.0.0.1:8000/api/dub/long" \
  -F "video=@samples/sample_reel.mp4" \
  -F "dub_lang=te-IN" \
  -F "sub_lang=en-IN" \
  -F "voice_mode=cloned_video"
```
Response:
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "queued",
  "message": "Long-form dubbing pipeline initiated successfully."
}
```

---

## 📁 Repository Structure

```text
IndicReel/
├── backend/                        # Production FastAPI Core
│   ├── core/                       # Processing Pipeline Modules
│   │   ├── __init__.py             # Module exports
│   │   ├── chunker.py              # Silence-aware VAD chunking (<=24s)
│   │   ├── extractor.py            # FFmpeg audio & 10s voice sample slicer
│   │   ├── muxer.py                # Dynamic SRT builder & video muxer
│   │   ├── stt.py                  # Gnani Prisma v3.0 STT client + cache
│   │   ├── sync.py                 # Audio tempo & duration alignment
│   │   ├── translator.py           # Multi-tier dynamic Indic translation engine
│   │   ├── voice_clone.py          # Gnani vachana-vc-v1 neural voice cloning
│   │   └── voice_store.py          # Persistent voice profiles store
│   ├── data/
│   │   └── voices.json             # Local speaker embedding tensors storage
│   ├── config.py                   # Central paths, directories & settings
│   └── main.py                     # FastAPI application endpoints & routes
├── frontend/                       # Interactive Web Studio UI
│   ├── app.js                      # Reactive state, job polling & audio viz
│   ├── favicon.ico                 # App icon
│   ├── index.html                  # Studio layout (9:16 & 16:9 viewports)
│   └── style.css                   # Glassmorphism dark-mode UI stylesheet
├── samples/
│   └── sample_reel.mp4             # Production test sample video
├── .env.example                    # Template for environment credentials
├── .gitignore                      # Git ignore rules for media & caches
├── cli.py                          # Headless CLI entry point
├── requirements.txt                # Production Python dependencies
├── run_studio.bat                  # Windows 1-click execution script
└── README.md                       # Documentation & Architecture Guide
```

---

## 💡 Engineering Highlights & Technical Innovation

1. **Overcoming the 30s STT Limit**:
   Gnani Prisma v3.0 strictly limits audio duration to 30 seconds (`MAX_AUDIO_DURATION_EXCEEDED`). IndicReel implements a **silence-aware chunker** with energy fallback that segments arbitrary-length videos into $\le 24$s clips, transcribes concurrently, and stitches the timeline flawlessly.

2. **Adaptive Audio-Tempo Alignment**:
   Indic translations naturally differ in length and syllables compared to English. IndicReel compares original speech duration with synthesized dubbed duration, dynamically applying non-pitch-shifting `atempo` filters ($0.5\times$ to $2.0\times$) to ensure the dubbed voice matches lip-movement timing.

3. **Dual-Tier Resilient Translation Engine**:
   To prevent rate-limiting when translating long video transcripts, IndicReel employs a primary neural translation layer via `deep-translator` with automatic tier-2 fallback to the Google Translate `gtx` endpoint, split on clause boundaries ($<1500$ chars).

4. **Zero-Credit Embedding Caching**:
   Extracting voice embeddings consumes network bandwidth and API quota. IndicReel serializes the raw speaker embedding tensor into `backend/data/voices.json`. Once cloned, a voice profile can be reused indefinitely at zero embedding cost.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/Prohith45/IndicReel/issues).

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 👨‍💻 Author & Attribution

Developed with ❤️ by **Rohith Papana**  
*Built for **The Great Indian AI Internship Challenge** powered by **Gnani AI**.*
