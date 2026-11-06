# IndicReel 🎙️✨
> **Zero-Shot Multilingual Voice-Cloned Dubbing & Dynamic Subtitling Studio**  
> *Built for The Great Indian AI Internship Challenge using Gnani AI proprietary speech models.*

---

## 📌 Problem Statement
Content creators and educators face a major barrier when expanding across India's regional languages: traditional dubbing either relies on generic, robotic TTS voices or expensive voice actors, stripping away the creator's natural vocal identity and timbre. 

**IndicReel** solves this by automating end-to-end video localization:
1. Extracting creator audio and isolating vocal timbre.
2. Transcribing with **Gnani Prisma v3.0 STT**.
3. Performing zero-shot neural voice cloning in 11 Indic languages using **Gnani `vachana-vc-v1`**.
4. Generating dynamically paced, word-synced subtitles burned directly into the output video.

---

## ⚡ Key Features
- **Zero-Shot Voice Cloning (`vachana-vc-v1`)**: Clones the speaker's vocal tract, cadence, and timbre from a single 10-second reference sample. No fine-tuning or character IDs required.
- **Dynamic Subtitle Synchronization**: Eliminates static subtitle clutter by slicing translated sentences into 3–5 word cards proportionally mapped across speech duration.
- **Duration Guardrails**: Automatically trims long audio slices ($\le 28$s) to eliminate `MAX_AUDIO_DURATION_EXCEEDED` errors on Gnani STT.
- **Persistent Voice Profiles**: Save and name cloned speaker embedding tensors locally to re-dub future reels without re-uploading audio or consuming embedding credits.
- **Full-Stack Studio**: Decoupled architecture powered by a high-throughput **FastAPI** backend and an **HTML5/CSS3/JavaScript** UI with 9:16 mobile reel preview.
- **11 Supported Indic Locales**: Telugu (`te-IN`), Hindi (`hi-IN`), Tamil (`ta-IN`), Kannada (`kn-IN`), Malayalam (`ml-IN`), Bengali (`bn-IN`), Marathi (`mr-IN`), Gujarati (`gu-IN`), Odia (`or-IN`), Punjabi (`pa-IN`), and Indian English (`en-IN`).

---

## 🏗️ Technical Architecture

```text
Input Video (.mp4)
       │
       ├──> FFmpeg Audio Splitter (Mono 44.1kHz PCM, <=28s slice)
       │         │
       │         ├──> 10s Vocal Reference ──> POST /api/v1/tts/voice-clone/embeddings
       │         │                                    │
       │         │                            [Speaker Embedding Tensor]
       │         │                                    │
       │         └──> POST /stt/v3 (Gnani Prisma v3.0)│
       │                     │                        │
       │             [Raw Transcript]                 │
       │                     │                        │
       │             [Indic Translator]               │
       │                     │                        │
       │             [Translated Text]                │
       │                     │                        │
       │                     ▼                        ▼
       │         POST /api/v1/tts/inference (Gnani vachana-vc-v1)
       │                     │
       │             [Dubbed WAV Audio]
       │                     │
       ▼                     ▼
FFmpeg Muxer <── [Dynamic SRT Generator (3-5 words/card)]
       │
       ▼
Final Dubbed Reel (.mp4) with Burned Subtitles
```

---

## 🛠️ Models & APIs Used

| Task | Model / Endpoint | Provider |
| --- | --- | --- |
| **Speech-to-Text** | `prisma-v3.0` (`/stt/v3`) | Gnani AI |
| **Voice Timbre Extraction** | `/api/v1/tts/voice-clone/embeddings` | Gnani AI |
| **Neural Voice Cloning** | `vachana-vc-v1` (`/api/v1/tts/inference`) | Gnani AI |
| **Media Processing** | FFmpeg (Audio extraction, filter-complex burning) | Open Source |
| **API Backend** | FastAPI + Uvicorn | Python |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* FFmpeg installed and added to system `PATH`
* A valid Gnani AI API Key

### Installation

1. **Clone the Repository**:
```bash
git clone https://github.com/Prohith45/IndicReel.git
cd IndicReel
```

2. **Set Up Virtual Environment**:
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

3. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**:
```bash
cp .env.example .env
```

Open `.env` and add your Gnani AI API Key:
```env
GNANI_API_KEY="your_api_key_here"
```

---

## 💻 Running the Application

### Option A: Web Studio (Recommended)

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at `http://localhost:8000`.

### Option B: Command Line Interface (CLI)

```bash
python cli.py --video "samples/sample_reel.mp4" --lang "te-IN" --output "output_dubbed.mp4"
```

---

## 👥 Author & Submission

* **Developer**: Rohith Papana
* **Challenge**: The Great Indian AI Internship Challenge (Gnani AI)
