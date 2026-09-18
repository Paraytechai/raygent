"""
LivePortrait Real-Time Webcam Avatar Runner (Option 1)
Syncs the active avatar from Raygent into ComfyUI and launches the real-time webcam workflow.
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.parse
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
AVATARS_DIR = BASE_DIR / "static" / "avatars"
COMFY_INPUT_DIR = Path("D:/Comfy-Desktop/ComfyUI-Shared/input")
COMFY_EXAMPLES_DIR = Path("D:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/custom_nodes/ComfyUI-LivePortraitKJ/examples")

def get_comfy_port():
    for port in [8189, 8188]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=0.8) as r:
                if r.status == 200:
                    return port
        except Exception:
            pass
    return 8189

def get_latest_avatar():
    if not AVATARS_DIR.exists():
        return None
    files = [f for f in AVATARS_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]]
    if not files:
        return None
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]

def main():
    print("==================================================================")
    print("       LIVEPORTRAIT REAL-TIME WEBCAM AVATAR DRIVER (OPTION 1)     ")
    print("   Mirror your face, eyes, and mouth to ANY avatar at 30-60 FPS   ")
    print("==================================================================")

    port = get_comfy_port()
    print(f"[1/4] Checking ComfyUI Server on port {port}...")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=1.5) as r:
            stats = json.loads(r.read().decode())
            gpu_name = stats.get("devices", [{}])[0].get("name", "GPU")
            print(f"      Connected! {gpu_name}")
    except Exception as e:
        print(f"      Warning: Could not contact ComfyUI on {port}: {e}")

    # Find active avatar
    latest = get_latest_avatar()
    if latest:
        print(f"[2/4] Found active avatar: {latest.name}")
        COMFY_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        target_img = COMFY_INPUT_DIR / "active_webcam_avatar.png"
        shutil.copy2(str(latest), str(target_img))
        print(f"      Copied to: {target_img}")
    else:
        print("[2/4] Using default avatar image.")

    # Prepare Real-time workflow JSON
    src_workflow = COMFY_EXAMPLES_DIR / "liveportrait_realtime_example_01.json"
    if src_workflow.exists():
        print(f"[3/4] Preparing LivePortrait Real-Time Workflow...")
        with open(src_workflow, "r", encoding="utf-8") as f:
            wf_data = json.load(f)

        for node in wf_data.get("nodes", []):
            if node.get("type") == "LoadImage":
                node["widgets_values"] = ["active_webcam_avatar.png", "image"]
                print("      Updated LoadImage node -> active_webcam_avatar.png")

        dest_wf = COMFY_INPUT_DIR / "liveportrait_realtime_webcam.json"
        with open(dest_wf, "w", encoding="utf-8") as f:
            json.dump(wf_data, f, indent=2)
        print(f"      Saved customized workflow to: {dest_wf}")
    else:
        print(f"[3/4] Workflow example file not found at {src_workflow}")

    print(f"[4/4] Opening ComfyUI Studio at http://127.0.0.1:{port}...")
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)

    print("\n------------------------------------------------------------------")
    print("HOW TO RUN REAL-TIME WEBCAM DRIVING IN COMFYUI:")
    print(" 1. In ComfyUI, drag & drop:")
    print("    D:\\Comfy-Desktop\\ComfyUI-Shared\\input\\liveportrait_realtime_webcam.json")
    print("    onto the workspace canvas.")
    print(" 2. In the bottom-right menu, check 'Extra options' -> check 'Auto Queue'.")
    print(" 3. Click 'Queue Prompt'.")
    print(" 4. Look into your webcam - your head, blinking, and mouth will")
    print("    drive the avatar in real-time at 30-60 FPS!")
    print(" 5. In OBS Studio, add a 'Window Capture' source selecting ComfyUI.")
    print("------------------------------------------------------------------\n")

if __name__ == "__main__":
    main()
