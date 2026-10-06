import os
import json
import base64
import urllib.request
from typing import Optional
from backend.antigravity_core import get_auth_token

GCP_PROJECT = os.getenv("GCP_PROJECT", "gen-lang-client-0399378755")
LOCATION = "us-central1"

class CloudSpeechToText:
    """Google Cloud Speech-to-Text V2 & Chirp Universal Multimodal Transcriber."""

    @staticmethod
    async def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> Optional[str]:
        if not audio_bytes:
            return None

        token = get_auth_token()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-User-Project": GCP_PROJECT
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        api_key = os.getenv("GOOGLE_API_KEY", "")
        base_url = "https://speech.googleapis.com/v1/speech:recognize"
        if not token and api_key:
            base_url += f"?key={api_key}"

        b64_content = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Audio recognition configuration
        encoding = "WEBM_OPUS" if "webm" in mime_type.lower() else "LINEAR16"
        payload = {
            "config": {
                "encoding": encoding,
                "languageCode": "en-US",
                "enableAutomaticPunctuation": True,
                "model": "latest_long"
            },
            "audio": {
                "content": b64_content
            }
        }

        try:
            req = urllib.request.Request(
                base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                results = res_data.get("results", [])
                if results and len(results) > 0:
                    alt = results[0].get("alternatives", [])
                    if alt and len(alt) > 0:
                        return alt[0].get("transcript", "").strip()
        except Exception as e:
            print(f"[Google Cloud STT Error]: {e}")

        return None
