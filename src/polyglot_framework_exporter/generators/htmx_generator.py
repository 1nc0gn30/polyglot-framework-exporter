"""HTMX 2.x + Alpine.js + Tailwind Hypermedia Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Hypermedia-driven projects
with HTMX 2.x, Alpine.js 3.x reactivity, Tailwind CSS, Master Theme tokens,
and a standalone zero-dependency Python Standard Library server (server.py)
serving dynamic HTML partials and API endpoints.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class HTMXGenerator:
    """Generates a complete HTMX + Alpine.js + Tailwind hypermedia web application."""

    name = "htmx"
    display_name = "HTMX 2 + Alpine.js + Tailwind (Hypermedia)"
    description = "Ultra-lightweight hypermedia web application powered by HTMX 2, Alpine.js, and pure Python server."

    def generate(
        self,
        ast: ProjectAST,
        output_dir: Optional[Union[str, Path]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        theme = ast.get_theme()
        files: Dict[str, str] = {}
        pkg_name = ast.title.lower().replace(" ", "-").replace("_", "-")

        # Extract AST sections
        hero_sec = ast.get_section("hero")
        hero_title = (hero_sec.data if hero_sec else {}).get("title", ast.title)
        hero_sub = (hero_sec.data if hero_sec else {}).get("subtitle", ast.description)

        feat_sec = ast.get_section("features")
        feat_items = (feat_sec.data if feat_sec else {}).get("items", [
            {"title": "Zero Build Overhead", "description": "True hypermedia driven directly by server HTML partials.", "icon": "⚡"},
            {"title": "Alpine.js Client State", "description": "Declarative, reactive UI toggles with no heavy JavaScript bundle.", "icon": "🎯"},
            {"title": "Python Stdlib Backend", "description": "Pure standard library HTTP server ready for deployment.", "icon": "🐍"},
        ])

        price_sec = ast.get_section("pricing")
        price_tiers = (price_sec.data if price_sec else {}).get("tiers", [
            {"name": "Developer", "price": "$0", "description": "Zero runtime dependencies", "features": ["HTMX 2.0 hypermedia", "Alpine.js reactivity", "Tailwind styling"]},
            {"name": "Production", "price": "$19/mo", "description": "High-concurrency servers", "features": ["Custom partial endpoints", "All 6 Master Themes", "Container packaging"]},
        ])

        css_vars = theme.to_css_string()

        # 1. public/index.html
        feat_cards = []
        for f in feat_items:
            icon = f.get("icon", "✨")
            ftitle = f.get("title", "Feature")
            fdesc = f.get("description", "")
            feat_cards.append(f"""        <div class="p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--accent-primary)] hover:bg-[var(--bg-surface-hover)] transition-all shadow-sm">
          <div class="text-3xl mb-3">{icon}</div>
          <h3 class="text-lg font-bold mb-2">{html.escape(ftitle)}</h3>
          <p class="text-sm text-[var(--text-muted)] leading-relaxed">{html.escape(fdesc)}</p>
        </div>""")
        feat_cards_html = "\n".join(feat_cards)

        price_cards = []
        for p in price_tiers:
            pname = p.get("name", "Tier")
            pprice = p.get("price", "$0")
            pdesc = p.get("description", "")
            pfeats = p.get("features", [])
            pfeat_li = "".join(f'<li class="flex items-center space-x-2"><span>✓</span><span>{html.escape(pf)}</span></li>' for pf in pfeats)
            price_cards.append(f"""        <div class="p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col justify-between">
          <div>
            <h3 class="text-xl font-bold">{html.escape(pname)}</h3>
            <p class="text-sm text-[var(--text-muted)] mt-1">{html.escape(pdesc)}</p>
            <div class="text-3xl font-extrabold my-4 text-[var(--accent-primary)]">{html.escape(pprice)}</div>
            <ul class="space-y-2 text-sm text-[var(--text-secondary)]">
              {pfeat_li}
            </ul>
          </div>
          <button
            hx-post="/api/contact"
            hx-vals='{{"tier": "{html.escape(pname)}"}}'
            hx-target="#notification-toast"
            hx-swap="innerHTML"
            class="mt-6 w-full py-2.5 rounded-lg text-sm font-semibold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-colors shadow-sm"
          >
            Select {html.escape(pname)}
          </button>
        </div>""")
        price_cards_html = "\n".join(price_cards)

        files["public/index.html"] = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(ast.title)} - HTMX + Alpine.js Hypermedia</title>
  <meta name="description" content="{html.escape(ast.description)}">
  
  <!-- HTMX 2.0 & Alpine.js 3 & Tailwind CSS CDN -->
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <script defer src="https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>

  <style>
{css_vars}

    body {{
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-sans), system-ui, -apple-system, sans-serif;
    }}
    [x-cloak] {{ display: none !important; }}
    .htmx-indicator {{
      opacity: 0;
      transition: opacity 200ms ease-in;
    }}
    .htmx-request .htmx-indicator {{
      opacity: 1;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-[var(--accent-primary)] selection:text-black">

  <!-- Header Navigation -->
  <header class="sticky top-0 z-50 backdrop-blur-md bg-[var(--bg-primary)]/80 border-b border-[var(--border-subtle)]" x-data="{{ mobileOpen: false }}">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-2xl">⚡</span>
        <span class="font-bold text-lg tracking-tight">{html.escape(ast.title)}</span>
        <span class="text-xs px-2 py-0.5 rounded-full bg-[var(--badge-bg)] text-[var(--badge-text)] font-mono border border-[var(--border-subtle)]">HTMX 2.0</span>
      </div>

      <nav class="hidden md:flex items-center space-x-6">
        <a href="#features" class="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors">Features</a>
        <a href="#pricing" class="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors">Pricing</a>
        <a href="#dynamic" class="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors">Live Partial</a>
      </nav>

      <div class="flex items-center space-x-3">
        <span id="nav-spinner" class="htmx-indicator text-xs text-[var(--accent-primary)] font-mono">Loading...</span>
        <button
          hx-get="/partials/live-stats"
          hx-target="#stats-display"
          hx-indicator="#nav-spinner"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] transition-colors"
        >
          Refresh Stats
        </button>
        <a href="#pricing" class="px-4 py-2 rounded-lg text-sm font-semibold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-all shadow-sm">
          Get Started
        </a>
      </div>
    </div>
  </header>

  <!-- Notification Banner Container -->
  <div id="notification-toast" class="max-w-md mx-auto fixed bottom-6 right-6 z-50"></div>

  <!-- Main Content -->
  <main class="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-24">

    <!-- Hero Section -->
    <section class="text-center max-w-3xl mx-auto pt-8">
      <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--badge-bg)] text-[var(--badge-text)] border border-[var(--border-subtle)] mb-6">
        <span>⚡ Pure Hypermedia Architecture</span>
      </div>
      <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 bg-gradient-to-r from-[var(--text-primary)] via-[var(--accent-primary)] to-[var(--accent-secondary)] bg-clip-text text-transparent">
        {html.escape(hero_title)}
      </h1>
      <p class="text-lg text-[var(--text-secondary)] leading-relaxed mb-8">
        {html.escape(hero_sub)}
      </p>
      
      <!-- Alpine.js Client-Side Counter and HTMX Partial Trigger -->
      <div class="flex flex-wrap items-center justify-center gap-4" x-data="{{ localCount: 0 }}">
        <button
          @click="localCount++"
          class="px-6 py-3 rounded-xl font-bold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-transform active:scale-95 shadow-md flex items-center space-x-2"
        >
          <span>🎯 Alpine Client Signal:</span>
          <span class="px-2 py-0.5 rounded bg-black/20 font-mono" x-text="localCount">0</span>
        </button>

        <button
          hx-get="/partials/system-info"
          hx-target="#dynamic-container"
          hx-swap="innerHTML"
          hx-indicator="#hero-indicator"
          class="px-6 py-3 rounded-xl font-semibold border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] transition-colors flex items-center space-x-2"
        >
          <span>📡 HTMX Server Partial</span>
          <span id="hero-indicator" class="htmx-indicator text-xs text-[var(--accent-primary)]">⟳</span>
        </button>
      </div>

      <!-- Live Server Stats Card -->
      <div id="stats-display" class="mt-8 p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-xs text-[var(--text-muted)] inline-block">
        <span class="text-[var(--accent-primary)] font-bold">● Server Status:</span> Online & Ready • Powered by Python Standard Library
      </div>
    </section>

    <!-- Dynamic HTMX Container Target -->
    <section id="dynamic" class="max-w-4xl mx-auto">
      <div id="dynamic-container" class="transition-all duration-300">
        <!-- Content will be injected here via HTMX partials -->
      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="space-y-8">
      <div class="text-center max-w-2xl mx-auto">
        <h2 class="text-3xl font-bold tracking-tight">Key Architectural Strengths</h2>
        <p class="text-[var(--text-muted)] mt-2">Zero bundle latency, seamless server synchronization.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
{feat_cards_html}
      </div>
    </section>

    <!-- Pricing Section -->
    <section id="pricing" class="space-y-8">
      <div class="text-center max-w-2xl mx-auto">
        <h2 class="text-3xl font-bold tracking-tight">Simple, Transparent Deployment</h2>
        <p class="text-[var(--text-muted)] mt-2">Deploy with Docker, standard Linux VM, or lightweight edge container.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
{price_cards_html}
      </div>
    </section>

  </main>

  <!-- Footer -->
  <footer class="border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)] py-8 text-center text-sm text-[var(--text-muted)] mt-16">
    <p>© <span x-text="new Date().getFullYear()">{theme.name}</span> {html.escape(ast.title)}. Built with HTMX & Alpine.js via Polyglot Exporter.</p>
  </footer>

</body>
</html>
"""

        # 2. server.py (Pure Python stdlib ThreadingHTTPServer)
        files["server.py"] = f"""#!/usr/bin/env python3
\"\"\"Zero-Dependency HTTP Server for {ast.title} (HTMX + Alpine.js).

Pure Python Standard Library runtime (Python 3.9+).
Serves static assets and dynamic HTMX HTML partials.
\"\"\"

from __future__ import annotations

import html
import http.server
import json
import os
from pathlib import Path
import socketserver
import sys
import time
import urllib.parse

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
START_TIME = time.time()


class HTMXHypermediaHandler(http.server.SimpleHTTPRequestHandler):
    \"\"\"HTTP Request Handler serving static files & HTMX hypermedia partials.\"\"\"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def _send_html(self, content: str, status: int = 200) -> None:
        raw = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # HTMX Partials
        if path == "/partials/system-info":
            uptime = round(time.time() - START_TIME, 1)
            partial = f\"\"\"
            <div class="p-6 rounded-2xl border border-[var(--border-color)] bg-[var(--bg-surface)] shadow-lg animate-fade-in">
              <div class="flex items-center justify-between mb-4 border-b border-[var(--border-subtle)] pb-3">
                <span class="font-bold text-sm text-[var(--accent-primary)]">⚡ Server Dynamic Hypermedia Partial</span>
                <span class="text-xs text-[var(--text-muted)]">Rendered in pure Python</span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div class="p-3 rounded-lg bg-[var(--bg-primary)]">
                  <div class="text-xs text-[var(--text-muted)]">Server Uptime</div>
                  <div class="text-lg font-bold font-mono">{{uptime}}s</div>
                </div>
                <div class="p-3 rounded-lg bg-[var(--bg-primary)]">
                  <div class="text-xs text-[var(--text-muted)]">Python Version</div>
                  <div class="text-lg font-bold font-mono">{{sys.version_info.major}}.{{sys.version_info.minor}}.{{sys.version_info.micro}}</div>
                </div>
                <div class="p-3 rounded-lg bg-[var(--bg-primary)]">
                  <div class="text-xs text-[var(--text-muted)]">Platform</div>
                  <div class="text-lg font-bold font-mono">{{sys.platform}}</div>
                </div>
                <div class="p-3 rounded-lg bg-[var(--bg-primary)]">
                  <div class="text-xs text-[var(--text-muted)]">HTMX Mode</div>
                  <div class="text-lg font-bold font-mono text-[var(--accent-primary)]">Active</div>
                </div>
              </div>
            </div>
            \"\"\"
            self._send_html(partial)
            return

        elif path == "/partials/live-stats":
            uptime = round(time.time() - START_TIME, 1)
            partial = f\"\"\"
            <span class="text-green-400 font-bold">● Server Active:</span> Uptime {{uptime}}s • Python {{sys.version_info.major}}.{{sys.version_info.minor}} • 0 dependencies
            \"\"\"
            self._send_html(partial)
            return

        elif path == "/api/health":
            self._send_json({{
                "status": "healthy",
                "app": {json.dumps(ast.title)},
                "framework": "htmx-alpine",
                "uptime_seconds": round(time.time() - START_TIME, 2),
            }})
            return

        # Fallback to serving static assets from /public
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/contact":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8", errors="ignore")
            params = urllib.parse.parse_qs(body)
            tier = params.get("tier", ["Standard"])[0]

            toast = f\"\"\"
            <div x-data="{{ show: true }}" x-show="show" x-init="setTimeout(() => show = false, 4000)" class="p-4 rounded-xl border border-green-500/50 bg-green-950/80 text-green-200 text-sm shadow-xl flex items-center justify-between">
              <span>🎉 Successfully selected plan: <strong>{{html.escape(tier)}}</strong>!</span>
              <button @click="show = false" class="ml-4 text-green-400 hover:text-white">&times;</button>
            </div>
            \"\"\"
            self._send_html(toast)
            return

        self._send_html("<p class='text-red-400'>Not Found</p>", status=404)

    def log_message(self, format: str, *args) -> None:
        pass


def run_server(port: int = PORT) -> None:
    print(f"🚀 Starting HTMX Hypermedia Server on http://0.0.0.0:{{port}}")
    print("Zero runtime dependencies - 100% Python Standard Library.")
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), HTMXHypermediaHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nShutting down server...")


if __name__ == "__main__":
    run_server()
"""

        # 3. package.json (Optional npm convenience scripts)
        files["package.json"] = json.dumps({
            "name": pkg_name,
            "version": ast.version,
            "description": ast.description,
            "scripts": {
                "start": "python3 server.py",
                "dev": "python3 server.py"
            },
            "devDependencies": {}
        }, indent=2)

        # 4. README.md
        files["README.md"] = f"""# {ast.title} (HTMX 2 + Alpine.js + Tailwind)

> {ast.description}

This project was exported with [Polyglot Framework Exporter](https://github.com/polyglot-framework/polyglot-framework-exporter) using the **HTMX + Alpine.js Hypermedia** generator and the **{theme.display_name}** theme.

## 🚀 Instant Launch (Zero Dependencies)

No `npm install` or heavy toolchain required! Simply run with Python 3.9+:

```bash
# Start local hypermedia server
python3 server.py
# or
npm start
```

Visit [http://localhost:8000/](http://localhost:8000/) in your browser.

## 🏛️ Architecture Highlights
- **HTMX 2.0**: Server-driven HTML partial swaps with declarative attributes (`hx-get`, `hx-post`, `hx-target`, `hx-swap`).
- **Alpine.js 3**: Fine-grained client-side reactive state (`x-data`, `x-show`, `@click`).
- **Tailwind CSS**: Instant modern typography, container sizing, and elevation shadows.
- **Master Theme Tokens**: {theme.display_name} design tokens injected directly via CSS custom properties.
- **Python Stdlib Server**: Lightweight `ThreadingHTTPServer` handling partial routes and JSON endpoints.
"""

        # Write to disk if output_dir specified
        if output_dir:
            base = Path(output_dir)
            ensure_directory(base)
            for rel_path, content in files.items():
                dest = safe_join(base, rel_path)
                ensure_directory(dest.parent)
                atomic_write_text(dest, content)

        return files
