"""Bun + Hono 4 Edge API & Full-Stack Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Bun + Hono 4 server projects
with TypeScript, middleware (CORS, Logger, Secure Headers), structured API routing,
health probes, Zod request validation, and Master Theme styled UI dashboard.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class BunHonoGenerator:
    """Generates a complete Bun + Hono 4 edge microservice and web API project."""

    name = "bun_hono"
    display_name = "Bun + Hono 4 (Edge API & Web)"
    description = "Ultra-fast server-side TypeScript edge microservice and web server powered by Bun and Hono 4."

    def generate(
        self,
        ast: ProjectAST,
        output_dir: Optional[Union[str, Path]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        theme = ast.get_theme()
        files: Dict[str, str] = {}
        pkg_name = ast.title.lower().replace(" ", "-").replace("_", "-")

        # 1. package.json
        files["package.json"] = json.dumps({
            "name": pkg_name,
            "version": ast.version,
            "description": ast.description,
            "type": "module",
            "scripts": {
                "dev": "bun run --hot src/index.ts",
                "start": "bun run src/index.ts",
                "test": "bun test"
            },
            "dependencies": {
                "hono": "^4.6.14",
                "@hono/node-server": "^1.13.7",
                "zod": "^3.23.8"
            },
            "devDependencies": {
                "@types/bun": "latest",
                "typescript": "^5.7.2"
            }
        }, indent=2)

        # 2. tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "lib": ["ESNext"],
                "module": "ESNext",
                "target": "ESNext",
                "moduleResolution": "bundler",
                "moduleDetection": "force",
                "noEmit": True,
                "composite": True,
                "strict": True,
                "downlevelIteration": True,
                "skipLibCheck": True,
                "jsx": "react-jsx",
                "jsxImportSource": "hono/jsx",
                "allowSyntheticDefaultImports": True,
                "forceConsistentCasingInFileNames": True
            }
        }, indent=2)

        # 3. src/routes/api.ts
        feat_sec = ast.get_section("features")
        f_items = (feat_sec.data if feat_sec else {}).get("items", [])

        price_sec = ast.get_section("pricing")
        p_tiers = (price_sec.data if price_sec else {}).get("tiers", [])

        files["src/routes/api.ts"] = f"""import {{ Hono }} from "hono";
import {{ z }} from "zod";

export const api = new Hono();

// Project Information
api.get("/info", (c) => {{
  return c.json({{
    title: {json.dumps(ast.title)},
    description: {json.dumps(ast.description)},
    version: {json.dumps(ast.version)},
    author: {json.dumps(ast.author)},
    theme: {json.dumps(theme.name)},
    framework: "Bun + Hono 4",
    runtime: typeof Bun !== "undefined" ? "bun" : "node",
    timestamp: new Date().toISOString(),
  }});
}});

// Feature Catalog
api.get("/features", (c) => {{
  const features = {json.dumps(f_items, indent=2)};
  return c.json({{ count: features.length, features }});
}});

// Pricing Plans
api.get("/pricing", (c) => {{
  const tiers = {json.dumps(p_tiers, indent=2)};
  return c.json({{ count: tiers.length, tiers }});
}});

// Health Probe (liveness & readiness)
api.get("/health", (c) => {{
  return c.json({{
    status: "healthy",
    uptime_seconds: process.uptime(),
    memory_usage_mb: Math.round(process.memoryUsage().rss / (1024 * 1024)),
    timestamp: new Date().toISOString(),
  }});
}});

// Validated Echo Endpoint
const echoSchema = z.object({{
  message: z.string().min(1).max(500),
  category: z.string().optional().default("general"),
}});

api.post("/echo", async (c) => {{
  const body = await c.req.json().catch(() => null);
  const parsed = echoSchema.safeParse(body);
  if (!parsed.success) {{
    return c.json({{ error: "Validation failed", details: parsed.error.issues }}, 400);
  }}
  return c.json({{
    received: parsed.data,
    processed_at: new Date().toISOString(),
    status: "success",
  }});
}});
"""

        # 4. src/views/home.ts
        hero_sec = ast.get_section("hero")
        h_data = hero_sec.data if hero_sec else {}
        hero_title = h_data.get("title", ast.title)
        hero_subtitle = h_data.get("subtitle", ast.description)

        files["src/views/home.ts"] = f"""export function renderHomePage(): string {{
  const css = `{theme.to_css_string()}`;
  return `<!DOCTYPE html>
<html lang="{ast.lang}" class="{ 'dark' if theme.is_dark else '' }">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(ast.title)} — Bun + Hono 4</title>
  <style>
    ${{css}}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
      line-height: 1.6;
      padding: 2rem;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    header {{
      text-align: center;
      padding: 3rem 1rem 2rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      background: var(--accent-glow, rgba(99, 102, 241, 0.15));
      color: var(--accent-primary);
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 1rem;
      border: 1px solid var(--border-color);
    }}
    h1 {{
      font-size: 2.75rem;
      font-family: var(--font-heading, inherit);
      letter-spacing: -0.02em;
      margin-bottom: 1rem;
    }}
    p.lead {{
      font-size: 1.25rem;
      color: var(--text-secondary);
      max-width: 650px;
      margin: 0 auto 2rem;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin: 2.5rem 0;
    }}
    .card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .card h3 {{
      font-size: 1.15rem;
      color: var(--accent-primary);
      margin-bottom: 0.5rem;
    }}
    .card code {{
      font-family: var(--font-mono, monospace);
      font-size: 0.85rem;
      background: var(--bg-secondary);
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
    }}
    footer {{
      margin-top: 4rem;
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border-subtle);
      padding-top: 2rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge">🔥 Bun + Hono 4 Edge Architecture</div>
      <h1>{html.escape(hero_title)}</h1>
      <p class="lead">{html.escape(hero_subtitle)}</p>
    </header>

    <div class="card-grid">
      <div class="card">
        <h3>⚡ Health & Metrics</h3>
        <p>Liveness check and system uptime.</p>
        <p style="margin-top: 0.5rem;"><code>GET /api/health</code></p>
      </div>
      <div class="card">
        <h3>📦 App Metadata</h3>
        <p>Read exported AST configuration.</p>
        <p style="margin-top: 0.5rem;"><code>GET /api/info</code></p>
      </div>
      <div class="card">
        <h3>✨ Feature Catalog</h3>
        <p>Dynamic features queried directly via JSON.</p>
        <p style="margin-top: 0.5rem;"><code>GET /api/features</code></p>
      </div>
      <div class="card">
        <h3>💳 Pricing Plans</h3>
        <p>Structured subscription and pricing tiers.</p>
        <p style="margin-top: 0.5rem;"><code>GET /api/pricing</code></p>
      </div>
    </div>

    <footer>
      <p>Design influenced by Material 3 tokens • Powered by Bun + Hono 4 Edge API Engine</p>
    </footer>
  </div>
</body>
</html>`;
}}
"""

        # 5. src/index.ts
        files["src/index.ts"] = """import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { prettyJSON } from "hono/pretty-json";
import { secureHeaders } from "hono/secure-headers";
import { api } from "./routes/api";
import { renderHomePage } from "./views/home";

const app = new Hono();

// Global Middlewares
app.use("*", logger());
app.use("*", cors());
app.use("*", secureHeaders());
app.use("*", prettyJSON());

// Mount API Router
app.route("/api", api);

// Serve Web Landing Page
app.get("/", (c) => {
  return c.html(renderHomePage());
});

// 404 Fallback
app.notFound((c) => {
  return c.json({ error: "Not Found", path: c.req.path }, 404);
});

// Error Handler
app.onError((err, c) => {
  console.error("Server error:", err);
  return c.json({ error: "Internal Server Error", message: err.message }, 500);
});

const port = Number(process.env.PORT) || 3000;

console.log(`🚀 Bun + Hono 4 server running at http://localhost:${port}`);

export default {
  port,
  fetch: app.fetch,
};
"""

        # 6. README.md
        files["README.md"] = f"""# {ast.title} (Bun + Hono 4)

Exported with **Polyglot Framework Exporter** using the **{theme.display_name}** theme.
High-throughput, ultra-fast server-side TypeScript edge API and microservice powered by [Bun](https://bun.sh) and [Hono 4](https://hono.dev).

## 🚀 Quickstart

Ensure [Bun](https://bun.sh) is installed on your system.

```bash
# Install dependencies
bun install

# Start development server with hot-reload
bun run dev

# Run unit tests
bun test
```

## 📡 API Routes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Responsive HTML dashboard |
| `GET` | `/api/info` | Service info and theme configuration |
| `GET` | `/api/health` | Service liveness & memory metrics |
| `GET` | `/api/features` | Catalog of AST features |
| `GET` | `/api/pricing` | Pricing plans and subscription tiers |
| `POST` | `/api/echo` | Zod-validated payload echo test |

## 🧪 Testing with curl

```bash
# Health check
curl http://localhost:3000/api/health

# App info
curl http://localhost:3000/api/info

# Validated echo
curl -X POST http://localhost:3000/api/echo \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "Hello from Bun and Hono!"}}'
```
"""

        # Save to disk if output_dir provided
        if output_dir:
            out_path = Path(output_dir)
            ensure_directory(out_path)
            for rel_path, content in files.items():
                dest = safe_join(out_path, rel_path)
                atomic_write_text(dest, content)

        return files
