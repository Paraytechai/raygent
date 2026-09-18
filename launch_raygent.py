import os
import sys
import time
import subprocess
import webbrowser
import uvicorn
from multiprocessing import Process

def start_server():
    from backend.server import app
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")

def main():
    print("==================================================")
    print("       STARTING RAYGENT PERSONAL AVATAR AGENT      ")
    print("   Google Antigravity SDK | Sarcastic Persona      ")
    print("   Global Hotkeys: Win + Shift + R | Alt + Space   ")
    print("==================================================")

    # Launch server in background via subprocess
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # Wait 2 seconds for server to bind
    time.sleep(2)

    # Launch Desktop HUD or open browser
    try:
        from desktop_hud import run_hud
        print("Launching Raygent PySide6 Desktop HUD...")
        run_hud(port=8765)
    except Exception as e:
        print("Falling back to web browser HUD:", e)
        webbrowser.open("http://127.0.0.1:8765")
        server_process.wait()
    finally:
        try:
            server_process.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()