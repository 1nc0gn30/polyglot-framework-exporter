#!/usr/bin/env python3
"""Google Framework Studio UI Server for Polyglot Framework Exporter.

Zero-dependency, multi-threaded HTTP server providing Google Material 3 Web UI
and REST API endpoints for scaffolding, AST component transpilation, in-memory ZIP
streaming, diagnostics, and MCP configuration.

Pure Python standard library only (http.server.ThreadingHTTPServer).
"""

from __future__ import annotations

import argparse
import html
import io
import json
import logging
import mimetypes
import os
from pathlib import Path
import platform
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple, Union

# Internal package imports with graceful fallbacks
try:
    from .compat import is_safe_subpath, normalize_path, sanitize_filename
except ImportError:
    def is_safe_subpath(target_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
        try:
            p_base = Path(base_dir).resolve()
            p_target = Path(target_path).resolve()
            p_target.relative_to(p_base)
            return True
        except Exception:
            return False

    def sanitize_filename(name: str, max_length: int = 255, replacement: str = "_") -> str:
        import re
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', replacement, name).strip(". ")
        return cleaned or "unnamed"

    def normalize_path(path: Union[str, Path]) -> Path:
        return Path(path).resolve()

try:
    from .zip_bundler import ZipBundler, build_zip_bundle
except ImportError:
    import zipfile
    class ZipBundler:  # type: ignore[no-redef]
        def __init__(self, project_name="app", framework="generic", theme="system", description=""):
            self.project_name = project_name
            self.framework = framework
            self.theme = theme
            self.description = description
            self._files = {}
        def add_file(self, path, content):
            if isinstance(content, str):
                content = content.encode("utf-8")
            self._files[str(path)] = content
            return self
        def add_files(self, file_map):
            for p, c in file_map.items():
                self.add_file(p, c)
            return self
        def build_bytes(self) -> bytes:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for p, c in self._files.items():
                    zf.writestr(p, c)
            return buf.getvalue()

try:
    from .mcp_server import (
        FRAMEWORK_CATALOG,
        THEME_PRESETS,
        HTMLTranspiler,
        generate_project_scaffold,
        get_system_diagnostics,
    )
except ImportError:
    FRAMEWORK_CATALOG = {
        "astro": {"id": "astro", "name": "Astro 5", "category": "static", "default_port": 4321, "description": "Islands architecture & zero-JS SSG."},
        "nextjs": {"id": "nextjs", "name": "Next.js 15", "category": "meta", "default_port": 3000, "description": "React Server Components & App Router."},
        "react": {"id": "react", "name": "Vite React 19", "category": "spa", "default_port": 5173, "description": "Ultra-fast modern SPA bundle."},
        "svelte": {"id": "svelte", "name": "SvelteKit 2", "category": "spa", "default_port": 5173, "description": "Compiler-driven runes reactivity."},
        "vue": {"id": "vue", "name": "Nuxt 3", "category": "meta", "default_port": 3000, "description": "Intuitive Vue 3 & Nitro universal SSR."},
        "fresh": {"id": "fresh", "name": "Deno Fresh 2", "category": "meta", "default_port": 8000, "description": "Zero-build JIT islands & edge native."},
        "remix": {"id": "remix", "name": "Remix / RRv7", "category": "meta", "default_port": 3000, "description": "Web standards & nested loaders."},
        "tauri": {"id": "tauri", "name": "Tauri v2", "category": "desktop", "default_port": "Desktop", "description": "Native desktop shell with Rust."},
        "electron": {"id": "electron", "name": "Electron 30+", "category": "desktop", "default_port": "Desktop", "description": "Chromium + Node.js cross-platform shell."}
    }
    THEME_PRESETS = {"system": {"name": "Material 3 Light", "primary": "#1a73e8"}}
    HTMLTranspiler = None  # type: ignore[assignment, misc]
    def generate_project_scaffold(framework: str, project_name: str, **kwargs) -> Dict[str, str]:
        return {
            "README.md": f"# {project_name}\n\nExported for {framework}.",
            "package.json": json.dumps({"name": project_name, "version": "0.1.0"}, indent=2)
        }
    def get_system_diagnostics(verbose: bool = False) -> Dict[str, Any]:
        return {"platform": platform.platform(), "python": sys.version}

logger = logging.getLogger("polyglot_framework_exporter.ui_server")
SERVER_START_TIME = time.time()


# ==============================================================================
# Fallback Embedded Studio HTML (used if public/index.html is not found)
# ==============================================================================

FALLBACK_EMBEDDED_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="material-light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Google Framework Studio • Standalone</title>
  <style>
    :root {
      --bg: #f8f9fa; --surface: #ffffff; --primary: #1a73e8; --text: #202124; --text-muted: #5f6368;
      --border: #dadce0; --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    body { background: var(--bg); color: var(--text); font-family: var(--font); margin: 0; padding: 2rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; max-width: 900px; margin: 0 auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { color: var(--primary); font-size: 1.75rem; margin-bottom: 0.5rem; }
    p { color: var(--text-muted); line-height: 1.6; }
    .actions { margin-top: 1.5rem; display: flex; gap: 1rem; }
    button, a.btn { background: var(--primary); color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; text-decoration: none; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
    pre { background: #f1f3f4; padding: 1rem; border-radius: 8px; overflow-x: auto; margin-top: 1rem; font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Google Framework Studio</h1>
    <p>Polyglot Multi-Framework Exporter UI Server is running. All REST APIs are online and active.</p>
    <div class="actions">
      <a class="btn" href="/api/health" target="_blank">Health Status</a>
      <a class="btn" href="/api/frameworks" target="_blank">Frameworks Catalog</a>
      <a class="btn" href="/api/download-zip?framework=astro&project_name=my-app" target="_blank">Download Sample Astro ZIP</a>
    </div>
    <pre id="api-output">Checking /api/health...</pre>
  </div>
  <script>
    fetch('/api/health').then(r => r.json()).then(d => {
      document.getElementById('api-output').textContent = JSON.stringify(d, null, 2);
    }).catch(e => {
      document.getElementById('api-output').textContent = 'Error fetching health: ' + e;
    });
  </script>
</body>
</html>
"""


# ==============================================================================
# Helper Utilities & Static File Resolution
# ==============================================================================

def find_public_directory() -> Optional[Path]:
    """Locate the public/ directory containing web assets."""
    cwd_public = Path.cwd() / "public"
    if cwd_public.is_dir() and (cwd_public / "index.html").is_file():
        return cwd_public

    pkg_dir = Path(__file__).resolve().parent
    repo_public = pkg_dir.parent.parent / "public"
    if repo_public.is_dir() and (repo_public / "index.html").is_file():
        return repo_public

    internal_public = pkg_dir / "public"
    if internal_public.is_dir() and (internal_public / "index.html").is_file():
        return internal_public

    return None


def get_supported_frameworks_list() -> List[Dict[str, Any]]:
    """Return normalized list of supported frameworks."""
    frameworks = []
    
    defaults = [
        {"id": "astro", "name": "Astro 5", "tagline": "Island Architecture & Zero-JS SSG", "category": "static", "default_port": 4321, "icon": "🚀", "color": "#ff5d01", "tags": ["Islands", "SSR/SSG", "Tailwind"]},
        {"id": "nextjs", "name": "Next.js 15", "tagline": "React Server Components & App Router", "category": "meta", "default_port": 3000, "icon": "▲", "color": "#000000", "tags": ["App Router", "Turbopack", "Server Actions"]},
        {"id": "vite_react", "name": "Vite React 19", "tagline": "Ultra-Fast Modern SPA Bundle", "category": "spa", "default_port": 5173, "icon": "⚛️", "color": "#61dafb", "tags": ["Vite 6", "React 19", "Tailwind"]},
        {"id": "sveltekit", "name": "SvelteKit 2", "tagline": "Compiler-Driven Runes Reactivity", "category": "spa", "default_port": 5173, "icon": "⚡", "color": "#ff3e00", "tags": ["Svelte 5", "Runes", "Edge-Ready"]},
        {"id": "nuxt", "name": "Nuxt 3", "tagline": "Intuitive Vue 3 & Nitro Universal SSR", "category": "meta", "default_port": 3000, "icon": "💚", "color": "#00dc82", "tags": ["Vue 3", "Nitro", "Auto-Imports"]},
        {"id": "deno_fresh", "name": "Deno Fresh 2", "tagline": "Zero-Build JIT Islands & Edge Native", "category": "meta", "default_port": 8000, "icon": "🍋", "color": "#ffd600", "tags": ["Deno", "TypeScript", "Edge"]},
        {"id": "remix", "name": "Remix / RRv7", "tagline": "Web Standards & Nested Loaders", "category": "meta", "default_port": 3000, "icon": "💿", "color": "#e11d48", "tags": ["Loaders", "Optimistic UI", "Vite"]},
        {"id": "tauri", "name": "Tauri v2", "tagline": "Tiny Native Desktop Binary with Rust", "category": "desktop", "default_port": "Desktop", "icon": "🦀", "color": "#24c8db", "tags": ["Desktop", "Rust", "Vite React"]},
        {"id": "electron", "name": "Electron 30+", "tagline": "Chromium + Node.js Cross-Platform", "category": "desktop", "default_port": "Desktop", "icon": "⚡", "color": "#47848f", "tags": ["Desktop", "Node IPC", "Multi-Window"]},
    ]

    for item in defaults:
        cat_info = FRAMEWORK_CATALOG.get(item["id"], {}) or FRAMEWORK_CATALOG.get(item["id"].replace("_", ""), {})
        merged = dict(item)
        if cat_info:
            merged["version"] = cat_info.get("version", "latest")
            merged["description"] = cat_info.get("description", item["tagline"])
            if "styling" in cat_info:
                merged["styling"] = cat_info["styling"]
        frameworks.append(merged)

    return frameworks


# ==============================================================================
# HTTP Request Handler & REST API Router
# ==============================================================================

class StudioHTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP handler serving Google Framework Studio UI and REST APIs."""

    server_version = "PolyglotStudioServer/0.1.0"

    def log_message(self, format: str, *args: Any) -> None:
        """Custom logger writing to Python logging rather than raw stderr."""
        logger.debug(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")

    def send_cors_headers(self) -> None:
        """Add standard CORS headers for local and cross-origin access."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def send_json_response(self, data: Any, status: int = 200) -> None:
        """Send JSON response with UTF-8 encoding and CORS headers."""
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message: str, status: int = 400, details: Optional[Dict[str, Any]] = None) -> None:
        """Send formatted JSON error response."""
        err_body = {
            "success": False,
            "error": message,
            "status_code": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if details:
            err_body["details"] = details
        self.send_json_response(err_body, status=status)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests to API handlers or static file server."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/health":
            self.handle_api_health()
        elif path == "/api/frameworks":
            self.handle_api_frameworks()
        elif path == "/api/diagnostics":
            self.handle_api_diagnostics()
        elif path == "/api/download-zip":
            self.handle_api_download_zip_get(query)
        elif path.startswith("/api/"):
            self.send_error_json(f"API endpoint not found: {path}", status=404)
        else:
            self.serve_static_file(parsed_url.path)

    def do_POST(self) -> None:
        """Route POST requests to API handlers."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/") or "/"

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body_json = json.loads(post_body.decode("utf-8")) if post_body else {}
        except json.JSONDecodeError as err:
            self.send_error_json(f"Invalid JSON payload: {err}", status=400)
            return

        if path == "/api/export":
            self.handle_api_export(body_json)
        elif path in ("/api/convert", "/api/transpile"):
            self.handle_api_convert(body_json)
        elif path == "/api/download-zip":
            self.handle_api_download_zip_post(body_json)
        else:
            self.send_error_json(f"Unknown POST endpoint: {path}", status=404)

    # --------------------------------------------------------------------------
    # API Handlers
    # --------------------------------------------------------------------------

    def handle_api_health(self) -> None:
        """GET /api/health - returns server uptime, version, and status."""
        uptime = round(time.time() - SERVER_START_TIME, 2)
        health_data = {
            "status": "ok",
            "version": "0.1.0",
            "service": "Google Framework Studio & Polyglot Exporter",
            "uptime_seconds": uptime,
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "frameworks_count": len(get_supported_frameworks_list()),
            "themes_count": len(THEME_PRESETS),
        }
        self.send_json_response(health_data)

    def handle_api_frameworks(self) -> None:
        """GET /api/frameworks - returns catalog of supported frameworks."""
        frameworks = get_supported_frameworks_list()
        self.send_json_response({
            "success": True,
            "count": len(frameworks),
            "frameworks": frameworks,
            "themes": list(THEME_PRESETS.keys()),
        })

    def handle_api_diagnostics(self) -> None:
        """GET /api/diagnostics - system diagnostics and runtime stats."""
        try:
            diag = get_system_diagnostics(verbose=True)
        except Exception as err:
            diag = {"diagnostics_error": str(err)}

        uptime = round(time.time() - SERVER_START_TIME, 2)
        diag["server_uptime_seconds"] = uptime
        diag["active_threads"] = threading.active_count()
        diag["public_dir"] = str(find_public_directory())
        self.send_json_response(diag)

    def handle_api_export(self, payload: Dict[str, Any]) -> None:
        """POST /api/export - exports project files dictionary for chosen framework."""
        framework = payload.get("framework", "astro")
        project_name = sanitize_filename(payload.get("project_name", "polyglot-app"))
        title = payload.get("title", "Polyglot Framework App")
        description = payload.get("description", "Scaffolded with Polyglot Framework Exporter")
        theme = payload.get("theme", "light")
        features = payload.get("features", ["tailwind", "typescript"])

        try:
            files = generate_project_scaffold(
                framework=framework,
                project_name=project_name,
                theme=theme,
                options={"title": title, "description": description, "features": features},
            )
            file_count = len(files)
            total_bytes = sum(len(c.encode("utf-8") if isinstance(c, str) else c) for c in files.values())

            self.send_json_response({
                "success": True,
                "framework": framework,
                "project_name": project_name,
                "file_count": file_count,
                "total_bytes": total_bytes,
                "files": files,
                "instructions": f"cd {project_name} && npm install && npm run dev",
            })
        except Exception as err:
            logger.exception("Error in /api/export")
            self.send_error_json(f"Export failed: {err}", status=500)

    def handle_api_convert(self, payload: Dict[str, Any]) -> None:
        """POST /api/convert or /api/transpile - converts component code across frameworks."""
        source_fw = payload.get("source_framework", "react")
        target_fw = payload.get("target_framework", "astro")
        code = payload.get("code", "")
        component_name = payload.get("component_name", "ConvertedComponent")

        if not code:
            self.send_error_json("Missing 'code' parameter in conversion payload.", status=400)
            return

        try:
            if HTMLTranspiler:
                result = HTMLTranspiler.transpile(
                    html_code=code,
                    framework=target_fw,
                    component_name=component_name,
                    options={"theme": "system", "typescript": True}
                )
                target_code = result.get("code", "")
                self.send_json_response({
                    "success": True,
                    "source_framework": source_fw,
                    "target_framework": target_fw,
                    "component_name": component_name,
                    "target_code": target_code,
                    "ast_summary": result.get("stats", {}),
                })
            else:
                target_code = f"// Transpiled to {target_fw}\n{code}"
                self.send_json_response({
                    "success": True,
                    "source_framework": source_fw,
                    "target_framework": target_fw,
                    "component_name": component_name,
                    "target_code": target_code,
                })
        except Exception as err:
            logger.exception("Error in /api/convert")
            self.send_error_json(f"Transpilation failed: {err}", status=500)

    def handle_api_download_zip_get(self, query: Dict[str, List[str]]) -> None:
        """GET /api/download-zip?framework=astro&project_name=my-app..."""
        fw = query.get("framework", ["astro"])[0]
        name = query.get("project_name", ["polyglot-app"])[0]
        title = query.get("title", ["Polyglot App"])[0]
        theme = query.get("theme", ["light"])[0]

        payload = {
            "framework": fw,
            "project_name": name,
            "title": title,
            "theme": theme,
        }
        self.stream_zip_bundle(payload)

    def handle_api_download_zip_post(self, payload: Dict[str, Any]) -> None:
        """POST /api/download-zip - generates and streams ZIP archive."""
        self.stream_zip_bundle(payload)

    def stream_zip_bundle(self, payload: Dict[str, Any]) -> None:
        """Generate project files and stream in-memory binary ZIP archive."""
        fw = payload.get("framework", "astro")
        name = sanitize_filename(payload.get("project_name", "polyglot-app"))
        title = payload.get("title", f"{name.replace('-', ' ').title()}")
        description = payload.get("description", "Polyglot generated application")
        theme = payload.get("theme", "light")
        features = payload.get("features", ["tailwind", "typescript", "mcp"])

        try:
            files = generate_project_scaffold(
                framework=fw,
                project_name=name,
                theme=theme,
                options={"title": title, "description": description, "features": features},
            )

            bundler = ZipBundler(project_name=name, framework=fw, theme=theme, description=description)
            bundler.add_files(files)
            zip_bytes = bundler.build_bytes()

            filename = f"{name}-{fw}.zip"

            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(zip_bytes)
        except Exception as err:
            logger.exception("Failed to generate zip bundle")
            self.send_error_json(f"ZIP Bundle generation failed: {err}", status=500)

    # --------------------------------------------------------------------------
    # Static File Serving
    # --------------------------------------------------------------------------

    def serve_static_file(self, raw_path: str) -> None:
        """Serve files from public/ with security checks and embedded fallback."""
        clean_path = raw_path.lstrip("/")
        if not clean_path or clean_path == "index.html":
            clean_path = "index.html"

        public_dir = find_public_directory()

        if public_dir:
            file_path = public_dir / clean_path
            if is_safe_subpath(file_path, public_dir) and file_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(file_path))
                mime_type = mime_type or "application/octet-stream"

                try:
                    data = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if mime_type.startswith("text/") else mime_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except OSError as err:
                    logger.warning(f"Error reading {file_path}: {err}")

        # Fallback for index.html if public/ isn't found
        if clean_path in ("", "index.html", "/"):
            data = FALLBACK_EMBEDDED_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error_json(f"File not found: {raw_path}", status=404)


# ==============================================================================
# Server Lifecycle & Port Binding
# ==============================================================================

def find_available_port(host: str = "127.0.0.1", preferred_port: int = 8080, max_tries: int = 20) -> int:
    """Find an available TCP port starting from preferred_port."""
    for port in range(preferred_port, preferred_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    return preferred_port


def create_ui_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    handler_class: Any = StudioHTTPRequestHandler,
) -> ThreadingHTTPServer:
    """Instantiate a ThreadingHTTPServer configured for Google Framework Studio."""
    actual_port = find_available_port(host, port)
    server = ThreadingHTTPServer((host, actual_port), handler_class)
    server.daemon_threads = True
    return server


def run_ui_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = False,
) -> None:
    """Start the UI Server loop and optionally open the browser."""
    server = create_ui_server(host, port)
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}/"

    print("=" * 70)
    print("  🚀 Google Framework Studio & Polyglot Exporter UI Server")
    print(f"  🌐 Studio UI: {url}")
    print(f"  ⚡ REST API:  {url}api/health")
    print("  📦 Zero Runtime Dependencies (Pure Python stdlib)")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 70)

    if open_browser:
        threading.Thread(
            target=lambda: (time.sleep(0.5), webbrowser.open(url)),
            daemon=True
        ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Google Framework Studio UI server...")
    finally:
        server.server_close()


# ==============================================================================
# CLI Entrypoint for Standalone Execution
# ==============================================================================

def main() -> int:
    """CLI entrypoint for running the studio UI server directly."""
    parser = argparse.ArgumentParser(
        description="Google Framework Studio Web UI Server for Polyglot Exporter"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--open", "-o", action="store_true", help="Automatically open browser on launch")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    run_ui_server(host=args.host, port=args.port, open_browser=args.open)
    return 0


if __name__ == "__main__":
    sys.exit(main())
