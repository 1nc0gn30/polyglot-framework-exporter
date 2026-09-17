"""Tests for polyglot_framework_exporter.compat cross-platform utilities."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest

from polyglot_framework_exporter.compat import (
    atomic_write_bytes,
    atomic_write_text,
    ensure_directory,
    is_linux,
    is_macos,
    is_safe_subpath,
    is_termux,
    is_windows,
    is_wsl,
    normalize_path,
    read_bytes_safely,
    read_text_safely,
    safe_copy_file,
    safe_join,
    safe_relpath,
    safe_remove,
    sanitize_filename,
)


class TestPlatformDetection:
    """Test OS detection flags."""

    def test_boolean_flags(self) -> None:
        assert isinstance(is_windows(), bool)
        assert isinstance(is_macos(), bool)
        assert isinstance(is_linux(), bool)
        assert isinstance(is_termux(), bool)
        assert isinstance(is_wsl(), bool)


class TestPathNormalizationAndSanitization:
    """Test path normalization and filename sanitization."""

    def test_normalize_path(self, temp_dir: Path) -> None:
        p = normalize_path(str(temp_dir))
        assert isinstance(p, Path)
        assert p.is_absolute()

    def test_sanitize_filename_standard(self) -> None:
        assert sanitize_filename("valid_name-123.txt") == "valid_name-123.txt"
        assert sanitize_filename("my project.zip") == "my project.zip"

    def test_sanitize_filename_illegal_chars(self) -> None:
        assert sanitize_filename('bad:name*with?illegal<chars>.txt') == "bad_name_with_illegal_chars_.txt"
        assert sanitize_filename('foo/bar\\baz') == "foo_bar_baz"

    def test_sanitize_filename_windows_reserved(self) -> None:
        assert sanitize_filename("CON.txt") == "_CON.txt"
        assert sanitize_filename("NUL.json") == "_NUL.json"
        assert sanitize_filename("aux") == "_aux"
        assert sanitize_filename("COM1.log") == "_COM1.log"

    def test_sanitize_filename_empty_or_whitespace(self) -> None:
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ...   ") == "unnamed"

    def test_sanitize_filename_length_truncation(self) -> None:
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name, max_length=100)
        assert len(sanitized.encode("utf-8")) <= 100
        assert sanitized.endswith(".txt")


class TestSafePathOperations:
    """Test safe path validation and joining."""

    def test_is_safe_subpath_valid(self, temp_dir: Path) -> None:
        sub = temp_dir / "subdir" / "file.txt"
        assert is_safe_subpath(sub, temp_dir) is True

    def test_is_safe_subpath_traversal(self, temp_dir: Path) -> None:
        outside = temp_dir.parent / "escape.txt"
        assert is_safe_subpath(outside, temp_dir) is False

    def test_safe_join_valid(self, temp_dir: Path) -> None:
        joined = safe_join(temp_dir, "subdir", "deep", "file.json")
        assert joined == temp_dir / "subdir" / "deep" / "file.json"

    def test_safe_join_traversal_error(self, temp_dir: Path) -> None:
        with pytest.raises(ValueError):
            safe_join(temp_dir, "subdir", "..", "..", "escape.txt")

    def test_safe_relpath(self, temp_dir: Path) -> None:
        sub = temp_dir / "a" / "b" / "c.txt"
        rel = safe_relpath(sub, start=temp_dir)
        assert "\\" not in rel
        assert rel == "a/b/c.txt"


class TestFileIOOperations:
    """Test atomic read/write and file manipulation."""

    def test_ensure_directory(self, temp_dir: Path) -> None:
        target = temp_dir / "nested" / "dir" / "level"
        ensured = ensure_directory(target)
        assert ensured.exists()
        assert ensured.is_dir()

    def test_atomic_write_and_read_text(self, temp_dir: Path) -> None:
        file_path = temp_dir / "atomic.txt"
        content = "Hello, Polyglot Exporter!\nLine 2 with UTF-8: 🚀"
        written = atomic_write_text(file_path, content)
        assert written == file_path
        assert file_path.exists()

        read_content = read_text_safely(file_path)
        assert read_content == content

    def test_atomic_write_and_read_bytes(self, temp_dir: Path) -> None:
        file_path = temp_dir / "data.bin"
        data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        written = atomic_write_bytes(file_path, data)
        assert written == file_path
        assert file_path.exists()

        read_data = read_bytes_safely(file_path)
        assert read_data == data

    def test_read_nonexistent_file_default(self, temp_dir: Path) -> None:
        non_existent = temp_dir / "missing.txt"
        assert read_text_safely(non_existent, default="fallback") == "fallback"
        assert read_bytes_safely(non_existent, default=b"fallback_bin") == b"fallback_bin"

    def test_safe_copy_and_remove(self, temp_dir: Path) -> None:
        src = temp_dir / "orig.txt"
        atomic_write_text(src, "Original text")

        dst = temp_dir / "copied" / "dest.txt"
        copied = safe_copy_file(src, dst)
        assert copied.exists()
        assert read_text_safely(copied) == "Original text"

        assert safe_remove(dst) is True
        assert not dst.exists()
        assert safe_remove(temp_dir / "copied") is True
