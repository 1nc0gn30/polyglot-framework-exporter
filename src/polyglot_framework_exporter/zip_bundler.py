"""ZIP Bundler for Polyglot Framework Exporter.

Creates clean, deterministic, in-memory (io.BytesIO) and on-disk ZIP archives
containing generated framework file trees with README, manifest, and proper
file permissions.

Pure Python standard library only (zero external runtime dependencies).
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import zipfile


# Deterministic timestamp for reproducible builds (2026-01-01 00:00:00 UTC)
DETERMINISTIC_DATETIME: Tuple[int, int, int, int, int, int] = (2026, 1, 1, 0, 0, 0)
DETERMINISTIC_TIME_TUPLE = time.struct_time(
    (2026, 1, 1, 0, 0, 0, 3, 1, 0)
)

# File extension heuristics for executable scripts
EXECUTABLE_EXTENSIONS = {".sh", ".bash", ".command", ".py", ".rb", ".pl"}
EXECUTABLE_NAMES = {"entrypoint", "build.sh", "run.sh", "start.sh", "deploy.sh"}


def normalize_zip_path(path: Union[str, Path, PurePosixPath]) -> str:
    """Normalize file path to a forward-slash separated relative POSIX path.

    Strips leading slashes, dots, and Windows drive prefixes.
    """
    raw = str(path).replace("\\", "/")
    # Remove drive letter if present (e.g., C:/)
    if len(raw) > 1 and raw[1] == ":":
        raw = raw[2:]
    parts = [p for p in raw.split("/") if p and p != "." and p != ".."]
    return "/".join(parts)


def is_likely_executable(filename: str, content: Union[str, bytes] = b"") -> bool:
    """Determine if a file should have POSIX executable permissions (0755)."""
    norm_name = os.path.basename(filename.lower())
    _, ext = os.path.splitext(norm_name)
    if ext in EXECUTABLE_EXTENSIONS or norm_name in EXECUTABLE_NAMES:
        return True
    if norm_name.startswith("bin/"):
        return True
    # Check for shebang in content
    if isinstance(content, str) and content.startswith("#!"):
        return True
    if isinstance(content, bytes) and content.startswith(b"#!"):
        return True
    return False


class ZipBundler:
    """Builder for clean, reproducible ZIP archives of generated projects.

    Supports both in-memory and on-disk generation with automatic manifest
    generation, file hashing, permission mapping, and deterministic timestamps.
    """

    def __init__(
        self,
        project_name: str = "exported-project",
        framework: str = "generic",
        theme: str = "system",
        description: str = "",
        deterministic: bool = True,
    ) -> None:
        self.project_name = project_name
        self.framework = framework
        self.theme = theme
        self.description = description
        self.deterministic = deterministic
        self._files: Dict[str, Tuple[bytes, bool]] = {}  # path -> (content_bytes, is_executable)
        self._metadata: Dict[str, Any] = {
            "name": project_name,
            "framework": framework,
            "theme": theme,
            "description": description,
            "generator": "polyglot-framework-exporter",
            "version": "0.1.0",
        }

    def add_file(
        self,
        path: Union[str, Path],
        content: Union[str, bytes],
        is_executable: Optional[bool] = None,
    ) -> "ZipBundler":
        """Add a single file to the archive."""
        norm_path = normalize_zip_path(path)
        if not norm_path:
            raise ValueError(f"Invalid path for zip archive: {path!r}")

        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        elif isinstance(content, bytes):
            content_bytes = content
        else:
            content_bytes = str(content).encode("utf-8")

        if is_executable is None:
            is_exec = is_likely_executable(norm_path, content_bytes)
        else:
            is_exec = bool(is_executable)

        self._files[norm_path] = (content_bytes, is_exec)
        return self

    def add_files(
        self,
        file_tree: Dict[str, Union[str, bytes, Path]],
        prefix: str = "",
    ) -> "ZipBundler":
        """Add a dictionary of file paths to contents."""
        for raw_path, content in file_tree.items():
            if prefix:
                full_path = f"{prefix.rstrip('/')}/{raw_path.lstrip('/')}"
            else:
                full_path = raw_path

            if isinstance(content, Path) and content.is_file():
                self.add_file(full_path, content.read_bytes())
            else:
                self.add_file(full_path, content)  # type: ignore[arg-type]
        return self

    def add_directory(
        self,
        dir_path: Union[str, Path],
        target_prefix: str = "",
        exclude_patterns: Optional[List[str]] = None,
    ) -> "ZipBundler":
        """Add all files from an on-disk directory recursively."""
        base_dir = Path(dir_path)
        if not base_dir.exists() or not base_dir.is_dir():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        excludes = set(exclude_patterns or [".git", "__pycache__", ".DS_Store", "node_modules", ".venv"])

        for root, dirs, files in os.walk(base_dir):
            # Filter out ignored directories in-place
            dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]

            for file in sorted(files):
                if file in excludes or file.startswith("."):
                    continue
                file_full_path = Path(root) / file
                rel_path = file_full_path.relative_to(base_dir)
                if target_prefix:
                    archive_path = f"{target_prefix.rstrip('/')}/{rel_path.as_posix()}"
                else:
                    archive_path = rel_path.as_posix()

                try:
                    content = file_full_path.read_bytes()
                    # Check on-disk executable bit on POSIX
                    is_exec = os.access(file_full_path, os.X_OK) or is_likely_executable(archive_path, content)
                    self.add_file(archive_path, content, is_executable=is_exec)
                except (IOError, OSError) as e:
                    # Skip unreadable files gracefully
                    continue
        return self

    def add_manifest(
        self,
        extra_metadata: Optional[Dict[str, Any]] = None,
        filename: str = "project.manifest.json",
    ) -> "ZipBundler":
        """Generate and insert a rich project manifest JSON file."""
        meta = dict(self._metadata)
        if extra_metadata:
            meta.update(extra_metadata)

        manifest_data = self._generate_manifest_dict(meta)
        manifest_json = json.dumps(manifest_data, indent=2, sort_keys=True) + "\n"
        self.add_file(filename, manifest_json)
        return self

    def add_readme(
        self,
        content: Optional[str] = None,
        filename: str = "README.md",
    ) -> "ZipBundler":
        """Add a README markdown file. If none provided, generates a clean default."""
        if content is None:
            content = self._generate_default_readme()
        self.add_file(filename, content)
        return self

    def _generate_default_readme(self) -> str:
        """Generate a well-formatted README for the exported project."""
        lines = [
            f"# {self.project_name}",
            "",
            f"> Generated with **Polyglot Framework Exporter**",
            "",
            f"- **Target Framework:** `{self.framework}`",
            f"- **Theme:** `{self.theme}`",
            f"- **Generated At:** `{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            "",
            "## Getting Started",
            "",
            "### Prerequisites",
            "- Node.js >= 18.0.0 (or Bun / pnpm / yarn depending on your toolchain)",
            "",
            "### Installation",
            "```bash",
            "# Install dependencies",
            "npm install",
            "",
            "# Start local development server",
            "npm run dev",
            "```",
            "",
            "### Production Build",
            "```bash",
            "npm run build",
            "npm run preview",
            "```",
            "",
            "## Project Structure",
            "```text",
        ]

        # Add top 20 files to the readme tree
        sorted_paths = sorted(self._files.keys())
        for path in sorted_paths[:25]:
            lines.append(f"  ├── {path}")
        if len(sorted_paths) > 25:
            lines.append(f"  └── ... ({len(sorted_paths) - 25} more files)")

        lines.extend([
            "```",
            "",
            "---",
            "Generated by Polyglot Studio (design influenced by Material 3).",
        ])
        return "\n".join(lines) + "\n"

    def _generate_manifest_dict(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Build dictionary for project.manifest.json."""
        file_list: List[Dict[str, Any]] = []
        total_bytes = 0

        for path in sorted(self._files.keys()):
            data, is_exec = self._files[path]
            file_size = len(data)
            total_bytes += file_size
            sha256_hash = hashlib.sha256(data).hexdigest()
            file_list.append({
                "path": path,
                "size_bytes": file_size,
                "sha256": sha256_hash,
                "is_executable": is_exec,
            })

        manifest = {
            **meta,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat() if not self.deterministic else "2026-01-01T00:00:00Z",
            "deterministic_build": self.deterministic,
            "total_files": len(self._files),
            "total_size_bytes": total_bytes,
            "files": file_list,
        }
        return manifest

    def build_bytes(self) -> bytes:
        """Construct the ZIP archive in memory and return bytes."""
        bio = io.BytesIO()
        dt_tuple = DETERMINISTIC_DATETIME if self.deterministic else time.localtime()[:6]

        with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            # Sort files for deterministic archive order
            for path in sorted(self._files.keys()):
                content, is_exec = self._files[path]

                zinfo = zipfile.ZipInfo(filename=path, date_time=dt_tuple)
                zinfo.compress_type = zipfile.ZIP_DEFLATED

                # External attributes (POSIX permissions)
                # Upper 16 bits = POSIX mode, Lower bits = MS-DOS FAT flags
                if is_exec:
                    posix_mode = stat.S_IFREG | 0o755  # -rwxr-xr-x
                else:
                    posix_mode = stat.S_IFREG | 0o644  # -rw-r--r--
                zinfo.external_attr = (posix_mode << 16) | (0 if not is_exec else 0x20)

                # Set create system to Unix (3) for proper permission preservation
                zinfo.create_system = 3

                zf.writestr(zinfo, content)

        bio.seek(0)
        return bio.getvalue()

    def to_bytes(self) -> bytes:
        """Alias for build_bytes()."""
        return self.build_bytes()

    def to_bytes_io(self) -> io.BytesIO:
        """Return BytesIO stream containing the ZIP archive."""
        return io.BytesIO(self.build_bytes())

    def save(self, output_path: Union[str, Path]) -> Path:
        """Write the ZIP archive to disk."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        zip_bytes = self.build_bytes()
        target.write_bytes(zip_bytes)
        return target

    def calculate_sha256(self) -> str:
        """Calculate SHA-256 hash of the generated ZIP bytes."""
        return hashlib.sha256(self.build_bytes()).hexdigest()

    def list_contents(self) -> List[Dict[str, Any]]:
        """Return list of files with their details."""
        result = []
        for path in sorted(self._files.keys()):
            data, is_exec = self._files[path]
            result.append({
                "path": path,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "executable": is_exec,
            })
        return result

    def get_manifest_summary(self) -> Dict[str, Any]:
        """Return summary dictionary for diagnostics and UI responses."""
        total_size = sum(len(d) for d, _ in self._files.values())
        return {
            "project_name": self.project_name,
            "framework": self.framework,
            "theme": self.theme,
            "file_count": len(self._files),
            "total_bytes": total_size,
            "files": sorted(self._files.keys()),
        }


def build_zip_bundle(
    file_tree: Dict[str, Union[str, bytes]],
    project_name: str = "exported-project",
    manifest: Optional[Dict[str, Any]] = None,
    readme: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    framework: str = "generic",
    theme: str = "system",
    deterministic: bool = True,
) -> Union[bytes, Path]:
    """High-level helper to bundle a file tree into a ZIP archive.

    If output_path is specified, writes to disk and returns Path.
    Otherwise, returns bytes.
    """
    bundler = ZipBundler(
        project_name=project_name,
        framework=framework,
        theme=theme,
        deterministic=deterministic,
    )
    bundler.add_files(file_tree)  # type: ignore[arg-type]

    # Automatically add manifest if requested or provided
    if manifest is not None or "project.manifest.json" not in file_tree:
        bundler.add_manifest(manifest)

    # Automatically add README if not present in file_tree
    if "README.md" not in file_tree:
        bundler.add_readme(readme)

    if output_path is not None:
        return bundler.save(output_path)
    return bundler.to_bytes()


def create_project_zip(
    project_dir: Union[str, Path],
    output_zip_path: Optional[Union[str, Path]] = None,
    project_name: Optional[str] = None,
    framework: str = "auto",
    theme: str = "system",
    deterministic: bool = True,
) -> Union[bytes, Path]:
    """Create a ZIP bundle directly from an existing directory on disk."""
    base_dir = Path(project_dir)
    name = project_name or base_dir.name
    bundler = ZipBundler(
        project_name=name,
        framework=framework,
        theme=theme,
        deterministic=deterministic,
    )
    bundler.add_directory(base_dir)
    bundler.add_manifest({"source_directory": str(base_dir.resolve())})

    if output_zip_path is not None:
        return bundler.save(output_zip_path)
    return bundler.to_bytes()


def inspect_zip(zip_data: Union[bytes, str, Path]) -> Dict[str, Any]:
    """Inspect a ZIP file (from bytes or path) and return detailed structural metadata."""
    if isinstance(zip_data, (str, Path)):
        bio: io.BytesIO = io.BytesIO(Path(zip_data).read_bytes())
    else:
        bio = io.BytesIO(zip_data)

    entries = []
    total_uncompressed = 0
    total_compressed = 0

    with zipfile.ZipFile(bio, "r") as zf:
        for info in zf.infolist():
            total_uncompressed += info.file_size
            total_compressed += info.compress_size
            entries.append({
                "filename": info.filename,
                "file_size": info.file_size,
                "compress_size": info.compress_size,
                "date_time": f"{info.date_time[0]:04d}-{info.date_time[1]:02d}-{info.date_time[2]:02d} {info.date_time[3]:02d}:{info.date_time[4]:02d}:{info.date_time[5]:02d}",
                "is_dir": info.is_dir(),
                "external_attr": hex(info.external_attr),
                "crc": info.CRC,
            })

    return {
        "file_count": len(entries),
        "total_uncompressed_bytes": total_uncompressed,
        "total_compressed_bytes": total_compressed,
        "compression_ratio": round((1 - (total_compressed / total_uncompressed)) * 100, 2) if total_uncompressed > 0 else 0.0,
        "entries": entries,
    }


def extract_zip(
    zip_data: Union[bytes, str, Path],
    target_dir: Union[str, Path],
    overwrite: bool = True,
) -> List[str]:
    """Safely extract a ZIP archive into the target directory, preventing ZipSlip attacks."""
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if isinstance(zip_data, (str, Path)):
        bio: io.BytesIO = io.BytesIO(Path(zip_data).read_bytes())
    else:
        bio = io.BytesIO(zip_data)

    extracted_files: List[str] = []

    with zipfile.ZipFile(bio, "r") as zf:
        for member in zf.infolist():
            # Security: ZipSlip protection
            member_path = target_path / member.filename
            resolved_member_path = member_path.resolve()
            if not str(resolved_member_path).startswith(str(target_path)):
                raise RuntimeError(f"Security exception: ZipSlip attempted with member {member.filename}")

            if member.is_dir():
                resolved_member_path.mkdir(parents=True, exist_ok=True)
                continue

            resolved_member_path.parent.mkdir(parents=True, exist_ok=True)

            if resolved_member_path.exists() and not overwrite:
                continue

            with zf.open(member) as source, open(resolved_member_path, "wb") as dest:
                dest.write(source.read())

            # Restore POSIX executable permissions if present in external_attr
            mode = member.external_attr >> 16
            if mode & 0o111:
                try:
                    os.chmod(resolved_member_path, 0o755)
                except OSError:
                    pass

            extracted_files.append(str(resolved_member_path))

    return extracted_files
