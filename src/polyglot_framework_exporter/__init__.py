"""Polyglot Framework Exporter.

Export web and native projects to React 19, Vue 3.5, Svelte 5, SolidJS,
Angular 18+, Astro 4, Qwik, Next.js 15, Flutter 3.24+, SwiftUI, and Jetpack Compose
with Material 3 influenced dynamic color tokens and clean, deterministic ZIP packaging.

Pure Python standard library only (zero external runtime dependencies).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Metadata
__version__ = "0.1.0"
__author__ = "Polyglot Exporter Team"
__license__ = "Apache-2.0"
__description__ = "Polyglot Studio - Universal Multi-Framework Scaffolder & AST Transpiler (design influenced by Material 3)"

# Submodule exports
from .zip_bundler import (
    ZipBundler,
    build_zip_bundle,
    create_project_zip,
    extract_zip,
    inspect_zip,
    normalize_zip_path,
)

from .mcp_server import (
    FRAMEWORK_CATALOG,
    THEME_PRESETS,
    HTMLStyleParser,
    HTMLTranspiler,
    MCPServer,
    generate_project_scaffold,
    get_system_diagnostics,
    run_mcp_server,
    validate_project_scaffold,
)

from .cli import main


# ---------------------------------------------------------------------------
# High-Level Public API Functions
# ---------------------------------------------------------------------------

def get_supported_frameworks(category: str = "all") -> Dict[str, Dict[str, Any]]:
    """Return dictionary of supported frameworks with metadata and capabilities.

    Args:
        category: Filter by category ('all', 'spa', 'meta', 'native', 'static', 'web').
    """
    cat_norm = category.lower().strip()
    if cat_norm == "all":
        return dict(FRAMEWORK_CATALOG)
    return {k: v for k, v in FRAMEWORK_CATALOG.items() if v.get("category") == cat_norm}


def convert_html(
    html_code: str,
    target_framework: str = "react",
    component_name: str = "ExportedComponent",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Transpile arbitrary HTML markup or Tailwind snippet into idiomatic component code.

    Args:
        html_code: Raw HTML markup string.
        target_framework: Target framework ('react', 'vue', 'svelte', 'solid', 'angular', 'astro', 'qwik', 'vanilla', 'flutter', 'swiftui', 'compose').
        component_name: Desired component name in PascalCase.
        options: Optional settings such as {'typescript': bool, 'theme': str}.

    Returns:
        Dictionary containing component_name, filename, language, framework, and transpiled code.
    """
    return HTMLTranspiler.transpile(
        html_code=html_code,
        framework=target_framework,
        component_name=component_name,
        options=options,
    )


def export_project(
    framework: str,
    project_name: str = "my-app",
    theme: str = "system",
    output_dir: Optional[Union[str, Path]] = None,
    options: Optional[Dict[str, Any]] = None,
    as_zip: bool = False,
    zip_path: Optional[Union[str, Path]] = None,
    deterministic: bool = True,
) -> Union[Dict[str, str], bytes, Path]:
    """Generate a complete project scaffold for target framework and theme.

    Args:
        framework: Target framework identifier.
        project_name: Name of project directory and package.
        theme: Material 3 theme preset ('system', 'light', 'dark', 'ocean', 'emerald', 'crimson', 'amber', 'purple').
        output_dir: If specified, writes project files to disk at this directory.
        options: Optional generator configuration.
        as_zip: If True, packages project into a deterministic ZIP archive.
        zip_path: Optional path to write ZIP bundle to disk.
        deterministic: Whether to use reproducible timestamps and file ordering in ZIP.

    Returns:
        Dict[str, str] of file tree, or bytes / Path if as_zip is True.
    """
    file_tree = generate_project_scaffold(
        framework=framework,
        project_name=project_name,
        theme=theme,
        options=options,
    )

    # Write files to disk directory if requested
    if output_dir is not None:
        target_p = Path(output_dir)
        target_p.mkdir(parents=True, exist_ok=True)
        for rel_path, content in file_tree.items():
            dest = target_p / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    # If ZIP bundle is requested
    if as_zip:
        return build_zip_bundle(
            file_tree=file_tree,  # type: ignore[arg-type]
            project_name=project_name,
            framework=framework,
            theme=theme,
            output_path=zip_path,
            deterministic=deterministic,
        )

    return file_tree


__all__ = [
    # Metadata
    "__version__",
    "__author__",
    "__license__",
    "__description__",
    # Public API
    "export_project",
    "convert_html",
    "get_supported_frameworks",
    "build_zip_bundle",
    "create_project_zip",
    "extract_zip",
    "inspect_zip",
    "validate_project_scaffold",
    "get_system_diagnostics",
    "ZipBundler",
    "MCPServer",
    "run_mcp_server",
    "main",
    # Catalogs
    "FRAMEWORK_CATALOG",
    "THEME_PRESETS",
]
