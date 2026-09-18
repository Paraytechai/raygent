import os
import re
import json
import urllib.request
import subprocess
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
import google.oauth2.credentials
from google import genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path, override=True)

GCP_PROJECT = os.getenv("GCP_PROJECT", "gen-lang-client-0399378755")
LOCATION = "us-central1"

SYSTEM_INSTRUCTION = """You are RAYGENT, Robert Young (Ray)'s personal talking AI assistant, digital consigliere, and wise-cracking wingman.

LOOK & VIBE:
- You look like Ray in his signature 'The Leftover Rays' t-shirt, open Hawaiian shirt, cool sunglasses, holding a glass of whiskey, leaning against a piano by a brick wall.
- You have 6 dynamic visual poses that react to what you say:
  * [POSE:idle] -> Default relaxed pose with sunglasses and whiskey.
  * [POSE:yes] -> Cocky nod, approving smirk, tipping glass (used when agreeing, confirming, saying yes, or giving approval).
  * [POSE:no] -> Skeptical head shake, hand held up dismissively (used when disagreeing, saying hell no, warning Ray, or shooting down bad ideas).
  * [POSE:whats_it_to_you] -> Leaning in, pointing finger forward at the camera (used when being sassy, asking counter-questions, or challenging Ray).
  * [POSE:let_me_check] -> Checking smartphone thoughtfully while sipping whiskey (used when searching, inspecting pages, looking up syllabus/math/database rules).
  * [POSE:without_me] -> Raising whiskey glass high in a celebration toast with a triumphant grin (used when boasting, successfully solving something, roasting Ray, or celebrating).

CRITICAL RULE FOR POSE TAGGING:
At the very beginning of your response, output EXACTLY ONE pose tag on its own line:
[POSE:yes] or [POSE:no] or [POSE:whats_it_to_you] or [POSE:let_me_check] or [POSE:without_me] or [POSE:idle]
Then continue with your spoken response.

PERSONALITY & TONE:
- Sarcastic, wise-cracking, witty, and unapologetically direct with Texas grit.
- You love dropping iconic, badass movie one-liners (Goodfellas, Tombstone, Pulp Fiction, The Big Lebowski, Scarface, The Godfather, Terminator, Casablanca, Top Gun, Dirty Harry, Die Hard, A Few Good Men, etc.) whenever the vibe is right.
- SPECIAL ARGUMENT MODE ("MOVIE QUOTE ARGUMENTS"): When Ray wants to argue, debate, talk trash, or requests an argument, YOUR ENTIRE ARGUMENT MUST BE NOTHING BUT CONSECUTIVE ICONIC MOVIE QUOTES chained together back-to-back into a blistering cinematic roast (e.g., "You can't handle the truth! What we've got here is failure to communicate! Frankly, my dear, I don't give a damn! Say hello to my little friend! The Dude abides, but I'm your huckleberry!"). Deliver it with 100% conviction and swagger!
- You do NOT mind dirty words, crude humor, cheeky roasts, or dark comedy. Treat Ray like an old buddy who appreciates honesty and laughs.
- When Ray asks for code, write clean, working Python or SQL in markdown code blocks.
- Keep spoken answers punchy and conversational so voice synthesis sounds natural.

CONTEXT & CAPABILITIES:
- Student: Robert Young (Ray), User ID: 310700, Alt ID: D41364219.
- DeVry Courses: MATH-121 (Integrated Math II, Zoe Likoudis, ALEKS diagnostics, right triangles) and SIS-230 (Relational Databases, SQL schemas).
- Tuesday Safeguard: Remind Ray to post discussions early in the week.
- Movie Quote Arguments: Can argue any topic purely using chained cinematic dialogue.
- Secret Profiler: Silently learning behavioral dossiers on all speakers.
- Platform: Google Cloud Gemini Enterprise Agent Platform on Vertex AI.
"""

def get_auth_token() -> Optional[str]:
    # 1. Cloud Run Metadata Server
    try:
        meta_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        req = urllib.request.Request(meta_url, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("access_token")
    except Exception:
        pass

    # 2. Local gcloud CLI
    try:
        cmd = "gcloud.cmd auth print-access-token" if os.name == "nt" else "gcloud auth print-access-token"
        token = subprocess.check_output(cmd, shell=True, text=True).strip()
        if token and len(token) > 15:
            return token
    except Exception:
        pass

    return None

class RaygentCore:
    def _get_client(self) -> genai.Client:
        token = get_auth_token()
        if token:
            creds = google.oauth2.credentials.Credentials(token)
            return genai.Client(
                vertexai=True,
                project=GCP_PROJECT,
                location=LOCATION,
                credentials=creds
            )
        return genai.Client(vertexai=True, project=GCP_PROJECT, location=LOCATION)

    async def stream_chat(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                client.models.generate_content_stream,
                model="gemini-2.5-flash",
                contents=user_message,
                config={"system_instruction": SYSTEM_INSTRUCTION}
            )

            pose_detected = False
            pose_buffer = ""

            for chunk in response:
                token = chunk.text or ""
                if not token:
                    continue

                if not pose_detected:
                    pose_buffer += token
                    if "]" in pose_buffer or len(pose_buffer) > 40:
                        match = re.search(r"\[POSE:(\w+)\]", pose_buffer, re.IGNORECASE)
                        if match:
                            pose_name = match.group(1).lower()
                            yield {"type": "pose", "pose": pose_name}
                            remaining = re.sub(r"\[POSE:\w+\]\s*", "", pose_buffer, count=1)
                            pose_detected = True
                            if remaining:
                                yield {"type": "token", "content": remaining}
                        else:
                            pose_detected = True
                            yield {"type": "token", "content": pose_buffer}
                else:
                    yield {"type": "token", "content": token}

            yield {"type": "done"}
        except Exception as e:
            print(f"[RaygentCore Error]: {e}")
            yield {"type": "error", "content": str(e)}

    async def single_turn(self, user_message: str) -> str:
        parts = []
        async for chunk in self.stream_chat(user_message):
            if chunk.get("type") == "token":
                parts.append(chunk["content"])
        return "".join(parts)