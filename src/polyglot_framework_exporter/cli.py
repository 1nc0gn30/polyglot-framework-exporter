"""Command Line Interface (CLI) for Polyglot Framework Exporter.

Provides interactive and scriptable subcommands for project generation,
HTML conversion, framework catalog inspection, Web Studio server,
MCP server execution, and platform diagnostics.

Pure Python standard library only (zero external runtime dependencies).
"""

from __future__ import annotations

import argparse
import base64
import http.server
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socketserver
import sys
import time
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional, Tuple, Union

# Internal package imports
from .mcp_server import (
    FRAMEWORK_CATALOG,
    THEME_PRESETS,
    HTMLTranspiler,
    MCPServer,
    generate_project_scaffold,
    get_system_diagnostics,
    run_mcp_server,
    validate_project_scaffold,
)
from .zip_bundler import (
    ZipBundler,
    build_zip_bundle,
    create_project_zip,
    extract_zip,
    inspect_zip,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# ANSI Color & Terminal Styling (Graceful No-Color Fallback)
# ---------------------------------------------------------------------------

class TermColor:
    """ANSI color formatter with auto-detection for TTY and NO_COLOR."""

    def __init__(self, force_disable: bool = False) -> None:
        self.enabled = not force_disable and self._should_enable_color()

    @staticmethod
    def _should_enable_color() -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") == "dumb":
            return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def color(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def bold(self, text: str) -> str:
        return self.color("1", text)

    def dim(self, text: str) -> str:
        return self.color("2", text)

    def cyan(self, text: str) -> str:
        return self.color("36", text)

    def blue(self, text: str) -> str:
        return self.color("34", text)

    def green(self, text: str) -> str:
        return self.color("32", text)

    def yellow(self, text: str) -> str:
        return self.color("33", text)

    def red(self, text: str) -> str:
        return self.color("31", text)

    def magenta(self, text: str) -> str:
        return self.color("35", text)

    def badge(self, label: str, color_fn: str = "cyan") -> str:
        fn = getattr(self, color_fn, self.cyan)
        return self.bold(f"[{fn(label)}]")


# Global color instance
tc = TermColor()


def print_banner() -> None:
    """Print the Material 3 Polyglot Exporter banner."""
    banner = r"""
  ____        _             _       _     _____                            _   
 |  _ \  ___ | |_   _  __ _| | ___ | |_  | ____|_  ___ __   ___  _ __| |_ 
 | |_) |/ _ \| | | | |/ _` | |/ _ \| __| |  _| \ \/ / '_ \ / _ \| '__| __|
 |  __/| (_) | | |_| | (_| | | (_) | |_  | |___ >  <| |_) | (_) | |  | |_ 
 |_|    \___/|_|\__, |\__, |_|\___/ \__| |_____/_/\_\ .__/ \___/|_|   \__|
                |___/ |___/                          |_|                   
"""
    print(tc.cyan(banner))
    print(tc.bold(f"  Google Material 3 Polyglot Framework Exporter v{__version__}"))
    print(tc.dim("  Export production apps to React, Vue, Svelte, Solid, Angular, Flutter, SwiftUI & more\n"))


# ---------------------------------------------------------------------------
# Embedded Studio HTML UI (Default Fallback Web Studio)
# ---------------------------------------------------------------------------

EMBEDDED_STUDIO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Material 3 Polyglot Framework Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Google Sans"', 'Roboto', 'sans-serif'],
            mono: ['"Roboto Mono"', 'monospace']
          },
          colors: {
            m3: {
              primary: '#006495',
              surface: '#f8f9fa',
              background: '#fbfcfe',
              container: '#cbe6ff'
            }
          }
        }
      }
    }
  </script>
  <style>
    body { font-family: 'Google Sans', sans-serif; }
    pre, code { font-family: 'Roboto Mono', monospace; }
  </style>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen">
  <!-- Header -->
  <header class="border-b border-zinc-800 bg-zinc-900/60 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">M3</div>
        <div>
          <h1 class="font-bold text-base tracking-tight">Polyglot Framework Studio</h1>
          <p class="text-xs text-zinc-400">Google Material Design 3 Multi-Target Exporter</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span id="health-badge" class="px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/50 flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Engine Active v0.1.0
        </span>
      </div>
    </div>
  </header>

  <!-- Main Grid -->
  <main class="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
    <!-- Controls Column -->
    <div class="lg:col-span-4 space-y-6">
      <div class="bg-zinc-900/90 rounded-3xl p-6 border border-zinc-800 space-y-5">
        <h2 class="text-lg font-bold flex items-center gap-2 text-zinc-200">
          <span>Target Configuration</span>
        </h2>

        <div>
          <label class="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Target Framework</label>
          <select id="framework-select" class="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500">
            <option value="react">React 19 (TypeScript + Vite + Tailwind)</option>
            <option value="vue">Vue 3.5 (Composition API + Script Setup)</option>
            <option value="svelte">Svelte 5 (Runes Reactivity)</option>
            <option value="solid">SolidJS (Fine-grained JSX)</option>
            <option value="angular">Angular 18 (Standalone + Signals)</option>
            <option value="astro">Astro 4 (Islands Architecture)</option>
            <option value="qwik">Qwik (Resumable Components)</option>
            <option value="vanilla">Vanilla Modern ES / Web Components</option>
            <option value="flutter">Flutter 3.24 (Dart + Material 3)</option>
            <option value="swiftui">SwiftUI 5 / 6 (Apple Native)</option>
            <option value="compose">Jetpack Compose (Android Kotlin)</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Material 3 Color Theme</label>
          <select id="theme-select" class="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500">
            <option value="system">System Dynamic Blue</option>
            <option value="light">Clean Light</option>
            <option value="dark">Cyber Dark</option>
            <option value="ocean">Pacific Ocean</option>
            <option value="emerald">Emerald Growth</option>
            <option value="crimson">Crimson Velvet</option>
            <option value="amber">Amber Sunset</option>
            <option value="purple">Royal Purple</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">Project Name</label>
          <input id="project-name" type="text" value="my-m3-app" class="w-full bg-zinc-800 border border-zinc-700 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 font-mono" />
        </div>

        <div class="pt-2 flex flex-col gap-3">
          <button id="btn-generate" onclick="generateProject()" class="w-full py-3.5 bg-blue-600 hover:bg-blue-500 active:scale-[0.99] text-white font-medium rounded-2xl transition shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2">
            Generate Project Tree
          </button>
          <button id="btn-download-zip" onclick="downloadZip()" class="w-full py-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium rounded-2xl transition border border-zinc-700 flex items-center justify-center gap-2">
            Download Clean ZIP
          </button>
        </div>
      </div>

      <!-- Quick Convert Card -->
      <div class="bg-zinc-900/90 rounded-3xl p-6 border border-zinc-800 space-y-4">
        <h3 class="text-base font-bold text-zinc-200">HTML Component Transpiler</h3>
        <p class="text-xs text-zinc-400 leading-relaxed">Paste arbitrary HTML or Tailwind markup below to transpile into framework-specific component code on the fly.</p>
        <button onclick="transpileHTML()" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-xl text-sm transition">
          Transpile Code
        </button>
      </div>
    </div>

    <!-- Output & Code Preview Column -->
    <div class="lg:col-span-8 space-y-6">
      <div class="bg-zinc-900/90 rounded-3xl border border-zinc-800 overflow-hidden flex flex-col h-[700px]">
        <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/40">
          <div class="flex items-center gap-3">
            <span id="preview-tab-label" class="text-xs font-semibold uppercase tracking-wider text-blue-400">File Preview</span>
            <span id="active-filename" class="text-xs font-mono text-zinc-400">src/App.tsx</span>
          </div>
          <button onclick="copyCode()" class="px-3 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl transition border border-zinc-700">
            Copy Code
          </button>
        </div>

        <div class="flex-1 flex overflow-hidden">
          <!-- File Explorer Sidebar -->
          <div id="file-tree-sidebar" class="w-64 border-r border-zinc-800 p-3 overflow-y-auto font-mono text-xs space-y-1 bg-zinc-950/20">
            <div class="text-zinc-500 px-3 py-2 uppercase text-[10px] tracking-wider font-semibold">Project Tree</div>
            <div id="file-list" class="space-y-1">
              <div class="px-3 py-2 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20 cursor-pointer">src/App.tsx</div>
              <div class="px-3 py-2 rounded-xl text-zinc-400 hover:bg-zinc-800/50 cursor-pointer">package.json</div>
              <div class="px-3 py-2 rounded-xl text-zinc-400 hover:bg-zinc-800/50 cursor-pointer">vite.config.ts</div>
            </div>
          </div>

          <!-- Code View Area -->
          <div class="flex-1 p-6 overflow-auto bg-zinc-950/60">
            <pre><code id="code-output" class="text-xs text-zinc-300 leading-relaxed font-mono">Click "Generate Project Tree" to preview full framework scaffold.</code></pre>
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let currentProjectFiles = {};

    async function generateProject() {
      const fw = document.getElementById('framework-select').value;
      const theme = document.getElementById('theme-select').value;
      const name = document.getElementById('project-name').value || 'my-m3-app';

      try {
        const res = await fetch('/api/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ framework: fw, theme: theme, project_name: name })
        });
        const data = await res.json();
        currentProjectFiles = data.files || {};
        renderFileTree();
      } catch (err) {
        alert('Failed to generate project: ' + err);
      }
    }

    function renderFileTree() {
      const listEl = document.getElementById('file-list');
      listEl.innerHTML = '';
      const filenames = Object.keys(currentProjectFiles).sort();
      
      filenames.forEach((fn, idx) => {
        const item = document.createElement('div');
        item.className = 'px-3 py-2 rounded-xl cursor-pointer text-xs transition ' + (idx === 0 ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' : 'text-zinc-400 hover:bg-zinc-800/50');
        item.textContent = fn;
        item.onclick = () => showFile(fn);
        listEl.appendChild(item);
      });

      if (filenames.length > 0) {
        showFile(filenames[0]);
      }
    }

    function showFile(fn) {
      document.getElementById('active-filename').textContent = fn;
      document.getElementById('code-output').textContent = currentProjectFiles[fn] || '';
    }

    function downloadZip() {
      const fw = document.getElementById('framework-select').value;
      const theme = document.getElementById('theme-select').value;
      const name = document.getElementById('project-name').value || 'my-m3-app';
      window.location.href = `/api/export/zip?framework=${fw}&theme=${theme}&name=${name}`;
    }

    async function transpileHTML() {
      const htmlSnippet = prompt('Paste HTML or Tailwind snippet to convert:', '<div class="p-6 bg-surface rounded-3xl"><h1 class="text-xl font-bold">Hello M3</h1></div>');
      if (!htmlSnippet) return;

      const fw = document.getElementById('framework-select').value;
      const res = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html_code: htmlSnippet, target_framework: fw, component_name: 'CustomCard' })
      });
      const data = await res.json();
      currentProjectFiles = { [data.filename || 'Converted.tsx']: data.code };
      renderFileTree();
    }

    function copyCode() {
      const text = document.getElementById('code-output').textContent;
      navigator.clipboard.writeText(text);
      alert('Code copied to clipboard!');
    }

    // Initial trigger
    window.addEventListener('load', () => generateProject());
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Framework Studio HTTP Server & API Dispatcher
# ---------------------------------------------------------------------------

class FrameworkStudioHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler serving static web files and REST API endpoints."""

    def __init__(self, *args: Any, directory: Optional[str] = None, **kwargs: Any) -> None:
        self.public_dir = Path(directory) if directory else Path("public")
        super().__init__(*args, directory=str(self.public_dir) if self.public_dir.exists() else None, **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API: Frameworks Catalog
        if path == "/api/frameworks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(FRAMEWORK_CATALOG, indent=2).encode("utf-8"))
            return

        # API: Themes Catalog
        if path == "/api/themes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(THEME_PRESETS, indent=2).encode("utf-8"))
            return

        # API: System Diagnostics
        if path == "/api/diagnostics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_system_diagnostics(verbose=True), indent=2).encode("utf-8"))
            return

        # API: Download ZIP bundle
        if path == "/api/export/zip":
            fw = query.get("framework", ["react"])[0]
            theme = query.get("theme", ["system"])[0]
            name = query.get("name", ["my-app"])[0]

            files = generate_project_scaffold(framework=fw, project_name=name, theme=theme)
            zip_bytes = build_zip_bundle(
                file_tree=files,  # type: ignore[arg-type]
                project_name=name,
                framework=fw,
                theme=theme,
                deterministic=True,
            )

            zip_data = zip_bytes if isinstance(zip_bytes, bytes) else zip_bytes.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{name}.zip"')
            self.send_header("Content-Length", str(len(zip_data)))
            self.end_headers()
            self.wfile.write(zip_data)
            return

        # Serve static public files if public/index.html exists, else fallback to embedded UI
        if path in ("/", "/index.html") and (not self.public_dir.exists() or not (self.public_dir / "index.html").exists()):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(EMBEDDED_STUDIO_HTML.encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")
        try:
            req_data = json.loads(post_body) if post_body else {}
        except json.JSONDecodeError:
            req_data = {}

        # API: Generate Export
        if path == "/api/export":
            fw = req_data.get("framework", "react")
            theme = req_data.get("theme", "system")
            name = req_data.get("project_name", "my-app")
            options = req_data.get("options", {})

            files = generate_project_scaffold(framework=fw, project_name=name, theme=theme, options=options)
            resp = {
                "project_name": name,
                "framework": fw,
                "theme": theme,
                "file_count": len(files),
                "files": files,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp, indent=2).encode("utf-8"))
            return

        # API: Convert HTML
        if path == "/api/convert":
            html_code = req_data.get("html_code", "")
            target_fw = req_data.get("target_framework", "react")
            comp_name = req_data.get("component_name", "ConvertedComponent")
            options = req_data.get("options", {})

            result = HTMLTranspiler.transpile(
                html_code=html_code,
                framework=target_fw,
                component_name=comp_name,
                options=options,
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_studio_server(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = False) -> None:
    """Launch the Web Studio HTTP Server."""
    try:
        from .ui_server import run_studio_server as _run_ui_server  # type: ignore
        _run_ui_server(host=host, port=port, open_browser=open_browser)
        return
    except (ImportError, AttributeError):
        pass

    handler_factory = lambda *args, **kwargs: FrameworkStudioHandler(*args, directory="public", **kwargs)  # noqa: E731
    socketserver.TCPServer.allow_reuse_address = True

    try:
        with socketserver.TCPServer((host, port), handler_factory) as httpd:
            url = f"http://{host}:{port}"
            print(f"{tc.badge('STUDIO', 'green')} Google Material 3 Framework Studio running at: {tc.bold(url)}")
            print(f"{tc.dim('Press Ctrl+C to stop the server.')}\n")

            if open_browser:
                try:
                    webbrowser.open(url)
                except Exception:
                    pass

            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{tc.badge('STOP', 'yellow')} Studio server stopped.")


# ---------------------------------------------------------------------------
# Self-Verification Test Runner
# ---------------------------------------------------------------------------

def run_self_verification_tests(verbose: bool = False) -> bool:
    """Run internal test suite verifying all framework generators, bundler, and MCP."""
    print(f"\n{tc.bold('Running Polyglot Framework Exporter Internal Verification Tests...')}\n")

    total_tests = 0
    passed_tests = 0

    def test(name: str, fn: Any) -> None:
        nonlocal total_tests, passed_tests
        total_tests += 1
        try:
            fn()
            passed_tests += 1
            print(f"  {tc.green('✔ PASS')} {name}")
        except Exception as e:
            print(f"  {tc.red('✖ FAIL')} {name}: {tc.yellow(str(e))}")
            if verbose:
                traceback.print_exc()

    # Test 1: Supported frameworks catalog
    def t_catalog() -> None:
        assert len(FRAMEWORK_CATALOG) >= 10, "Expected at least 10 supported frameworks"
        assert "react" in FRAMEWORK_CATALOG
        assert "vue" in FRAMEWORK_CATALOG
        assert "flutter" in FRAMEWORK_CATALOG

    test("Framework Catalog Completeness", t_catalog)

    # Test 2: Scaffold Generation for all frameworks
    for fw in ("react", "vue", "svelte", "solid", "angular", "vanilla", "flutter"):
        def t_scaffold(f_target=fw) -> None:
            files = generate_project_scaffold(f_target, project_name="test-app", theme="system")
            assert len(files) >= 3, f"Framework {f_target} produced fewer than 3 files"
            assert "project.manifest.json" in files

        test(f"Scaffold Generation: {fw.capitalize()}", t_scaffold)

    # Test 3: HTML Transpiler to JSX & Vue
    def t_transpile() -> None:
        sample_html = '<div class="card" onclick="alert(1)"><img src="pic.jpg"><p style="color: red">Hi</p></div>'
        react_res = HTMLTranspiler.transpile(sample_html, "react", "CustomCard")
        assert "className=\"card\"" in react_res["code"]
        assert "<img src=\"pic.jpg\" />" in react_res["code"]
        assert "onClick=" in react_res["code"]
        assert "style={{ color: 'red' }}" in react_res["code"]

        vue_res = HTMLTranspiler.transpile(sample_html, "vue", "VueCard")
        assert "<template>" in vue_res["code"]
        assert "<script setup" in vue_res["code"]

    test("HTML to Component Transpiler", t_transpile)

    # Test 4: Deterministic ZIP Bundler
    def t_zip_bundler() -> None:
        sample_files = {
            "README.md": "# Test App",
            "src/index.ts": "console.log('hello');",
            "bin/run.sh": "#!/bin/bash\necho 'running'",
        }
        b1 = build_zip_bundle(sample_files, project_name="test-app", deterministic=True)  # type: ignore[arg-type]
        b2 = build_zip_bundle(sample_files, project_name="test-app", deterministic=True)  # type: ignore[arg-type]
        assert isinstance(b1, bytes) and isinstance(b2, bytes)
        assert b1 == b2, "Deterministic ZIP must generate byte-for-byte identical output"

        info = inspect_zip(b1)
        assert info["file_count"] >= 3
        assert info["total_uncompressed_bytes"] > 0

    test("Deterministic ZIP Bundling & Inspection", t_zip_bundler)

    # Test 5: Project Scaffold Validator
    def t_validator() -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            files = generate_project_scaffold("react", project_name="val-test")
            for rel, c in files.items():
                dest = tmppath / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(c)

            val_res = validate_project_scaffold(tmpdir, "react")
            assert val_res["valid"] is True
            assert val_res["score"] >= 80

    test("Project Scaffold Validator", t_validator)

    # Test 6: MCP Server JSON-RPC Interface
    def t_mcp() -> None:
        server = MCPServer()
        # Initialize
        init_res = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init_res is not None
        assert init_res["result"]["serverInfo"]["name"] == "polyglot-framework-exporter"

        # Tools list
        tools_res = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert tools_res is not None
        tool_names = [t["name"] for t in tools_res["result"]["tools"]]
        assert "exporter_generate" in tool_names
        assert "exporter_supported_frameworks" in tool_names
        assert "exporter_convert_html" in tool_names
        assert "exporter_validate_scaffold" in tool_names
        assert "exporter_diagnostics" in tool_names

        # Call tool
        call_res = server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "exporter_supported_frameworks",
                "arguments": {"category": "spa"}
            }
        })
        assert call_res is not None
        assert call_res["result"]["isError"] is False

    test("MCP Server JSON-RPC Protocol & Tools", t_mcp)

    print(f"\n{tc.bold('Test Summary:')} {passed_tests}/{total_tests} passed.\n")
    return passed_tests == total_tests


# ---------------------------------------------------------------------------
# CLI Command Handlers
# ---------------------------------------------------------------------------

def handle_export(args: argparse.Namespace) -> None:
    """Handle `export <framework>` subcommand."""
    framework = args.framework.lower().strip()
    theme = args.theme
    project_name = args.name or f"{framework}-m3-app"
    options = {
        "typescript": args.typescript,
        "styling": args.styling,
        "include_routing": args.include_routing,
    }

    if framework not in FRAMEWORK_CATALOG and framework != "all":
        print(f"{tc.badge('ERROR', 'red')} Unknown framework '{framework}'.")
        print(f"Supported frameworks: {tc.cyan(', '.join(FRAMEWORK_CATALOG.keys()))}")
        sys.exit(1)

    print(f"{tc.badge('EXPORT', 'cyan')} Generating project scaffold for {tc.bold(framework)} (Theme: {tc.yellow(theme)})...")

    file_tree = generate_project_scaffold(
        framework=framework,
        project_name=project_name,
        theme=theme,
        options=options,
    )

    if args.dry_run:
        print(f"\n{tc.bold('Dry run preview:')}")
        for path in sorted(file_tree.keys()):
            size = len(file_tree[path].encode("utf-8"))
            print(f"  ├── {tc.cyan(path)} ({size} bytes)")
        print(f"\nTotal: {len(file_tree)} files.")
        return

    # ZIP archive output
    if args.zip:
        zip_dest = Path(args.output or f"{project_name}.zip")
        build_zip_bundle(
            file_tree=file_tree,  # type: ignore[arg-type]
            project_name=project_name,
            framework=framework,
            theme=theme,
            output_path=zip_dest,
            deterministic=True,
        )
        print(f"{tc.badge('SUCCESS', 'green')} Deterministic ZIP bundle generated: {tc.bold(str(zip_dest.resolve()))}")
        return

    # Filesystem directory output
    out_dir = Path(args.output or project_name)
    out_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in file_tree.items():
        dest = out_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    print(f"{tc.badge('SUCCESS', 'green')} Project written to: {tc.bold(str(out_dir.resolve()))}")
    print(f"\n{tc.bold('Next Steps:')}")
    print(f"  cd {out_dir}")
    print("  npm install")
    print("  npm run dev\n")


def handle_convert(args: argparse.Namespace) -> None:
    """Handle `convert <file>` subcommand."""
    target_fw = args.to.lower().strip()
    component_name = args.name or "ConvertedComponent"

    if args.input:
        html_content = args.input
    elif args.file:
        file_p = Path(args.file)
        if not file_p.exists():
            print(f"{tc.badge('ERROR', 'red')} Input file not found: {args.file}")
            sys.exit(1)
        html_content = file_p.read_text(encoding="utf-8")
    else:
        print(f"{tc.badge('ERROR', 'red')} Please specify an input file or use --input.")
        sys.exit(1)

    result = HTMLTranspiler.transpile(
        html_code=html_content,
        framework=target_fw,
        component_name=component_name,
        options={"typescript": args.typescript},
    )

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(result["code"], encoding="utf-8")
        print(f"{tc.badge('SUCCESS', 'green')} Converted code written to {tc.bold(str(out_p.resolve()))}")
    else:
        print(f"\n{tc.badge('CODE', 'cyan')} Transpiled {result['filename']}:\n")
        print(result["code"])


def handle_frameworks(args: argparse.Namespace) -> None:
    """Handle `frameworks` subcommand."""
    cat = args.category.lower().strip() if args.category else "all"

    if cat == "all":
        items = FRAMEWORK_CATALOG
    else:
        items = {k: v for k, v in FRAMEWORK_CATALOG.items() if v.get("category") == cat}

    if args.json:
        print(json.dumps(items, indent=2))
        return

    print_banner()
    print(f"{tc.bold('Supported Target Frameworks')} (Category: {tc.cyan(cat)})\n")
    print(f"{'ID':<10} {'Name':<22} {'Version':<12} {'Category':<10} {'Language':<20}")
    print("-" * 75)
    for fw_id, meta in sorted(items.items()):
        print(f"{tc.cyan(fw_id):<19} {meta['name']:<22} {meta['version']:<12} {meta['category']:<10} {meta['language']:<20}")
    print(f"\nTotal: {len(items)} frameworks supported.\n")


def handle_diagnostics(args: argparse.Namespace) -> None:
    """Handle `doctor` / `diagnostics` subcommand."""
    diag = get_system_diagnostics(verbose=args.verbose)

    if args.json:
        print(json.dumps(diag, indent=2))
        return

    print_banner()
    print(f"{tc.bold('Polyglot Framework Exporter Diagnostics')}\n")
    print(f"  {tc.bold('Version:')}      v{diag['exporter_version']}")
    print(f"  {tc.bold('OS Platform:')}  {diag['platform']['system']} {diag['platform']['release']} ({diag['platform']['architecture']})")
    print(f"  {tc.bold('Python:')}       {diag['platform']['python_version']} ({diag['platform']['python_executable']})")
    print(f"  {tc.bold('Frameworks:')}   {diag['supported_frameworks_count']} registered")
    print(f"  {tc.bold('Theme Tokens:')} {diag['theme_presets_count']} M3 presets\n")

    print(f"{tc.bold('Installed Toolchain Status:')}")
    for tool, status in sorted(diag["toolchain"].items()):
        if status["available"]:
            badge = tc.green("FOUND")
            print(f"  [{badge}] {tool:<10} -> {tc.dim(status['path'])}")
        else:
            badge = tc.dim("MISSING")
            print(f"  [{badge}] {tool:<10}")
    print("")


# ---------------------------------------------------------------------------
# CLI Argument Parser & Main Entrypoint
# ---------------------------------------------------------------------------

def build_cli_parser() -> argparse.ArgumentParser:
    """Construct top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="polyglot-framework-exporter",
        description="Google Material 3 Polyglot Framework Exporter CLI & MCP Server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s v{__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output.")

    subparsers = parser.add_subparsers(dest="command", title="Subcommands", help="Available actions")

    # Subcommand: export
    p_export = subparsers.add_parser("export", help="Generate full project files or ZIP for target framework.")
    p_export.add_argument("framework", help="Target framework (e.g., react, vue, svelte, solid, angular, flutter, swiftui, vanilla).")
    p_export.add_argument("-o", "--output", help="Output directory or ZIP archive path.")
    p_export.add_argument("-z", "--zip", action="store_true", help="Bundle output as a clean, deterministic ZIP archive.")
    p_export.add_argument("-t", "--theme", default="system", choices=list(THEME_PRESETS.keys()), help="Material 3 theme preset.")
    p_export.add_argument("-n", "--name", help="Project name.")
    p_export.add_argument("--typescript", action="store_true", default=True, help="Enable TypeScript (default: True).")
    p_export.add_argument("--no-typescript", action="store_false", dest="typescript", help="Disable TypeScript.")
    p_export.add_argument("--styling", default="tailwind", help="Styling approach (tailwind, m3, scoped).")
    p_export.add_argument("--include-routing", action="store_true", help="Include multi-page client routing setup.")
    p_export.add_argument("--dry-run", action="store_true", help="Preview file generation without writing.")

    # Subcommand: convert
    p_convert = subparsers.add_parser("convert", help="Transpile arbitrary HTML/Tailwind to target framework component.")
    p_convert.add_argument("file", nargs="?", help="Input HTML file path.")
    p_convert.add_argument("-i", "--input", help="Raw HTML code string.")
    p_convert.add_argument("-t", "--to", default="react", help="Target framework (default: react).")
    p_convert.add_argument("-n", "--name", default="ConvertedComponent", help="Component name.")
    p_convert.add_argument("-o", "--output", help="Output file path.")
    p_convert.add_argument("--typescript", action="store_true", default=True, help="Generate TypeScript component.")

    # Subcommand: frameworks
    p_fw = subparsers.add_parser("frameworks", help="List all supported frameworks, versions, and capabilities.")
    p_fw.add_argument("-c", "--category", help="Filter by category (spa, meta, native, static, web, all).")
    p_fw.add_argument("--json", action="store_true", help="Output as JSON.")

    # Subcommand: serve
    p_serve = subparsers.add_parser("serve", help="Launch the Google Material 3 Framework Studio Web UI.")
    p_serve.add_argument("-H", "--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1).")
    p_serve.add_argument("-p", "--port", type=int, default=8080, help="Port to listen on (default: 8080).")
    p_serve.add_argument("-b", "--open", action="store_true", help="Auto-open browser on startup.")

    # Subcommand: mcp
    subparsers.add_parser("mcp", help="Run Model Context Protocol (MCP) server over stdio for AI assistants.")

    # Subcommand: doctor / diagnostics / platform
    for alias in ("doctor", "diagnostics", "platform"):
        p_diag = subparsers.add_parser(alias, help="Run multi-OS environment and toolchain diagnostics.")
        p_diag.add_argument("-V", "--verbose", action="store_true", help="Verbose diagnostic output.")
        p_diag.add_argument("--json", action="store_true", help="Output as JSON.")

    # Subcommand: test
    p_test = subparsers.add_parser("test", help="Run internal self-verification test suite.")
    p_test.add_argument("-V", "--verbose", action="store_true", help="Verbose test runner output.")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """CLI Entrypoint function."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    global tc
    if args.no_color:
        tc = TermColor(force_disable=True)

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "export":
        handle_export(args)
    elif args.command == "convert":
        handle_convert(args)
    elif args.command == "frameworks":
        handle_frameworks(args)
    elif args.command == "serve":
        run_studio_server(host=args.host, port=args.port, open_browser=args.open)
    elif args.command == "mcp":
        run_mcp_server()
    elif args.command in ("doctor", "diagnostics", "platform"):
        handle_diagnostics(args)
    elif args.command == "test":
        success = run_self_verification_tests(verbose=args.verbose)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
