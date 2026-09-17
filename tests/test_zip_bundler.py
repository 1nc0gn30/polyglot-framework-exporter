"""Tests for polyglot_framework_exporter.zip_bundler module."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import zipfile
import pytest

from polyglot_framework_exporter.zip_bundler import (
    ZipBundler,
    build_zip_bundle,
    create_project_zip,
    extract_zip,
    inspect_zip,
    is_likely_executable,
    normalize_zip_path,
)


class TestPathAndPermissionHelpers:
    """Test path normalization and executable permission heuristics."""

    def test_normalize_zip_path(self) -> None:
        assert normalize_zip_path("src/components/Button.tsx") == "src/components/Button.tsx"
        assert normalize_zip_path(r"src\pages\index.astro") == "src/pages/index.astro"
        assert normalize_zip_path("/var/app/README.md") == "var/app/README.md"
        assert normalize_zip_path("C:/Users/app/package.json") == "Users/app/package.json"
        assert normalize_zip_path("./relative/path.ts") == "relative/path.ts"

    def test_is_likely_executable(self) -> None:
        assert is_likely_executable("build.sh") is True
        assert is_likely_executable("deploy.bash") is True
        assert is_likely_executable("script.py") is True
        assert is_likely_executable("bin/entrypoint") is True
        assert is_likely_executable("package.json") is False
        assert is_likely_executable("script.sh", content="#!/bin/bash\necho 1") is True
        assert is_likely_executable("anyfile", content=b"#!/usr/bin/env python3") is True


class TestZipBundler:
    """Test ZipBundler core builder methods."""

    def test_add_file_string_and_bytes(self) -> None:
        bundler = ZipBundler(project_name="test-app", framework="astro")
        bundler.add_file("README.md", "# Test App")
        bundler.add_file("data.bin", b"\x01\x02\x03\x04")

        zip_bytes = bundler.build_bytes()
        assert len(zip_bytes) > 0

        # Verify ZIP contains files
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            assert "README.md" in names
            assert "data.bin" in names
            assert zf.read("README.md") == b"# Test App"
            assert zf.read("data.bin") == b"\x01\x02\x03\x04"

    def test_add_files_dict(self) -> None:
        bundler = ZipBundler(project_name="dict-app", framework="react")
        files = {
            "package.json": '{"name": "dict-app"}',
            "src/App.tsx": "export default function App() { return <h1>Hi</h1>; }",
            "public/favicon.ico": b"FAVICON_DATA",
        }
        bundler.add_files(files)
        zip_bytes = bundler.build_bytes()

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "package.json" in zf.namelist()
            assert "src/App.tsx" in zf.namelist()
            assert "public/favicon.ico" in zf.namelist()

    def test_add_manifest_and_readme(self) -> None:
        bundler = ZipBundler(project_name="meta-app", framework="sveltekit", theme="obsidian_gold")
        bundler.add_file("src/routes/+page.svelte", "<h1>Svelte</h1>")
        bundler.add_manifest({"custom_field": "val123"})
        bundler.add_readme()

        zip_bytes = bundler.build_bytes()
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            assert "project.manifest.json" in names
            assert "README.md" in names

            manifest_content = json.loads(zf.read("project.manifest.json").decode("utf-8"))
            assert manifest_content["name"] == "meta-app"
            assert manifest_content["framework"] == "sveltekit"
            assert manifest_content["theme"] == "obsidian_gold"
            assert manifest_content["custom_field"] == "val123"

    def test_deterministic_reproducible_zip(self) -> None:
        bundler1 = ZipBundler(project_name="det-app", deterministic=True)
        bundler1.add_file("index.html", "<h1>Deterministic</h1>")

        bundler2 = ZipBundler(project_name="det-app", deterministic=True)
        bundler2.add_file("index.html", "<h1>Deterministic</h1>")

        bytes1 = bundler1.build_bytes()
        bytes2 = bundler2.build_bytes()

        assert bytes1 == bytes2
        assert bundler1.calculate_sha256() == bundler2.calculate_sha256()

    def test_save_to_disk(self, temp_dir: Path) -> None:
        bundler = ZipBundler(project_name="disk-app")
        bundler.add_file("file.txt", "On disk")
        out_path = temp_dir / "output.zip"

        saved = bundler.save(out_path)
        assert saved == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_list_contents_and_manifest_summary(self) -> None:
        bundler = ZipBundler(project_name="summary-app", framework="nuxt")
        bundler.add_file("app.vue", "<template>Nuxt</template>")
        bundler.add_file("nuxt.config.ts", "export default {}")

        contents = bundler.list_contents()
        assert len(contents) == 2
        paths = [c["path"] for c in contents]
        assert "app.vue" in paths
        assert "nuxt.config.ts" in paths

        summary = bundler.get_manifest_summary()
        assert summary["project_name"] == "summary-app"
        assert summary["framework"] == "nuxt"
        assert summary["file_count"] == 2


class TestHighLevelBundlerFunctions:
    """Test build_zip_bundle, create_project_zip, inspect_zip, and extract_zip."""

    def test_build_zip_bundle_bytes(self) -> None:
        files = {
            "package.json": '{"name": "high-level"}',
            "src/index.ts": "console.log('hi');",
        }
        res_bytes = build_zip_bundle(files, project_name="high-level", framework="astro")
        assert isinstance(res_bytes, bytes)
        assert len(res_bytes) > 0

    def test_build_zip_bundle_file_path(self, temp_dir: Path) -> None:
        files = {"index.html": "<p>Hello</p>"}
        out_zip = temp_dir / "bundle.zip"
        res_path = build_zip_bundle(files, output_path=out_zip)
        assert res_path == out_zip
        assert out_zip.exists()

    def test_create_project_zip_from_directory(self, temp_dir: Path) -> None:
        src_dir = temp_dir / "sample_project"
        src_dir.mkdir()
        (src_dir / "package.json").write_text('{"name": "test"}')
        (src_dir / "src").mkdir()
        (src_dir / "src" / "index.js").write_text("console.log(1);")

        out_zip = temp_dir / "archived.zip"
        create_project_zip(src_dir, output_zip_path=out_zip, project_name="sample-app")

        assert out_zip.exists()
        inspection = inspect_zip(out_zip)
        assert inspection["file_count"] >= 2
        filenames = [e["filename"] for e in inspection["entries"]]
        assert "package.json" in filenames
        assert "src/index.js" in filenames

    def test_inspect_and_extract_zip(self, temp_dir: Path) -> None:
        files = {
            "a.txt": "File A",
            "b/c.txt": "File C in B",
        }
        zip_bytes = build_zip_bundle(files, project_name="extract-test")
        inspection = inspect_zip(zip_bytes)
        assert inspection["file_count"] >= 2
        assert "compression_ratio" in inspection

        extract_target = temp_dir / "extracted"
        extracted_paths = extract_zip(zip_bytes, extract_target)
        assert (extract_target / "a.txt").exists()
        assert (extract_target / "b" / "c.txt").exists()
        assert (extract_target / "a.txt").read_text() == "File A"
