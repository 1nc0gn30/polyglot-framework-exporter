"""Tests for SolidStart 1.0 (SolidJS) generator in polyglot_framework_exporter."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.generators import get_generator, list_generators
from polyglot_framework_exporter.generators.solidstart_generator import SolidStartGenerator
from polyglot_framework_exporter.mcp_server import generate_project_scaffold
from polyglot_framework_exporter.transpiler import ProjectAST


class TestSolidStartGenerator:
    """Test SolidStart 1.0 full-stack framework generator."""

    def test_solidstart_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = SolidStartGenerator()
        assert generator.name == "solidstart"
        assert "SolidStart" in generator.display_name

        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert len(files) >= 12

        # Check required configuration and source files
        assert "package.json" in files
        assert "app.config.ts" in files
        assert "tsconfig.json" in files
        assert "tailwind.config.mjs" in files
        assert "src/app.css" in files
        assert "src/entry-client.tsx" in files
        assert "src/entry-server.tsx" in files
        assert "src/app.tsx" in files
        assert "src/routes/index.tsx" in files
        assert "src/routes/[...404].tsx" in files
        assert "src/components/Header.tsx" in files
        assert "src/components/Hero.tsx" in files
        assert "src/components/Features.tsx" in files
        assert "src/components/Footer.tsx" in files
        assert "README.md" in files

        # Check package.json contents
        pkg = json.loads(files["package.json"])
        assert pkg["name"] == sample_ast.title.lower().replace(" ", "-").replace("_", "-")
        assert "solid-js" in pkg["dependencies"]
        assert "@solidjs/start" in pkg["dependencies"]
        assert "vinxi" in pkg["dependencies"]
        assert pkg["scripts"]["dev"] == "vinxi dev"
        assert pkg["scripts"]["build"] == "vinxi build"

        # Check app.config.ts
        app_cfg = files["app.config.ts"]
        assert '@solidjs/start/config' in app_cfg
        assert 'export default defineConfig' in app_cfg

        # Check tsconfig.json
        tsconfig = json.loads(files["tsconfig.json"])
        assert tsconfig["compilerOptions"]["jsx"] == "preserve"
        assert tsconfig["compilerOptions"]["jsxImportSource"] == "solid-js"

        # Check reactive components and signals
        hero_tsx = files["src/components/Hero.tsx"]
        assert 'createSignal' in hero_tsx
        assert 'setCount' in hero_tsx

        feat_tsx = files["src/components/Features.tsx"]
        assert '<For each={FEATURES}>' in feat_tsx

    def test_solidstart_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        generator = SolidStartGenerator()
        out_dir = temp_dir / "solid_export"
        files = generator.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()
        assert (out_dir / "app.config.ts").exists()
        assert (out_dir / "src/routes/index.tsx").exists()
        assert (out_dir / "README.md").exists()

        # Content match verification
        with open(out_dir / "package.json", "r", encoding="utf-8") as f:
            disk_pkg = json.load(f)
            assert disk_pkg["name"] == json.loads(files["package.json"])["name"]

    def test_solidstart_registry_lookup(self) -> None:
        assert "solidstart" in list_generators()
        gen_inst = get_generator("solidstart")
        assert isinstance(gen_inst, SolidStartGenerator)

        # Test aliases
        assert isinstance(get_generator("solid"), SolidStartGenerator)
        assert isinstance(get_generator("solidjs"), SolidStartGenerator)

    def test_generate_project_scaffold_delegation(self) -> None:
        files = generate_project_scaffold("solidstart", project_name="acme-solid")
        assert "package.json" in files
        assert "app.config.ts" in files
        assert "src/app.tsx" in files
        pkg = json.loads(files["package.json"])
        assert "solid-js" in pkg["dependencies"]
