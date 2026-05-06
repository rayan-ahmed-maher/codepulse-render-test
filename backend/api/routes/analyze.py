"""
Analysis Routes — Project scanning with persistent storage
=============================================================
Handles BOTH zip uploads AND folder (multi-file) uploads.
Stores everything in backend/uploads/ and returns absolute paths.
"""
import os, re, shutil, logging, time, asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File
from services.analyzer import ProjectAnalyzer
from services.deployment import DeploymentOrchestrator
from services.ai_agent import NIMDiagnosticsAgent

router = APIRouter(prefix="/analyze", tags=["Analysis"])
orchestrator = DeploymentOrchestrator()
logger = logging.getLogger(__name__)

# Persistent upload directory — ALWAYS inside backend/uploads/
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    """Sanitize project name: lowercase, no spaces, no special chars."""
    name = name.lower().strip()
    name = re.sub(r'\.zip$', '', name)
    name = re.sub(r'[^a-z0-9\-]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name[:100] or "project"


def _run_analysis(project_path: str, safe_name: str) -> dict:
    """Shared analysis logic — used by both zip and folder upload routes."""
    analyzer = ProjectAnalyzer(project_path)
    result = analyzer.analyze()

    # ── GATE: File count check
    if result.file_count == 0:
        return {
            "valid": False, "error": "NO_FILES",
            "message": "No files detected in the upload.",
            "readiness_score": 0, "project_path": project_path,
        }

    # ── GATE: Project Signature check
    SIGNATURES = {"package.json", "index.html", "requirements.txt", "Pipfile",
                   "setup.py", "pyproject.toml", "Cargo.toml", "go.mod", "Dockerfile"}
    has_signature = any(os.path.basename(f) in SIGNATURES for f in result.detected_files)
    if not has_signature and result.framework.value == "unknown":
        return {
            "valid": False, "error": "NO_SIGNATURE",
            "message": "No Project Signature detected (package.json, index.html, etc.).",
            "readiness_score": result.readiness_score,
            "file_count": result.file_count,
            "detected_files": result.detected_files[:15],
            "project_path": project_path,
        }

    # ── Security scan
    sre = NIMDiagnosticsAgent()
    file_contents = {}
    for fp in result.detected_files[:5]:
        full = os.path.join(project_path, fp)
        if os.path.isfile(full) and os.path.getsize(full) < 50000:
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    file_contents[fp] = fh.read()
            except Exception:
                pass
    scan = sre.security_scan(file_contents)
    adjusted_score = max(0, result.readiness_score - scan.score_penalty)

    # Determine project type
    fw = result.framework.value
    BACKEND_FW = {"fastapi", "flask", "django", "python"}
    FRONTEND_FW = {"react", "nextjs", "vue", "vite", "angular"}
    has_dockerfile = any("dockerfile" in f.lower() for f in result.detected_files)

    if has_dockerfile:
        project_type = "fullstack"
    elif fw in BACKEND_FW:
        project_type = "backend"
    elif fw == "static":
        project_type = "static"
    elif fw in FRONTEND_FW:
        project_type = "frontend"
    else:
        project_type = "unknown"

    # Local run commands — ports are allocated dynamically at deploy time
    LOCAL_COMMANDS = {
        "react":   ["npm install", "npm run dev (auto-port)"],
        "nextjs":  ["npm install", "next dev -p <auto> (auto-port)"],
        "vue":     ["npm install", "npm run dev (auto-port)"],
        "vite":    ["npm install", "npx vite --port <auto>"],
        "angular": ["npm install", "ng serve --port <auto>"],
        "nodejs":  ["npm install", "npm start (auto-port)"],
        "fastapi": ["pip install -r requirements.txt", "uvicorn main:app --port <auto>"],
        "flask":   ["pip install -r requirements.txt", "python app.py"],
        "django":  ["pip install -r requirements.txt", "manage.py runserver 0.0.0.0:<auto>"],
        "python":  ["pip install -r requirements.txt", "python main.py"],
        "static":  [f'npx serve "{project_path}" -l <auto-port>'],
    }
    local_commands = LOCAL_COMMANDS.get(fw, [])

    # Platform recommendations
    recs = orchestrator.recommend(fw)
    costs = {}
    for r in recs:
        c = orchestrator.get_costs(r.platform)
        if c:
            costs[r.platform] = {"free": c.free_tier, "pro": c.pro_tier, "price": c.pro_price}

    return {
        "valid": True,
        "framework": fw,
        "project_type": project_type,
        "project_path": project_path,
        "project_name": safe_name,
        "readiness_score": result.readiness_score,
        "adjusted_score": adjusted_score,
        "confidence": adjusted_score,
        "file_count": result.file_count,
        "total_size_bytes": result.total_size_bytes,
        "entry_points": result.entry_points,
        "dependencies": result.dependencies,
        "build_scripts": result.build_scripts,
        "has_build_script": result.has_build_script,
        "has_entry_point": result.has_entry_point,
        "has_lock_file": result.has_lock_file,
        "issues": result.issues,
        "recommendations": result.recommendations,
        "detected_files": result.detected_files[:20],
        "local_commands": local_commands,
        "auto_fixes": result.auto_fixes,
        "platforms": [{"platform": r.platform, "confidence": r.confidence, "reason": r.reason} for r in recs],
        "costs": costs,
        "security": {
            "risk": scan.overall_risk,
            "findings_count": len(scan.findings),
            "penalty": scan.score_penalty,
        },
    }


# ═══════════════════════════════════════════════════════════════
#  ROUTE 1: ZIP upload (single .zip file)
# ═══════════════════════════════════════════════════════════════
@router.post("/project")
async def analyze_project(file: UploadFile = File(...)):
    """Upload a ZIP archive for full project analysis."""
    if not file.filename.endswith((".zip",)):
        raise HTTPException(400, "Only .zip files are supported. Use /analyze/folder for folder uploads.")

    content = await file.read()
    if len(content) < 512:
        return {"valid": False, "error": "PROJECT_TOO_SMALL",
                "message": "ZIP file is too small — likely empty.", "readiness_score": 0}

    safe_name = _sanitize_name(file.filename)
    project_dest = UPLOADS_DIR / safe_name

    if project_dest.exists():
        shutil.rmtree(project_dest, ignore_errors=True)
    project_dest.mkdir(parents=True, exist_ok=True)

    zip_path = project_dest / file.filename
    with open(zip_path, "wb") as f:
        f.write(content)

    try:
        project_path = ProjectAnalyzer.extract_zip(str(zip_path), str(project_dest))
    except Exception as e:
        return {"valid": False, "error": "EXTRACTION_FAILED",
                "message": f"Failed to extract: {str(e)}", "readiness_score": 0}

    try:
        zip_path.unlink()
    except Exception:
        pass

    # Recursive root detection handles nested structures
    project_path = str(Path(project_path).resolve())
    logger.info(f"[ANALYZE] ZIP extracted, project root: {project_path}")
    
    # Run analysis in executor to avoid blocking async loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_analysis, project_path, safe_name)


# ═══════════════════════════════════════════════════════════════
#  ROUTE 2: FOLDER upload (multiple files with relative paths)
# ═══════════════════════════════════════════════════════════════
@router.post("/folder")
async def analyze_folder(files: List[UploadFile] = File(...)):
    """Upload a folder as multiple files. Each file's filename contains the relative path."""
    if not files or len(files) == 0:
        return {"valid": False, "error": "NO_FILES",
                "message": "No files were uploaded.", "readiness_score": 0}

    # Determine project name from first file's path
    first_path = files[0].filename or "project"
    # e.g. "MyProject/src/index.html" → "MyProject"
    parts = first_path.replace("\\", "/").split("/")
    folder_name = parts[0] if len(parts) > 1 else "uploaded-project"
    safe_name = _sanitize_name(folder_name)

    project_dest = UPLOADS_DIR / safe_name
    if project_dest.exists():
        shutil.rmtree(project_dest, ignore_errors=True)
    project_dest.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for f in files:
        raw_path = (f.filename or "").replace("\\", "/")
        # Strip the top-level folder name so files go directly into project_dest
        path_parts = raw_path.split("/")
        if len(path_parts) > 1:
            rel_path = "/".join(path_parts[1:])  # Remove top folder
        else:
            rel_path = path_parts[0]

        if not rel_path:
            continue

        # Security: prevent path traversal
        if ".." in rel_path:
            continue

        target = project_dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        content = await f.read()
        with open(target, "wb") as out:
            out.write(content)
        saved_count += 1

    if saved_count == 0:
        return {"valid": False, "error": "NO_FILES",
                "message": "No valid files were saved from the upload.", "readiness_score": 0}

    # Use recursive root detection in case folder structure is nested
    root = ProjectAnalyzer.find_project_root(str(project_dest.resolve()))
    if not root:
        return {"valid": False, "error": "PROJECT_ROOT_NOT_FOUND",
                "message": "No valid project signature found (package.json, index.html, etc.).", "readiness_score": 0}
    
    project_path = str(Path(root).resolve())
    logger.info(f"[ANALYZE] Folder upload root: {project_path} ({saved_count} files saved)")
    
    # Run analysis in executor to avoid blocking async loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_analysis, project_path, safe_name)
