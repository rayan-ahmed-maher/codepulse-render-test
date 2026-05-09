"""
Pre-Deploy File Cleaner — Intelligent file sanitization before deployment.

Creates a CLEAN COPY of the project folder, removing all non-deployable files.
Never modifies the user's original upload.
"""

import os
import shutil
import logging
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


# =========================================================
# REMOVAL REASONS
# =========================================================

REASON_VIDEO_TOO_LARGE = "video file exceeds platform size limit"
REASON_FILE_TOO_LARGE = "file exceeds platform size limit"
REASON_BINARY_EXEC = "binary executable — not deployable"
REASON_SYSTEM_FILE = "system metadata file — not needed for deployment"
REASON_DEV_CACHE = "build dependency/cache — not needed for deployment"
REASON_LOG_FILE = "log file — not needed for deployment"
REASON_ENV_FILE = "environment file — security risk"


# =========================================================
# FILE CATEGORIES
# =========================================================

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}
BINARY_EXTENSIONS = {".exe", ".dll", ".bat", ".sh", ".bin"}
SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini"}
LOG_EXTENSIONS = {".log"}
ENV_FILES = {".env", ".env.local", ".env.production", ".env.development", ".env.staging"}

# Directories to always remove (these are copied but then pruned)
ALWAYS_REMOVE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next/cache", ".next/dev",
    ".venv", "venv", ".cache", ".turbo",
}

# Top-level directory names to prune during copy
PRUNE_DIR_NAMES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".cache", ".turbo",
}


# =========================================================
# PLATFORM SIZE LIMITS
# =========================================================

PLATFORM_LIMITS = {
    "cloudflare": 25 * 1024 * 1024,   # 25 MB
    "vercel":     100 * 1024 * 1024,   # 100 MB
    "netlify":    100 * 1024 * 1024,   # 100 MB
    "render":     500 * 1024 * 1024,   # 500 MB (generous)
}


@dataclass
class RemovedFile:
    filename: str
    size_bytes: int
    reason: str

    @property
    def size_human(self) -> str:
        mb = self.size_bytes / (1024 * 1024)
        if mb >= 1:
            return f"{mb:.1f}MB"
        kb = self.size_bytes / 1024
        return f"{kb:.1f}KB"

    def __str__(self) -> str:
        return f"{self.filename} ({self.size_human}) — removed: {self.reason}"


@dataclass
class CleanResult:
    clean_path: str
    original_path: str
    platform: str
    removed_files: List[RemovedFile] = field(default_factory=list)
    kept_file_count: int = 0
    kept_total_bytes: int = 0
    original_file_count: int = 0
    original_total_bytes: int = 0

    @property
    def kept_size_human(self) -> str:
        mb = self.kept_total_bytes / (1024 * 1024)
        if mb >= 1:
            return f"{mb:.1f} MB"
        kb = self.kept_total_bytes / 1024
        return f"{kb:.1f} KB"

    @property
    def original_size_human(self) -> str:
        mb = self.original_total_bytes / (1024 * 1024)
        if mb >= 1:
            return f"{mb:.1f} MB"
        kb = self.original_total_bytes / 1024
        return f"{kb:.1f} KB"

    @property
    def is_empty(self) -> bool:
        return self.kept_file_count == 0

    def terminal_report(self) -> List[str]:
        """Generate terminal-formatted log lines."""
        lines = []
        lines.append(f"→ Scanning project files...")
        lines.append(
            f"→ Found {self.original_file_count} files "
            f"({self.original_size_human} total)"
        )

        if self.removed_files:
            for rf in self.removed_files:
                lines.append(f"⚠ Removed: {rf}")
            lines.append(
                f"⚠ {len(self.removed_files)} file(s) removed for clean deployment — see list above"
            )
        else:
            lines.append("✓ Project is clean — no files removed")

        lines.append(
            f"✓ Clean project ready: "
            f"{self.kept_file_count} files ({self.kept_size_human})"
        )
        lines.append(f"→ Deploying to {self.platform.title()}...")
        return lines


def _should_prune_dir(dir_name: str, rel_path: str) -> bool:
    """Check if a directory should be pruned during copy."""
    if dir_name in PRUNE_DIR_NAMES:
        return True
    # Check composite paths like .next/cache
    normalized = rel_path.replace("\\", "/")
    for pattern in ALWAYS_REMOVE_DIRS:
        if normalized == pattern or normalized.endswith(f"/{pattern}"):
            return True
    return False


def _classify_file(
    filepath: Path,
    rel_path: str,
    file_size: int,
    platform: str,
) -> Optional[str]:
    """
    Return a removal reason string if the file should be removed.
    Return None if the file should be kept.
    """
    name_lower = filepath.name.lower()
    ext_lower = filepath.suffix.lower()
    size_limit = PLATFORM_LIMITS.get(platform.lower(), 100 * 1024 * 1024)

    # 1. System files
    if name_lower in SYSTEM_FILES:
        return REASON_SYSTEM_FILE

    # 2. Environment files (security risk)
    if name_lower in ENV_FILES:
        return REASON_ENV_FILE

    # 3. Log files
    if ext_lower in LOG_EXTENSIONS:
        return REASON_LOG_FILE

    # 4. Binary executables
    if ext_lower in BINARY_EXTENSIONS:
        return REASON_BINARY_EXEC

    # 5. Video files over 25MB (always too large for web deploy)
    if ext_lower in VIDEO_EXTENSIONS and file_size > 25 * 1024 * 1024:
        return REASON_VIDEO_TOO_LARGE

    # 6. Any file exceeding platform size limit
    if file_size > size_limit:
        limit_mb = size_limit // (1024 * 1024)
        return f"exceeds {platform.title()} {limit_mb}MB limit"

    # 7. Any file over 100MB on any platform (universal safety net)
    if file_size > 100 * 1024 * 1024:
        return "exceeds 100MB universal deployment limit"

    return None


def clean_for_deploy(
    project_path: str,
    platform: str,
    work_dir: Optional[str] = None,
) -> CleanResult:
    """
    Create a sanitized COPY of the project folder for deployment.

    - Never modifies the original folder.
    - Prunes heavy directories (node_modules, .git, etc.) during copy.
    - Removes individual non-deployable files from the copy.
    - Returns a CleanResult with the path to the clean copy and a full report.
    """
    src = Path(project_path).resolve()
    platform_lower = platform.lower()

    if not src.is_dir():
        raise FileNotFoundError(f"Project directory not found: {src}")

    # ── Create a clean copy directory ──
    import time
    timestamp = int(time.time() * 1000)

    if work_dir:
        clean_dir = Path(work_dir) / f"clean_{src.name}"
    else:
        clean_dir = src.parent / f".deploy_clean_{src.name}_{timestamp}"

    # Remove any previous clean copies (pattern: .deploy_clean_{name}_*)
    for old in src.parent.glob(f".deploy_clean_{src.name}_*"):
        if old.is_dir():
            try:
                shutil.rmtree(str(old))
            except Exception:
                # OneDrive or antivirus may hold locks — ignore stale copies
                logger.warning(f"[CLEANER] Could not remove old copy: {old.name}")

    # Also remove the legacy name without timestamp (from previous code)
    legacy_clean = src.parent / f".deploy_clean_{src.name}"
    if legacy_clean.exists():
        try:
            shutil.rmtree(str(legacy_clean))
        except Exception:
            logger.warning(f"[CLEANER] Could not remove legacy copy: {legacy_clean.name}")

    # ── Phase 1: Copy with directory pruning ──
    # We use shutil.copytree with an ignore function to skip heavy dirs
    removed_dirs: List[RemovedFile] = []

    def _ignore_fn(directory: str, contents: list) -> set:
        ignored = set()
        dir_path = Path(directory)
        for item in contents:
            item_path = dir_path / item
            if item_path.is_dir():
                rel = str(item_path.relative_to(src)).replace("\\", "/")
                if _should_prune_dir(item, rel):
                    # Calculate size for reporting
                    try:
                        dir_size = sum(
                            f.stat().st_size
                            for f in item_path.rglob("*")
                            if f.is_file()
                        )
                    except Exception:
                        dir_size = 0
                    removed_dirs.append(RemovedFile(
                        filename=f"{rel}/",
                        size_bytes=dir_size,
                        reason=REASON_DEV_CACHE,
                    ))
                    ignored.add(item)
        return ignored

    shutil.copytree(str(src), str(clean_dir), ignore=_ignore_fn, dirs_exist_ok=True)

    # ── Phase 2: Scan original for total counts ──
    original_file_count = 0
    original_total_bytes = 0
    for root, dirs, files in os.walk(str(src)):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                sz = 0
            original_file_count += 1
            original_total_bytes += sz

    # ── Phase 3: Walk the copy and remove non-deployable files ──
    removed_files: List[RemovedFile] = list(removed_dirs)
    kept_count = 0
    kept_bytes = 0

    for root, dirs, files in os.walk(str(clean_dir)):
        # Also prune any nested dirs that slipped through (e.g., .next/cache)
        for d in list(dirs):
            rel = str((Path(root) / d).relative_to(clean_dir)).replace("\\", "/")
            if _should_prune_dir(d, rel):
                full = os.path.join(root, d)
                try:
                    dir_size = sum(
                        f.stat().st_size
                        for f in Path(full).rglob("*")
                        if f.is_file()
                    )
                except Exception:
                    dir_size = 0
                shutil.rmtree(full, ignore_errors=True)
                dirs.remove(d)
                removed_files.append(RemovedFile(
                    filename=f"{rel}/",
                    size_bytes=dir_size,
                    reason=REASON_DEV_CACHE,
                ))

        for fn in files:
            fp = Path(root) / fn
            rel = str(fp.relative_to(clean_dir)).replace("\\", "/")
            try:
                fsize = fp.stat().st_size
            except OSError:
                fsize = 0

            reason = _classify_file(fp, rel, fsize, platform_lower)
            if reason:
                removed_files.append(RemovedFile(
                    filename=rel,
                    size_bytes=fsize,
                    reason=reason,
                ))
                try:
                    fp.unlink()
                except OSError:
                    pass
            else:
                kept_count += 1
                kept_bytes += fsize

    result = CleanResult(
        clean_path=str(clean_dir),
        original_path=str(src),
        platform=platform_lower,
        removed_files=removed_files,
        kept_file_count=kept_count,
        kept_total_bytes=kept_bytes,
        original_file_count=original_file_count,
        original_total_bytes=original_total_bytes,
    )

    # ── Log the terminal report ──
    for line in result.terminal_report():
        logger.info(f"[CLEANER] {line}")

    return result


def cleanup_deploy_copy(clean_path: str) -> None:
    """Remove the temporary clean copy after deployment is complete."""
    try:
        if os.path.isdir(clean_path):
            shutil.rmtree(clean_path, ignore_errors=True)
            logger.info(f"[CLEANER] Removed deploy copy: {clean_path}")
    except Exception as e:
        logger.warning(f"[CLEANER] Failed to cleanup {clean_path}: {e}")
