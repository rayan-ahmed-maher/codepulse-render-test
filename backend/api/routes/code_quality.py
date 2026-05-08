"""
AI Code Quality Scanner — NVIDIA NIM powered code analysis
=============================================================
Scans uploaded projects for security issues, code quality problems,
performance anti-patterns, and dependency vulnerabilities.
"""
import os
import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel
from core.config import settings
from core.supabase_client import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality", tags=["Code Quality"])

# ── File Extensions to Scan ──────────────────────────────────
SCANNABLE_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".go",
    ".rb", ".php", ".html", ".css", ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".env", ".sh",
}

MAX_FILE_SIZE = 50_000  # 50KB per file
MAX_FILES = 80


# ── Scoring ──────────────────────────────────────────────────
SEVERITY_PENALTY = {
    "Critical": 20,
    "High": 10,
    "Medium": 5,
    "Low": 2,
}

# ── Static Pattern Rules (Fast, no AI needed) ────────────────
STATIC_RULES = [
    # Security
    {
        "pattern": r"""(?:api[_-]?key|secret|password|token|auth)\s*[:=]\s*['"][A-Za-z0-9+/=_\-]{10,}['"]""",
        "type": "Security",
        "severity": "Critical",
        "description": "Hardcoded secret or API key detected in source code",
        "fix": "Move sensitive values to environment variables (.env) and access via process.env or os.environ",
        "extensions": {".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".php", ".go", ".java"},
    },
    {
        "pattern": r"""(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\+\s*(?:req|request|params|query)""",
        "type": "Security",
        "severity": "Critical",
        "description": "Potential SQL injection — string concatenation in SQL query",
        "fix": "Use parameterized queries or ORM methods instead of string concatenation",
        "extensions": {".js", ".ts", ".py", ".rb", ".php", ".java"},
    },
    {
        "pattern": r"eval\s*\(|exec\s*\(|__import__\s*\(",
        "type": "Security",
        "severity": "High",
        "description": "Dynamic code execution detected (eval/exec)",
        "fix": "Avoid eval/exec — use safe alternatives like JSON.parse or ast.literal_eval",
        "extensions": {".js", ".ts", ".py"},
    },
    # Code Quality
    {
        "pattern": r"console\.log\s*\(",
        "type": "Quality",
        "severity": "Low",
        "description": "console.log left in production code",
        "fix": "Remove console.log or replace with a proper logging library",
        "extensions": {".js", ".jsx", ".ts", ".tsx"},
    },
    {
        "pattern": r"catch\s*\([^)]*\)\s*\{\s*\}",
        "type": "Quality",
        "severity": "Medium",
        "description": "Empty catch block — errors are being silently swallowed",
        "fix": "Add error logging inside catch blocks: console.error(err) or logger.error(err)",
        "extensions": {".js", ".jsx", ".ts", ".tsx", ".java"},
    },
    {
        "pattern": r"except\s*:\s*\n\s*pass",
        "type": "Quality",
        "severity": "Medium",
        "description": "Bare except with pass — errors are being silently swallowed",
        "fix": "Log the exception: except Exception as e: logger.error(e)",
        "extensions": {".py"},
    },
    {
        "pattern": r"TODO|FIXME|HACK|XXX",
        "type": "Quality",
        "severity": "Low",
        "description": "Unresolved TODO/FIXME marker found",
        "fix": "Resolve the TODO or remove the comment if no longer relevant",
        "extensions": SCANNABLE_EXTENSIONS,
    },
    # Performance
    {
        "pattern": r"readFileSync\s*\(|writeFileSync\s*\(",
        "type": "Performance",
        "severity": "Medium",
        "description": "Synchronous file I/O detected — blocks the event loop",
        "fix": "Use async fs.readFile / fs.writeFile with await instead",
        "extensions": {".js", ".ts"},
    },
    {
        "pattern": r"time\.sleep\s*\(",
        "type": "Performance",
        "severity": "Medium",
        "description": "Blocking sleep detected in Python — blocks async event loop",
        "fix": "Use asyncio.sleep() instead of time.sleep() in async code",
        "extensions": {".py"},
    },
    {
        "pattern": r"for\s+.*\s+in\s+.*:\s*\n\s*.*\.append\(",
        "type": "Performance",
        "severity": "Low",
        "description": "List built with for-loop + append — can use list comprehension",
        "fix": "Use list comprehension: result = [transform(x) for x in items]",
        "extensions": {".py"},
    },
]


class ScanRequest(BaseModel):
    project_path: str
    project_id: str = ""


class FixRequest(BaseModel):
    file_path: str
    line_number: int
    issue_description: str
    code_snippet: str


def _collect_files(project_path: str) -> list:
    """Collect scannable source files from project."""
    files = []
    root = Path(project_path)
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}

    for f in root.rglob("*"):
        if f.is_dir():
            continue
        # Skip excluded directories
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue
        if f.stat().st_size > MAX_FILE_SIZE:
            continue
        files.append(f)
        if len(files) >= MAX_FILES:
            break
    return files


def _scan_file_static(filepath: Path, project_root: Path) -> list:
    """Run static pattern matching rules on a single file."""
    issues = []
    ext = filepath.suffix.lower()

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    lines = content.split("\n")
    rel_path = str(filepath.relative_to(project_root))

    for rule in STATIC_RULES:
        if ext not in rule.get("extensions", SCANNABLE_EXTENSIONS):
            continue
        for i, line in enumerate(lines, 1):
            if re.search(rule["pattern"], line, re.IGNORECASE):
                issues.append({
                    "file_name": rel_path,
                    "line_number": i,
                    "issue_type": rule["type"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "suggested_fix": rule["fix"],
                    "code_snippet": line.strip()[:150],
                })
    return issues


def _scan_dependencies(project_path: str) -> list:
    """Check package.json / requirements.txt for known patterns."""
    issues = []
    root = Path(project_path)

    # Check package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            # Check for wildcard versions
            for name, version in deps.items():
                if version in ("*", "latest"):
                    issues.append({
                        "file_name": "package.json",
                        "line_number": 0,
                        "issue_type": "Dependencies",
                        "severity": "High",
                        "description": f"Dependency '{name}' uses wildcard version '{version}' — unpredictable builds",
                        "suggested_fix": f"Pin to a specific version: npm install {name}@latest --save-exact",
                        "code_snippet": f'"{name}": "{version}"',
                    })

            # Check for known vulnerable patterns
            risky_deps = {"event-stream": "High", "flatmap-stream": "Critical", "ua-parser-js": "Medium"}
            for name, sev in risky_deps.items():
                if name in deps:
                    issues.append({
                        "file_name": "package.json",
                        "line_number": 0,
                        "issue_type": "Dependencies",
                        "severity": sev,
                        "description": f"Package '{name}' has known security vulnerabilities",
                        "suggested_fix": f"Remove or replace '{name}' with a maintained alternative",
                        "code_snippet": f'"{name}": "{deps[name]}"',
                    })
        except Exception:
            pass

    # Check requirements.txt for unpinned versions
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        try:
            lines = req_txt.read_text(encoding="utf-8").strip().split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    if "==" not in line and ">=" not in line and "<=" not in line:
                        issues.append({
                            "file_name": "requirements.txt",
                            "line_number": i,
                            "issue_type": "Dependencies",
                            "severity": "Medium",
                            "description": f"Dependency '{line}' has no pinned version — builds may break",
                            "suggested_fix": f"Pin version: {line}==<version> (run: pip freeze | grep {line})",
                            "code_snippet": line,
                        })
        except Exception:
            pass

    return issues


def _calculate_score(issues: list) -> int:
    """Calculate quality score 0-100 from issue list."""
    score = 100
    for issue in issues:
        penalty = SEVERITY_PENALTY.get(issue.get("severity", "Low"), 2)
        score -= penalty
    return max(0, score)


@router.post("/scan")
async def scan_project(data: ScanRequest):
    """Scan a project for code quality issues."""
    project_path = data.project_path
    if not os.path.isdir(project_path):
        return {
            "status": "error",
            "reason": "Project path not found",
            "evidence": f"Path: {project_path}",
            "solution": "Upload a project first, then run the quality scan.",
        }

    logger.info(f"[QUALITY] Scanning project at {project_path}")

    # Collect files
    files = _collect_files(project_path)
    logger.info(f"[QUALITY] Found {len(files)} scannable files")

    # Run static analysis
    all_issues = []
    for f in files:
        file_issues = _scan_file_static(f, Path(project_path))
        all_issues.extend(file_issues)

    # Run dependency check
    dep_issues = _scan_dependencies(project_path)
    all_issues.extend(dep_issues)

    # AI-enhanced scan (use NIM to find deeper issues)
    ai_issues = await _ai_deep_scan(files[:10], Path(project_path))  # Top 10 files
    all_issues.extend(ai_issues)

    # Calculate score
    score = _calculate_score(all_issues)

    # Category breakdown
    categories = {
        "Security": {"count": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "issues": []},
        "Quality": {"count": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "issues": []},
        "Performance": {"count": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "issues": []},
        "Dependencies": {"count": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "issues": []},
    }

    for issue in all_issues:
        cat = issue.get("issue_type", "Quality")
        if cat not in categories:
            cat = "Quality"
        categories[cat]["count"] += 1
        sev = issue.get("severity", "Low").lower()
        if sev in categories[cat]:
            categories[cat][sev] += 1
        categories[cat]["issues"].append(issue)

    result = {
        "status": "success",
        "score": score,
        "total_issues": len(all_issues),
        "files_scanned": len(files),
        "categories": categories,
        "issues": all_issues,
    }

    # Store in Supabase
    if data.project_id:
        try:
            await db.store_quality_scan(data.project_id, result)
        except Exception as e:
            logger.warning(f"[QUALITY] Failed to store scan: {e}")

    # PostHog event
    try:
        from core.observability import track_event
        track_event("quality_scan_complete", properties={
            "score": score,
            "total_issues": len(all_issues),
            "critical_count": sum(1 for i in all_issues if i.get("severity") == "Critical"),
        })
    except Exception:
        pass

    logger.info(f"[QUALITY] Scan complete: score={score}, issues={len(all_issues)}")
    return result


@router.get("/scan/{project_id}")
async def get_scan_results(project_id: str):
    """Retrieve previous scan results for a project."""
    try:
        result = await db.get_quality_scan(project_id)
        if result:
            return result
        return {
            "status": "error",
            "reason": "No scan results found",
            "evidence": f"project_id: {project_id}",
            "solution": "Run a quality scan first using POST /api/v1/quality/scan",
        }
    except Exception as e:
        return {
            "status": "error",
            "reason": "Failed to retrieve scan results",
            "evidence": str(e)[:200],
            "solution": "Check the Supabase connection and try again.",
        }


@router.post("/fix")
async def ai_fix_issue(data: FixRequest):
    """Use NVIDIA NIM to generate an AI fix for a specific code issue."""
    if not settings.has_nvidia:
        return {
            "status": "error",
            "reason": "NVIDIA NIM API not configured",
            "evidence": "NVIDIA_API_KEY is not set in .env",
            "solution": "Add your NVIDIA API key to the .env file.",
        }

    try:
        import httpx
        prompt = f"""You are a senior code reviewer. Fix the following issue:

FILE: {data.file_path}
LINE: {data.line_number}
ISSUE: {data.issue_description}
CODE:
```
{data.code_snippet}
```

Respond with ONLY a JSON object containing:
- "original": the original problematic code (exact match)
- "fixed": the corrected code
- "explanation": brief explanation of the fix

Do not include markdown fences or any text outside the JSON."""

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta/llama-3.1-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 800,
                },
            )
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse JSON response
            try:
                fix_data = json.loads(content.strip().strip("```json").strip("```"))
            except json.JSONDecodeError:
                fix_data = {
                    "original": data.code_snippet,
                    "fixed": content,
                    "explanation": "AI generated fix — review before applying",
                }

            return {
                "status": "success",
                "fix": fix_data,
                "file_path": data.file_path,
                "line_number": data.line_number,
            }
    except Exception as e:
        logger.error(f"[QUALITY] AI fix failed: {e}")
        return {
            "status": "error",
            "reason": "AI fix generation failed",
            "evidence": str(e)[:200],
            "solution": "Check the NVIDIA NIM API key and network connection.",
        }


async def _ai_deep_scan(files: list, project_root: Path) -> list:
    """Use NVIDIA NIM to find deeper code issues that static rules miss."""
    if not settings.has_nvidia:
        return []

    issues = []
    try:
        import httpx

        # Build a summary of the codebase for NIM
        code_summary = ""
        for f in files:
            try:
                rel = str(f.relative_to(project_root))
                content = f.read_text(encoding="utf-8", errors="ignore")[:2000]
                code_summary += f"\n--- {rel} ---\n{content}\n"
            except Exception:
                continue

        if not code_summary.strip():
            return []

        prompt = f"""Analyze this codebase for security, quality, and performance issues.
For each issue found, respond with a JSON array of objects with these exact keys:
- "file_name": relative file path
- "line_number": approximate line number (integer)
- "issue_type": one of "Security", "Quality", "Performance"
- "severity": one of "Critical", "High", "Medium", "Low"
- "description": clear description of the issue
- "suggested_fix": actionable fix instruction

Only report REAL issues. Do not fabricate. Maximum 10 issues.
Respond with ONLY the JSON array, no markdown fences.

CODEBASE:
{code_summary[:8000]}"""

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta/llama-3.1-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
            )
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse response
            try:
                ai_issues = json.loads(content.strip().strip("```json").strip("```"))
                if isinstance(ai_issues, list):
                    for issue in ai_issues[:10]:
                        issue["code_snippet"] = ""
                        issues.append(issue)
            except json.JSONDecodeError:
                logger.debug("[QUALITY] AI scan response was not valid JSON")

    except Exception as e:
        logger.warning(f"[QUALITY] AI deep scan failed: {e}")

    return issues
