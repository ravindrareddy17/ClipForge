"""
Path security and file access validation.
Enforces strict file extension checks, path normalization, safe directory sandboxing,
system path protection, symlink resolution, and file size limits.
"""

import os
from pathlib import Path
from typing import List, Optional, Set, Union

ALLOWED_EXTENSIONS: Set[str] = {".json", ".srt", ".vtt", ".txt"}
DEFAULT_MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB

BLOCKED_SYSTEM_PREFIXES = [
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\system32",
    "/etc",
    "/var",
    "/proc",
    "/sys",
    "/dev",
    "/boot",
    "/root"
]


class SecurityError(ValueError):
    """Raised when a file path violates security sandboxing or extension rules."""
    pass


def is_safe_subpath(path: Path, parent: Path) -> bool:
    """Checks whether path is within parent directory after resolving symlinks."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_and_read_transcript_file(
    file_source: Union[str, Path],
    allowed_directories: Optional[List[Union[str, Path]]] = None,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
) -> str:
    """
    Validates and reads a transcript file strictly within authorized boundaries.
    """
    raw_str = str(file_source).strip()

    # If multi-line, JSON array/object, or formatted string, treat as inline content
    if "\n" in raw_str or raw_str.startswith("{") or raw_str.startswith("[") or "-->" in raw_str:
        return raw_str

    path_obj = Path(file_source)

    # Extension check
    ext = path_obj.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise SecurityError(
            f"Invalid file extension '{ext}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Resolve strict path and symlinks
    try:
        real_path = path_obj.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"Transcript file not found: {path_obj}")

    if not real_path.is_file():
        raise SecurityError(f"Path is not a regular file: {real_path}")

    # Check against known system directories
    norm_path_str = str(real_path).lower()
    for blocked in BLOCKED_SYSTEM_PREFIXES:
        if norm_path_str.startswith(blocked):
            raise SecurityError(f"Access to protected system directory denied: {real_path}")

    # Determine safe directories
    safe_dirs: List[Path] = []
    if allowed_directories:
        for d in allowed_directories:
            safe_dirs.append(Path(d).resolve())
    else:
        # Default sandboxes: current working directory & skill directory
        safe_dirs.append(Path.cwd().resolve())
        safe_dirs.append(Path(__file__).resolve().parent.parent)

    # Verify path is inside at least one safe directory
    within_safe = any(is_safe_subpath(real_path, sd) for sd in safe_dirs)
    if not within_safe:
        raise SecurityError(
            f"Path traversal rejected: '{real_path}' is outside authorized directories."
        )

    # Check file size limit
    file_size = real_path.stat().st_size
    if file_size > max_size_bytes:
        raise SecurityError(
            f"File size {file_size:,} bytes exceeds limit of {max_size_bytes:,} bytes (25 MB)."
        )

    return real_path.read_text(encoding="utf-8")
