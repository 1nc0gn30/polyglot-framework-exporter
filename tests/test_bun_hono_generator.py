"""Tests for Bun + Hono 4 generator in polyglot_framework_exporter."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.generators.bun_hono_generator import BunHonoGenerator
from polyglot_framework_exporter.transpiler import ProjectAST


class TestBunHonoGenerator:
    """Test Bun + Hono 4 edge API and web framework generator."""

    def test_bun_hono_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = BunHonoGenerator()
        assert generator.name == "bun_hono"
        assert "Hono" in generator.display_name

        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert len(files) >= 6

        # Check required files
        assert "package.json" in files
        assert "tsconfig.json" in files
        assert "src/index.ts" in files
        assert "src/routes/api.ts" in files
        assert "src/views/home.ts" in files
        assert "README.md" in files

        # Check package.json contents
        pkg = json.loads(files["package.json"])
        assert pkg["name"] == sample_ast.title.lower().replace(" ", "-").replace("_", "-")
        assert "hono" in pkg["dependencies"]
        assert "zod" in pkg["dependencies"]
        assert "@hono/node-server" in pkg["dependencies"]
        assert pkg["scripts"]["dev"] == "bun run --hot src/index.ts"
        assert pkg["scripts"]["test"] == "bun test"

        # Check tsconfig.json
        tsconfig = json.loads(files["tsconfig.json"])
        assert tsconfig["compilerOptions"]["target"] == "ESNext"
        assert tsconfig["compilerOptions"]["jsxImportSource"] == "hono/jsx"

        # Check src/index.ts
        index_ts = files["src/index.ts"]
        assert "import { Hono } from \"hono\"" in index_ts
        assert "app.route(\"/api\", api)" in index_ts
        assert "export default {" in index_ts

        # Check src/routes/api.ts
        api_ts = files["src/routes/api.ts"]
        assert "api.get(\"/health\"" in api_ts
        assert "api.get(\"/info\"" in api_ts
        assert "api.get(\"/features\"" in api_ts
        assert "api.get(\"/pricing\"" in api_ts
        assert "api.post(\"/echo\"" in api_ts
        assert "echoSchema" in api_ts

        # Check home page template
        home_ts = files["src/views/home.ts"]
        assert "renderHomePage" in home_ts
        assert "Material 3" in home_ts
        assert "GET /api/health" in home_ts

        # Check README
        readme = files["README.md"]
        assert "bun run dev" in readme
        assert "curl http://localhost:3000/api/health" in readme

    def test_bun_hono_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        generator = BunHonoGenerator()
        out_dir = temp_dir / "bun_hono_export"

        files = generator.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()
        assert (out_dir / "tsconfig.json").exists()
        assert (out_dir / "src" / "index.ts").exists()
        assert (out_dir / "src" / "routes" / "api.ts").exists()
        assert (out_dir / "src" / "views" / "home.ts").exists()
        assert (out_dir / "README.md").exists()

        # Check file content matches
        written_pkg = json.loads((out_dir / "package.json").read_text(encoding="utf-8"))
        assert written_pkg["dependencies"]["hono"] == "^4.6.14"

    def test_bun_hono_via_registry(self, sample_ast: ProjectAST) -> None:
        from polyglot_framework_exporter.generators import get_generator, generate

        gen = get_generator("bun_hono")
        assert isinstance(gen, BunHonoGenerator)

        alias_gen = get_generator("bun")
        assert isinstance(alias_gen, BunHonoGenerator)

        files = generate("hono", ast=sample_ast)
        assert "src/routes/api.ts" in files
