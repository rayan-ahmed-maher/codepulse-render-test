"""
Local Deployment Route — Production-grade localhost runner
============================================================
- Auto-increments ports (5000, 5001, 5002...)
- Kills any existing process on the allocated port before starting
- Kills previous deployment for same project before redeploying
- NEVER uses port 3000 or 8000
- 3-layer health verification: process alive → port listening → HTTP responds
"""
import os
import subprocess
import signal
import socket
import asyncio
import logging
import json
import time
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/deploy", tags=["Local Deploy"])
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  GLOBAL STATE
# ═══════════════════════════════════════════════════════════════

# Track running local processes: pid → {process, port, project_path, ...}
_local_processes: dict = {}

# Port registry: tracks the next port to assign. Guarantees uniqueness.
_next_port = 5000

# Ports that MUST NEVER be used
BLOCKED_PORTS = {3000, 8000}


# ═══════════════════════════════════════════════════════════════
#  PORT MANAGEMENT
# ═══════════════════════════════════════════════════════════════
def _is_port_free(port: int) -> bool:
    """Check if a port is free using socket bind test."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def _kill_port(port: int):
    """Kill whatever process is using this port (Windows + Unix). Retries until port is free."""
    killed_pids = set()
    try:
        if os.name == "nt":
            # Find ALL PIDs using this port via netstat
            result = subprocess.run(
                f'netstat -aon | findstr ":{port}"',
                shell=True, capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    # Match exact port in local address (second column like 0.0.0.0:5000 or 127.0.0.1:5000)
                    local_addr = parts[1]
                    if local_addr.endswith(f":{port}"):
                        pid = parts[-1].strip()
                        if pid.isdigit() and int(pid) > 0 and pid not in killed_pids:
                            killed_pids.add(pid)
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", pid],
                                capture_output=True, timeout=5,
                            )
                            logger.info(f"[PORT] Killed PID {pid} on port {port}")
        else:
            result = subprocess.run(
                f"lsof -ti:{port}", shell=True,
                capture_output=True, text=True, timeout=5,
            )
            for pid in result.stdout.strip().split("\n"):
                pid = pid.strip()
                if pid.isdigit():
                    os.kill(int(pid), signal.SIGTERM)
                    killed_pids.add(pid)
                    logger.info(f"[PORT] Killed PID {pid} on port {port}")

        if killed_pids:
            time.sleep(0.5)  # Give OS time to release the port
    except Exception as e:
        logger.debug(f"[PORT] Kill on port {port} error: {e}")


def _allocate_port() -> int:
    """Allocate the next unique port. Skips blocked and busy ports.
    Auto-kills processes on ports if needed."""
    global _next_port

    # Collect ports already in use by our tracked processes
    used_ports = {e["port"] for e in _local_processes.values()}

    attempts = 0
    while attempts < 50:
        port = _next_port
        _next_port += 1
        attempts += 1

        # Skip blocked ports
        if port in BLOCKED_PORTS:
            continue

        # Skip ports we're already using
        if port in used_ports:
            continue

        # If port is free, use it
        if _is_port_free(port):
            logger.info(f"[PORT] Allocated free port: {port}")
            return port

        # Port is busy but not ours — kill whatever is on it
        logger.info(f"[PORT] Port {port} is busy, killing existing process...")
        _kill_port(port)
        time.sleep(0.5)

        if _is_port_free(port):
            logger.info(f"[PORT] Port {port} freed and allocated")
            return port

    # Extreme fallback: ask OS
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        except Exception:
            return -1 # PORT_IN_USE indicator
    logger.info(f"[PORT] OS fallback port: {port}")
    return port


def _is_port_listening(port: int) -> bool:
    """TCP connect test."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except (ConnectionRefusedError, OSError, TimeoutError):
            return False


# ═══════════════════════════════════════════════════════════════
#  FRAMEWORK DETECTION
# ═══════════════════════════════════════════════════════════════
def _detect_local_command(project_path: str) -> dict:
    """Detect framework and return run command with {port} placeholder."""
    p = Path(project_path)

    pkg_json = None
    if (p / "package.json").exists():
        try:
            pkg_json = json.loads((p / "package.json").read_text(encoding="utf-8"))
        except Exception:
            pass

    has_req = (p / "requirements.txt").exists()

    # Next.js
    if any((p / f).exists() for f in ["next.config.js", "next.config.mjs", "next.config.ts"]):
        return {"framework": "nextjs", "install": "npm install",
                "command": "npx next dev -p {port}", "type": "frontend"}

    # Vite
    if any((p / f).exists() for f in ["vite.config.js", "vite.config.ts"]):
        return {"framework": "vite", "install": "npm install",
                "command": "npx vite --port {port} --host", "type": "frontend"}

    # Angular
    if (p / "angular.json").exists():
        return {"framework": "angular", "install": "npm install",
                "command": "npx ng serve --port {port}", "type": "frontend"}

    # React CRA
    if pkg_json and "react-scripts" in pkg_json.get("dependencies", {}):
        if os.name == "nt":
            return {"framework": "react", "install": "npm install",
                    "command": "set PORT={port}&& npx react-scripts start", "type": "frontend"}
        else:
            return {"framework": "react", "install": "npm install",
                    "command": "PORT={port} npx react-scripts start", "type": "frontend"}

    # Vue CLI
    if (p / "vue.config.js").exists() or (pkg_json and "vue" in pkg_json.get("dependencies", {})):
        return {"framework": "vue", "install": "npm install",
                "command": "npx vue-cli-service serve --port {port}", "type": "frontend"}

    # Python: FastAPI
    if has_req:
        req_text = (p / "requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
        if "fastapi" in req_text or "uvicorn" in req_text:
            return {"framework": "fastapi", "install": "pip install -r requirements.txt",
                    "command": "python -m uvicorn main:app --host 0.0.0.0 --port {port}",
                    "type": "backend"}
        if "flask" in req_text:
            return {"framework": "flask", "install": "pip install -r requirements.txt",
                    "command": "python -m flask run --host 0.0.0.0 --port {port}",
                    "type": "backend"}
        if "django" in req_text:
            return {"framework": "django", "install": "pip install -r requirements.txt",
                    "command": "python manage.py runserver 0.0.0.0:{port}",
                    "type": "backend"}
        return {"framework": "python", "install": "pip install -r requirements.txt",
                "command": "python main.py", "type": "backend"}

    # Node.js generic
    if pkg_json:
        scripts = pkg_json.get("scripts", {})
        if "dev" in scripts:
            if os.name == "nt":
                return {"framework": "nodejs", "install": "npm install",
                        "command": "set PORT={port}&& npm run dev", "type": "backend"}
            else:
                return {"framework": "nodejs", "install": "npm install",
                        "command": "PORT={port} npm run dev", "type": "backend"}
        if "start" in scripts:
            if os.name == "nt":
                return {"framework": "nodejs", "install": "npm install",
                        "command": "set PORT={port}&& npm start", "type": "backend"}
            else:
                return {"framework": "nodejs", "install": "npm install",
                        "command": "PORT={port} npm start", "type": "backend"}
        return {"framework": "nodejs", "install": "npm install",
                "command": "node index.js", "type": "backend"}

    # Static HTML
    if any((p / f).exists() for f in ["index.html", "index.htm"]):
        abs_path = str(p.resolve()).replace("\\", "/")
        return {"framework": "static", "install": None,
                "command": f'npx serve "{abs_path}" -l {{port}}', "type": "static"}

    return {"framework": "unknown", "install": None, "command": None, "type": "unknown"}


# ═══════════════════════════════════════════════════════════════
#  HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════
async def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    """Wait until something is listening on the port."""
    start = time.time()
    while time.time() - start < timeout:
        if _is_port_listening(port):
            logger.info(f"[HEALTH] Port {port} listening (took {time.time()-start:.1f}s)")
            return True
        await asyncio.sleep(0.5)
    logger.warning(f"[HEALTH] Port {port} never started listening within {timeout}s")
    return False


async def _check_http(port: int, max_retries: int = 5, delay: float = 2.0) -> dict:
    """HTTP GET to verify the server actually responds."""
    import httpx
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"http://localhost:{port}")
                logger.info(f"[HEALTH] HTTP localhost:{port} → {resp.status_code} (attempt {attempt+1})")
                return {"ok": True, "status_code": resp.status_code}
        except Exception:
            pass
        await asyncio.sleep(delay)
    return {"ok": False, "status_code": 0}


def _is_process_alive(proc: subprocess.Popen) -> bool:
    return proc.poll() is None


# ═══════════════════════════════════════════════════════════════
#  PROCESS MANAGEMENT
# ═══════════════════════════════════════════════════════════════
def _kill_process(pid: int):
    """Kill a process tree (Windows-safe)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=10)
        else:
            os.kill(pid, signal.SIGTERM)
        logger.info(f"[CLEANUP] Killed PID {pid}")
    except Exception as e:
        logger.debug(f"[CLEANUP] Kill PID {pid} error: {e}")


def _cleanup_dead_processes():
    """Remove dead processes from tracking."""
    dead = [pid for pid, entry in _local_processes.items()
            if "process" in entry and not _is_process_alive(entry["process"])]
    for pid in dead:
        _local_processes.pop(pid, None)
        logger.info(f"[CLEANUP] Removed dead PID {pid}")


def _stop_previous_for_project(project_path: str):
    """Kill any existing deployment for the same project path."""
    to_remove = []
    for pid, entry in _local_processes.items():
        if entry["project_path"] == project_path:
            _kill_process(pid)
            _kill_port(entry["port"])
            to_remove.append(pid)
            logger.info(f"[CLEANUP] Stopped previous deploy for {project_path} (PID {pid}, port {entry['port']})")
    for pid in to_remove:
        _local_processes.pop(pid, None)


# ═══════════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════════
class LocalDeployRequest(BaseModel):
    project_path: str
    project_name: Optional[str] = "local-project"


class LocalStopRequest(BaseModel):
    pid: int


@router.post("/local")
async def deploy_local(req: LocalDeployRequest):
    """Start a project locally with guaranteed unique port."""
    t_start = time.time()
    project_path = req.project_path
    logger.info(f"[LOCAL] === Deploy request: {project_path} ===")

    # Validate
    if not project_path or not project_path.strip():
        return {"status": "ERROR", "error": "project_path is empty"}
    if not os.path.isdir(project_path):
        return {"status": "ERROR", "error": f"Directory not found: {project_path}"}

    # Clean up dead processes
    _cleanup_dead_processes()

    # Kill any previous deploy for the same project (prevents stale content)
    _stop_previous_for_project(project_path)

    # Detect framework
    detection = _detect_local_command(project_path)
    logger.info(f"[LOCAL] Framework: {detection['framework']}, Type: {detection.get('type')}")

    if not detection["command"]:
        return {
            "status": "ERROR",
            "error": "Cannot determine how to run this project. No package.json, requirements.txt, or index.html found.",
        }

    # Allocate unique port (auto-kills anything already on it)
    port = _allocate_port()
    if port == -1:
        return {"status": "ERROR", "error": "PORT_IN_USE", "message": "Failed to allocate a free port"}
    
    # Track the new process BEFORE starting to ensure isolation
    _local_processes[0] = {"project_path": project_path, "port": port}
    
    command = detection["command"].replace("{port}", str(port))
    install_cmd = detection["install"]
    logger.info(f"[LOCAL] Port: {port} | Command: {command}")

    # Install dependencies
    if install_cmd:
        logger.info(f"[LOCAL] Installing: {install_cmd}")
        try:
            install_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    install_cmd, shell=True, cwd=project_path,
                    capture_output=True, text=True, timeout=120,
                )
            )
            if install_result.returncode != 0:
                err_msg = install_result.stderr[:500] if install_result.stderr else "Unknown install error"
                logger.error(f"[LOCAL] Install failed: {err_msg}")
                return {
                    "status": "ERROR",
                    "error": "BUILD_FAILED",
                    "message": f"Install failed (exit {install_result.returncode}): {err_msg}",
                    "install_command": install_cmd,
                }
            logger.info("[LOCAL] Install OK")
        except subprocess.TimeoutExpired:
            return {"status": "ERROR", "error": "Install timed out after 120s"}
        except Exception as e:
            return {"status": "ERROR", "error": f"Install error: {str(e)}"}

    # Start server
    logger.info(f"[LOCAL] Starting: {command}")
    try:
        proc = subprocess.Popen(
            command, shell=True, cwd=project_path,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
    except Exception as e:
        return {"status": "ERROR", "error": "LOCAL_DEPLOY_FAILED", "message": f"Failed to start: {str(e)}"}

    logger.info(f"[LOCAL] PID: {proc.pid}")
    await asyncio.sleep(2)

    # CHECK 1: Process alive?
    if not _is_process_alive(proc):
        stderr = ""
        try:
            stderr = proc.stderr.read().decode(errors="ignore")[:500]
        except Exception:
            pass
        logger.error(f"[LOCAL] Process died (exit {proc.returncode}): {stderr}")
        return {
            "status": "ERROR",
            "error": f"Server exited immediately (exit code {proc.returncode}). stderr: {stderr}",
            "command": command,
        }

    # CHECK 2: Port listening?
    port_ok = await _wait_for_port(port, timeout=20.0)
    if not port_ok:
        if not _is_process_alive(proc):
            stderr = ""
            try:
                stderr = proc.stderr.read().decode(errors="ignore")[:500]
            except Exception:
                pass
            _kill_process(proc.pid)
            return {
                "status": "ERROR",
                "error": f"Process crashed before port {port} opened. stderr: {stderr}",
                "command": command,
            }
        logger.warning(f"[LOCAL] Port {port} not detected listening, but process alive — trying HTTP...")

    # CHECK 3: HTTP responds?
    http_result = await _check_http(port, max_retries=5, delay=2.0)

    # Track the process regardless of HTTP result (process is running)
    _local_processes[proc.pid] = {
        "process": proc, "port": port,
        "project_path": project_path, "command": command,
        "started_at": time.time(),
    }
    elapsed = time.time() - t_start

    if http_result["ok"]:
        logger.info(f"[LOCAL] === SUCCESS: localhost:{port} verified (PID {proc.pid}, {elapsed:.1f}s) ===")
        return {
            "status": "RUNNING",
            "url": f"http://localhost:{port}",
            "pid": proc.pid,
            "port": port,
            "framework": detection["framework"],
            "command": command,
            "install_command": install_cmd,
            "health_verified": True,
            "http_status": http_result["status_code"],
            "elapsed_seconds": round(elapsed, 1),
        }
    else:
        if _is_process_alive(proc):
            logger.warning(f"[LOCAL] HTTP failed but PID {proc.pid} alive — returning with warning")
            return {
                "status": "RUNNING",
                "url": f"http://localhost:{port}",
                "pid": proc.pid,
                "port": port,
                "framework": detection["framework"],
                "command": command,
                "install_command": install_cmd,
                "health_verified": False,
                "warning": f"Server running (PID {proc.pid}) but HTTP check didn't respond yet. Try the URL manually — it may still be compiling.",
                "elapsed_seconds": round(elapsed, 1),
            }
        else:
            stderr = ""
            try:
                stderr = proc.stderr.read().decode(errors="ignore")[:500]
            except Exception:
                pass
            _local_processes.pop(proc.pid, None)
            _kill_process(proc.pid)
            return {
                "status": "ERROR",
                "error": f"Server crashed during startup. stderr: {stderr}",
                "command": command,
            }


@router.post("/local/stop")
async def stop_local(req: LocalStopRequest):
    """Stop a locally running process by PID."""
    entry = _local_processes.pop(req.pid, None)
    if entry:
        _kill_process(entry["process"].pid)
        _kill_port(entry["port"])
        logger.info(f"[LOCAL] Stopped PID {req.pid} on port {entry['port']}")
        return {"status": "STOPPED", "pid": req.pid, "port": entry["port"]}

    _kill_process(req.pid)
    return {"status": "STOPPED", "pid": req.pid}


@router.post("/local/stop-all")
async def stop_all_local():
    """Stop ALL locally running processes."""
    stopped = []
    for pid, entry in list(_local_processes.items()):
        _kill_process(entry["process"].pid)
        _kill_port(entry["port"])
        stopped.append({"pid": pid, "port": entry["port"]})
    _local_processes.clear()
    logger.info(f"[LOCAL] Stopped all: {len(stopped)} processes")
    return {"status": "ALL_STOPPED", "count": len(stopped), "stopped": stopped}


@router.get("/local/list")
async def list_local():
    """List running local processes with live status."""
    _cleanup_dead_processes()
    result = []
    for pid, entry in _local_processes.items():
        proc = entry["process"]
        port = entry["port"]
        alive = _is_process_alive(proc)
        listening = _is_port_listening(port) if alive else False
        result.append({
            "pid": pid,
            "port": port,
            "url": f"http://localhost:{port}",
            "project_path": entry["project_path"],
            "command": entry["command"],
            "alive": alive,
            "port_listening": listening,
            "uptime_seconds": round(time.time() - entry.get("started_at", time.time())),
        })
    return result
