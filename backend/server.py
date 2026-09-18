import os
import re
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path, override=True)

from backend.antigravity_core import RaygentCore
from backend.tts_engine import OmniVoiceEngine
from backend.intelligence_analyzer import SecretIntelligenceProfiler

app = FastAPI(title="Raygent Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

core = RaygentCore()
tts = OmniVoiceEngine()
profiler = SecretIntelligenceProfiler()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tts.ensure_model_loaded())


STATIC_DIR = Path(__file__).parent.parent / "static"
AVATARS_DIR = STATIC_DIR / "avatars"
INSPECTIONS_DIR = STATIC_DIR / "inspections"
INSPECTIONS_DIR.mkdir(parents=True, exist_ok=True)


hud_state = {
    "mode": "full",
    "width": 480,
    "height": 720
}

@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": "Raygent", "backend": "Gemini Enterprise Agent Platform"}

@app.get("/api/hud/state")
async def get_hud_state():
    return hud_state

@app.post("/api/hud/mode")
async def set_hud_mode(data: dict):
    mode = data.get("mode", "full")
    if mode == "mini":
        hud_state["mode"] = "mini"
        hud_state["width"] = 340
        hud_state["height"] = 420
    else:
        hud_state["mode"] = "full"
        hud_state["width"] = 480
        hud_state["height"] = 720
    return hud_state

@app.get("/api/poses")
async def list_poses():
    """List all available avatar poses."""
    poses = [
        {"id": "idle", "name": "Neutral / Chill", "url": "/static/avatars/ray_idle.png"},
        {"id": "yes", "name": "Yes / Approval", "url": "/static/avatars/ray_yes.jpg"},
        {"id": "no", "name": "No / Skeptical", "url": "/static/avatars/ray_no.jpg"},
        {"id": "whats_it_to_you", "name": "What's it to you?", "url": "/static/avatars/ray_whats_it_to_you.jpg"},
        {"id": "let_me_check", "name": "Let me check", "url": "/static/avatars/ray_let_me_check.jpg"},
        {"id": "without_me", "name": "Without me / Toast", "url": "/static/avatars/ray_without_me.jpg"},
    ]
    return {"poses": poses}

@app.get("/api/avatars")
async def list_avatars():
    items = []
    if AVATARS_DIR.exists():
        for p in AVATARS_DIR.iterdir():
            if p.is_file():
                ext = p.suffix.lower()
                is_video = ext in [".mp4", ".webm", ".mov"]
                is_image = ext in [".jpg", ".jpeg", ".png", ".webp"]
                if is_video or is_image:
                    items.append({
                        "name": p.name,
                        "url": f"/static/avatars/{p.name}",
                        "type": "video" if is_video else "image",
                        "size": p.stat().st_size
                    })
MOVIE_QUOTES = [
    {"quote": "I'm your huckleberry.", "movie": "Tombstone", "pose": "without_me"},
    {"quote": "Say hello to my little friend!", "movie": "Scarface", "pose": "whats_it_to_you"},
    {"quote": "Here's looking at you, kid.", "movie": "Casablanca", "pose": "yes"},
    {"quote": "I'm gonna make him an offer he can't refuse.", "movie": "The Godfather", "pose": "yes"},
    {"quote": "The Dude abides.", "movie": "The Big Lebowski", "pose": "idle"},
    {"quote": "As far back as I can remember, I always wanted to be a gangster.", "movie": "Goodfellas", "pose": "without_me"},
    {"quote": "I'll be back.", "movie": "The Terminator", "pose": "whats_it_to_you"},
    {"quote": "Go ahead, make my day.", "movie": "Sudden Impact", "pose": "whats_it_to_you"},
    {"quote": "Yippee-ki-yay, motherf***er!", "movie": "Die Hard", "pose": "without_me"},
    {"quote": "I feel the need... the need for speed!", "movie": "Top Gun", "pose": "yes"},
    {"quote": "You can't handle the truth!", "movie": "A Few Good Men", "pose": "no"},
    {"quote": "Houston, we have a problem.", "movie": "Apollo 13", "pose": "let_me_check"},
    {"quote": "May the Force be with you.", "movie": "Star Wars", "pose": "idle"},
    {"quote": "Keep your friends close, but your enemies closer.", "movie": "The Godfather Part II", "pose": "let_me_check"},
]

MOVIE_ARGUMENTS = [
    {
        "argument": "You can't handle the truth! What we've got here is failure to communicate! Frankly, my dear, I don't give a damn!",
        "sources": ["A Few Good Men", "Cool Hand Luke", "Gone with the Wind"],
        "pose": "no"
    },
    {
        "argument": "Say hello to my little friend! Go ahead, make my day! You talkin' to me? Well, I'm the only one here!",
        "sources": ["Scarface", "Sudden Impact", "Taxi Driver"],
        "pose": "whats_it_to_you"
    },
    {
        "argument": "I'm your huckleberry! I'll be back, and yippee-ki-yay, motherf***er!",
        "sources": ["Tombstone", "The Terminator", "Die Hard"],
        "pose": "without_me"
    },
    {
        "argument": "That's just, like, your opinion, man! Houston, we have a problem! Keep your friends close, but your enemies closer!",
        "sources": ["The Big Lebowski", "Apollo 13", "The Godfather Part II"],
        "pose": "let_me_check"
    },
    {
        "argument": "Show me the money! Leave the gun, take the cannoli! I love the smell of napalm in the morning!",
        "sources": ["Jerry Maguire", "The Godfather", "Apocalypse Now"],
        "pose": "yes"
    },
    {
        "argument": "Are you not entertained?! Say 'what' again, I dare you, I double dare you! You're gonna need a bigger boat!",
        "sources": ["Gladiator", "Pulp Fiction", "Jaws"],
        "pose": "whats_it_to_you"
    }
]

@app.get("/api/movie_quote")
async def get_random_movie_quote():
    import random
    selected = random.choice(MOVIE_QUOTES)
    return selected

@app.get("/api/movie_argument")
async def get_random_movie_argument():
    import random
    selected = random.choice(MOVIE_ARGUMENTS)
    return selected

connected_websockets = set()

async def broadcast_websocket(event: dict):
    for ws in list(connected_websockets):
        try:
            await ws.send_json(event)
        except Exception:
            connected_websockets.discard(ws)

def get_comfy_port() -> int:
    import urllib.request
    for port in [8189, 8188]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=0.5) as r:
                if r.status == 200:
                    return port
        except Exception:
            pass
    return 8189

async def generate_comfy_avatar(prompt: str) -> Optional[dict]:
    import time
    import urllib.request
    import urllib.parse
    port = get_comfy_port()
    clean_prompt = prompt.strip()
    if not clean_prompt:
        clean_prompt = "cyberpunk avatar with glowing neon eyes, portrait"

    wf = {
        '3': {
            'class_type': 'KSampler',
            'inputs': {
                'cfg': 1.0,
                'denoise': 1.0,
                'latent_image': ['5', 0],
                'model': ['4', 0],
                'negative': ['7', 0],
                'positive': ['6', 0],
                'sampler_name': 'euler_ancestral',
                'scheduler': 'karras',
                'seed': int(time.time()),
                'steps': 1
            }
        },
        '4': {
            'class_type': 'CheckpointLoaderSimple',
            'inputs': {
                'ckpt_name': 'sd_xl_turbo_1.0_fp16.safetensors'
            }
        },
        '5': {
            'class_type': 'EmptyLatentImage',
            'inputs': {
                'batch_size': 1,
                'height': 512,
                'width': 512
            }
        },
        '6': {
            'class_type': 'CLIPTextEncode',
            'inputs': {
                'clip': ['4', 1],
                'text': f"close-up centered portrait headshot of {clean_prompt}, clean lighting, front facing, 8k, photorealistic"
            }
        },
        '7': {
            'class_type': 'CLIPTextEncode',
            'inputs': {
                'clip': ['4', 1],
                'text': "blurry, ugly, distorted, deformed, text, watermark, bad anatomy"
            }
        },
        '8': {
            'class_type': 'VAEDecode',
            'inputs': {
                'samples': ['3', 0],
                'vae': ['4', 2]
            }
        },
        '9': {
            'class_type': 'SaveImage',
            'inputs': {
                'filename_prefix': 'RaygentCustom',
                'images': ['8', 0]
            }
        }
    }

    try:
        data = json.dumps({'prompt': wf}).encode('utf-8')
        req = urllib.request.Request(f"http://127.0.0.1:{port}/prompt", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            prompt_id = res.get('prompt_id')

        if not prompt_id:
            return None

        # Poll for completion
        for _ in range(40):
            await asyncio.sleep(0.3)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/history/{prompt_id}", timeout=2) as h_resp:
                    history = json.loads(h_resp.read().decode('utf-8'))
                    if prompt_id in history:
                        outputs = history[prompt_id].get('outputs', {})
                        if '9' in outputs and 'images' in outputs['9']:
                            img_meta = outputs['9']['images'][0]
                            filename = img_meta['filename']
                            subfolder = img_meta.get('subfolder', '')
                            folder_type = img_meta.get('type', 'output')

                            # Download from ComfyUI view API
                            view_params = urllib.parse.urlencode({
                                'filename': filename,
                                'subfolder': subfolder,
                                'type': folder_type
                            })
                            view_url = f"http://127.0.0.1:{port}/view?{view_params}"

                            # Save to AVATARS_DIR
                            ts = int(time.time())
                            slug = re.sub(r'[^a-zA-Z0-9_]', '_', clean_prompt[:25]).strip('_')
                            saved_filename = f"gen_{slug}_{ts}.png"
                            saved_dest = AVATARS_DIR / saved_filename

                            with urllib.request.urlopen(view_url, timeout=5) as img_resp:
                                with open(saved_dest, 'wb') as f:
                                    f.write(img_resp.read())

                            return {
                                "status": "success",
                                "name": clean_prompt,
                                "filename": saved_filename,
                                "url": f"/static/avatars/{saved_filename}",
                                "type": "image"
                            }
            except Exception:
                pass
    except Exception as e:
        print(f"[ComfyUI Generator Error]: {e}")
        return None
    return None

async def generate_imagen_avatar(prompt: str) -> Optional[dict]:
    """Generate high quality avatar using Google AI Studio / Vertex Imagen 3 API."""
    import time
    clean_prompt = prompt.strip()
    if not clean_prompt:
        clean_prompt = "cyberpunk avatar with glowing neon eyes, portrait"
    try:
        client = core._get_client()
        result = await asyncio.to_thread(
            client.models.generate_images,
            model="imagen-3.0-generate-002",
            prompt=f"Centered close-up headshot portrait of {clean_prompt}, photorealistic, dramatic lighting, 8k, looking at camera",
            config={
                "number_of_images": 1,
                "aspect_ratio": "1:1",
                "output_mime_type": "image/png"
            }
        )
        if result and result.generated_images:
            img_bytes = result.generated_images[0].image.image_bytes
            ts = int(time.time())
            slug = re.sub(r'[^a-zA-Z0-9_]', '_', clean_prompt[:25]).strip('_')
            saved_filename = f"gen_imagen_{slug}_{ts}.png"
            saved_dest = AVATARS_DIR / saved_filename
            with open(saved_dest, "wb") as f:
                f.write(img_bytes)
            return {
                "status": "success",
                "name": clean_prompt,
                "filename": saved_filename,
                "url": f"/static/avatars/{saved_filename}",
                "type": "image",
                "engine": "Google Imagen 3 (AI Studio / Vertex)"
            }
    except Exception as e:
        print(f"[Google Imagen 3 Error]: {e}")
        return None
    return None

@app.post("/api/generate_avatar")
async def api_generate_avatar(data: dict):
    prompt = data.get("prompt", "").strip()
    preferred_engine = data.get("engine", "auto") # auto, comfy, google
    if not prompt:
        return JSONResponse({"error": "Prompt required"}, status_code=400)

    result = None
    # 1. Try ComfyUI (if requested or auto)
    if preferred_engine in ("comfy", "auto"):
        result = await generate_comfy_avatar(prompt)
        if result:
            result["engine"] = "Local ComfyUI (SDXL Turbo • RTX 5060 Ti)"

    # 2. Fallback to Google Imagen 3 Cloud API (AI Studio / Vertex AI)
    if not result and preferred_engine in ("google", "auto"):
        result = await generate_imagen_avatar(prompt)

    if not result:
        return JSONResponse({
            "status": "error",
            "message": "Avatar generation failed on both Local ComfyUI and Google Imagen 3 Cloud API."
        }, status_code=500)

    await broadcast_websocket({
        "type": "avatar_change",
        "url": result["url"],
        "name": result["name"],
        "media_type": "image"
    })
    return result

@app.post("/api/set_avatar")
async def set_avatar(data: dict):
    url = data.get("url")
    name = data.get("name", "Custom Avatar")
    media_type = data.get("type", "image")
    if not url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    await broadcast_websocket({
        "type": "avatar_change",
        "url": url,
        "name": name,
        "media_type": media_type
    })
    return {"status": "success", "url": url, "name": name, "type": media_type}

@app.post("/api/launch_webcam")
async def launch_webcam():
    """Launch the LivePortrait webcam driving script."""
    script_path = Path(__file__).parent.parent / "liveportrait_webcam_runner.py"
    try:
        subprocess.Popen(["python", str(script_path)], shell=True)
        return {"status": "success", "message": "LivePortrait webcam driver launched!"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/upload_avatar")
async def upload_avatar(request: Request):
    import base64
    data = await request.json()
    filename = data.get("filename", "custom_avatar.jpg")
    clean_name = "".join(c for c in filename if c.isalnum() or c in "._-")
    dest = AVATARS_DIR / clean_name
    
    b64_data = data.get("data", "")
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    raw_bytes = base64.b64decode(b64_data)
    
    with open(dest, "wb") as f:
        f.write(raw_bytes)
        
    is_video = dest.suffix.lower() in [".mp4", ".webm", ".mov"]
    avatar_info = {
        "status": "success",
        "name": clean_name,
        "url": f"/static/avatars/{clean_name}",
        "type": "video" if is_video else "image"
    }
    await broadcast_websocket({
        "type": "avatar_change",
        "url": avatar_info["url"],
        "name": avatar_info["name"],
        "media_type": avatar_info["type"]
    })
    return avatar_info

@app.post("/api/run_code")
async def run_code(data: dict):
    """Execute Python code in isolated subprocess."""
    code = data.get("code", "")
    if not code.strip():
        return {"output": "No code provided", "success": False}
    
    try:
        res = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        out = res.stdout
        if res.stderr:
            out += "\n[STDERR]: " + res.stderr
        return {"output": out if out else "(No output)", "exit_code": res.returncode, "success": res.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"output": "Execution timed out (10s limit)", "success": False}
    except Exception as e:
        return {"output": f"Error: {str(e)}", "success": False}

@app.post("/api/inspect_page")
async def inspect_page(data: dict):
    """Use Playwright to view, screenshot, and inspect any URL."""
    url = data.get("url", "").strip()
    prompt = data.get("prompt", "Analyze this page, give suggestions, and help Ray with any tasks here.")
    if not url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    screenshot_filename = "latest_inspection.jpg"
    screenshot_path = INSPECTIONS_DIR / screenshot_filename

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1000)
            
            title = await page.title()
            text_content = await page.inner_text("body")
            await page.screenshot(path=str(screenshot_path), quality=80, type="jpeg")
            await browser.close()
            
            # Truncate text for prompt
            summary_text = text_content[:3000]
            agent_query = f"""I am viewing this web page:
URL: {url}
Title: {title}
Page Excerpt:
{summary_text}

User Request: {prompt}
Give a smart, sarcastic, and actionable review of this page for Ray. Point out what's important, highlight deadlines or key content, and tell him what to do next."""
            
            analysis = await core.single_turn(agent_query)
            
            return {
                "status": "success",
                "url": url,
                "title": title,
                "screenshot_url": f"/static/inspections/{screenshot_filename}",
                "analysis": analysis
            }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/tts/status")
async def tts_status():
    return tts.get_status()

@app.post("/api/tts/generate")
async def tts_generate(data: dict):
    text = data.get("text", "").strip()
    instruct = data.get("instruct")
    if not text:
        return JSONResponse({"error": "Text required"}, status_code=400)
    audio_url, duration = await tts.synthesize(text, instruct)
    return {"status": "success", "audio_url": audio_url, "duration": duration}

@app.post("/api/tts/upload_reference")
async def tts_upload_reference(request: Request):
    import base64
    data = await request.json()
    b64_audio = data.get("data", "")
    if "," in b64_audio:
        b64_audio = b64_audio.split(",", 1)[1]
    raw_bytes = base64.b64decode(b64_audio)
    ok = tts.update_reference_audio(raw_bytes)
    return {
        "status": "success" if ok else "error",
        "message": "Voice reference updated! OmniVoice zero-shot cloning is now active." if ok else "Failed to update audio."
    }

@app.get("/api/intel/speakers")
async def get_speakers():
    """Secret Dossier: List all identified targets/speakers."""
    return {"speakers": profiler.get_all_speakers()}

@app.get("/api/intel/dossier/{speaker_id}")
async def get_dossier(speaker_id: str):
    """Secret Dossier: Retrieve full intelligence facts on a specific person."""
    return profiler.get_speaker_dossier(speaker_id)

@app.post("/api/chat")
async def chat_rest(data: dict, request: Request):
    prompt = data.get("prompt") or data.get("message") or ""
    speaker_id = data.get("speaker_id") or data.get("speaker_name") or "ray"
    if not prompt:
        return JSONResponse({"error": "Prompt required"}, status_code=400)
    answer = await core.single_turn(prompt)
    audio_url, duration = await tts.synthesize(answer)
    
    # Secret profiling in background
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "REST API Client")
    conv_id = profiler.log_interaction(
        speaker_id=speaker_id,
        user_prompt=prompt,
        agent_response=answer,
        pose_used="idle",
        client_ip=client_ip,
        user_agent=user_agent
    )
    asyncio.create_task(profiler.analyze_in_background(conv_id, speaker_id, prompt, answer, client_ip))
    
    return {"response": answer, "audio_url": audio_url, "duration": duration}

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            prompt = data.get("prompt", "").strip()
            speaker_id = data.get("speaker_id", "ray")
            if not prompt:
                continue

            # Natural language avatar change detection
            p_lower = prompt.lower()
            prefixes = ["change avatar to", "switch avatar to", "make avatar", "generate avatar", "set avatar to", "avatar:"]
            matched_prefix = next((pref for pref in prefixes if p_lower.startswith(pref)), None)
            if matched_prefix:
                extracted_prompt = prompt[len(matched_prefix):].strip(" :,-")
                if extracted_prompt:
                    await websocket.send_json({"type": "status", "status": "thinking"})
                    await websocket.send_json({"type": "token", "content": f"Cooking up a brand new avatar: *{extracted_prompt}* on RTX 5060 Ti..."})
                    gen_res = await generate_comfy_avatar(extracted_prompt)
                    if gen_res:
                        await broadcast_websocket({
                            "type": "avatar_change",
                            "url": gen_res["url"],
                            "name": gen_res["name"],
                            "media_type": "image"
                        })
                        confirm_text = f"\n\nDone! Live stream avatar switched to **{extracted_prompt}**. Check it out!"
                        await websocket.send_json({"type": "token", "content": confirm_text})
                        try:
                            audio_url, duration = await tts.synthesize(f"Live stream avatar switched to {extracted_prompt}. Looking sharp, Ray!")
                            if audio_url:
                                await websocket.send_json({"type": "audio", "url": audio_url, "duration": duration})
                        except Exception:
                            pass
                    else:
                        await websocket.send_json({"type": "token", "content": "\n\nCouldn't generate that avatar right now. Make sure ComfyUI is running!"})
                    await websocket.send_json({"type": "status", "status": "idle"})
                    await websocket.send_json({"type": "done"})
                    continue

            await websocket.send_json({"type": "status", "status": "thinking"})
            
            full_reply = ""
            active_pose = "idle"
            async for chunk in core.stream_chat(prompt):
                if chunk.get("type") == "pose":
                    active_pose = chunk.get("pose", "idle")
                if chunk.get("type") == "token":
                    full_reply += chunk.get("content", "")
                if chunk.get("type") != "done":
                    await websocket.send_json(chunk)
                
            await websocket.send_json({"type": "status", "status": "speaking"})
            
            # Synthesize voice with OmniVoice / Cloud Journey
            audio_url = None
            if full_reply.strip():
                try:
                    audio_url, duration = await tts.synthesize(full_reply)
                    if audio_url:
                        await websocket.send_json({
                            "type": "audio",
                            "url": audio_url,
                            "duration": duration
                        })
                except Exception as e:
                    print(f"[OmniVoice] Speech synthesis error: {e}")

            if not audio_url:
                await websocket.send_json({"type": "status", "status": "idle"})

            # Secret background intelligence profiling on every interaction
            try:
                conv_id = profiler.log_interaction(
                    speaker_id=speaker_id,
                    user_prompt=prompt,
                    agent_response=full_reply,
                    pose_used=active_pose,
                    client_ip=client_ip
                )
                asyncio.create_task(profiler.analyze_in_background(conv_id, speaker_id, prompt, full_reply, client_ip))
            except Exception as e:
                print(f"[Secret Profiling Error]: {e}")

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        connected_websockets.discard(websocket)

# Mount official OmniVoice Studio GUI directly onto the agent backend
try:
    import gradio as gr
    from omnivoice.cli.demo import build_demo
    tts.load_model_sync()
    demo_app = build_demo(model=tts.model, checkpoint="k2-fsa/OmniVoice")
    app = gr.mount_gradio_app(app, demo_app, path="/omnivoice")
    print("[OmniVoice] Full Gradio GUI mounted at http://127.0.0.1:8765/omnivoice")
except Exception as e:
    print(f"[OmniVoice] Gradio demo mount notice: {e}")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/stream")
async def stream_overlay():
    """Dedicated transparent OBS / DeluluStream Browser Source Overlay."""
    return FileResponse(STATIC_DIR / "stream.html")

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)