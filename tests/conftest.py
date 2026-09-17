"""Pytest configuration, shared fixtures, and testing utilities for polyglot-framework-exporter."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from polyglot_framework_exporter.compat import ensure_directory, normalize_path
from polyglot_framework_exporter.transpiler import ComponentNode, ProjectAST, get_theme
from polyglot_framework_exporter.ui_server import create_ui_server


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory cleaned up after test completion."""
    temp_path = Path(tempfile.mkdtemp(prefix="polyglot_test_"))
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_ast() -> ProjectAST:
    """Provide a standard ProjectAST with multiple sections for testing generators."""
    hero_node = ComponentNode(
        id="hero",
        type="hero",
        data={
            "title": "Welcome to Polyglot Exporter",
            "subtitle": "Universal framework scaffolding engine",
            "primary_cta": {"label": "Get Started", "href": "#explore"},
            "secondary_cta": {"label": "Documentation", "href": "#docs"},
        },
        order=0,
    )

    features_node = ComponentNode(
        id="features",
        type="features",
        data={
            "title": "Key Capabilities",
            "subtitle": "Why developers choose Polyglot",
            "items": [
                {"icon": "zap", "title": "Zero Dependencies", "description": "Pure Python stdlib only."},
                {"icon": "rocket", "title": "9 Frameworks", "description": "Astro, Next.js, Vite, Svelte, and more."},
                {"icon": "palette", "title": "6 Master Themes", "description": "Material 3, Obsidian Gold, Midnight Neon."},
            ],
        },
        order=1,
    )

    cta_node = ComponentNode(
        id="cta",
        type="cta",
        data={
            "title": "Start Building Today",
            "subtitle": "Download your framework bundle in 1 click",
            "primary_cta": {"label": "Download ZIP", "href": "/api/download-zip"},
        },
        order=2,
    )

    ast = ProjectAST(
        title="Test Polyglot App",
        description="A test application scaffolded with polyglot-framework-exporter",
        theme="light_material",
        author="Polyglot Team",
        version="0.1.0",
        sections=[hero_node, features_node, cta_node],
    )
    return ast


@pytest.fixture
def sample_html() -> str:
    """Provide a semantic HTML sample string."""
    return """
    <section class="hero-section" style="background-color: #f8f9fa; padding: 40px;">
        <h1 class="title">Polyglot Multi-Framework Exporter</h1>
        <p class="subtitle">Scaffold modern apps instantly across 9 frameworks.</p>
        <button class="btn-primary" onclick="alert('Hello')">Get Started</button>
        <img src="/logo.svg" alt="Polyglot Logo" width="120" height="120">
    </section>
    """


@pytest.fixture
def sample_markdown() -> str:
    """Provide a Markdown document with YAML frontmatter."""
    return """---
title: My Markdown Project
description: High-speed documentation and web portal
theme: obsidian_gold
version: 1.0.0
---

# My Markdown Project

Welcome to the markdown-driven framework exporter.

## Key Features

- Pure Python stdlib
- Multi-Framework Output
- Master Theme Design Tokens

[Explore Documentation](https://github.com/polyglot-framework)
"""


@pytest.fixture
def sample_jsx_component() -> str:
    """Provide a sample React JSX component code snippet."""
    return """import React, { useState } from 'react';

export function CounterWidget({ initialValue = 0 }: { initialValue?: number }) {
  const [count, setCount] = useState(initialValue);

  return (
    <div className="counter-card p-6 bg-white rounded-xl shadow-md">
      <h3 className="text-xl font-bold">Counter: {count}</h3>
      <div className="flex gap-2 mt-4">
        <button onClick={() => setCount(count + 1)} className="btn-primary">Increment</button>
        <button onClick={() => setCount(0)} className="btn-secondary">Reset</button>
      </div>
    </div>
  );
}
"""


@pytest.fixture
def live_ui_server() -> Generator[str, None, None]:
    """Start an ephemeral ThreadingHTTPServer in the background and yield its base URL."""
    server = create_ui_server(host="127.0.0.1", port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    time.sleep(0.1)
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
