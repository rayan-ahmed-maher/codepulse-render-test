"""
GitHub Import Route — Downloads repo as ZIP, extracts, and analyzes locally
===========================================================================
This replaces the old API-based tree scanning. Imported repos now behave
EXACTLY like manually uploaded ZIP files.
"""
import os
import re
import shutil
import logging
import zipfile
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from core.config import settings
from services.analyzer import ProjectAnalyzer

# Import shared logic from analyze.py
from api.routes.analyze import _run_analysis, _sanitize_name, UPLOADS_DIR

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = logging.getLogger(__name__)


class GitHubImportInput(BaseModel):
    url: str
    branch: str | None = None


def parse_github_url(url: str) -> tuple:
    """Extract owner and repo from a GitHub URL."""
    patterns = [
        r"github\.com/([^/]+)/([^/\s?#]+)",
        r"^([^/]+)/([^/\s]+)$",
    ]
    for p in patterns:
        m = re.search(p, url.strip().rstrip("/").replace(".git", ""))
        if m:
            return m.group(1), m.group(2)
    return None, None


@router.post("/github")
async def analyze_github(data: GitHubImportInput):
    owner, repo = parse_github_url(data.url)
    if not owner or not repo:
        raise HTTPException(400, "Invalid GitHub URL. Expected: https://github.com/owner/repo")

    # 1. AUTHENTICATION FIX
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DeployAI",
    }
    if settings.has_github_token:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    # Determine zipball URL (with optional branch)
    branch_path = f"/{data.branch}" if data.branch else ""
    zipball_url = f"https://api.github.com/repos/{owner}/{repo}/zipball{branch_path}"
    logger.info(f"[GITHUB_IMPORT] Starting download from: {zipball_url}")

    # 2. DOWNLOAD HANDLING
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        try:
            # Check repo exists and handle private repo authentication
            check_resp = await http.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            
            if check_resp.status_code == 404:
                return {"valid": False, "error": "NOT_FOUND", "message": f"Repository not found or is private (no valid token provided): {owner}/{repo}"}
            
            if check_resp.status_code == 401 or check_resp.status_code == 403:
                return {"valid": False, "error": "AUTH_ERROR", "message": "GitHub API access denied or rate limit exceeded."}
            
            repo_info = check_resp.json()
            is_private = repo_info.get("private", False)
            
            if is_private and not settings.has_github_token:
                return {"valid": False, "error": "PRIVATE_REPO_NO_TOKEN", "message": "Repository is private but no GitHub token was provided. Add GITHUB_TOKEN to .env."}

            # Download zipball (retry up to 3 times)
            download_success = False
            for attempt in range(3):
                try:
                    zip_resp = await http.get(zipball_url, headers=headers)
                    if zip_resp.status_code == 200:
                        download_success = True
                        break
                    else:
                        logger.warning(f"[GITHUB_IMPORT] Download attempt {attempt+1} failed: HTTP {zip_resp.status_code}")
                except Exception as e:
                    logger.warning(f"[GITHUB_IMPORT] Download attempt {attempt+1} exception: {e}")
                await asyncio.sleep(1)

            if not download_success:
                return {"valid": False, "error": "DOWNLOAD_FAILED", "message": f"Failed to download repository zip from GitHub."}

            zip_bytes = zip_resp.content
            if len(zip_bytes) == 0:
                return {"valid": False, "error": "EMPTY_ZIP", "message": "Downloaded repository zip is empty."}
            
            logger.info(f"[GITHUB_IMPORT] Downloaded {len(zip_bytes)} bytes")

        except Exception as e:
            logger.error(f"[GITHUB_IMPORT] Connection error: {e}")
            return {"valid": False, "error": "CONNECTION_ERROR", "message": f"Error connecting to GitHub: {e}"}

    # 3. EXTRACTION FIX
    safe_name = _sanitize_name(repo)
    project_dest = UPLOADS_DIR / safe_name
    
    if project_dest.exists():
        shutil.rmtree(project_dest, ignore_errors=True)
    project_dest.mkdir(parents=True, exist_ok=True)

    try:
        with NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(zip_bytes)
            tmp_path = tmp.name

        with zipfile.ZipFile(tmp_path, "r") as zip_ref:
            # Extract to temporary project_dest
            zip_ref.extractall(project_dest)
            
            # GitHub ZIPs always contain a root folder `owner-repo-commitHash`
            # We must move the contents UP one level to match manual upload behavior.
            extracted_items = list(project_dest.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                nested_dir = extracted_items[0]
                logger.info(f"[GITHUB_IMPORT] Removing nested folder: {nested_dir.name}")
                
                # Move all contents of nested_dir to project_dest
                for item in nested_dir.iterdir():
                    shutil.move(str(item), str(project_dest))
                
                # Remove the now empty nested folder
                nested_dir.rmdir()
                
    except Exception as e:
        logger.error(f"[GITHUB_IMPORT] Extraction failed: {e}")
        return {"valid": False, "error": "EXTRACTION_FAILED", "message": "Failed to extract repository archive."}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 4. PROJECT ROOT DETECTION
    # Using the same logic as analyze.py to find the actual project root
    root = ProjectAnalyzer.find_project_root(str(project_dest.resolve()))
    if not root:
        return {"valid": False, "error": "PROJECT_ROOT_NOT_FOUND", 
                "message": "No valid project structure found in the repository."}
    
    project_path = str(Path(root).resolve())
    
    # 5. PATH VALIDATION
    if not os.path.exists(project_path) or not os.listdir(project_path):
        return {"valid": False, "error": "PROJECT_ROOT_NOT_FOUND", "message": "Extracted repository contains no files."}

    logger.info(f"[GITHUB_IMPORT] Extracted to: {project_dest}")
    logger.info(f"[GITHUB_IMPORT] Detected root: {project_path}")

    # 6. ANALYZER COMPATIBILITY
    # Run exact same analysis logic as manual folder uploads
    loop = asyncio.get_event_loop()
    analysis_result = await loop.run_in_executor(None, _run_analysis, project_path, safe_name)
    
    # Check if analysis failed
    if not analysis_result.get("valid", False):
        return analysis_result

    # Override source and repo fields
    analysis_result["source"] = "github"
    analysis_result["repo"] = f"{owner}/{repo}"

    return analysis_result
