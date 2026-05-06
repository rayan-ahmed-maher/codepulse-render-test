"""
Project Analyzer Service — Recursive Deep Scanner
====================================================
1. Recursively scans all files (ZIP, folder, GitHub clone).
2. Finds the TRUE project root (handles nested ZIPs like project/inner/package.json).
3. Detects framework from DEPENDENCIES, not folder names.
4. Assigns Deployment Readiness Score (0-100).
5. Auto-fixes common issues (missing build scripts, .gitignore).
6. Generates actionable issues and recommendations.
"""

import os
import zipfile
import json
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Performance limits
MAX_FILES = 10000          # Stop scanning after this many files
MAX_SCAN_DEPTH = 20        # Max directory recursion depth
SCAN_TIMEOUT_SEC = 30      # Abort scan after this many seconds

# Binary/media extensions to skip (not useful for analysis)
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg', '.webp', '.avif',
    '.mp4', '.mp3', '.wav', '.ogg', '.avi', '.mov', '.webm',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt',
    '.exe', '.dll', '.so', '.dylib', '.o', '.obj',
    '.pyc', '.pyo', '.class', '.jar',
    '.sqlite', '.db', '.sqlite3',
    '.lock',  # lockfiles are huge, we only check existence
}


class FrameworkType(str, Enum):
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    VITE = "vite"
    ANGULAR = "angular"
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    STATIC = "static"
    NODEJS = "nodejs"
    PYTHON = "python"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    project_path: str
    framework: FrameworkType
    readiness_score: int
    entry_points: List[str]
    dependencies: List[str]
    build_scripts: List[str]
    issues: List[str]
    recommendations: List[str]
    file_count: int = 0
    total_size_bytes: int = 0
    has_build_script: bool = False
    has_entry_point: bool = False
    has_lock_file: bool = False
    detected_files: List[str] = field(default_factory=list)
    auto_fixes: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  PROJECT ROOT SIGNATURE FILES
# ═══════════════════════════════════════════════════════════════
ROOT_SIGNATURES = {
    "package.json", "requirements.txt", "pyproject.toml",
    "pipfile", "setup.py", "cargo.toml", "go.mod",
    "dockerfile", "docker-compose.yml",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.js", "vite.config.ts",
    "angular.json",
    "manage.py", "app.py", "wsgi.py",
    "composer.json", "wrangler.toml",
    "index.html",
}


class ProjectAnalyzer:
    """Scans project files and produces a deployment readiness report."""

    # Framework detection fingerprints — keyed by FILES and DEPS
    FINGERPRINTS = {
        FrameworkType.NEXTJS: {
            "files": ["next.config.js", "next.config.mjs", "next.config.ts"],
            "deps": ["next"],
        },
        FrameworkType.ANGULAR: {
            "files": ["angular.json"],
            "deps": ["@angular/core"],
        },
        FrameworkType.REACT: {
            "files": ["src/app.jsx", "src/app.tsx", "src/app.js", "public/index.html"],
            "deps": ["react", "react-dom"],
        },
        FrameworkType.VUE: {
            "files": ["vue.config.js", "src/app.vue"],
            "deps": ["vue"],
        },
        FrameworkType.VITE: {
            "files": ["vite.config.js", "vite.config.ts"],
            "deps": ["vite"],
        },
        FrameworkType.DJANGO: {
            "files": ["manage.py"],
            "deps": ["django"],
        },
        FrameworkType.FASTAPI: {
            "files": ["main.py", "app/main.py"],
            "deps": ["fastapi", "uvicorn"],
        },
        FrameworkType.FLASK: {
            "files": ["app.py", "wsgi.py"],
            "deps": ["flask"],
        },
        FrameworkType.NODEJS: {
            "files": ["server.js", "app.js", "index.js"],
            "deps": ["express", "koa", "fastify", "hapi"],
        },
    }

    ENTRY_POINTS = [
        "index.html", "index.htm",
        "main.py", "app.py", "wsgi.py", "manage.py",
        "server.js", "index.js", "app.js",
        "src/main.jsx", "src/main.tsx", "src/index.js", "src/index.tsx",
    ]

    BUILD_SCRIPTS = ["build", "start", "dev"]

    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".next",
        "dist", "build", ".venv", "venv", ".cache",
        ".idea", ".vscode", ".tox", "env", ".mypy_cache",
        ".pytest_cache", "coverage", ".turbo",
    }

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.files: List[str] = []
        self.files_lower: Dict[str, str] = {}  # lowercase → original
        self.package_json: Optional[dict] = None
        self.requirements_txt: List[str] = []

    # ───────────────────────────────────────────────────────────
    #  RECURSIVE PROJECT ROOT DETECTION
    # ───────────────────────────────────────────────────────────
    @staticmethod
    def find_project_root(base_path: str, max_depth: int = 4) -> Optional[str]:
        """
        Recursively search for the true project root by looking for
        signature files. Handles nested ZIPs like:
            project.zip/outer/inner/package.json → returns 'inner/'

        Returns the path to the deepest directory containing signature files,
        preferring the shallowest match (closest to base), or None if not found.
        """
        base = Path(base_path)
        logger.info(f"[ROOT DETECT] Searching for project root in: {base}")

        # Check if current directory has signatures
        for item in base.iterdir():
            if item.is_file() and item.name.lower() in ROOT_SIGNATURES:
                logger.info(f"[ROOT DETECT] Found signature '{item.name}' at root level")
                return str(base)

        # BFS: walk directories level by level up to max_depth
        candidates = []
        for depth in range(1, max_depth + 1):
            for root, dirs, files in os.walk(base):
                # Calculate depth relative to base
                rel = os.path.relpath(root, base)
                current_depth = 0 if rel == "." else len(Path(rel).parts)

                if current_depth != depth:
                    continue

                # Skip non-project directories
                dirs[:] = [d for d in dirs if d.lower() not in ProjectAnalyzer.SKIP_DIRS]

                for f in files:
                    if f.lower() in ROOT_SIGNATURES:
                        candidates.append((current_depth, root, f))
                        logger.info(f"[ROOT DETECT] Found signature '{f}' at depth {current_depth}: {root}")

            # If we found any signatures at this depth, use the best one
            if candidates:
                # Prefer package.json > requirements.txt > Dockerfile > index.html
                priority = ["package.json", "requirements.txt", "pyproject.toml",
                            "dockerfile", "next.config.js", "next.config.mjs",
                            "vite.config.js", "angular.json", "manage.py",
                            "index.html"]
                best = candidates[0]
                for p in priority:
                    for c in candidates:
                        if c[2].lower() == p:
                            best = c
                            break
                    if best[2].lower() == p:
                        break
                logger.info(f"[ROOT DETECT] Selected project root: {best[1]} (signature: {best[2]})")
                return best[1]

        # No signatures found anywhere
        logger.warning(f"[ROOT DETECT] No signatures found in: {base}")
        return None

    # ───────────────────────────────────────────────────────────
    #  FILE COLLECTION (recursive, with lowercase index)
    # ───────────────────────────────────────────────────────────
    def _collect_files(self) -> None:
        """Walk the project tree with performance limits."""
        self.files = []
        self.files_lower = {}
        t_start = time.time()
        dirs_scanned = 0
        dirs_skipped = 0

        for root, dirs, filenames in os.walk(self.project_path):
            # Depth check
            rel_root = os.path.relpath(root, self.project_path)
            depth = 0 if rel_root == "." else len(Path(rel_root).parts)
            if depth > MAX_SCAN_DEPTH:
                dirs.clear()
                continue

            # Timeout check
            if time.time() - t_start > SCAN_TIMEOUT_SEC:
                logger.warning(f"[SCAN] Timeout after {SCAN_TIMEOUT_SEC}s, collected {len(self.files)} files")
                break

            # File count limit
            if len(self.files) >= MAX_FILES:
                logger.warning(f"[SCAN] Hit file limit ({MAX_FILES}), stopping")
                break

            # Skip excluded directories
            original_count = len(dirs)
            dirs[:] = [d for d in dirs if d.lower() not in self.SKIP_DIRS]
            dirs_skipped += original_count - len(dirs)
            dirs_scanned += 1

            for fname in filenames:
                if len(self.files) >= MAX_FILES:
                    break
                # Skip binary/media files
                ext = os.path.splitext(fname)[1].lower()
                if ext in BINARY_EXTENSIONS:
                    continue
                rel = os.path.relpath(os.path.join(root, fname), self.project_path)
                rel_normalized = rel.replace("\\", "/")
                self.files.append(rel_normalized)
                self.files_lower[rel_normalized.lower()] = rel_normalized

        elapsed = time.time() - t_start
        logger.info(
            f"[SCAN] Collected {len(self.files)} files from {dirs_scanned} dirs "
            f"(skipped {dirs_skipped} dirs) in {elapsed:.2f}s"
        )

    def _has_file(self, name: str) -> bool:
        """Case-insensitive file existence check."""
        return name.lower() in self.files_lower

    def _load_package_json(self) -> None:
        """Try to load package.json from project root."""
        pkg_path = self.project_path / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    self.package_json = json.load(f)
                logger.info(f"[SCAN] Loaded package.json with {len(self.package_json.get('dependencies', {}))} deps")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[SCAN] Failed to parse package.json: {e}")
                self.package_json = None

    def _load_requirements(self) -> None:
        """Try to load requirements.txt from project root."""
        req_path = self.project_path / "requirements.txt"
        if req_path.exists():
            try:
                with open(req_path, "r", encoding="utf-8") as f:
                    self.requirements_txt = [
                        line.strip().split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].split("[")[0].lower().strip()
                        for line in f
                        if line.strip() and not line.startswith("#") and not line.startswith("-")
                    ]
                logger.info(f"[SCAN] Loaded requirements.txt with {len(self.requirements_txt)} packages")
            except IOError:
                self.requirements_txt = []
        # Also check pyproject.toml for deps
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists() and not self.requirements_txt:
            try:
                content = pyproject.read_text(encoding="utf-8")
                # Simple extraction of dependency names
                if "dependencies" in content:
                    import re
                    deps = re.findall(r'"([a-zA-Z0-9_-]+)', content)
                    self.requirements_txt = [d.lower() for d in deps]
                    logger.info(f"[SCAN] Extracted {len(self.requirements_txt)} deps from pyproject.toml")
            except Exception:
                pass

    def _detect_framework(self) -> FrameworkType:
        """Detect framework by matching fingerprints using DEPENDENCY-FIRST logic."""
        all_deps = set()
        if self.package_json:
            all_deps.update(self.package_json.get("dependencies", {}).keys())
            all_deps.update(self.package_json.get("devDependencies", {}).keys())
        all_deps.update(self.requirements_txt)
        all_deps_lower = {d.lower() for d in all_deps}

        logger.info(f"[DETECT] Dependencies found: {list(all_deps_lower)[:20]}")

        # Score each framework
        scores = {}
        for framework, fp in self.FINGERPRINTS.items():
            score = 0
            for f in fp["files"]:
                if self._has_file(f):
                    score += 2
                    logger.debug(f"[DETECT] {framework.value}: file match '{f}' (+2)")
            for d in fp["deps"]:
                if d.lower() in all_deps_lower:
                    score += 3
                    logger.debug(f"[DETECT] {framework.value}: dep match '{d}' (+3)")
            if score > 0:
                scores[framework] = score

        if scores:
            winner = max(scores, key=scores.get)
            logger.info(f"[DETECT] Framework scores: {', '.join(f'{k.value}={v}' for k,v in sorted(scores.items(), key=lambda x: -x[1]))}")
            logger.info(f"[DETECT] Winner: {winner.value} (score: {scores[winner]})")
            return winner

        # Fallback: check for static HTML
        if any(f.lower().endswith(".html") for f in self.files):
            logger.info("[DETECT] No framework deps found, but HTML files exist → STATIC")
            return FrameworkType.STATIC

        logger.info("[DETECT] No framework detected → UNKNOWN")
        return FrameworkType.UNKNOWN

    def _compute_readiness(self, framework: FrameworkType) -> tuple:
        """Compute readiness score (0-100) and gather issues/recommendations."""
        score = 0
        issues = []
        recommendations = []
        entry_points = []
        build_scripts = []
        deps = []

        # 1. Entry Point Detection (30 points)
        for ep in self.ENTRY_POINTS:
            if self._has_file(ep):
                entry_points.append(ep)
        if entry_points:
            score += 30
        else:
            issues.append("No entry point found (index.html, main.py, server.js, etc.)")
            recommendations.append("Add an entry point file to your project root")

        # 2. Build Script Detection (25 points)
        if self.package_json:
            scripts = self.package_json.get("scripts", {})
            for bs in self.BUILD_SCRIPTS:
                if bs in scripts:
                    build_scripts.append(f"{bs}: {scripts[bs]}")
            if "build" in scripts:
                score += 25
            else:
                score += 10
                issues.append("No 'build' script in package.json")
                recommendations.append("Add a build script: e.g., 'vite build' or 'next build'")
        elif self.requirements_txt:
            score += 20  # Python projects don't always need build scripts
        elif self._has_file("index.html"):
            score += 20  # Static sites don't need build scripts

        # 3. Dependency Management (20 points)
        has_lock = any(self._has_file(f) for f in [
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "Pipfile.lock", "poetry.lock",
        ])
        if has_lock:
            score += 20
        elif self.package_json or self.requirements_txt:
            score += 10
            recommendations.append("Add a lockfile for reproducible builds")
        else:
            if not self._has_file("index.html"):
                issues.append("No dependency manifest found")

        # 4. Configuration Files (15 points)
        config_files = [
            ".gitignore", "readme.md", "dockerfile",
            "vercel.json", "netlify.toml", "wrangler.toml",
        ]
        found_configs = [f for f in config_files if self._has_file(f)]
        score += min(15, len(found_configs) * 5)

        if not self._has_file(".gitignore"):
            recommendations.append("Add a .gitignore file")
        if not self._has_file("readme.md"):
            recommendations.append("Add a README.md for documentation")

        # 5. Project Size (10 points)
        if 1 <= len(self.files) <= 5000:
            score += 10
        elif len(self.files) > 5000:
            score += 5
            recommendations.append("Consider reducing project size for faster deployments")

        # Collect dependencies
        if self.package_json:
            deps = list(self.package_json.get("dependencies", {}).keys())[:20]
        elif self.requirements_txt:
            deps = self.requirements_txt[:20]

        return min(100, score), issues, recommendations, entry_points, build_scripts, deps, has_lock

    # ───────────────────────────────────────────────────────────
    #  AUTO-FIX ENGINE
    # ───────────────────────────────────────────────────────────
    def _auto_fix(self, framework: FrameworkType) -> List[str]:
        """Attempt to auto-fix common deployment issues. Returns list of fixes applied."""
        fixes = []

        # Fix 1: Missing build script in package.json
        if self.package_json and "build" not in self.package_json.get("scripts", {}):
            build_cmd = {
                FrameworkType.NEXTJS: "next build",
                FrameworkType.REACT: "react-scripts build",
                FrameworkType.VUE: "vue-cli-service build",
                FrameworkType.VITE: "vite build",
            }.get(framework)
            if build_cmd:
                try:
                    pkg_path = self.project_path / "package.json"
                    if "scripts" not in self.package_json:
                        self.package_json["scripts"] = {}
                    self.package_json["scripts"]["build"] = build_cmd
                    with open(pkg_path, "w", encoding="utf-8") as f:
                        json.dump(self.package_json, f, indent=2)
                    fixes.append(f"Added missing build script: \"{build_cmd}\"")
                    logger.info(f"[AUTOFIX] Added build script: {build_cmd}")
                except Exception as e:
                    logger.warning(f"[AUTOFIX] Failed to add build script: {e}")

        # Fix 2: Missing .gitignore
        if not self._has_file(".gitignore"):
            try:
                gitignore_content = "node_modules/\n.next/\ndist/\nbuild/\n.env\n.env.local\n__pycache__/\n*.pyc\n.venv/\n"
                (self.project_path / ".gitignore").write_text(gitignore_content)
                fixes.append("Generated .gitignore file")
                logger.info("[AUTOFIX] Created .gitignore")
            except Exception as e:
                logger.warning(f"[AUTOFIX] Failed to create .gitignore: {e}")

        return fixes

    # ───────────────────────────────────────────────────────────
    #  MAIN ANALYSIS PIPELINE
    # ───────────────────────────────────────────────────────────
    def analyze(self) -> AnalysisResult:
        """Run the full analysis pipeline with timing."""
        t_start = time.time()
        logger.info(f"[ANALYZE] Starting analysis of: {self.project_path}")

        self._collect_files()
        self._load_package_json()
        self._load_requirements()

        framework = self._detect_framework()
        score, issues, recs, entries, builds, deps, has_lock = self._compute_readiness(framework)

        # Run auto-fixes
        auto_fixes = self._auto_fix(framework)
        if auto_fixes:
            # Recalculate score after fixes
            self._collect_files()
            self._load_package_json()
            score, issues, recs, entries, builds, deps, has_lock = self._compute_readiness(framework)

        # Calculate total size (limit to first 500 files to avoid hanging)
        total_size = 0
        for f in self.files[:500]:
            fp = self.project_path / f
            try:
                if fp.exists() and fp.is_file():
                    total_size += fp.stat().st_size
            except OSError:
                pass

        elapsed = time.time() - t_start
        logger.info(
            f"[ANALYZE] Complete in {elapsed:.2f}s: framework={framework.value}, "
            f"score={score}, files={len(self.files)}, size={total_size}, fixes={len(auto_fixes)}"
        )

        return AnalysisResult(
            project_path=str(self.project_path),
            framework=framework,
            readiness_score=score,
            entry_points=entries,
            dependencies=deps,
            build_scripts=builds,
            issues=issues,
            recommendations=recs,
            file_count=len(self.files),
            total_size_bytes=total_size,
            has_build_script=len(builds) > 0,
            has_entry_point=len(entries) > 0,
            has_lock_file=has_lock,
            detected_files=self.files[:50],
            auto_fixes=auto_fixes,
        )

    @staticmethod
    def extract_zip(zip_path: str, extract_to: str) -> Optional[str]:
        """
        Safely extract a ZIP archive with zip-slip protection.
        Returns the path to the extracted project root (recursively detected),
        or None if no root is found.
        """
        logger.info(f"[ZIP] Extracting {zip_path} → {extract_to}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Zip-slip protection
                target = os.path.realpath(os.path.join(extract_to, member))
                if not target.startswith(os.path.realpath(extract_to)):
                    raise ValueError(f"Zip-slip detected: {member}")
            zf.extractall(extract_to)

        # If the zip contains a single root folder, descend into it
        contents = [c for c in os.listdir(extract_to)
                     if not c.startswith(".") and c != "__MACOSX"]
        if len(contents) == 1 and os.path.isdir(os.path.join(extract_to, contents[0])):
            candidate = os.path.join(extract_to, contents[0])
            logger.info(f"[ZIP] Single root folder detected: {contents[0]}")
            # Now find the TRUE project root recursively
            return ProjectAnalyzer.find_project_root(candidate)

        # Multiple items at top level — find the root among them
        return ProjectAnalyzer.find_project_root(extract_to)
