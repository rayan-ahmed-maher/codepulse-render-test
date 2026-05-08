"""
Pre-Deploy Validation Route — Standalone validation endpoint
================================================================
MUST RUN BEFORE DEPLOY.
Returns structured pass/fail results for every check.
No guessing — only evidence-based validation.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validate", tags=["Validation"])


# ── Platform-specific file size limits (bytes) ────────────────
PLATFORM_FILE_LIMITS = {
    "Cloudflare": 25 * 1024 * 1024,   # 25MB per file
    "Vercel":     100 * 1024 * 1024,   # 100MB per file (serverless bundled)
    "Netlify":    100 * 1024 * 1024,   # 100MB per file
    "Render":     500 * 1024 * 1024,   # 500MB per file
}

# ── Dangerous / forbidden file types ────────────────────────
FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".msi", ".scr",
    ".com", ".pif", ".vbs", ".wsf",
}

LARGE_MEDIA_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv",
    ".mp3", ".wav", ".flac", ".aac",
    ".iso", ".img", ".dmg",
}

# ── Project signature files (at least one must exist) ────────
SIGNATURE_FILES = {
    "package.json", "index.html", "index.htm",
    "requirements.txt", "pyproject.toml", "pipfile",
    "setup.py", "manage.py", "app.py", "main.py", "wsgi.py",
    "cargo.toml", "go.mod", "dockerfile",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.js", "vite.config.ts", "angular.json",
    "composer.json", "wrangler.toml",
}


class ValidateRequest(BaseModel):
    project_path: str
    platform: Optional[str] = None  # If provided, applies platform-specific rules


class ValidationIssue(BaseModel):
    check: str
    passed: bool
    reason: str
    evidence: str
    solution: str


class ValidationResponse(BaseModel):
    valid: bool
    score: int  # 0-100 — percentage of checks passed
    issues: List[ValidationIssue]
    total_checks: int
    passed_checks: int
    failed_checks: int


@router.post("/pre-deploy", response_model=ValidationResponse)
async def validate_before_deploy(req: ValidateRequest):
    """
    Standalone pre-deploy validation.
    Runs ALL checks from the PRD:
      1. File Size Check (platform-specific)
      2. File Type Check (forbidden extensions)
      3. Structure Check (signature files)
      4. Empty Folder Detection
      5. Large Media Warning
    Returns structured results with reason / evidence / solution.
    """
    issues: List[ValidationIssue] = []
    project_path = Path(req.project_path)

    # ────────────────────────────────────────────────────────────
    # CHECK 0: Project path exists
    # ────────────────────────────────────────────────────────────
    if not project_path.exists() or not project_path.is_dir():
        issues.append(ValidationIssue(
            check="PATH_EXISTS",
            passed=False,
            reason="Project directory does not exist",
            evidence=f"Path not found: {req.project_path}",
            solution="Re-upload and analyze your project before deploying.",
        ))
        return ValidationResponse(
            valid=False, score=0, issues=issues,
            total_checks=1, passed_checks=0, failed_checks=1,
        )

    # Collect all files recursively (skip node_modules, .git, etc.)
    SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".next", "dist",
                 "build", ".venv", "venv", ".cache", ".tox", "env"}

    all_files = []
    for root, dirs, filenames in os.walk(project_path):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fname in filenames:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, project_path)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            all_files.append((rel_path, full_path, size, fname))

    # ────────────────────────────────────────────────────────────
    # CHECK 1: Empty folder detection
    # ────────────────────────────────────────────────────────────
    if len(all_files) == 0:
        issues.append(ValidationIssue(
            check="EMPTY_PROJECT",
            passed=False,
            reason="Project directory is empty",
            evidence=f"0 files found in {req.project_path}",
            solution="Upload a project with source files before deploying.",
        ))
    else:
        issues.append(ValidationIssue(
            check="EMPTY_PROJECT",
            passed=True,
            reason="Project contains files",
            evidence=f"{len(all_files)} files found",
            solution="",
        ))

    # ────────────────────────────────────────────────────────────
    # CHECK 2: Structure check — at least one signature file
    # ────────────────────────────────────────────────────────────
    found_signatures = [
        fname for (_, _, _, fname) in all_files
        if fname.lower() in SIGNATURE_FILES
    ]
    if found_signatures:
        issues.append(ValidationIssue(
            check="PROJECT_STRUCTURE",
            passed=True,
            reason="Valid project structure detected",
            evidence=f"Signature files found: {', '.join(found_signatures[:5])}",
            solution="",
        ))
    else:
        issues.append(ValidationIssue(
            check="PROJECT_STRUCTURE",
            passed=False,
            reason="No project signature file found",
            evidence="Missing: package.json, index.html, requirements.txt, main.py, etc.",
            solution="Add at least one signature file (package.json for Node, index.html for static, requirements.txt for Python).",
        ))

    # ────────────────────────────────────────────────────────────
    # CHECK 3: Forbidden file types (.exe, .dll, .bat, etc.)
    # ────────────────────────────────────────────────────────────
    forbidden_found = [
        rel for (rel, _, _, fname) in all_files
        if os.path.splitext(fname)[1].lower() in FORBIDDEN_EXTENSIONS
    ]
    if forbidden_found:
        issues.append(ValidationIssue(
            check="FORBIDDEN_FILES",
            passed=False,
            reason="Forbidden file types detected",
            evidence=f"Found: {', '.join(forbidden_found[:5])}",
            solution="Remove all .exe, .dll, .bat, and other binary executables before deploying.",
        ))
    else:
        issues.append(ValidationIssue(
            check="FORBIDDEN_FILES",
            passed=True,
            reason="No forbidden file types detected",
            evidence="All files have safe extensions",
            solution="",
        ))

    # ────────────────────────────────────────────────────────────
    # CHECK 4: Large media files warning
    # ────────────────────────────────────────────────────────────
    large_media = [
        (rel, size) for (rel, _, size, fname) in all_files
        if os.path.splitext(fname)[1].lower() in LARGE_MEDIA_EXTENSIONS
        and size > 10 * 1024 * 1024  # > 10MB
    ]
    if large_media:
        details = "; ".join(f"{r} ({s // (1024*1024)}MB)" for r, s in large_media[:5])
        issues.append(ValidationIssue(
            check="LARGE_MEDIA",
            passed=False,
            reason="Large media files detected (>10MB)",
            evidence=details,
            solution="Compress or remove large media files. Use CDN for video/audio hosting.",
        ))
    else:
        issues.append(ValidationIssue(
            check="LARGE_MEDIA",
            passed=True,
            reason="No oversized media files detected",
            evidence="All media files are within acceptable limits",
            solution="",
        ))

    # ────────────────────────────────────────────────────────────
    # CHECK 5: Platform-specific file size limits
    # ────────────────────────────────────────────────────────────
    if req.platform:
        max_size = PLATFORM_FILE_LIMITS.get(req.platform, 100 * 1024 * 1024)
        oversized = [
            (rel, size) for (rel, _, size, _) in all_files
            if size > max_size
        ]
        if oversized:
            details = "; ".join(
                f"{r} ({s // (1024*1024)}MB, limit {max_size // (1024*1024)}MB)"
                for r, s in oversized[:5]
            )
            issues.append(ValidationIssue(
                check="FILE_TOO_LARGE",
                passed=False,
                reason=f"Files exceed {req.platform} size limit ({max_size // (1024*1024)}MB)",
                evidence=details,
                solution=f"Compress or remove files exceeding the {req.platform} per-file limit.",
            ))
        else:
            issues.append(ValidationIssue(
                check="FILE_TOO_LARGE",
                passed=True,
                reason=f"All files within {req.platform} size limits",
                evidence=f"Max allowed: {max_size // (1024*1024)}MB per file",
                solution="",
            ))

    # ────────────────────────────────────────────────────────────
    # CHECK 6: Total project size
    # ────────────────────────────────────────────────────────────
    total_size = sum(s for (_, _, s, _) in all_files)
    if total_size > 500 * 1024 * 1024:  # > 500MB total
        issues.append(ValidationIssue(
            check="TOTAL_SIZE",
            passed=False,
            reason="Project total size exceeds 500MB",
            evidence=f"Total: {total_size // (1024*1024)}MB",
            solution="Reduce project size by removing unused assets, node_modules, or build artifacts.",
        ))
    else:
        issues.append(ValidationIssue(
            check="TOTAL_SIZE",
            passed=True,
            reason="Project size is within limits",
            evidence=f"Total: {total_size // (1024*1024)}MB",
            solution="",
        ))

    # ── SCORE CALCULATION ──
    passed = sum(1 for i in issues if i.passed)
    failed = sum(1 for i in issues if not i.passed)
    total = len(issues)
    score = int((passed / total) * 100) if total > 0 else 0

    logger.info(f"[VALIDATE] Pre-deploy: {passed}/{total} checks passed (score: {score})")

    return ValidationResponse(
        valid=failed == 0,
        score=score,
        issues=issues,
        total_checks=total,
        passed_checks=passed,
        failed_checks=failed,
    )
