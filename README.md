# 🤠 Raygent - Autonomous AI Wingman & Intelligent Agent Platform

Raygent is an interactive, cyberpunk-themed autonomous AI agent and personal wingman engineered with **Google Gemini Pro**, **Vertex AI Agent Builder**, neural voice synthesis, and real-time audio-reactive formant avatar lip-sync.

---

## ⚡ Key Capabilities

- **🎙️ Formant Audio-Reactive Lip-Sync Avatar**: Real-time multi-band FFT spectral decomposition driving mouth, jaw, and lip-spread visemes ({\text{jaw}}$, {\text{spread}}$, {\text{sibilant}}$) on video and photo avatars.
- **🕵️ Secret Intelligence Profiler**: Non-blocking background behavioral and psychological profiling engine storing speaker dossiers, sentiments, vulnerability flags, and extracted facts in a relational SQLite intelligence database (protected with password authentication).
- **🎬 Movie Argument & Quote Engine**: Instant classic one-liners and full debate arguments constructed entirely from famous movie lines.
- **🔊 Multi-Tier TTS Voice Engine**:
  1. Priority 1: Zero-Shot OmniVoice Neural Voice Cloning on GPU / CUDA.
  2. Priority 2: Google Cloud Neural Journey Studio Voices.
  3. Priority 3: Low-latency Web Audio fallback.
- **☁️ Cloud Run & Vertex AI Ready**: Containerized with Dockerfile and integrated with Google Cloud Run and Vertex AI Agent Builder via OpenAPI 3.0 specs.
- **🗖 Mini Widget HUD Mode**: Compact, floating desktop HUD with hotkey listeners (Alt+M for mini toggle, Alt+I for secret intel access, push-to-talk).

---

## 🛠️ Quick Start

### 1. Clone & Install Dependencies
\\\ash
git clone https://github.com/Paraytechai/raygent.git
cd raygent
pip install -r requirements.txt
\\\

### 2. Configure Environment Variables
Create a \.env\ file in the root directory:
\\\ini
GOOGLE_API_KEY=your_gemini_api_key
GCP_PROJECT=your_gcp_project_id
USE_VERTEX=true
\\\

### 3. Run Locally
\\\ash
python run_server.py
\\\
Visit \http://127.0.0.1:8765\ in your browser.

---

## 🚀 Google Cloud Run Deployment
\\\ash
gcloud run deploy raygent \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
\\\

---

## 📄 License
MIT License. Created for Ray Young (@cyberray68).
