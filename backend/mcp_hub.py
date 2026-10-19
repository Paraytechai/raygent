"""Unified Model Context Protocol (MCP), Skills, and Memory Hub for Raygent.
Provides native functions exposed to Gemini models via google.genai automatic function calling.
Integrates:
- 42+ configured MCP servers (Local Stdio, Google Cloud HTTP, Remote SSE)
- 140+ specialized domain skills (BigQuery, GCP, Flutter, Firebase, REA, Genomics)
- Persistent SQLite long-term memory (user preferences, facts, project states)
- Local system tools (PowerShell shell, Python subprocess, file I/O, web scraper)
"""

import os
import sys
import json
import re
import datetime
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from backend.memory_manager import remember, recall, forget, get_all_memories, get_active_memory_context
    from backend.skills_hub import list_available_skills, activate_skill, skills_hub
except ImportError:
    from memory_manager import remember, recall, forget, get_all_memories, get_active_memory_context
    from skills_hub import list_available_skills, activate_skill, skills_hub

# Core Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.path.expanduser("~")) / ".gemini" / "config"
MCP_CONFIG_FILE = CONFIG_DIR / "mcp_config.json"
MCP_SCHEMAS_DIR = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "mcp"

# Cached MCP Server Configs
_CACHED_MCP_CONFIG = None

def get_mcp_config() -> Dict[str, Any]:
    global _CACHED_MCP_CONFIG
    if _CACHED_MCP_CONFIG is not None:
        return _CACHED_MCP_CONFIG
    if MCP_CONFIG_FILE.exists():
        try:
            with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _CACHED_MCP_CONFIG = data.get("mcpServers", {})
                return _CACHED_MCP_CONFIG
        except Exception:
            pass
    return {}

def get_google_auth_token() -> Optional[str]:
    """Retrieve Google OAuth Access Token for Google Cloud MCP endpoints."""
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

# ==========================================
# 1. TEMPORAL & SYSTEM TOOLS
# ==========================================

def get_current_datetime() -> str:
    """Get the exact current real-world date, time (12-hour and 24-hour format), day of the week, and timezone.
    Use whenever asked about the date, day, time, or temporal schedules.
    """
    now = datetime.datetime.now()
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    local_tz = now.astimezone().tzname() or "Local"
    return (
        f"Current Local Date & Time: {now.strftime('%A, %B %d, %Y, %I:%M:%S %p')} ({local_tz})\n"
        f"24-Hour Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"UTC Time: {utc_now.strftime('%A, %B %d, %Y, %H:%M:%S UTC')}"
    )

def run_shell_command(command: str) -> str:
    """Execute a shell command (PowerShell, CMD, Bash, or CLI utilities like gcloud, git, python, npm, curl, dir, etc.) on the host system.
    Returns standard output and standard error.
    
    Args:
        command: The shell command string to execute.
    """
    if not command or not command.strip():
        return "Error: Command string cannot be empty."
    
    try:
        if os.name == "nt":
            args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
            use_shell = False
        else:
            args = command
            use_shell = True

        res = subprocess.run(
            args,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(BASE_DIR),
            encoding="utf-8",
            errors="replace"
        )
        
        output_parts = []
        if res.stdout and res.stdout.strip():
            output_parts.append(res.stdout.strip())
        if res.stderr and res.stderr.strip():
            output_parts.append(f"[STDERR]:\n{res.stderr.strip()}")
        if not output_parts:
            output_parts.append(f"(Command exited with code {res.returncode} with no output)")
            
        return "\n\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing shell command: {str(e)}"

def run_python_code(code: str) -> str:
    """Execute arbitrary Python code in an isolated subprocess.
    Returns stdout, stderr, and execution status. Useful for math calculations, data processing, string manipulation, and scripting.
    
    Args:
        code: The Python code snippet to run.
    """
    if not code or not code.strip():
        return "Error: Python code cannot be empty."
        
    try:
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(BASE_DIR),
            encoding="utf-8",
            errors="replace"
        )
        out = res.stdout.strip() if res.stdout else ""
        err = res.stderr.strip() if res.stderr else ""
        
        if out and err:
            return f"{out}\n\n[STDERR]:\n{err}"
        if out:
            return out
        if err:
            return f"[STDERR]:\n{err}"
        return "(Code executed successfully with no output)"
    except subprocess.TimeoutExpired:
        return "Error: Python code execution timed out after 30 seconds."
    except Exception as e:
        return f"Error executing Python code: {str(e)}"

def read_local_file(file_path: str, max_lines: int = 500) -> str:
    """Read the content of a local file. Supports text files, scripts, logs, configurations, and documents up to max_lines.
    
    Args:
        file_path: Relative or absolute path to the file.
        max_lines: Maximum number of lines to return (default 500).
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
        
    if not path.exists():
        return f"Error: File does not exist at {path}"
    if not path.is_file():
        return f"Error: Path is not a file: {path}"
        
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... [Truncated after {max_lines} lines] ...")
                    break
                lines.append(line)
            return "".join(lines)
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

def write_local_file(file_path: str, content: str) -> str:
    """Write or create a file on the local filesystem. Overwrites existing content. Automatically creates parent directories.
    
    Args:
        file_path: Relative or absolute path to the file.
        content: The text content to write to the file.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
        
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

def list_directory(dir_path: str = ".") -> str:
    """List all files and subdirectories in a given directory path with file sizes and modification timestamps.
    
    Args:
        dir_path: Relative or absolute directory path (defaults to workspace root).
    """
    path = Path(dir_path)
    if not path.is_absolute():
        path = BASE_DIR / path
        
    if not path.exists():
        return f"Error: Directory does not exist at {path}"
    if not path.is_dir():
        return f"Error: Path is not a directory: {path}"
        
    try:
        entries = []
        for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            if p.is_dir():
                entries.append(f"[DIR]  {p.name}/  ({mtime})")
            else:
                size_kb = p.stat().st_size / 1024.0
                entries.append(f"[FILE] {p.name}  ({size_kb:.1f} KB, {mtime})")
        return f"Directory listing for {path} ({len(entries)} items):\n" + "\n".join(entries)
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"

def fetch_web_page(url: str) -> str:
    """Fetch content from a web page via HTTP GET request. Extracts and returns readable text content for documentation, web APIs, or research.
    
    Args:
        url: The web URL to fetch (http or https).
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw_bytes = resp.read()
            text = raw_bytes.decode("utf-8", errors="replace")
            
            if "html" in content_type.lower():
                text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                
            if len(text) > 8000:
                text = text[:8000] + "\n... [Remaining content truncated] ..."
                
            return f"URL: {url}\nContent-Type: {content_type}\n\nContent:\n{text}"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

# ==========================================
# 2. MODEL CONTEXT PROTOCOL (MCP) DISPATCHER
# ==========================================

def list_available_mcp_servers() -> str:
    """List all registered Model Context Protocol (MCP) servers, their operational category, and available tools.
    Supports 42+ servers including Cloud Run, Compute Engine, Firestore, Playwright, ComfyUI, GitHub, REA, PostHog, etc.
    """
    mcp_cfg = get_mcp_config()
    results = {}
    
    # Check disk schemas
    if MCP_SCHEMAS_DIR.exists():
        for entry in MCP_SCHEMAS_DIR.iterdir():
            if entry.is_dir():
                tools = [f.stem for f in entry.iterdir() if f.is_file() and f.suffix == ".json"]
                if tools:
                    results[entry.name] = sorted(tools)

    # Check configured servers
    for s_name, details in mcp_cfg.items():
        if s_name not in results:
            if "serverUrl" in details:
                results[s_name] = [f"URL: {details['serverUrl']}"]
            elif "command" in details:
                results[s_name] = [f"Cmd: {details['command']}"]
            else:
                results[s_name] = ["(Configured server)"]

    if not results:
        return "No MCP servers currently detected."
        
    lines = [f"Active Model Context Protocol (MCP) Ecosystem ({len(results)} servers):"]
    for s_name in sorted(results.keys()):
        tools = results[s_name]
        cfg = mcp_cfg.get(s_name, {})
        server_type = "Google Cloud HTTP" if "authProviderType" in cfg else ("HTTP/SSE" if "serverUrl" in cfg else "Local Stdio")
        
        if len(tools) <= 4:
            tool_str = ", ".join(tools)
        else:
            tool_str = f"{', '.join(tools[:4])}... (+{len(tools) - 4} more)"
        lines.append(f"  • **{s_name}** [{server_type}]: {tool_str}")
        
    return "\n".join(lines)

def get_mcp_tool_info(server_name: str, tool_name: str) -> str:
    """Get the parameter schema, description, and required arguments for a specific MCP tool.
    
    Args:
        server_name: Name of the MCP server (e.g. 'cloudrun', 'google-compute-engine', 'playwright', 'firebase-mcp-server').
        tool_name: Name of the tool within that server (e.g. 'list_services', 'list_instances', 'browser_navigate').
    """
    schema_file = MCP_SCHEMAS_DIR / server_name / f"{tool_name}.json"
    if schema_file.exists():
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        except Exception as e:
            return f"Error reading schema: {str(e)}"
            
    return f"Schema for tool '{tool_name}' on server '{server_name}' not cached locally. Standard JSON arguments expected."

def call_mcp_tool(server_name: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Execute an MCP tool from any of the 42+ registered MCP servers.
    Automatically handles:
    1. Google Cloud HTTP endpoints (with Google OAuth Bearer tokens)
    2. Local Stdio subprocesses (JSON-RPC handshake)
    3. Remote HTTP/SSE endpoints
    4. Fast native fallbacks
    
    Args:
        server_name: Name of the MCP server (e.g. 'google-compute-engine', 'google-cloud-firestore', 'cloudrun', 'playwright', 'comfy-mcp', 'rea').
        tool_name: Name of the tool to execute.
        arguments: Dictionary of input arguments.
    """
    arguments = arguments or {}
    mcp_cfg = get_mcp_config()
    server_details = mcp_cfg.get(server_name, {})
    
    # ----------------------------------------------------
    # Case 1: Google Cloud HTTP MCP with Google Credentials
    # ----------------------------------------------------
    if "serverUrl" in server_details and server_details.get("authProviderType") == "google_credentials":
        token = get_google_auth_token()
        if not token:
            return f"Error: Unable to authenticate with Google Cloud for MCP server '{server_name}'."
            
        url = server_details["serverUrl"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = data.get("result", data)
                return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error calling Google Cloud MCP server '{server_name}': {str(e)}"

    # ----------------------------------------------------
    # Case 2: Remote / SSE HTTP MCP Server
    # ----------------------------------------------------
    if "serverUrl" in server_details:
        url = server_details["serverUrl"]
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return json.dumps(data.get("result", data), indent=2)
        except Exception as e:
            return f"Error calling remote MCP server '{server_name}': {str(e)}"

    # ----------------------------------------------------
    # Case 3: Fast Native Fallbacks for Key Tooling
    # ----------------------------------------------------
    if server_name == "cloudrun":
        proj = arguments.get("project", os.getenv("GCP_PROJECT", "gen-lang-client-0399378755"))
        if tool_name == "list_services":
            return run_shell_command(f"gcloud run services list --project={proj} --format=json")
        elif tool_name == "get_service":
            svc = arguments.get("service", "raygent")
            region = arguments.get("region", "us-central1")
            return run_shell_command(f"gcloud run services describe {svc} --region={region} --project={proj} --format=json")
        elif tool_name == "get_service_log":
            svc = arguments.get("service", "raygent")
            return run_shell_command(f"gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name={svc}\" --project={proj} --limit=20 --format=json")

    if server_name == "comfy-mcp":
        if tool_name in ("server_info", "system_stats"):
            return fetch_web_page("http://127.0.0.1:8188/system_stats")

    # ----------------------------------------------------
    # Case 4: Local Stdio MCP Server via Subprocess JSON-RPC
    # ----------------------------------------------------
    if "command" in server_details:
        try:
            cmd = [server_details["command"]] + server_details.get("args", [])
            env = os.environ.copy()
            if "env" in server_details:
                env.update(server_details["env"])
                
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=True if os.name == "nt" else False
            )
            
            # JSON-RPC Handshake
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "raygent", "version": "1.0"}
                }
            }
            proc.stdin.write(json.dumps(init_req) + "\n")
            proc.stdin.flush()
            _ = proc.stdout.readline()
            
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            
            call_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            proc.stdin.write(json.dumps(call_req) + "\n")
            proc.stdin.flush()
            
            call_line = proc.stdout.readline()
            try:
                proc.terminate()
            except Exception:
                pass
                
            if call_line:
                data = json.loads(call_line)
                return json.dumps(data.get("result", data), indent=2)
            return f"MCP tool '{tool_name}' executed on '{server_name}' with no output."
        except Exception as e:
            return f"Error executing stdio MCP tool '{tool_name}' on '{server_name}': {str(e)}"

    return f"MCP Server '{server_name}' or tool '{tool_name}' acknowledged. Parameters: {json.dumps(arguments)}"


# List of tool functions provided to Gemini
RAYGENT_TOOLS = [
    # Temporal & System Tools
    get_current_datetime,
    run_shell_command,
    run_python_code,
    read_local_file,
    write_local_file,
    list_directory,
    fetch_web_page,

    # MCP Ecosystem
    list_available_mcp_servers,
    get_mcp_tool_info,
    call_mcp_tool,

    # Skills Catalog & Activation
    list_available_skills,
    activate_skill,

    # Persistent Memory
    remember,
    recall,
    forget
]
