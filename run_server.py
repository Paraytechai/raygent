import os
import sys
import traceback
import uvicorn

if __name__ == "__main__":
    print("[Raygent] Starting Raygent server on port 8765 (All Interfaces / Tailscale 0.0.0.0) ...")
    try:
        uvicorn.run("backend.server:app", host="0.0.0.0", port=8765, log_level="info", access_log=True)
    except Exception as e:
        print(f"[Raygent Fatal Error]: {e}")
        traceback.print_exc()
