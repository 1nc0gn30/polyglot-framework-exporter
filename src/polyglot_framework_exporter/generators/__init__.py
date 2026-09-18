"""Framework Generators Registry for polyglot-framework-exporter.

Exports all 9 production-grade framework generator implementations:
- Astro 5 (`astro`)
- Next.js 15 App Router (`nextjs`)
- Vite 6 + React 19 (`vite_react`)
- SvelteKit 2 + Svelte 5 (`svelte`)
- Nuxt 3 (`nuxt`)
- Deno Fresh (`deno_fresh`)
- Remix / React Router v7 (`remix`)
- Tauri v2 Desktop (`tauri`)
- Electron Desktop (`electron`)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from ..compat import ensure_directory
from ..transpiler import ProjectAST
from .astro_generator import AstroGenerator
from .bun_hono_generator import BunHonoGenerator
from .deno_fresh_generator import DenoFreshGenerator
from .electron_generator import ElectronGenerator
from .htmx_generator import HTMXGenerator
from .nextjs_generator import NextjsGenerator
from .nuxt_generator import NuxtGenerator
from .qwik_generator import QwikGenerator
from .remix_generator import RemixGenerator
from .solidstart_generator import SolidStartGenerator
from .svelte_generator import SvelteGenerator
from .tauri_generator import TauriGenerator
from .vite_react_generator import ViteReactGenerator

# Generator Registry
GENERATORS: Dict[str, Any] = {
    "astro": AstroGenerator,
    "bun_hono": BunHonoGenerator,
    "htmx": HTMXGenerator,
    "nextjs": NextjsGenerator,
    "vite_react": ViteReactGenerator,
    "qwik": QwikGenerator,
    "svelte": SvelteGenerator,
    "solidstart": SolidStartGenerator,
    "nuxt": NuxtGenerator,
    "deno_fresh": DenoFreshGenerator,
    "remix": RemixGenerator,
    "tauri": TauriGenerator,
    "electron": ElectronGenerator,
}

# Convenient aliases
ALIASES: Dict[str, str] = {
    "next": "nextjs",
    "react": "vite_react",
    "vite": "vite_react",
    "sveltekit": "svelte",
    "solid": "solidstart",
    "solidjs": "solidstart",
    "vue": "nuxt",
    "fresh": "deno_fresh",
    "deno": "deno_fresh",
    "react_router": "remix",
    "hono": "bun_hono",
    "bun": "bun_hono",
    "qwikcity": "qwik",
    "alpine_htmx": "htmx",
    "hypermedia": "htmx",
}


def list_generators() -> List[str]:
    """Return a list of all supported framework generator identifiers."""
    return list(GENERATORS.keys())


def get_generator(name: str) -> Any:
    """Retrieve generator class by name or alias.
    
    Raises:
        ValueError: If framework generator name is unrecognized.
    """
    key = name.lower().strip().replace("-", "_")
    resolved_key = ALIASES.get(key, key)
    
    if resolved_key not in GENERATORS:
        valid = ", ".join(list_generators())
        raise ValueError(f"Unknown framework generator: {name!r}. Supported frameworks: {valid}")
        
    return GENERATORS[resolved_key]()


def generate_all(
    ast: ProjectAST,
    output_base_dir: Union[str, Path],
    frameworks: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, str]]:
    """Generate all specified frameworks (or all 9 by default) under output_base_dir.
    
    Returns a dictionary mapping framework names to their generated files dict.
    """
    target_frameworks = frameworks or list_generators()
    base_path = Path(output_base_dir)
    ensure_directory(base_path)
    
    results: Dict[str, Dict[str, str]] = {}
    for fw_name in target_frameworks:
        gen = get_generator(fw_name)
        fw_out_dir = base_path / fw_name
        generated_files = gen.generate(ast, output_dir=fw_out_dir, options=options)
        results[fw_name] = generated_files
        
    return results


def generate(
    framework: str,
    project_name: str = "my-app",
    theme: str = "obsidian_gold",
    options: Optional[Dict[str, Any]] = None,
    ast: Optional[ProjectAST] = None,
) -> Dict[str, str]:
    """Generate project files for a specific framework using ProjectAST or scaffold defaults."""
    gen = get_generator(framework)
    target_ast = ast or ProjectAST(title=project_name, theme=theme)
    return gen.generate(target_ast, options=options)


__all__ = [
    "AstroGenerator",
    "BunHonoGenerator",
    "NextjsGenerator",
    "ViteReactGenerator",
    "SvelteGenerator",
    "NuxtGenerator",
    "DenoFreshGenerator",
    "RemixGenerator",
    "TauriGenerator",
    "ElectronGenerator",
    "GENERATORS",
    "get_generator",
    "list_generators",
    "generate",
    "generate_all",
]
