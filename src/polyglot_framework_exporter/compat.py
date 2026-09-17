"""Cross-platform compatibility utilities for polyglot-framework-exporter.

Provides robust, cross-platform helpers for atomic writes, path normalization,
safe subpath validation (anti-traversal), filename sanitization, and encoding-safe
file reading/writing across Linux, macOS, Windows, Termux, and WSL environments.
"""

from __future__ import annotations

import io
import os
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence, Tuple, Union

# Platform detection flags
_SYS_PLATFORM = sys.platform.lower()
_IS_WINDOWS = _SYS_PLATFORM.startswith("win") or _SYS_PLATFORM == "cygwin"
_IS_MACOS = _SYS_PLATFORM == "darwin"
_IS_LINUX = _SYS_PLATFORM.startswith("linux")
_IS_TERMUX = "TERMUX_VERSION" in os.environ or "com.termux" in os.environ.get("PREFIX", "")
_IS_WSL = "microsoft-standard" in platform.release().lower() if hasattr(platform, "release") else False

# Reserved filenames on Windows/DOS
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Invalid characters in Windows filenames
_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_windows() -> bool:
    """Return True if running on Windows or Cygwin."""
    return _IS_WINDOWS


def is_macos() -> bool:
    """Return True if running on macOS (Darwin)."""
    return _IS_MACOS


def is_linux() -> bool:
    """Return True if running on Linux (including WSL and Termux)."""
    return _IS_LINUX


def is_termux() -> bool:
    """Return True if running inside Termux on Android."""
    return _IS_TERMUX


def is_wsl() -> bool:
    """Return True if running inside Windows Subsystem for Linux (WSL)."""
    return _IS_WSL


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path to an absolute, resolved Path object.
    
    Handles tilde expansion (~), cross-platform path separators, and relative paths.
    """
    p = Path(path).expanduser()
    try:
        return p.resolve()
    except (OSError, RuntimeError):
        return p.absolute()


def sanitize_filename(name: str, max_length: int = 255, replacement: str = "_") -> str:
    """Sanitize a filename component, making it safe across Linux, macOS, and Windows.
    
    - Replaces invalid characters (<>:"/\\|?* and control characters)
    - Strips leading and trailing dots and spaces
    - Avoids Windows reserved device names (CON, NUL, COM1, etc.)
    - Truncates to max_length bytes
    """
    if not name:
        return "unnamed"
    
    # Strip illegal characters
    cleaned = _INVALID_FILENAME_CHARS_RE.sub(replacement, name)
    cleaned = cleaned.strip(". ")
    
    if not cleaned:
        cleaned = "unnamed"
    
    # Check for reserved Windows filenames (e.g., CON.txt, NUL.json)
    base_stem = cleaned.split(".")[0].upper()
    if base_stem in _WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    
    # Limit length
    if len(cleaned.encode("utf-8", "replace")) > max_length:
        stem, ext = os.path.splitext(cleaned)
        max_stem_len = max(1, max_length - len(ext.encode("utf-8", "replace")) - 1)
        cleaned = stem[:max_stem_len] + ext
        
    return cleaned


def is_safe_subpath(target_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """Check whether target_path is safely contained within base_dir.
    
    Prevents path traversal attacks (e.g., '../../etc/passwd').
    """
    try:
        norm_base = normalize_path(base_dir)
        norm_target = normalize_path(target_path)
        
        # Check if norm_target is identical or a child of norm_base
        norm_target.relative_to(norm_base)
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def safe_join(base_dir: Union[str, Path], *paths: str) -> Path:
    """Safely join path components to base_dir, preventing directory traversal.
    
    Raises:
        ValueError: If any component attempts to traverse outside of base_dir.
    """
    norm_base = normalize_path(base_dir)
    joined = norm_base
    
    for segment in paths:
        # Strip leading slashes to prevent absolute path overriding
        clean_segment = str(segment).lstrip("/\\")
        # Check for traversal attempts
        parts = Path(clean_segment).parts
        for part in parts:
            if part in ("..",):
                raise ValueError(f"Path traversal detected in segment: {segment!r}")
            joined = joined / part
            
    norm_joined = normalize_path(joined)
    if not is_safe_subpath(norm_joined, norm_base):
        raise ValueError(f"Target path {norm_joined} escapes base directory {norm_base}")
        
    return norm_joined


def safe_relpath(path: Union[str, Path], start: Union[str, Path] = ".") -> str:
    """Return a relative filepath using forward slashes regardless of OS."""
    try:
        rel = os.path.relpath(path, start)
        return rel.replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """Ensure a directory exists, creating parents if necessary.
    
    Returns the resolved Path of the directory.
    """
    p = normalize_path(path)
    p.mkdir(parents=True, exist_ok=True, mode=mode)
    return p


def atomic_write_text(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    errors: str = "replace",
    mode: int = 0o644,
) -> Path:
    """Atomically write text content to file_path.
    
    Writes to a temporary file in the same directory and renames it atomically.
    Ensures parent directories exist.
    """
    target = normalize_path(file_path)
    parent = target.parent
    ensure_directory(parent)
    
    # Create temp file in target's directory to ensure same filesystem for os.replace
    prefix = f".tmp_{target.name}_"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            errors=errors,
            dir=str(parent),
            prefix=prefix,
            delete=False,
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            
        # Apply permissions if on POSIX
        if not is_windows():
            try:
                os.chmod(tmp_path, mode)
            except OSError:
                pass
                
        # Atomic replace
        os.replace(tmp_path, target)
        return target
    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def atomic_write_bytes(
    file_path: Union[str, Path],
    data: bytes,
    mode: int = 0o644,
) -> Path:
    """Atomically write binary data to file_path."""
    target = normalize_path(file_path)
    parent = target.parent
    ensure_directory(parent)
    
    prefix = f".tmp_{target.name}_"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(parent),
            prefix=prefix,
            delete=False,
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(data)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            
        if not is_windows():
            try:
                os.chmod(tmp_path, mode)
            except OSError:
                pass
                
        os.replace(tmp_path, target)
        return target
    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def read_text_safely(
    file_path: Union[str, Path],
    default: str = "",
    encodings: Sequence[str] = ("utf-8", "utf-8-sig", "latin-1", "cp1252"),
) -> str:
    """Read text from file_path, trying multiple encodings before falling back to default.
    
    Handles BOM and legacy codepages gracefully without crashing.
    """
    path = normalize_path(file_path)
    if not path.is_file():
        return default
        
    raw_bytes = None
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read()
    except OSError:
        return default
        
    for enc in encodings:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
            
    # Final fallback with replacement characters
    return raw_bytes.decode("utf-8", errors="replace")


def read_bytes_safely(file_path: Union[str, Path], default: bytes = b"") -> bytes:
    """Read bytes from file_path, returning default on error."""
    path = normalize_path(file_path)
    if not path.is_file():
        return default
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return default


def safe_copy_file(src: Union[str, Path], dst: Union[str, Path]) -> Path:
    """Copy a file safely to dst, ensuring destination directory exists."""
    src_path = normalize_path(src)
    dst_path = normalize_path(dst)
    
    if not src_path.is_file():
        raise FileNotFoundError(f"Source file not found: {src_path}")
        
    ensure_directory(dst_path.parent)
    shutil.copy2(src_path, dst_path)
    return dst_path


def safe_remove(path: Union[str, Path]) -> bool:
    """Safely remove a file or directory tree if it exists."""
    p = normalize_path(path)
    if not p.exists():
        return True
    try:
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        return True
    except OSError:
        return False
