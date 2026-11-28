"""Loopback Host guard, security headers, body-cap, and numeric-validation
regression tests for the Polyglot Studio server (audit #072)."""

from __future__ import annotations

import http.client
import json

import pytest

from polyglot_framework_exporter.ui_server import _is_trusted_host


def _raw(port: int, method: str, path: str, host: str, body=None, extra_headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Host": host, "Connection": "close"}
    if extra_headers:
        headers.update(extra_headers)
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, {k.lower(): v for k, v in resp.getheaders()}, data


def _port_of(base_url: str) -> int:
    return int(base_url.rstrip("/").rsplit(":", 1)[1])


def test_trusted_hosts():
    for h in ("127.0.0.1", "127.0.0.1:8126", "localhost", "localhost:3000", "[::1]:8126"):
        assert _is_trusted_host(h), h
    for h in ("", "evil.example.invalid", "127.0.0.1.evil.com", "example.com", "192.168.1.5"):
        assert not _is_trusted_host(h), h


def test_evil_host_rejected(live_ui_server: str):
    port = _port_of(live_ui_server)
    status, _, _ = _raw(port, "GET", "/api/health", "evil.example.invalid")
    assert status == 403
    status, _, _ = _raw(
        port, "POST", "/api/export", "evil.example.invalid",
        body=b"{}", extra_headers={"Content-Type": "application/json"},
    )
    assert status == 403


def test_security_headers_and_banner(live_ui_server: str):
    import urllib.request
    with urllib.request.urlopen(f"{live_ui_server}/api/health", timeout=5) as resp:
        assert resp.status == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "strict-origin" in (resp.headers.get("Referrer-Policy") or "")
        csp = resp.headers.get("Content-Security-Policy") or ""
        assert "frame-ancestors" in csp
        assert "http://127.0.0.1:3000" in csp
        assert resp.headers.get("Server", "").startswith("Polyglot")
        assert "Python" not in resp.headers.get("Server", "")


def test_body_cap_enforced(live_ui_server: str):
    port = _port_of(live_ui_server)
    big = b"x" * (1_048_576 + 8)
    status, _, _ = _raw(
        port, "POST", "/api/export", "127.0.0.1",
        body=big, extra_headers={"Content-Type": "application/json"},
    )
    assert status == 413


def test_traversal_rooted(live_ui_server: str):
    port = _port_of(live_ui_server)
    status, _, body = _raw(port, "GET", "/%2e%2e/%2e%2e/etc/hostname", "127.0.0.1")
    assert status in (200, 403, 404)
    assert b"root:" not in body
