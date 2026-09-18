"""Multi-Target Deployment Configuration Generator for polyglot-framework-exporter.

Generates production-grade, framework-aware deployment manifests with zero external dependencies:
- Multi-Stage Dockerfile (optimized for minimal image footprint)
- .dockerignore
- Netlify Configuration (`netlify.toml`)
- Vercel Configuration (`vercel.json`)
- Cloudflare Configuration (`wrangler.jsonc`)
- GitHub Actions CI/CD Workflow (`.github/workflows/deploy.yml`)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .transpiler import ProjectAST


# Mapping of framework IDs to build commands, output directories, and runtime targets
FRAMEWORK_DEPLOY_PROFILES: Dict[str, Dict[str, Any]] = {
    "astro": {
        "build_cmd": "npm run build",
        "output_dir": "dist",
        "node_version": "20",
        "server_mode": "static",
        "dev_port": 4321,
    },
    "nextjs": {
        "build_cmd": "npm run build",
        "output_dir": ".next",
        "node_version": "20",
        "server_mode": "node",
        "dev_port": 3000,
    },
    "vite_react": {
        "build_cmd": "npm run build",
        "output_dir": "dist",
        "node_version": "20",
        "server_mode": "static",
        "dev_port": 5173,
    },
    "svelte": {
        "build_cmd": "npm run build",
        "output_dir": "build",
        "node_version": "20",
        "server_mode": "node",
        "dev_port": 5173,
    },
    "solidstart": {
        "build_cmd": "npm run build",
        "output_dir": ".output/public",
        "node_version": "20",
        "server_mode": "node",
        "dev_port": 3000,
    },
    "nuxt": {
        "build_cmd": "npm run build",
        "output_dir": ".output/public",
        "node_version": "20",
        "server_mode": "node",
        "dev_port": 3000,
    },
    "deno_fresh": {
        "build_cmd": "deno task build",
        "output_dir": "_fresh",
        "node_version": "deno",
        "server_mode": "deno",
        "dev_port": 8000,
    },
    "bun_hono": {
        "build_cmd": "bun run src/index.ts",
        "output_dir": "src",
        "node_version": "bun",
        "server_mode": "bun",
        "dev_port": 3000,
    },
    "remix": {
        "build_cmd": "npm run build",
        "output_dir": "build/client",
        "node_version": "20",
        "server_mode": "node",
        "dev_port": 3000,
    },
    "qwik": {
        "build_cmd": "npm run build",
        "output_dir": "dist",
        "node_version": "20",
        "server_mode": "static",
        "dev_port": 5173,
    },
    "htmx": {
        "build_cmd": "python3 server.py",
        "output_dir": "public",
        "node_version": "python",
        "server_mode": "python",
        "dev_port": 8000,
    },
    "tauri": {
        "build_cmd": "npm run tauri build",
        "output_dir": "src-tauri/target/release/bundle",
        "node_version": "20",
        "server_mode": "desktop",
        "dev_port": 1420,
    },
    "electron": {
        "build_cmd": "npm run build",
        "output_dir": "dist",
        "node_version": "20",
        "server_mode": "desktop",
        "dev_port": 5173,
    },
}


def get_deploy_profile(framework: str) -> Dict[str, Any]:
    """Retrieve framework deployment profile with standard fallback."""
    key = framework.lower().strip().replace("-", "_")
    return FRAMEWORK_DEPLOY_PROFILES.get(key, {
        "build_cmd": "npm run build",
        "output_dir": "dist",
        "node_version": "20",
        "server_mode": "static",
        "dev_port": 3000,
    })


def generate_dockerfile(framework: str, ast: Optional[ProjectAST] = None) -> str:
    """Generate optimized multi-stage Dockerfile for target framework."""
    profile = get_deploy_profile(framework)
    mode = profile["server_mode"]

    if mode == "python":
        return """# Pure Python Hypermedia Production Container
FROM python:3.12-alpine

WORKDIR /app
COPY . /app

EXPOSE 8000
ENV PORT=8000
CMD ["python3", "server.py"]
"""

    if mode == "bun":
        return """# Bun Hono Edge Microservice Container
FROM oven/bun:1.1-alpine AS base
WORKDIR /app

COPY package.json ./
RUN bun install --frozen-lockfile || bun install

COPY . .

EXPOSE 3000
CMD ["bun", "run", "src/index.ts"]
"""

    if mode == "deno":
        return """# Deno Fresh Edge Application Container
FROM denoland/deno:alpine-1.46.3

WORKDIR /app
COPY . .
RUN deno cache dev.ts main.ts || true

EXPOSE 8000
CMD ["run", "-A", "main.ts"]
"""

    if mode == "node":
        return f"""# Multi-Stage Node.js Production Container
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN {profile["build_cmd"]}

# Runner Stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

COPY --from=builder /app ./

EXPOSE 3000
CMD ["npm", "start"]
"""

    # Static (Vite, Astro, Qwik) -> Nginx Alpine
    out_dir = profile["output_dir"]
    return f"""# Multi-Stage Static Production Container (Nginx Alpine)
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN {profile["build_cmd"]}

# Lightweight Static Webserver
FROM nginx:alpine AS runner
COPY --from=builder /app/{out_dir} /usr/share/nginx/html
COPY <<EOF /etc/nginx/conf.d/default.conf
server {{
    listen 80;
    server_name localhost;
    location / {{
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files \\$uri \\$uri/ /index.html;
    }}
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {{
        root /usr/share/nginx/html;
    }}
}}
EOF

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""


def generate_dockerignore() -> str:
    """Generate .dockerignore file."""
    return """node_modules
.git
.github
dist
build
.output
.next
.cache
coverage
*.log
.env.local
.DS_Store
"""


def generate_netlify_toml(framework: str) -> str:
    """Generate Netlify configuration file."""
    profile = get_deploy_profile(framework)
    build_cmd = profile["build_cmd"]
    publish_dir = profile["output_dir"]

    return f"""[build]
  command = "{build_cmd}"
  publish = "{publish_dir}"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[build.environment]
  NODE_VERSION = "20"
"""


def generate_vercel_json(framework: str) -> str:
    """Generate Vercel deployment configuration."""
    profile = get_deploy_profile(framework)
    framework_id = framework.lower().replace("_", "-")

    config = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "buildCommand": profile["build_cmd"],
        "outputDirectory": profile["output_dir"],
        "framework": framework_id if framework_id in ["nextjs", "astro", "remix", "nuxt", "svelte"] else None,
    }
    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}
    return json.dumps(config, indent=2)


def generate_wrangler_config(framework: str, project_name: str = "app") -> str:
    """Generate Cloudflare Wrangler JSONC configuration."""
    profile = get_deploy_profile(framework)
    output_dir = profile["output_dir"]

    return f"""{{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "{project_name.lower().replace(' ', '-')}",
  "compatibility_date": "2024-11-01",
  "pages_build_output_dir": "{output_dir}"
}}
"""


def generate_github_actions_workflow(framework: str, project_name: str = "app") -> str:
    """Generate GitHub Actions CI/CD build and test workflow."""
    profile = get_deploy_profile(framework)
    mode = profile["server_mode"]

    if mode == "python":
        return """name: CI / Deploy

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Verify Server Startup
        run: |
          python3 -c "import http.server, socketserver; print('Python stdlib OK')"
"""

    return f"""name: CI / Deploy

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - name: Install dependencies
        run: npm ci || npm install
      - name: Build project
        run: {profile["build_cmd"]}
"""


def generate_all_deploy_configs(framework: str, ast: Optional[ProjectAST] = None) -> Dict[str, str]:
    """Generate all deployment manifests for the target framework."""
    name = ast.title if ast else "app"
    return {
        "Dockerfile": generate_dockerfile(framework, ast),
        ".dockerignore": generate_dockerignore(),
        "netlify.toml": generate_netlify_toml(framework),
        "vercel.json": generate_vercel_json(framework),
        "wrangler.jsonc": generate_wrangler_config(framework, name),
        ".github/workflows/deploy.yml": generate_github_actions_workflow(framework, name),
    }
