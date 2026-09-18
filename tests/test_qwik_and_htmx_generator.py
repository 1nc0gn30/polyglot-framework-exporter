"""Tests for Qwik City, HTMX Hypermedia generators, and Multi-Target Deployment Configs."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.deploy_configs import (
    generate_all_deploy_configs,
    generate_dockerfile,
    generate_dockerignore,
    generate_github_actions_workflow,
    generate_netlify_toml,
    generate_vercel_json,
    generate_wrangler_config,
    get_deploy_profile,
)
from polyglot_framework_exporter.generators import get_generator, list_generators
from polyglot_framework_exporter.generators.htmx_generator import HTMXGenerator
from polyglot_framework_exporter.generators.qwik_generator import QwikGenerator
from polyglot_framework_exporter.mcp_server import MCPServer
from polyglot_framework_exporter.transpiler import ProjectAST


class TestQwikGenerator:
    """Test Qwik City 1.x resumable framework generator."""

    def test_qwik_registry_lookup(self) -> None:
        assert "qwik" in list_generators()
        gen = get_generator("qwik")
        assert isinstance(gen, QwikGenerator)
        assert gen.name == "qwik"

        alias_gen = get_generator("qwikcity")
        assert isinstance(alias_gen, QwikGenerator)

    def test_qwik_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        gen = QwikGenerator()
        files = gen.generate(sample_ast)

        assert isinstance(files, dict)
        assert len(files) >= 9

        # Verify key Qwik files
        assert "package.json" in files
        assert "tsconfig.json" in files
        assert "vite.config.ts" in files
        assert "src/root.tsx" in files
        assert "src/entry.ssr.tsx" in files
        assert "src/routes/layout.tsx" in files
        assert "src/routes/index.tsx" in files
        assert "src/global.css" in files
        assert "README.md" in files

        # Validate package.json
        pkg = json.loads(files["package.json"])
        assert "@builder.io/qwik" in pkg["devDependencies"]
        assert "@builder.io/qwik-city" in pkg["devDependencies"]
        assert "vite" in pkg["devDependencies"]

        # Validate vite.config.ts
        vite_cfg = files["vite.config.ts"]
        assert "qwikCity" in vite_cfg
        assert "qwikVite" in vite_cfg

        # Validate root.tsx
        root_tsx = files["src/root.tsx"]
        assert "QwikCityProvider" in root_tsx
        assert "RouterOutlet" in root_tsx

        # Validate routes/index.tsx (resumable components and signals)
        index_tsx = files["src/routes/index.tsx"]
        assert "component$" in index_tsx
        assert "useSignal" in index_tsx
        assert "onClick$" in index_tsx

    def test_qwik_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        gen = QwikGenerator()
        out_dir = temp_dir / "qwik_output"
        files = gen.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()
        assert (out_dir / "src" / "routes" / "index.tsx").exists()
        assert (out_dir / "src" / "root.tsx").exists()


class TestHTMXGenerator:
    """Test HTMX 2.0 + Alpine.js + Tailwind hypermedia generator."""

    def test_htmx_registry_lookup(self) -> None:
        assert "htmx" in list_generators()
        gen = get_generator("htmx")
        assert isinstance(gen, HTMXGenerator)
        assert gen.name == "htmx"

        alias_gen = get_generator("alpine_htmx")
        assert isinstance(alias_gen, HTMXGenerator)

    def test_htmx_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        gen = HTMXGenerator()
        files = gen.generate(sample_ast)

        assert isinstance(files, dict)
        assert len(files) >= 4

        # Key HTMX hypermedia files
        assert "public/index.html" in files
        assert "server.py" in files
        assert "package.json" in files
        assert "README.md" in files

        # Validate public/index.html contains HTMX & Alpine.js directives
        html_code = files["public/index.html"]
        assert "htmx.org" in html_code
        assert "alpinejs" in html_code
        assert "cdn.tailwindcss.com" in html_code
        assert "hx-get=" in html_code
        assert "x-data=" in html_code

        # Validate server.py is executable pure Python stdlib server
        server_py = files["server.py"]
        assert "ThreadingTCPServer" in server_py or "SimpleHTTPRequestHandler" in server_py
        assert "/partials/system-info" in server_py
        assert "/api/health" in server_py

    def test_htmx_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        gen = HTMXGenerator()
        out_dir = temp_dir / "htmx_output"
        gen.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "public" / "index.html").exists()
        assert (out_dir / "server.py").exists()


class TestDeployConfigs:
    """Test multi-target deployment configuration generator."""

    @pytest.mark.parametrize("fw", ["vite_react", "astro", "nextjs", "bun_hono", "deno_fresh", "htmx", "qwik"])
    def test_generate_all_deploy_configs(self, fw: str, sample_ast: ProjectAST) -> None:
        configs = generate_all_deploy_configs(fw, sample_ast)

        assert "Dockerfile" in configs
        assert ".dockerignore" in configs
        assert "netlify.toml" in configs
        assert "vercel.json" in configs
        assert "wrangler.jsonc" in configs
        assert ".github/workflows/deploy.yml" in configs

        # Check Dockerfile content
        dockerfile = configs["Dockerfile"]
        assert "FROM" in dockerfile
        assert "EXPOSE" in dockerfile

        # Check Netlify config
        netlify = configs["netlify.toml"]
        assert "[build]" in netlify
        assert "command =" in netlify
        assert "publish =" in netlify

        # Check Vercel config is valid JSON
        vercel_data = json.loads(configs["vercel.json"])
        assert "buildCommand" in vercel_data

        # Check Wrangler config is valid JSON
        wrangler_data = json.loads(configs["wrangler.jsonc"])
        assert "pages_build_output_dir" in wrangler_data

        # Check GitHub Actions workflow
        gh_workflow = configs[".github/workflows/deploy.yml"]
        assert "name: CI / Deploy" in gh_workflow

    def test_dockerfile_runtime_variants(self) -> None:
        df_python = generate_dockerfile("htmx")
        assert "python:3.12-alpine" in df_python

        df_bun = generate_dockerfile("bun_hono")
        assert "oven/bun" in df_bun

        df_deno = generate_dockerfile("deno_fresh")
        assert "denoland/deno" in df_deno

        df_node = generate_dockerfile("nextjs")
        assert "node:20-alpine" in df_node

        df_static = generate_dockerfile("vite_react")
        assert "nginx:alpine" in df_static


class TestDeployConfigsMCPAndCLI:
    """Test MCP tool and CLI integration for deployment configs."""

    def test_mcp_exporter_deploy_configs(self) -> None:
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {
                "name": "exporter_deploy_configs",
                "arguments": {"framework": "nextjs", "project_name": "production-app"}
            }
        }
        res = server.handle_request(req)
        assert res is not None
        assert "result" in res
        content = res["result"]["content"][0]["text"]
        data = json.loads(content)
        assert data["framework"] == "nextjs"
        assert "Dockerfile" in data["manifests"]
        assert "netlify.toml" in data["manifests"]
        assert "configs" in data
