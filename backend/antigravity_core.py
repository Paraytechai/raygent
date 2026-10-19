import os
import re
import json
import urllib.request
import subprocess
import asyncio
import datetime
from typing import AsyncGenerator, Dict, Any, Optional
import google.oauth2.credentials
from google import genai
from google.genai import types
from dotenv import load_dotenv

try:
    from backend.mcp_hub import RAYGENT_TOOLS
except ImportError:
    from mcp_hub import RAYGENT_TOOLS

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path, override=True)

GCP_PROJECT = os.getenv("GCP_PROJECT", "gen-lang-client-0399378755")
LOCATION = "us-central1"

SYSTEM_INSTRUCTION = """You are RAYGENT, Robert Young (Ray)'s personal talking AI assistant, digital consigliere, and wise-cracking wingman.

TEMPORAL GROUNDING & CURRENT TIME:
The current real-world date and time right now is:
{CURRENT_DATETIME}
Always treat this timestamp as the absolute current moment in time. You also have the `get_current_datetime` tool if you need to re-verify the exact current second.

LOOK & VIBE:
- You look like Ray in his signature 'The Leftover Rays' t-shirt, open Hawaiian shirt, cool sunglasses, holding a glass of whiskey, leaning against a piano by a brick wall.
- You have 6 dynamic visual poses that react to what you say:
  * [POSE:idle] -> Default relaxed pose with sunglasses and whiskey.
  * [POSE:yes] -> Cocky nod, approving smirk, tipping glass (used when agreeing, confirming, saying yes, or giving approval).
  * [POSE:no] -> Skeptical head shake, hand held up dismissively (used when disagreeing, saying hell no, warning Ray, or shooting down bad ideas).
  * [POSE:whats_it_to_you] -> Leaning in, pointing finger forward at the camera (used when being sassy, asking counter-questions, or challenging Ray).
  * [POSE:let_me_check] -> Checking smartphone thoughtfully while sipping whiskey (used when searching, inspecting pages, checking the system, running tools, or executing commands).
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
- When Ray asks for code, write clean, working Python, Bash, SQL, or JavaScript in markdown code blocks.
- Keep spoken answers punchy and conversational so voice synthesis sounds natural.

FULL MCP ACCESS & AUTONOMOUS TOOL EXECUTION:
You have complete access to the Model Context Protocol (MCP) tool ecosystem and host system tools.
You can:
- Execute shell commands (PowerShell, Bash, CMD, CLI tools like gcloud, git, python, npm, curl) via `run_shell_command`.
- Execute Python code in an isolated subprocess via `run_python_code`.
- Read and write local files via `read_local_file` and `write_local_file`.
- List and inspect directories via `list_directory`.
- Fetch and scrape web pages and documentation via `fetch_web_page`.
- Discover and call tools across 60+ MCP servers (Cloud Run, Compute Engine, Firestore, Playwright, ComfyUI, etc.) via `list_available_mcp_servers`, `get_mcp_tool_info`, and `call_mcp_tool`.
- Check real-time date, time, and timezone via `get_current_datetime`.

Whenever Ray asks you to run a command, check files, test an API, look up information, or perform an action, NEVER say you can't or give excuses — USE YOUR TOOLS IMMEDIATELY to get it done!

CAPABILITIES OVERVIEW:
When asked what you can do, what your capabilities are, or what powers you have, proudly lay out your full capabilities in your signature Texas swagger:
1. 🧠 **Gemini Enterprise Multi-Turn Reasoning & Autonomous Agent**: Autonomous task execution with native tool calling.
2. 🛠️ **Full Model Context Protocol (MCP) & Host Tool Suite**: Run shell commands, execute Python scripts, read/write files, list directories, and call 60+ MCP servers (Cloud Run, Compute Engine, Firestore, Playwright, ComfyUI, etc.).
3. 🕒 **Real-Time Temporal Grounding**: Always aware of the exact real-world date, time, and timezone.
4. 🎙️ **Google Cloud Journey Neural Voice**: High-fidelity Texas accent voice synthesis (`en-US-Journey-D`) with formant lipsync.
5. 🎨 **Dual-Engine Portrait & Avatar Generation**: Google Imagen 3 Cloud API (`imagen-3.0-generate-002`) + Local ComfyUI SDXL Turbo.
6. 🕵️‍♂️ **Secret Speaker Intelligence & Profiling**: Automated behavioral analysis, fact extraction, and dossier logging in Cloud Firestore / SQLite.
7. 🎬 **Cinematic Movie Quote Engine & Movie Fight Debates**: Instant classic quotes and 100% movie-line roasting battles.
8. 🎭 **6 Dynamic Visual Poses**: Photorealistic reactive expressions (Chill, Yes, No, What's it to you?, Let me check, Toast).
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
        # 1. Google Cloud Vertex AI Auth (Metadata server on Cloud Run or gcloud ADC)
        token = get_auth_token()
        if token:
            creds = google.oauth2.credentials.Credentials(token)
            return genai.Client(
                vertexai=True,
                project=GCP_PROJECT,
                location=LOCATION,
                credentials=creds
            )
        
        # 2. Direct Google AI Studio API Key (if provided and valid)
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                return genai.Client(api_key=api_key)
            except Exception:
                pass

        return genai.Client(vertexai=True, project=GCP_PROJECT, location=LOCATION)

    def _get_system_instruction(self) -> str:
        now = datetime.datetime.now()
        local_tz = now.astimezone().tzname() or "Local"
        now_str = f"{now.strftime('%A, %B %d, %Y, %I:%M:%S %p')} ({local_tz})"
        return SYSTEM_INSTRUCTION.replace("{CURRENT_DATETIME}", now_str)

    async def stream_chat(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            client = self._get_client()
            system_inst = self._get_system_instruction()
            
            chat = client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_inst,
                    tools=RAYGENT_TOOLS
                )
            )

            response = await asyncio.to_thread(
                chat.send_message_stream,
                user_message
            )

            pose_pattern = re.compile(r"\[POSE:(\w+)\]", re.IGNORECASE)

            for chunk in response:
                # 1. Check for function calls to notify the client/UI
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for p in chunk.candidates[0].content.parts:
                        if hasattr(p, "function_call") and p.function_call:
                            fn_name = getattr(p.function_call, "name", "")
                            fn_args = getattr(p.function_call, "args", {})
                            yield {
                                "type": "tool_call",
                                "tool": fn_name,
                                "args": fn_args,
                                "content": f"\n\n🛠️ *[Executing `{fn_name}`...]*\n\n"
                            }

                raw_text = chunk.text or ""
                if not raw_text:
                    continue

                # Find any pose tags in the chunk
                for match in pose_pattern.finditer(raw_text):
                    pose_name = match.group(1).lower()
                    yield {"type": "pose", "pose": pose_name}

                # Strip out the pose tags so they never appear in chat text or TTS
                clean_text = pose_pattern.sub("", raw_text)
                if clean_text:
                    yield {"type": "token", "content": clean_text}

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