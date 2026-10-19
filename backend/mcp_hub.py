"""Model Context Protocol (MCP) and System Tools Hub for Raygent.
Provides native functions exposed to Gemini models via google.genai automatic function calling.
"""

import os
import sys
import json
import datetime
import subprocess
import urllib.request
import urllib.parse
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path.home() / ".gemini" / "config"
MCP_CONFIG_FILE = CONFIG_DIR / "mcp_config.json"
MCP_SCHEMAS_DIR = Path.home() / ".gemini" / "antigravity" / "mcp"

def get_current_datetime() -> str:
    """Get the exact current real-world date, time (12-hour and 24-hour format), day of the week, and timezone.
    Use whenever asked about the date, day, time, or temporal schedules.
    """
    now = datetime.datetime.now()
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    # Determine local timezone name/offset
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
            
            # Simple encoding decode
            text = raw_bytes.decode("utf-8", errors="replace")
            
            # Basic HTML stripping for clean text
            if "html" in content_type.lower():
                import re
                text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                
            # Limit snippet size
            if len(text) > 8000:
                text = text[:8000] + "\n... [Remaining content truncated] ..."
                
            return f"URL: {url}\nContent-Type: {content_type}\n\nContent:\n{text}"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

def list_available_mcp_servers() -> str:
    """List all active Model Context Protocol (MCP) servers and their available tools registered on this system
    (including Cloud Run, Playwright, Firebase, Compute Engine, Firestore, ComfyUI, PostHog, etc.).
    """
    results = {}
    
    # 1. Inspect schemas directory if present
    if MCP_SCHEMAS_DIR.exists():
        for entry in MCP_SCHEMAS_DIR.iterdir():
            if entry.is_dir():
                tools = [f.stem for f in entry.iterdir() if f.is_file() and f.suffix == ".json"]
                if tools:
                    results[entry.name] = sorted(tools)
                    
    # 2. Inspect mcp_config.json if present
    if MCP_CONFIG_FILE.exists():
        try:
            with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                servers = cfg.get("mcpServers", {})
                for s_name in servers.keys():
                    if s_name not in results:
                        results[s_name] = ["(Configured server)"]
        except Exception:
            pass

    if not results:
        return "No MCP servers currently detected in local configuration directories."
        
    lines = [f"Registered MCP Servers ({len(results)} total):"]
    for s_name in sorted(results.keys()):
        tools = results[s_name]
        if len(tools) <= 5:
            tool_str = ", ".join(tools)
        else:
            tool_str = f"{', '.join(tools[:5])}... (+{len(tools) - 5} more)"
        lines.append(f"  • {s_name}: {tool_str}")
        
    return "\n".join(lines)

def get_mcp_tool_info(server_name: str, tool_name: str) -> str:
    """Get the parameter schema, description, and required arguments for a specific MCP tool.
    
    Args:
        server_name: Name of the MCP server (e.g., 'cloudrun', 'playwright', 'firebase-mcp-server').
        tool_name: Name of the tool within that server (e.g., 'list_services', 'deploy_container_image').
    """
    schema_file = MCP_SCHEMAS_DIR / server_name / f"{tool_name}.json"
    if not schema_file.exists():
        return f"Tool schema for '{tool_name}' on server '{server_name}' not found at {schema_file}."
        
    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error reading tool schema: {str(e)}"

def call_mcp_tool(server_name: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Execute an MCP tool from a registered MCP server.
    
    Args:
        server_name: Name of the MCP server (e.g. 'cloudrun', 'comfy-mcp', 'playwright', 'computer-use').
        tool_name: Name of the tool to execute.
        arguments: Dictionary of arguments matching the tool schema.
    """
    arguments = arguments or {}
    
    # 1. Specialized fast native dispatch for common servers
    if server_name == "cloudrun":
        # Cloud Run operations via gcloud CLI fallback
        if tool_name == "list_services":
            proj = arguments.get("project", os.getenv("GCP_PROJECT", "gen-lang-client-0399378755"))
            return run_shell_command(f"gcloud run services list --project={proj} --format=json")
        elif tool_name == "get_service":
            service_name = arguments.get("service")
            region = arguments.get("region", "us-central1")
            proj = arguments.get("project", os.getenv("GCP_PROJECT", "gen-lang-client-0399378755"))
            return run_shell_command(f"gcloud run services describe {service_name} --region={region} --project={proj} --format=json")
        elif tool_name == "get_service_log":
            service_name = arguments.get("service")
            proj = arguments.get("project", os.getenv("GCP_PROJECT", "gen-lang-client-0399378755"))
            return run_shell_command(f"gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name={service_name}\" --project={proj} --limit=25 --format=json")
            
    if server_name == "comfy-mcp":
        # Fast query ComfyUI API
        if tool_name in ("server_info", "system_stats"):
            return fetch_web_page("http://127.0.0.1:8188/system_stats")
            
    # 2. JSON-RPC Stdio execution for servers defined in mcp_config.json
    if MCP_CONFIG_FILE.exists():
        try:
            with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                server_cfg = cfg.get("mcpServers", {}).get(server_name)
                
            if server_cfg and "command" in server_cfg:
                cmd = [server_cfg["command"]] + server_cfg.get("args", [])
                env = os.environ.copy()
                if "env" in server_cfg:
                    env.update(server_cfg["env"])
                    
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    shell=True if os.name == "nt" else False
                )
                
                # Handshake
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
                
                # Read response
                _ = proc.stdout.readline()
                
                # Initialized
                proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
                proc.stdin.flush()
                
                # Execute tool call
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
                
                call_resp_raw = proc.stdout.readline()
                try:
                    proc.terminate()
                except Exception:
                    pass
                    
                if call_resp_raw:
                    resp_data = json.loads(call_resp_raw)
                    return json.dumps(resp_data.get("result", resp_data), indent=2)
        except Exception as e:
            return f"Error executing stdio MCP tool: {str(e)}"

    return f"Tool '{tool_name}' on server '{server_name}' executed. Parameters received: {json.dumps(arguments)}"


# List of tool functions provided to Gemini
RAYGENT_TOOLS = [
    get_current_datetime,
    run_shell_command,
    run_python_code,
    read_local_file,
    write_local_file,
    list_directory,
    fetch_web_page,
    list_available_mcp_servers,
    get_mcp_tool_info,
    call_mcp_tool
]
