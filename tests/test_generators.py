"""Tests for framework generators in polyglot_framework_exporter.generators."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.generators.astro_generator import AstroGenerator
from polyglot_framework_exporter.generators.nextjs_generator import NextjsGenerator
from polyglot_framework_exporter.generators.vite_react_generator import ViteReactGenerator
from polyglot_framework_exporter.generators.svelte_generator import SvelteGenerator
from polyglot_framework_exporter.generators.nuxt_generator import NuxtGenerator
from polyglot_framework_exporter.generators.deno_fresh_generator import DenoFreshGenerator
from polyglot_framework_exporter.transpiler import ProjectAST


class TestAstroGenerator:
    """Test Astro 5 project generator."""

    def test_astro_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = AstroGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert len(files) > 5

        # Key Astro files
        assert "package.json" in files
        assert "astro.config.mjs" in files
        assert "tailwind.config.mjs" in files
        assert "src/pages/index.astro" in files

        # Validate package.json
        pkg = json.loads(files["package.json"])
        assert "astro" in pkg["dependencies"]
        assert pkg["scripts"]["dev"] == "astro dev"

    def test_astro_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        generator = AstroGenerator()
        out_dir = temp_dir / "astro_output"
        files = generator.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()
        assert (out_dir / "astro.config.mjs").exists()
        assert (out_dir / "src" / "pages" / "index.astro").exists()


class TestNextjsGenerator:
    """Test Next.js 15 App Router project generator."""

    def test_nextjs_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = NextjsGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "next.config.ts" in files or "next.config.mjs" in files
        assert "app/page.tsx" in files or "src/app/page.tsx" in files

        pkg = json.loads(files["package.json"])
        assert "next" in pkg["dependencies"]
        assert "react" in pkg["dependencies"]

    def test_nextjs_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        generator = NextjsGenerator()
        out_dir = temp_dir / "nextjs_output"
        files = generator.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()


class TestViteReactGenerator:
    """Test Vite + React 19 project generator."""

    def test_vite_react_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = ViteReactGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "vite.config.ts" in files
        assert "src/App.tsx" in files

        pkg = json.loads(files["package.json"])
        assert "react" in pkg["dependencies"]
        assert "vite" in pkg["devDependencies"]

    def test_vite_react_generate_to_disk(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        generator = ViteReactGenerator()
        out_dir = temp_dir / "vite_react_output"
        generator.generate(sample_ast, output_dir=out_dir)

        assert out_dir.exists()
        assert (out_dir / "package.json").exists()
        assert (out_dir / "src" / "App.tsx").exists()


class TestSvelteGenerator:
    """Test SvelteKit 2 / Svelte 5 generator."""

    def test_svelte_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = SvelteGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files

        pkg = json.loads(files["package.json"])
        assert "svelte" in pkg["devDependencies"] or "svelte" in pkg["dependencies"]


class TestNuxtGenerator:
    """Test Nuxt 3 project generator."""

    def test_nuxt_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = NuxtGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "nuxt.config.ts" in files
        pkg = json.loads(files["package.json"])
        assert "nuxt" in pkg["devDependencies"] or "nuxt" in pkg["dependencies"]


class TestDenoFreshGenerator:
    """Test Deno Fresh generator."""

    def test_deno_fresh_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        generator = DenoFreshGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "deno.json" in files
        assert "fresh.config.ts" in files or "main.ts" in files or "dev.ts" in files


class TestRemixGenerator:
    """Test Remix / React Router v7 generator."""

    def test_remix_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        from polyglot_framework_exporter.generators.remix_generator import RemixGenerator
        generator = RemixGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "vite.config.ts" in files
        assert "app/root.tsx" in files
        assert "app/routes/_index.tsx" in files

        pkg = json.loads(files["package.json"])
        assert "@remix-run/react" in pkg["dependencies"]


class TestTauriGenerator:
    """Test Tauri v2 desktop generator."""

    def test_tauri_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        from polyglot_framework_exporter.generators.tauri_generator import TauriGenerator
        generator = TauriGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "src-tauri/Cargo.toml" in files
        assert "src-tauri/tauri.conf.json" in files
        assert "src/App.tsx" in files

        tauri_conf = json.loads(files["src-tauri/tauri.conf.json"])
        assert tauri_conf["productName"] == sample_ast.title


class TestElectronGenerator:
    """Test Electron desktop generator."""

    def test_electron_generate_in_memory(self, sample_ast: ProjectAST) -> None:
        from polyglot_framework_exporter.generators.electron_generator import ElectronGenerator
        generator = ElectronGenerator()
        files = generator.generate(sample_ast)

        assert isinstance(files, dict)
        assert "package.json" in files
        assert "main.js" in files
        assert "preload.js" in files
        assert "index.html" in files
        assert "renderer.js" in files
        assert "styles.css" in files


class TestBatchGeneratorRegistry:
    """Test framework generator registry and batch generate_all."""

    def test_registry_functions(self) -> None:
        from polyglot_framework_exporter.generators import list_generators, get_generator
        frameworks = list_generators()
        assert len(frameworks) >= 10
        assert "astro" in frameworks
        assert "nextjs" in frameworks
        assert "tauri" in frameworks
        assert "electron" in frameworks
        assert "bun_hono" in frameworks

        gen = get_generator("bun_hono")
        assert gen.name == "bun_hono"
        alias_gen = get_generator("hono")
        assert alias_gen.name == "bun_hono"

    def test_generate_all(self, sample_ast: ProjectAST, temp_dir: Path) -> None:
        from polyglot_framework_exporter.generators import generate_all
        out_base = temp_dir / "all_exports"
        results = generate_all(sample_ast, output_base_dir=out_base, frameworks=["astro", "electron"])
        assert "astro" in results
        assert "electron" in results
        assert (out_base / "astro" / "package.json").exists()
        assert (out_base / "electron" / "main.js").exists()

