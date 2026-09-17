"""Tests for polyglot_framework_exporter.transpiler module."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.transpiler import (
    ComponentNode,
    ProjectAST,
    ThemeConfig,
    get_theme,
    transpile,
)


class TestThemeSystem:
    """Test Master Theme token generation and CSS properties."""

    def test_get_theme_default(self) -> None:
        theme = get_theme("light_material")
        assert theme.name == "light_material"
        assert theme.is_dark is False
        assert theme.accent_primary == "#4f46e5"

    def test_get_theme_dark_presets(self) -> None:
        obsidian = get_theme("obsidian_gold")
        assert obsidian.is_dark is True
        assert obsidian.accent_primary == "#eab308"

        neon = get_theme("midnight_neon")
        assert neon.is_dark is True
        assert neon.accent_primary == "#06b6d4"

        acid = get_theme("acid_grid")
        assert acid.is_dark is True
        assert acid.accent_primary == "#bef264"

    def test_get_theme_fallback(self) -> None:
        theme = get_theme("unknown_preset_123")
        assert theme is not None
        assert theme.name == "obsidian_gold"

    def test_to_css_variables_and_string(self) -> None:
        theme = get_theme("light_material")
        css_vars = theme.to_css_variables()
        assert "--bg-primary" in css_vars
        assert "--accent-primary" in css_vars
        assert css_vars["--accent-primary"] == "#4f46e5"

        css_string = theme.to_css_string()
        assert ":root {" in css_string
        assert "--accent-primary: #4f46e5;" in css_string


class TestProjectAST:
    """Test ProjectAST serialization, deserialization, and manipulation."""

    def test_ast_initialization_and_theme(self, sample_ast: ProjectAST) -> None:
        assert sample_ast.title == "Test Polyglot App"
        assert len(sample_ast.sections) >= 3
        theme = sample_ast.get_theme()
        assert theme.name == "light_material"

    def test_to_dict_and_to_json(self, sample_ast: ProjectAST) -> None:
        d = sample_ast.to_dict()
        assert isinstance(d, dict)
        assert d["title"] == "Test Polyglot App"
        assert "sections" in d

        json_str = sample_ast.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["title"] == "Test Polyglot App"

    def test_from_dict_roundtrip(self, sample_ast: ProjectAST) -> None:
        d = sample_ast.to_dict()
        reconstructed = ProjectAST.from_dict(d)
        assert reconstructed.title == sample_ast.title
        assert len(reconstructed.sections) == len(sample_ast.sections)

    def test_to_semantic_html(self, sample_ast: ProjectAST) -> None:
        html = sample_ast.to_semantic_html()
        assert "<!DOCTYPE html>" in html
        assert "<title>Test Polyglot App</title>" in html
        assert "Welcome to Polyglot Exporter" in html


class TestUniversalTranspilation:
    """Test transpile() universal parser across HTML, Markdown, and JSON."""

    def test_transpile_from_dict(self) -> None:
        data = {
            "title": "Dict App",
            "description": "Scaffolded from dict",
            "theme": "midnight_neon",
        }
        ast = transpile(data)
        assert ast.title == "Dict App"
        assert ast.theme == "midnight_neon"

    def test_transpile_from_json_string(self) -> None:
        raw_json = json.dumps({
            "title": "JSON App",
            "description": "From JSON string",
            "theme": "acid_grid",
        })
        ast = transpile(raw_json)
        assert ast.title == "JSON App"
        assert ast.theme == "acid_grid"

    def test_transpile_from_html(self, sample_html: str) -> None:
        ast = transpile(sample_html, theme="light_material")
        assert ast is not None
        assert isinstance(ast, ProjectAST)
        assert len(ast.sections) > 0

    def test_transpile_from_markdown(self, sample_markdown: str) -> None:
        ast = transpile(sample_markdown)
        assert ast is not None
        assert isinstance(ast, ProjectAST)
        assert "Markdown Project" in ast.title or len(ast.sections) > 0
