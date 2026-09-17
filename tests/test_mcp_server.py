"""Tests for polyglot_framework_exporter.mcp_server module."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from polyglot_framework_exporter.mcp_server import (
    FRAMEWORK_CATALOG,
    THEME_PRESETS,
    HTMLStyleParser,
    HTMLTranspiler,
    MCPServer,
    generate_project_scaffold,
    get_system_diagnostics,
    validate_project_scaffold,
)


class TestFrameworkAndThemeCatalogs:
    """Test framework catalog and theme preset metadata."""

    def test_framework_catalog_entries(self) -> None:
        assert len(FRAMEWORK_CATALOG) >= 9
        assert "react" in FRAMEWORK_CATALOG
        assert "astro" in FRAMEWORK_CATALOG
        assert "nextjs" in FRAMEWORK_CATALOG
        assert "svelte" in FRAMEWORK_CATALOG
        assert "vue" in FRAMEWORK_CATALOG

        for fw_id, meta in FRAMEWORK_CATALOG.items():
            assert "name" in meta
            assert "category" in meta
            assert "language" in meta
            assert "description" in meta

    def test_theme_presets(self) -> None:
        assert len(THEME_PRESETS) >= 6
        assert "system" in THEME_PRESETS
        assert "light" in THEME_PRESETS
        assert "dark" in THEME_PRESETS

        for theme_id, tokens in THEME_PRESETS.items():
            assert "primary" in tokens
            assert "surface" in tokens


class TestHTMLStyleAndTranspiler:
    """Test HTML and inline style parsing and transpilation."""

    def test_parse_inline_style(self) -> None:
        style_str = "background-color: #1a73e8; font-size: 16px; --custom-var: 10px;"
        styles = HTMLStyleParser.parse_inline_style(style_str)
        assert styles.get("backgroundColor") == "#1a73e8"
        assert styles.get("fontSize") == "16px"
        assert styles.get("--custom-var") == "10px"

    def test_to_jsx_style(self) -> None:
        style_str = "color: red; margin-top: 20px;"
        jsx_style = HTMLStyleParser.to_jsx_style(style_str)
        assert "color: 'red'" in jsx_style
        assert "marginTop: '20px'" in jsx_style

    def test_transpile_to_react(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="react", component_name="HeroCard")
        assert res["framework"] == "react"
        assert "export const HeroCard" in res["code"] or "export default" in res["code"] or "function HeroCard" in res["code"]
        assert "className=" in res["code"]

    def test_transpile_to_vue(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="vue", component_name="HeroCard")
        assert res["framework"] == "vue"
        assert "<template>" in res["code"]
        assert "<script setup" in res["code"]

    def test_transpile_to_svelte(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="svelte", component_name="HeroCard")
        assert res["framework"] == "svelte"
        assert "<script" in res["code"]

    def test_transpile_to_astro(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="astro", component_name="HeroCard")
        assert res["framework"] == "astro"
        assert "---" in res["code"]

    def test_transpile_to_flutter(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="flutter", component_name="HeroCard")
        assert res["framework"] == "flutter"
        assert "Widget build" in res["code"]

    def test_transpile_to_swiftui(self, sample_html: str) -> None:
        res = HTMLTranspiler.transpile(sample_html, framework="swiftui", component_name="HeroCard")
        assert res["framework"] == "swiftui"
        assert "struct HeroCard: View" in res["code"]


class TestScaffoldGenerationAndValidation:
    """Test project scaffolding and validation functions."""

    def test_generate_project_scaffold(self) -> None:
        file_tree = generate_project_scaffold(
            framework="astro",
            project_name="test-astro-app",
            theme="light",
        )
        assert isinstance(file_tree, dict)
        assert "package.json" in file_tree
        assert len(file_tree) >= 4

    def test_validate_project_scaffold_valid(self, temp_dir: Path) -> None:
        proj_dir = temp_dir / "valid_project"
        proj_dir.mkdir()
        (proj_dir / "project.manifest.json").write_text('{"name": "valid-app"}')
        (proj_dir / "package.json").write_text(json.dumps({"name": "valid-app", "dependencies": {"react": "^19.0.0"}}))
        (proj_dir / "src").mkdir()
        (proj_dir / "src" / "App.tsx").write_text("export default function App() {}")
        (proj_dir / "README.md").write_text("# Valid App")

        report = validate_project_scaffold(proj_dir, framework="react")
        assert report["valid"] is True
        assert report["score"] > 50

    def test_get_system_diagnostics(self) -> None:
        diag = get_system_diagnostics(verbose=True)
        assert "exporter_version" in diag
        assert "platform" in diag
        assert "supported_frameworks_count" in diag
        assert diag["supported_frameworks_count"] >= 9


class TestMCPServerProtocol:
    """Test JSON-RPC 2.0 MCP server interface and tool execution."""

    def test_mcp_initialize(self) -> None:
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }
        res = server.handle_request(req)
        assert res is not None
        assert res["id"] == 1
        assert res["result"]["serverInfo"]["name"] == "polyglot-framework-exporter"
        assert "capabilities" in res["result"]

    def test_mcp_tools_list(self) -> None:
        server = MCPServer()
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        res = server.handle_request(req)
        assert res is not None
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "exporter_generate" in tool_names
        assert "exporter_supported_frameworks" in tool_names
        assert "exporter_convert_html" in tool_names
        assert "exporter_validate_scaffold" in tool_names
        assert "exporter_diagnostics" in tool_names

    def test_mcp_tool_call_supported_frameworks(self) -> None:
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "exporter_supported_frameworks",
                "arguments": {"category": "spa"}
            }
        }
        res = server.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False
        text_content = res["result"]["content"][0]["text"]
        data = json.loads(text_content)
        assert "frameworks" in data
        assert len(data["frameworks"]) > 0

    def test_mcp_tool_call_convert_html(self, sample_html: str) -> None:
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "exporter_convert_html",
                "arguments": {
                    "html_code": sample_html,
                    "target_framework": "react",
                    "component_name": "TestComponent"
                }
            }
        }
        res = server.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

    def test_mcp_unknown_method_error(self) -> None:
        server = MCPServer()
        req = {"jsonrpc": "2.0", "id": 5, "method": "unknown/method"}
        res = server.handle_request(req)
        assert res is not None
        assert "error" in res
        assert res["error"]["code"] == -32601
