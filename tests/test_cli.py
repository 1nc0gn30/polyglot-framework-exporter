"""Tests for polyglot_framework_exporter.cli module."""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import pytest

from polyglot_framework_exporter.cli import (
    build_cli_parser,
    handle_convert,
    handle_diagnostics,
    handle_export,
    handle_frameworks,
    main,
)


class TestCLIParser:
    """Test CLI argument parsing and configuration."""

    def test_build_cli_parser_subcommands(self) -> None:
        parser = build_cli_parser()
        assert parser.prog == "polyglot-framework-exporter"

        # Check export args with valid theme from THEME_PRESETS
        args = parser.parse_args(["export", "astro", "--theme", "light", "--zip"])
        assert args.command == "export"
        assert args.framework == "astro"
        assert args.theme == "light"
        assert args.zip is True

        # Check convert args
        args = parser.parse_args(["convert", "-i", "<button>Click</button>", "-t", "svelte"])
        assert args.command == "convert"
        assert args.input == "<button>Click</button>"
        assert args.to == "svelte"

        # Check frameworks args
        args = parser.parse_args(["frameworks", "--json"])
        assert args.command == "frameworks"
        assert args.json is True

        # Check diagnostics args
        args = parser.parse_args(["diagnostics", "--json"])
        assert args.command == "diagnostics"
        assert args.json is True


class TestCLIExecution:
    """Test executing CLI subcommands in memory."""

    def test_cli_frameworks_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["frameworks", "--json"])
        handle_frameworks(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "astro" in data
        assert "react" in data

    def test_cli_diagnostics_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["diagnostics", "--json"])
        handle_diagnostics(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "exporter_version" in data
        assert "platform" in data

    def test_cli_export_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["export", "astro", "--dry-run", "--name", "dry-app"])
        handle_export(args)

        captured = capsys.readouterr()
        assert "Dry run" in captured.out or "package.json" in captured.out

    def test_cli_export_zip(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        zip_path = temp_dir / "cli_test.zip"
        parser = build_cli_parser()
        args = parser.parse_args(["export", "astro", "--zip", "--output", str(zip_path), "--name", "zip-app"])
        handle_export(args)

        assert zip_path.exists()
        assert zip_path.stat().st_size > 0

    def test_cli_convert_input(self, capsys: pytest.CaptureFixture[str], sample_html: str) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["convert", "-i", sample_html, "-t", "react", "-n", "TestButton"])
        handle_convert(args)

        captured = capsys.readouterr()
        assert "Transpiled" in captured.out or "export" in captured.out or "CODE" in captured.out
