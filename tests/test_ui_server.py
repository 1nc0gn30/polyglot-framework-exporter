"""Tests for polyglot_framework_exporter.ui_server module and REST API endpoints."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import pytest

from polyglot_framework_exporter.ui_server import (
    find_available_port,
    find_public_directory,
    get_supported_frameworks_list,
)


class TestServerHelpers:
    """Test helper functions in ui_server."""

    def test_find_public_directory(self) -> None:
        pub = find_public_directory()
        assert pub is not None
        assert (pub / "index.html").exists()

    def test_get_supported_frameworks_list(self) -> None:
        frameworks = get_supported_frameworks_list()
        assert len(frameworks) >= 9
        ids = [f["id"] for f in frameworks]
        assert "astro" in ids
        assert "nextjs" in ids
        assert "vite_react" in ids

    def test_find_available_port(self) -> None:
        port = find_available_port("127.0.0.1", preferred_port=8888)
        assert isinstance(port, int)
        assert port > 1024


class TestLiveUIServerAPIs:
    """Test live HTTP server endpoints using the live_ui_server fixture."""

    def test_get_root_serves_html(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            content_type = resp.headers.get("Content-Type", "")
            assert "text/html" in content_type
            body = resp.read().decode("utf-8")
            assert "Google Framework Studio" in body or "Polyglot" in body

    def test_api_health(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/health"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"
            assert "uptime_seconds" in data
            assert data["frameworks_count"] >= 9

    def test_api_frameworks(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/frameworks"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert "frameworks" in data
            assert len(data["frameworks"]) >= 9

    def test_api_diagnostics(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/diagnostics"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "server_uptime_seconds" in data
            assert "active_threads" in data

    def test_api_export_post(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/export"
        payload = {
            "framework": "astro",
            "project_name": "test-live-astro",
            "title": "Test Live Astro App",
            "theme": "material_light",
            "features": ["tailwind", "typescript"]
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert data["framework"] == "astro"
            assert "files" in data
            assert "package.json" in data["files"]

    def test_api_convert_post(self, live_ui_server: str, sample_html: str) -> None:
        url = f"{live_ui_server}/api/convert"
        payload = {
            "source_framework": "html",
            "target_framework": "react",
            "code": sample_html,
            "component_name": "LiveHero"
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert "target_code" in data
            assert len(data["target_code"]) > 0

    def test_api_download_zip_get(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/download-zip?framework=astro&project_name=my-test-zip"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            content_type = resp.headers.get("Content-Type", "")
            assert "application/zip" in content_type

            raw_zip = resp.read()
            assert len(raw_zip) > 0

            # Verify it's a valid ZIP archive
            with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
                names = zf.namelist()
                assert "package.json" in names

    def test_api_download_zip_post(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/download-zip"
        payload = {
            "framework": "nextjs",
            "project_name": "post-zip-app",
            "theme": "obsidian_gold"
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            raw_zip = resp.read()
            with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
                assert len(zf.namelist()) > 0

    def test_api_cors_options(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/export"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 204
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_api_404_not_found(self, live_ui_server: str) -> None:
        url = f"{live_ui_server}/api/non_existent_endpoint"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404
