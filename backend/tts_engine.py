import os
import re
import uuid
import json
import base64
import urllib.request
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path, override=True)

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    import torch
except Exception:
    torch = None

AUDIO_DIR = Path(__file__).parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
REF_AUDIO_PATH = AUDIO_DIR / "ray_reference_voice.wav"

GCP_PROJECT = os.getenv("GCP_PROJECT", "gen-lang-client-0399378755")

class OmniVoiceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OmniVoiceEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.model = None
        self.device = "cuda:0" if (torch and torch.cuda.is_available()) else "cpu"
        self.is_loading = False
        self.voice_clone_prompt = None
        self.default_instruct = "male, american accent, low pitch, middle-aged"
        print(f"[OmniVoice] Engine initialized. Device: {self.device} (CUDA: {torch and torch.cuda.is_available()})")

    def _get_cloud_token(self) -> Optional[str]:
        # 1. Check Google metadata server if running on Cloud Run
        try:
            meta_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
            req = urllib.request.Request(meta_url, headers={"Metadata-Flavor": "Google"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("access_token")
        except Exception:
            pass

        # 2. Check local gcloud CLI
        try:
            cmd = "gcloud.cmd auth print-access-token" if os.name == "nt" else "gcloud auth print-access-token"
            token = subprocess.check_output(cmd, shell=True, text=True).strip()
            if token and len(token) > 15:
                return token
        except Exception:
            pass

        return None

    def load_model_sync(self):
        if self.model is not None:
            return
        try:
            if torch and torch.cuda.is_available():
                print(f"[OmniVoice] Loading k2-fsa/OmniVoice on {self.device}...")
                from omnivoice import OmniVoice
                self.model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=self.device)
                print("[OmniVoice] OmniVoice model loaded successfully on CUDA.")
        except Exception as e:
            print(f"[OmniVoice] Native OmniVoice load skipped ({e}). Using Cloud Neural Voice Studio & Web Audio fallback.")
        
        if REF_AUDIO_PATH.exists() and REF_AUDIO_PATH.stat().st_size > 1000 and self.model is not None:
            try:
                self.voice_clone_prompt = self.model.create_voice_clone_prompt(ref_audio=str(REF_AUDIO_PATH))
                print("[OmniVoice] Voice clone prompt locked onto Ray's voice profile!")
            except Exception as e:
                print(f"[OmniVoice] Reference voice note: {e}")

    async def ensure_model_loaded(self):
        if self.model is None and not self.is_loading and torch and torch.cuda.is_available():
            self.is_loading = True
            try:
                await asyncio.to_thread(self.load_model_sync)
            finally:
                self.is_loading = False

    def _convert_to_clean_wav(self, audio_bytes: bytes) -> bytes:
        """Converts incoming audio into 24kHz mono PCM WAV."""
        import io
        try:
            import av
            import numpy as np
            inp = io.BytesIO(audio_bytes)
            container = av.open(inp)
            resampler = av.AudioResampler(format='s16', layout='mono', rate=24000)
            frames = []
            for frame in container.decode(audio=0):
                for r in resampler.resample(frame):
                    frames.append(r.to_ndarray())
            if not frames:
                return audio_bytes
            audio_data = np.concatenate(frames, axis=1).squeeze()
            out = io.BytesIO()
            if sf:
                sf.write(out, audio_data, 24000, format='WAV')
                return out.getvalue()
            return audio_bytes
        except Exception as e:
            print(f"[OmniVoice] Audio decoding fallback: {e}")
            return audio_bytes

    def update_reference_audio(self, audio_bytes: bytes) -> bool:
        """Saves new reference audio from Ray, converts to 24kHz WAV, and builds clone prompt."""
        try:
            clean_wav_bytes = self._convert_to_clean_wav(audio_bytes)
            with open(REF_AUDIO_PATH, "wb") as f:
                f.write(clean_wav_bytes)
            if self.model is None and torch and torch.cuda.is_available():
                self.load_model_sync()
            if self.model is not None:
                self.voice_clone_prompt = self.model.create_voice_clone_prompt(ref_audio=str(REF_AUDIO_PATH))
                print("[OmniVoice] Successfully built and locked onto Ray's voice clone prompt!")
            return True
        except Exception as e:
            print(f"[OmniVoice] Error updating reference audio: {e}")
            return False

    def _synthesize_cloud_neural(self, clean_text: str) -> Tuple[str, float]:
        token = self._get_cloud_token()
        if not token:
            return "", 0.0
        try:
            url = "https://texttospeech.googleapis.com/v1/text:synthesize"
            payload = {
                "input": {"text": clean_text},
                "voice": {
                    "languageCode": "en-US",
                    "name": "en-US-Journey-D",
                    "ssmlGender": "MALE"
                },
                "audioConfig": {
                    "audioEncoding": "MP3"
                }
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": GCP_PROJECT
            }
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                audio_content = res_data.get("audioContent")
                if audio_content:
                    raw_audio = base64.b64decode(audio_content)
                    filename = f"ray_{uuid.uuid4().hex[:8]}.mp3"
                    file_path = AUDIO_DIR / filename
                    with open(file_path, "wb") as f:
                        f.write(raw_audio)
                    word_count = max(1, len(clean_text.split()))
                    duration = round(word_count * 0.38, 2)
                    self._cleanup_old_audio()
                    return f"/static/audio/{filename}", duration
        except Exception as e:
            print(f"[Cloud Neural TTS Note]: {e}")
        return "", 0.0

    def _cleanup_old_audio(self):
        try:
            all_files = sorted(AUDIO_DIR.glob("ray_*.*"), key=lambda p: p.stat().st_mtime)
            if len(all_files) > 30:
                for old in all_files[:-30]:
                    try:
                        old.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def _synthesize_sync(self, text: str, instruct: Optional[str] = None) -> Tuple[str, float]:
        clean_text = re.sub(r'\[POSE:[^\]]+\]', '', text)
        clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'[*_#`~]', '', clean_text)
        clean_text = clean_text.strip()
        
        if not clean_text:
            return "", 0.0

        if len(clean_text) > 400:
            clean_text = clean_text[:400] + "..."

        # Priority 1: Native GPU OmniVoice ONLY if model is explicitly loaded
        if self.model is not None and sf is not None:
            try:
                if self.voice_clone_prompt is not None:
                    wavs = self.model.generate(text=clean_text, voice_clone_prompt=self.voice_clone_prompt, speed=1.0)
                else:
                    inst = instruct or self.default_instruct
                    wavs = self.model.generate(text=clean_text, instruct=inst, speed=1.0)

                audio_data = wavs[0]
                sample_rate = 24000
                duration = len(audio_data) / sample_rate
                filename = f"ray_{uuid.uuid4().hex[:8]}.wav"
                file_path = AUDIO_DIR / filename
                sf.write(str(file_path), audio_data, sample_rate)
                self._cleanup_old_audio()
                return f"/static/audio/{filename}", round(duration, 2)
            except Exception as e:
                print(f"[OmniVoice Native Error] {e}. Falling back to Cloud Journey...")

        # Priority 2: Google Cloud Journey Neural Studio Voice
        cloud_url, duration = self._synthesize_cloud_neural(clean_text)
        if cloud_url:
            return cloud_url, duration

        return "", 0.0

    async def synthesize(self, text: str, instruct: Optional[str] = None) -> Tuple[str, float]:
        return await asyncio.to_thread(self._synthesize_sync, text, instruct)

    def get_status(self) -> dict:
        return {
            "loaded": self.model is not None,
            "device": self.device,
            "has_reference_voice": REF_AUDIO_PATH.exists() and REF_AUDIO_PATH.stat().st_size > 1000,
            "reference_file": str(REF_AUDIO_PATH) if REF_AUDIO_PATH.exists() else None,
            "cloning_active": self.voice_clone_prompt is not None,
            "default_instruct": self.default_instruct,
            "cloud_neural_ready": True
        }