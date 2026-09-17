"""Model Context Protocol (MCP) Server for Polyglot Framework Exporter.

Implements JSON-RPC 2.0 protocol over stdio for LLM / AI coding assistants.
Provides tool execution for framework scaffolding, HTML conversion, ZIP bundling,
project validation, and multi-OS diagnostics.

Pure Python standard library only (zero external runtime dependencies).
"""

from __future__ import annotations

import base64
import datetime
import html.parser
import io
import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Internal imports
from .zip_bundler import (
    ZipBundler,
    build_zip_bundle,
    inspect_zip,
)

# Logger setup - write exclusively to stderr so stdout JSON-RPC stream is untouched
logger = logging.getLogger("polyglot_framework_exporter.mcp")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[MCP %(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Supported Frameworks Metadata Catalog
# ---------------------------------------------------------------------------

FRAMEWORK_CATALOG: Dict[str, Dict[str, Any]] = {
    "react": {
        "id": "react",
        "name": "React 19 / 18",
        "category": "spa",
        "version": "19.0.0",
        "template": "vite-react-ts",
        "language": "TypeScript / JavaScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS v3/v4", "Material 3 Tokens", "CSS Modules", "Emotion"],
        "features": ["Vite Bundler", "React 19 Actions", "Component Tree", "M3 Color System", "Lucide Icons"],
        "description": "Modern React with TypeScript, Vite HMR, Material 3 dynamic color tokens, and Tailwind styling.",
    },
    "vue": {
        "id": "vue",
        "name": "Vue 3.5",
        "category": "spa",
        "version": "3.5.0",
        "template": "vite-vue-ts",
        "language": "TypeScript",
        "primary_extension": ".vue",
        "styling": ["Tailwind CSS", "Scoped CSS", "M3 Design Tokens"],
        "features": ["Composition API", "<script setup>", "Pinia Store", "Vue Router", "Vite Bundler"],
        "description": "Vue 3 Single-File Components using Composition API, Pinia, and Material Design 3 tokens.",
    },
    "svelte": {
        "id": "svelte",
        "name": "Svelte 5",
        "category": "spa",
        "version": "5.0.0",
        "template": "vite-svelte-ts",
        "language": "TypeScript",
        "primary_extension": ".svelte",
        "styling": ["Tailwind CSS", "Scoped Svelte CSS", "M3 Tokens"],
        "features": ["Svelte 5 Runes ($state, $derived)", "Zero Runtime Overhead", "Vite Bundler"],
        "description": "Svelte 5 components with modern runes reactivity model and Material 3 design system.",
    },
    "solid": {
        "id": "solid",
        "name": "SolidJS",
        "category": "spa",
        "version": "1.9.4",
        "template": "vite-solid-ts",
        "language": "TypeScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS", "M3 Tokens", "CSS Modules"],
        "features": ["Fine-grained Reactivity", "JSX without Virtual DOM", "Vite Bundler"],
        "description": "Ultra-fast fine-grained reactive components with JSX syntax and Material 3 design system.",
    },
    "solidstart": {
        "id": "solidstart",
        "name": "SolidStart 1.0 (SolidJS)",
        "category": "meta",
        "version": "1.0.10",
        "template": "solidstart-ts",
        "language": "TypeScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS", "M3 Tokens"],
        "features": ["SolidStart Full-Stack", "Fine-grained Reactivity", "Vinxi Bundler", "Zero Virtual DOM"],
        "description": "Ultra-fast full-stack SolidStart 1.0 application powered by SolidJS and Vinxi.",
    },
    "bun_hono": {
        "id": "bun_hono",
        "name": "Bun + Hono 4",
        "category": "meta",
        "version": "4.6.14",
        "template": "bun-hono-ts",
        "language": "TypeScript",
        "primary_extension": ".ts",
        "styling": ["Tailwind CSS", "M3 Tokens"],
        "features": ["Bun Runtime", "Hono 4 Web API", "Edge Microservices", "Zod Validation"],
        "description": "Ultra-fast server-side TypeScript edge microservice and web server powered by Bun and Hono 4.",
    },
    "angular": {
        "id": "angular",
        "name": "Angular 18 / 19",
        "category": "spa",
        "version": "18.2.0",
        "template": "angular-standalone",
        "language": "TypeScript",
        "primary_extension": ".ts",
        "styling": ["Angular Material", "SCSS / CSS", "Tailwind CSS"],
        "features": ["Standalone Components", "Angular Signals", "Control Flow Syntax (@if, @for)", "RxJS"],
        "description": "Enterprise Angular with Standalone Components, reactive Signals, and Material 3 theme.",
    },
    "astro": {
        "id": "astro",
        "name": "Astro 4",
        "category": "static",
        "version": "4.15.0",
        "template": "astro-tailwind",
        "language": "TypeScript / Astro",
        "primary_extension": ".astro",
        "styling": ["Tailwind CSS", "Scoped CSS", "M3 Design Tokens"],
        "features": ["Islands Architecture", "Zero JS by default", "Multi-framework hydration", "Content Collections"],
        "description": "Content-focused Astro 4 site with Islands Architecture, client hydration, and M3 design tokens.",
    },
    "qwik": {
        "id": "qwik",
        "name": "Qwik City",
        "category": "meta",
        "version": "1.5.0",
        "template": "qwik-city",
        "language": "TypeScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS", "M3 Tokens"],
        "features": ["Resumability (Zero hydration)", "Fine-grained lazy loading", "Vite Bundler"],
        "description": "Instant-loading resumable Qwik components with Material 3 styling tokens.",
    },
    "nextjs": {
        "id": "nextjs",
        "name": "Next.js 15",
        "category": "meta",
        "version": "15.0.0",
        "template": "nextjs-app-router",
        "language": "TypeScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS v4", "M3 Tokens", "CSS Modules"],
        "features": ["App Router", "React Server Components (RSC)", "Server Actions", "Turbopack"],
        "description": "Production Next.js 15 with App Router, React Server Components, and Material 3 tokens.",
    },
    "remix": {
        "id": "remix",
        "name": "Remix / React Router 7",
        "category": "meta",
        "version": "2.12.0",
        "template": "remix-vite",
        "language": "TypeScript",
        "primary_extension": ".tsx",
        "styling": ["Tailwind CSS", "M3 Tokens"],
        "features": ["Full-stack Loaders/Actions", "Vite plugin", "Progressive Enhancement"],
        "description": "Remix fullstack web framework with Vite integration and Material 3 color system.",
    },
    "vanilla": {
        "id": "vanilla",
        "name": "Vanilla Modern ES / Web Components",
        "category": "web",
        "version": "ES2024",
        "template": "vite-vanilla-ts",
        "language": "TypeScript / Modern JavaScript",
        "primary_extension": ".ts",
        "styling": ["Material 3 CSS Custom Properties", "Tailwind CSS"],
        "features": ["Autonomous Custom Elements", "Shadow DOM", "Zero runtime framework", "Vite Bundler"],
        "description": "Standards-compliant Autonomous Web Components with M3 CSS custom properties and Vite.",
    },
    "flutter": {
        "id": "flutter",
        "name": "Flutter 3.24",
        "category": "native",
        "version": "3.24.0",
        "template": "flutter-m3",
        "language": "Dart",
        "primary_extension": ".dart",
        "styling": ["Material 3 ColorScheme", "ThemeData.useMaterial3"],
        "features": ["Cross-platform iOS/Android/Web/Desktop", "Stateful/Stateless Widgets", "M3 Widgets"],
        "description": "Flutter mobile & web application with declarative widgets and complete Material 3 Theme.",
    },
    "swiftui": {
        "id": "swiftui",
        "name": "SwiftUI 5 / 6",
        "category": "native",
        "version": "iOS 17+ / macOS 14+",
        "template": "swiftui-app",
        "language": "Swift",
        "primary_extension": ".swift",
        "styling": ["SwiftUI Color Assets", "M3 Design System mapping"],
        "features": ["Declarative UI", "Observable state macro (@Observable)", "Native Apple UX"],
        "description": "Apple native SwiftUI views and apps with Material 3 token mapping.",
    },
    "compose": {
        "id": "compose",
        "name": "Jetpack Compose",
        "category": "native",
        "version": "1.7.0",
        "template": "compose-m3",
        "language": "Kotlin",
        "primary_extension": ".kt",
        "styling": ["androidx.compose.material3", "MaterialTheme"],
        "features": ["Declarative Kotlin UI", "Material3 Composable Widgets", "State Hoisting"],
        "description": "Android Jetpack Compose UI with official Material 3 component library.",
    },
}

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "system": {
        "name": "Material 3 System Dynamic",
        "primary": "#006495",
        "on_primary": "#ffffff",
        "primary_container": "#cbe6ff",
        "on_primary_container": "#001e30",
        "secondary": "#50606e",
        "surface": "#f8f9fa",
        "on_surface": "#191c1e",
        "background": "#fbfcfe",
        "outline": "#71787e",
    },
    "light": {
        "name": "Material 3 Clean Light",
        "primary": "#1a73e8",
        "on_primary": "#ffffff",
        "primary_container": "#d2e3fc",
        "on_primary_container": "#041e49",
        "secondary": "#5f6368",
        "surface": "#ffffff",
        "on_surface": "#202124",
        "background": "#f8f9fa",
        "outline": "#dadce0",
    },
    "dark": {
        "name": "Material 3 Cyber Dark",
        "primary": "#8ecdff",
        "on_primary": "#003450",
        "primary_container": "#004b72",
        "on_primary_container": "#cbe6ff",
        "secondary": "#b8c8d8",
        "surface": "#121316",
        "on_surface": "#e2e2e5",
        "background": "#0b0d0e",
        "outline": "#8b9298",
    },
    "ocean": {
        "name": "Pacific Ocean Deep",
        "primary": "#00677e",
        "on_primary": "#ffffff",
        "primary_container": "#b5ebff",
        "on_primary_container": "#001f28",
        "secondary": "#4b626a",
        "surface": "#fbfcfe",
        "on_surface": "#191c1d",
        "background": "#f5fafb",
        "outline": "#6f797b",
    },
    "emerald": {
        "name": "Emerald Growth",
        "primary": "#006d42",
        "on_primary": "#ffffff",
        "primary_container": "#90f7bc",
        "on_primary_container": "#002111",
        "secondary": "#4f6354",
        "surface": "#fcfdf7",
        "on_surface": "#1a1c19",
        "background": "#f6fbf4",
        "outline": "#717971",
    },
    "crimson": {
        "name": "Crimson Velvet",
        "primary": "#b31b34",
        "on_primary": "#ffffff",
        "primary_container": "#ffd9dc",
        "on_primary_container": "#40000a",
        "secondary": "#755659",
        "surface": "#fff8f7",
        "on_surface": "#221919",
        "background": "#fffbfb",
        "outline": "#857374",
    },
    "amber": {
        "name": "Warm Amber Sunset",
        "primary": "#825500",
        "on_primary": "#ffffff",
        "primary_container": "#ffddb2",
        "on_primary_container": "#291800",
        "secondary": "#6e5c46",
        "surface": "#fff8f4",
        "on_surface": "#201a14",
        "background": "#fffbf7",
        "outline": "#837567",
    },
    "purple": {
        "name": "Deep Royal Purple",
        "primary": "#714ca7",
        "on_primary": "#ffffff",
        "primary_container": "#edd8ff",
        "on_primary_container": "#2a0054",
        "secondary": "#655a6f",
        "surface": "#fff7fb",
        "on_surface": "#1e1a20",
        "background": "#fdf8fd",
        "outline": "#7c747f",
    },
}


# ---------------------------------------------------------------------------
# HTML to Framework Transpiler Engine
# ---------------------------------------------------------------------------

class HTMLStyleParser:
    """Parse CSS inline styles into camelCase dictionary or framework format."""

    @staticmethod
    def parse_inline_style(style_str: str) -> Dict[str, str]:
        styles: Dict[str, str] = {}
        if not style_str:
            return styles
        declarations = style_str.split(";")
        for decl in declarations:
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            prop, val = decl.split(":", 1)
            prop = prop.strip()
            val = val.strip()

            # Convert kebab-case property to camelCase (e.g., background-color -> backgroundColor)
            parts = prop.split("-")
            camel_prop = parts[0] + "".join(word.capitalize() for word in parts[1:])
            # Special case for CSS custom variables: preserve --var-name
            if prop.startswith("--"):
                camel_prop = prop

            styles[camel_prop] = val
        return styles

    @staticmethod
    def to_jsx_style(style_str: str) -> str:
        styles = HTMLStyleParser.parse_inline_style(style_str)
        if not styles:
            return "{}"
        items = []
        for k, v in styles.items():
            val_escaped = v.replace("'", "\\'")
            items.append(f"{k}: '{val_escaped}'")
        return f"{{ {', '.join(items)} }}"


class HTMLTranspiler:
    """Transpiles arbitrary HTML snippets into idiomatic component code for any target framework."""

    SELF_CLOSING_HTML_TAGS = {"img", "input", "br", "hr", "meta", "link", "source", "area", "col"}

    @classmethod
    def transpile(
        cls,
        html_code: str,
        framework: str,
        component_name: str = "ConvertedComponent",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        options = options or {}
        use_ts = options.get("typescript", True)
        theme = options.get("theme", "system")
        framework_norm = framework.lower().strip()

        # Sanitize component name to PascalCase
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "", component_name)
        if not clean_name or not clean_name[0].isalpha():
            clean_name = "ConvertedComponent"

        if framework_norm in ("react", "nextjs", "remix"):
            return cls._to_react(html_code, clean_name, use_ts, theme)
        elif framework_norm == "vue":
            return cls._to_vue(html_code, clean_name, use_ts, theme)
        elif framework_norm == "svelte":
            return cls._to_svelte(html_code, clean_name, use_ts, theme)
        elif framework_norm == "solid":
            return cls._to_solid(html_code, clean_name, use_ts, theme)
        elif framework_norm == "angular":
            return cls._to_angular(html_code, clean_name, use_ts, theme)
        elif framework_norm == "astro":
            return cls._to_astro(html_code, clean_name, use_ts, theme)
        elif framework_norm == "qwik":
            return cls._to_qwik(html_code, clean_name, use_ts, theme)
        elif framework_norm == "vanilla":
            return cls._to_vanilla(html_code, clean_name, use_ts, theme)
        elif framework_norm == "flutter":
            return cls._to_flutter(html_code, clean_name, use_ts, theme)
        elif framework_norm == "swiftui":
            return cls._to_swiftui(html_code, clean_name, use_ts, theme)
        elif framework_norm == "compose":
            return cls._to_compose(html_code, clean_name, use_ts, theme)
        else:
            return cls._to_react(html_code, clean_name, use_ts, theme)

    @classmethod
    def _convert_html_to_jsx(cls, raw_html: str) -> str:
        """Convert raw HTML attributes and tags to valid JSX."""
        jsx = raw_html

        # Replace class= with className=
        jsx = re.sub(r'\bclass=(["\'])', r"className=\1", jsx)

        # Replace for= with htmlFor=
        jsx = re.sub(r'\bfor=(["\'])', r"htmlFor=\1", jsx)

        # Replace tabindex= with tabIndex=
        jsx = re.sub(r'\btabindex=(["\'])', r"tabIndex=\1", jsx)

        # Replace autocomplete= with autoComplete=
        jsx = re.sub(r'\bautocomplete=(["\'])', r"autoComplete=\1", jsx)

        # Replace onclick / onchange etc
        jsx = re.sub(r'\bonclick=(["\'])', r"onClick=\1", jsx)
        jsx = re.sub(r'\bonchange=(["\'])', r"onChange=\1", jsx)
        jsx = re.sub(r'\boninput=(["\'])', r"onInput=\1", jsx)
        jsx = re.sub(r'\bonsubmit=(["\'])', r"onSubmit=\1", jsx)

        # Convert SVG kebab-case attributes
        svg_attrs = ["stroke-width", "stroke-linecap", "stroke-linejoin", "fill-rule", "clip-rule", "stroke-dasharray"]
        for attr in svg_attrs:
            camel = attr.split("-")[0] + "".join(w.capitalize() for w in attr.split("-")[1:])
            jsx = re.sub(rf'\b{attr}=(["\'])', f"{camel}=\\1", jsx)

        # Convert inline styles style="..." -> style={{ ... }}
        def replace_style(match: re.Match[str]) -> str:
            style_content = match.group(1)
            jsx_obj = HTMLStyleParser.to_jsx_style(style_content)
            return f"style={{{jsx_obj}}}"

        jsx = re.sub(r'style=["\']([^"\']*)["\']', replace_style, jsx)

        # Ensure self-closing tags are closed (e.g. <img ...> -> <img ... />)
        for tag in cls.SELF_CLOSING_HTML_TAGS:
            jsx = re.sub(rf'<({tag}\b[^>]*?)(?<!/)>', r'<\1 />', jsx, flags=re.IGNORECASE)

        # Replace HTML comments <!-- ... --> with JSX comments {/* ... */}
        jsx = re.sub(r'<!--(.*?)-->', r'{/* \1 */}', jsx, flags=re.DOTALL)

        return jsx

    @classmethod
    def _to_react(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        jsx = cls._convert_html_to_jsx(html.strip())
        type_annot = ": React.FC<Props>" if ts else ""
        props_interface = "\ninterface Props {\n  className?: string;\n  children?: React.ReactNode;\n}\n" if ts else ""
        low_name = name.lower()

        code = (
            "import React from 'react';\n"
            + props_interface
            + f"export const {name}{type_annot} = ({{ className = '', children }}) => {{\n"
            + "  return (\n"
            + "    <div className={`" + low_name + "-container ${className}`}>\n"
            + f"      {jsx}\n"
            + "      {children}\n"
            + "    </div>\n"
            + "  );\n"
            + "};\n\n"
            + f"export default {name};\n"
        )

        return {
            "component_name": name,
            "filename": f"{name}.{'tsx' if ts else 'jsx'}",
            "language": "typescript" if ts else "javascript",
            "framework": "react",
            "code": code,
            "extracted_elements": ["Material 3 Container", "JSX Template"],
        }

    @classmethod
    def _to_vue(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        lang_ts = ' lang="ts"' if ts else ""
        low_name = name.lower()
        code = (
            f"<script setup{lang_ts}>\n"
            "import { ref } from 'vue';\n\n"
            "interface Props {\n"
            "  title?: string;\n"
            "  customClass?: string;\n"
            "}\n\n"
            f"const props = withDefaults(defineProps<Props>(), {{\n"
            f"  title: '{name}',\n"
            "  customClass: '',\n"
            "});\n"
            "</script>\n\n"
            "<template>\n"
            f"  <div :class=\"['{low_name}-wrapper', props.customClass]\">\n"
            f"    {html.strip()}\n"
            "    <slot />\n"
            "  </div>\n"
            "</template>\n\n"
            "<style scoped>\n"
            f".{low_name}-wrapper {{\n"
            "  display: block;\n"
            "}\n"
            "</style>\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.vue",
            "language": "vue",
            "framework": "vue",
            "code": code,
        }

    @classmethod
    def _to_svelte(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        lang_ts = ' lang="ts"' if ts else ""
        low_name = name.lower()
        code = (
            f"<script{lang_ts}>\n"
            "  interface Props {\n"
            "    class?: string;\n"
            "    children?: import('svelte').Snippet;\n"
            "  }\n\n"
            "  let { class: className = '', children }: Props = $props();\n"
            "</script>\n\n"
            f"<div class=\"{low_name}-root {{className}}\">\n"
            f"  {html.strip()}\n"
            "  {#if children}\n"
            "    {@render children()}\n"
            "  {/if}\n"
            "</div>\n\n"
            "<style>\n"
            f"  .{low_name}-root {{\n"
            "    position: relative;\n"
            "  }}\n"
            "</style>\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.svelte",
            "language": "svelte",
            "framework": "svelte",
            "code": code,
        }

    @classmethod
    def _to_solid(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        jsx = cls._convert_html_to_jsx(html.strip())
        type_annot = ": Component<Props>" if ts else ""
        props_interface = "\ninterface Props {\n  class?: string;\n  children?: JSX.Element;\n}\n" if ts else ""
        low_name = name.lower()

        code = (
            "import { Component, JSX } from 'solid-js';\n"
            + props_interface
            + f"export const {name}{type_annot} = (props) => {{\n"
            + "  return (\n"
            + "    <div class={`" + low_name + "-root ${props.class || ''}`}>\n"
            + f"      {jsx}\n"
            + "      {props.children}\n"
            + "    </div>\n"
            + "  );\n"
            + "};\n\n"
            + f"export default {name};\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.{'tsx' if ts else 'jsx'}",
            "language": "typescript" if ts else "javascript",
            "framework": "solid",
            "code": code,
        }

    @classmethod
    def _to_angular(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        selector = f"app-{name.lower()}"
        code = (
            "import { Component, Input, signal } from '@angular/core';\n"
            "import { CommonModule } from '@angular/common';\n\n"
            "@Component({\n"
            f"  selector: '{selector}',\n"
            "  standalone: true,\n"
            "  imports: [CommonModule],\n"
            "  template: `\n"
            f"    <div class=\"{name.lower()}-container\" [class]=\"customClass\">\n"
            f"      {html.strip()}\n"
            "      <ng-content></ng-content>\n"
            "    </div>\n"
            "  `,\n"
            "  styles: [`\n"
            f"    :{selector} {{\n"
            "      display: block;\n"
            "    }}\n"
            "  `]\n"
            "})\n"
            f"export class {name}Component {{\n"
            "  @Input() customClass = '';\n"
            "  protected active = signal(true);\n"
            "}\n"
        )
        return {
            "component_name": f"{name}Component",
            "filename": f"{name.lower()}.component.ts",
            "language": "typescript",
            "framework": "angular",
            "code": code,
        }

    @classmethod
    def _to_astro(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        low_name = name.lower()
        code = (
            "---\n"
            "interface Props {\n"
            "  class?: string;\n"
            f"  title?: string;\n"
            "}\n\n"
            f"const {{ class: className = '', title = '{name}' }} = Astro.props;\n"
            "---\n\n"
            "<div class={`" + low_name + "-container ${className}`}>\n"
            f"  {html.strip()}\n"
            "  <slot />\n"
            "</div>\n\n"
            "<style>\n"
            f"  .{low_name}-container {{\n"
            "    display: block;\n"
            "  }}\n"
            "</style>\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.astro",
            "language": "astro",
            "framework": "astro",
            "code": code,
        }

    @classmethod
    def _to_qwik(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        jsx = cls._convert_html_to_jsx(html.strip())
        low_name = name.lower()
        code = (
            "import { component$, Slot } from '@builder.io/qwik';\n\n"
            "interface Props {\n"
            "  class?: string;\n"
            "}\n\n"
            f"export const {name} = component$<Props>((props) => {{\n"
            "  return (\n"
            "    <div class={`" + low_name + "-root ${props.class || ''}`}>\n"
            f"      {jsx}\n"
            "      <Slot />\n"
            "    </div>\n"
            "  );\n"
            "});\n\n"
            f"export default {name};\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.tsx",
            "language": "typescript",
            "framework": "qwik",
            "code": code,
        }

    @classmethod
    def _to_vanilla(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        tag_name = f"m3-{name.lower()}"
        code = (
            "/**\n"
            f" * Material 3 Autonomous Custom Element: <{tag_name}>\n"
            " */\n"
            f"export class {name}Element extends HTMLElement {{\n"
            "  private _shadowRoot: ShadowRoot;\n\n"
            "  constructor() {\n"
            "    super();\n"
            "    this._shadowRoot = this.attachShadow({ mode: 'open' });\n"
            "  }\n\n"
            "  connectedCallback(): void {\n"
            "    this.render();\n"
            "  }\n\n"
            "  private render(): void {\n"
            "    this._shadowRoot.innerHTML = `\n"
            "      <style>\n"
            "        :host {\n"
            "          display: block;\n"
            "          box-sizing: border-box;\n"
            "          font-family: var(--md-sys-typescale-body-large-font, Roboto, sans-serif);\n"
            "        }\n"
            "        .container {\n"
            "          position: relative;\n"
            "        }\n"
            "      </style>\n"
            "      <div class=\"container\">\n"
            f"        {html.strip()}\n"
            "        <slot></slot>\n"
            "      </div>\n"
            "    `;\n"
            "  }\n"
            "}\n\n"
            f"if (!customElements.get('{tag_name}')) {{\n"
            f"  customElements.define('{tag_name}', {name}Element);\n"
            "}\n"
        )
        return {
            "component_name": name,
            "filename": f"{name.lower()}.ts" if ts else f"{name.lower()}.js",
            "language": "typescript" if ts else "javascript",
            "framework": "vanilla",
            "code": code,
        }

    @classmethod
    def _to_flutter(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        code = (
            "import 'package:flutter/material.dart';\n\n"
            f"class {name} extends StatelessWidget {{\n"
            "  final Widget? child;\n"
            "  final EdgeInsetsGeometry padding;\n\n"
            f"  const {name}({{\n"
            "    super.key,\n"
            "    this.child,\n"
            "    this.padding = const EdgeInsets.all(16.0),\n"
            "  }});\n\n"
            "  @override\n"
            "  Widget build(BuildContext context) {\n"
            "    final theme = Theme.of(context);\n"
            "    final colorScheme = theme.colorScheme;\n\n"
            "    return Container(\n"
            "      padding: padding,\n"
            "      decoration: BoxDecoration(\n"
            "        color: colorScheme.surface,\n"
            "        borderRadius: BorderRadius.circular(12.0),\n"
            "        border: Border.all(color: colorScheme.outlineVariant),\n"
            "      ),\n"
            "      child: Column(\n"
            "        crossAxisAlignment: CrossAxisAlignment.start,\n"
            "        mainAxisSize: MainAxisSize.min,\n"
            "        children: [\n"
            "          Text(\n"
            f"            '{name}',\n"
            "            style: theme.textTheme.titleLarge?.copyWith(\n"
            "              color: colorScheme.onSurface,\n"
            "            ),\n"
            "          ),\n"
            "          const SizedBox(height: 8.0),\n"
            "          if (child != null) child!,\n"
            "        ],\n"
            "      ),\n"
            "    );\n"
            "  }\n"
            "}\n"
        )
        return {
            "component_name": name,
            "filename": f"{name.lower()}.dart",
            "language": "dart",
            "framework": "flutter",
            "code": code,
        }

    @classmethod
    def _to_swiftui(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        code = (
            "import SwiftUI\n\n"
            f"struct {name}: View {{\n"
            f"    var title: String = \"{name}\"\n"
            "    \n"
            "    var body: some View {\n"
            "        VStack(alignment: .leading, spacing: 12) {\n"
            "            Text(title)\n"
            "                .font(.headline)\n"
            "                .foregroundColor(.primary)\n"
            "            \n"
            "            // Converted HTML Content Placeholder\n"
            "            Text(\"Material 3 Component Content\")\n"
            "                .font(.body)\n"
            "                .foregroundColor(.secondary)\n"
            "        }\n"
            "        .padding()\n"
            "        .background(Color(UIColor.secondarySystemBackground))\n"
            "        .cornerRadius(12)\n"
            "        .overlay(\n"
            "            RoundedRectangle(cornerRadius: 12)\n"
            "                .stroke(Color.gray.opacity(0.2), lineWidth: 1)\n"
            "        )\n"
            "    }\n"
            "}\n\n"
            "#Preview {\n"
            f"    {name}()\n"
            "}\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.swift",
            "language": "swift",
            "framework": "swiftui",
            "code": code,
        }

    @classmethod
    def _to_compose(cls, html: str, name: str, ts: bool, theme: str) -> Dict[str, Any]:
        code = (
            "package com.example.m3app.ui.components\n\n"
            "import androidx.compose.foundation.background\n"
            "import androidx.compose.foundation.border\n"
            "import androidx.compose.foundation.layout.*\n"
            "import androidx.compose.foundation.shape.RoundedCornerShape\n"
            "import androidx.compose.material3.MaterialTheme\n"
            "import androidx.compose.material3.Text\n"
            "import androidx.compose.runtime.Composable\n"
            "import androidx.compose.ui.Modifier\n"
            "import androidx.compose.ui.draw.clip\n"
            "import androidx.compose.ui.unit.dp\n\n"
            "@Composable\n"
            f"fun {name}(\n"
            "    modifier: Modifier = Modifier,\n"
            "    content: @Composable (() -> Unit)? = null\n"
            ") {\n"
            "    Box(\n"
            "        modifier = modifier\n"
            "            .clip(RoundedCornerShape(12.dp))\n"
            "            .background(MaterialTheme.colorScheme.surface)\n"
            "            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp))\n"
            "            .padding(16.dp)\n"
            "    ) {\n"
            "        Column(\n"
            "            verticalArrangement = Arrangement.spacedBy(8.dp)\n"
            "        ) {\n"
            "            Text(\n"
            f"                text = \"{name}\",\n"
            "                style = MaterialTheme.typography.titleMedium,\n"
            "                color = MaterialTheme.colorScheme.onSurface\n"
            "            )\n"
            "            content?.invoke()\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        return {
            "component_name": name,
            "filename": f"{name}.kt",
            "language": "kotlin",
            "framework": "compose",
            "code": code,
        }


# ---------------------------------------------------------------------------
# Project Scaffold Generator Engine (Standalone Fallback & Generator Hub)
# ---------------------------------------------------------------------------

def generate_project_scaffold(
    framework: str,
    project_name: str = "my-app",
    theme: str = "system",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Generate complete, functional project file tree for target framework.

    First attempts to delegate to specialized generator module in
    polyglot_framework_exporter.generators if available, and falls back to
    built-in complete production templates.
    """
    options = options or {}
    norm_fw = framework.lower().strip()

    # Dynamic check for submodule generator
    try:
        from .transpiler import ProjectAST
        from .generators.vite_react_generator import ViteReactGenerator
        from .generators.nextjs_generator import NextjsGenerator
        from .generators.astro_generator import AstroGenerator
        from .generators.svelte_generator import SvelteGenerator
        from .generators.nuxt_generator import NuxtGenerator
        from .generators.bun_hono_generator import BunHonoGenerator
        from .generators.solidstart_generator import SolidStartGenerator

        gen_classes: Dict[str, Any] = {
            "react": ViteReactGenerator,
            "vite_react": ViteReactGenerator,
            "nextjs": NextjsGenerator,
            "next": NextjsGenerator,
            "astro": AstroGenerator,
            "svelte": SvelteGenerator,
            "solidstart": SolidStartGenerator,
            "solid": SolidStartGenerator,
            "solidjs": SolidStartGenerator,
            "bun_hono": BunHonoGenerator,
            "hono": BunHonoGenerator,
            "bun": BunHonoGenerator,
            "vue": NuxtGenerator,
            "nuxt": NuxtGenerator,
        }
        if norm_fw in gen_classes:
            ast = ProjectAST(title=project_name, theme=theme)
            res = gen_classes[norm_fw]().generate(ast=ast, options=options)
            if isinstance(res, dict) and len(res) > 0:
                return res
    except Exception as e:
        logger.debug(f"Generator classes dispatch notice: {e}")

    try:
        from . import generators  # type: ignore
        if hasattr(generators, "generate") and callable(generators.generate):
            res = generators.generate(framework=norm_fw, project_name=project_name, theme=theme, options=options)
            if isinstance(res, dict) and len(res) > 0:
                return res
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Submodule generator fallback notice: {e}")

    theme_data = THEME_PRESETS.get(theme, THEME_PRESETS["system"])
    theme_json = json.dumps(theme_data, indent=2)

    files: Dict[str, str] = {}

    # Common README and Package files
    if norm_fw in ("react", "nextjs", "remix"):
        files["package.json"] = json.dumps({
            "name": project_name,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc -b && vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^19.0.0",
                "react-dom": "^19.0.0",
                "lucide-react": "^0.468.0",
                "clsx": "^2.1.1",
                "tailwind-merge": "^2.5.5"
            },
            "devDependencies": {
                "@types/react": "^19.0.0",
                "@types/react-dom": "^19.0.0",
                "@vitejs/plugin-react": "^4.3.4",
                "typescript": "^5.7.2",
                "vite": "^6.0.3",
                "tailwindcss": "^3.4.16",
                "postcss": "^8.4.49",
                "autoprefixer": "^10.4.20"
            }
        }, indent=2)

        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "target": "ES2022",
                "useDefineForClassFields": True,
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "resolveJsonModule": True,
                "isolatedModules": True,
                "moduleDetection": "force",
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "noUnusedLocals": True,
                "noUnusedParameters": True,
                "noFallthroughCasesInSwitch": True
            },
            "include": ["src"]
        }, indent=2)

        files["vite.config.ts"] = (
            "import { defineConfig } from 'vite';\n"
            "import react from '@vitejs/plugin-react';\n\n"
            "export default defineConfig({\n"
            "  plugins: [react()],\n"
            "  server: {\n"
            "    port: 3000,\n"
            "    open: true\n"
            "  }\n"
            "});\n"
        )

        files["tailwind.config.js"] = (
            "/** @type {import('tailwindcss').Config} */\n"
            "export default {\n"
            "  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],\n"
            "  darkMode: 'class',\n"
            "  theme: {\n"
            "    extend: {\n"
            f"      colors: {{\n        m3: {theme_json}\n      }}\n"
            "    }\n"
            "  },\n"
            "  plugins: []\n"
            "};\n"
        )

        files["index.html"] = (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "  <head>\n"
            "    <meta charset=\"UTF-8\" />\n"
            "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
            f"    <title>{project_name} - Polyglot Studio</title>\n"
            "  </head>\n"
            "  <body class=\"bg-surface text-on-surface font-sans antialiased\">\n"
            "    <div id=\"root\"></div>\n"
            "    <script type=\"module\" src=\"/src/main.tsx\"></script>\n"
            "  </body>\n"
            "</html>\n"
        )

        files["src/main.tsx"] = (
            "import React from 'react';\n"
            "import ReactDOM from 'react-dom/client';\n"
            "import App from './App.tsx';\n"
            "import './index.css';\n\n"
            "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
            "  <React.StrictMode>\n"
            "    <App />\n"
            "  </React.StrictMode>\n"
            ");\n"
        )

        files["src/index.css"] = (
            "@tailwind base;\n"
            "@tailwind components;\n"
            "@tailwind utilities;\n\n"
            ":root {\n"
            f"  --md-sys-color-primary: {theme_data['primary']};\n"
            f"  --md-sys-color-on-primary: {theme_data['on_primary']};\n"
            f"  --md-sys-color-primary-container: {theme_data['primary_container']};\n"
            f"  --md-sys-color-on-primary-container: {theme_data['on_primary_container']};\n"
            f"  --md-sys-color-surface: {theme_data['surface']};\n"
            f"  --md-sys-color-on-surface: {theme_data['on_surface']};\n"
            f"  --md-sys-color-background: {theme_data['background']};\n"
            f"  --md-sys-color-outline: {theme_data['outline']};\n"
            "}\n\n"
            "body {\n"
            "  margin: 0;\n"
            "  min-height: 100vh;\n"
            "  background-color: var(--md-sys-color-background);\n"
            "  color: var(--md-sys-color-on-surface);\n"
            "}\n"
        )

        files["src/App.tsx"] = (
            "import React, { useState } from 'react';\n"
            "import { Sparkles, Palette, Layers } from 'lucide-react';\n\n"
            "export default function App() {\n"
            "  const [count, setCount] = useState(0);\n\n"
            "  return (\n"
            "    <div className=\"min-h-screen flex flex-col items-center justify-center p-6\">\n"
            "      <div className=\"max-w-2xl w-full bg-white dark:bg-zinc-900 rounded-3xl shadow-xl p-8 border border-zinc-200 dark:border-zinc-800\">\n"
            "        <div className=\"flex items-center gap-3 mb-6\">\n"
            "          <div className=\"p-3 bg-blue-50 dark:bg-blue-950/50 rounded-2xl text-blue-600 dark:text-blue-400\">\n"
            "            <Sparkles className=\"w-8 h-8\" />\n"
            "          </div>\n"
            "          <div>\n"
            f"            <h1 className=\"text-2xl font-bold\">{project_name}</h1>\n"
            f"            <p className=\"text-zinc-500 text-sm\">Polyglot React 19 + Material 3 ({theme})</p>\n"
            "          </div>\n"
            "        </div>\n\n"
            "        <div className=\"grid grid-cols-1 md:grid-cols-2 gap-4 mb-8\">\n"
            "          <div className=\"p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800\">\n"
            "            <div className=\"flex items-center gap-2 font-semibold mb-1\">\n"
            "              <Palette className=\"w-4 h-4 text-emerald-500\" />\n"
            "              <span>Theme Tokens</span>\n"
            "            </div>\n"
            "            <p className=\"text-xs text-zinc-500\">M3 Dynamic color harmony with full token palette mapping.</p>\n"
            "          </div>\n\n"
            "          <div className=\"p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800\">\n"
            "            <div className=\"flex items-center gap-2 font-semibold mb-1\">\n"
            "              <Layers className=\"w-4 h-4 text-purple-500\" />\n"
            "              <span>Component Tree</span>\n"
            "            </div>\n"
            "            <p className=\"text-xs text-zinc-500\">Zero runtime bloat, tree-shakeable atomic components.</p>\n"
            "          </div>\n"
            "        </div>\n\n"
            "        <div className=\"flex items-center justify-between pt-4 border-t border-zinc-100 dark:border-zinc-800\">\n"
            "          <button\n"
            "            onClick={() => setCount((c) => c + 1)}\n"
            "            className=\"px-6 py-2.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm transition-colors shadow-sm\"\n"
            "          >\n"
            "            Count is {count}\n"
            "          </button>\n"
            "          <span className=\"text-xs text-zinc-400\">Polyglot Studio</span>\n"
            "        </div>\n"
            "      </div>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        )

    elif norm_fw == "vue":
        files["package.json"] = json.dumps({
            "name": project_name,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vue-tsc -b && vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "vue": "^3.5.0",
                "lucide-vue-next": "^0.468.0"
            },
            "devDependencies": {
                "@vitejs/plugin-vue": "^5.2.1",
                "typescript": "^5.7.2",
                "vite": "^6.0.3",
                "vue-tsc": "^2.1.10",
                "tailwindcss": "^3.4.16",
                "postcss": "^8.4.49",
                "autoprefixer": "^10.4.20"
            }
        }, indent=2)

        files["vite.config.ts"] = (
            "import { defineConfig } from 'vite';\n"
            "import vue from '@vitejs/plugin-vue';\n\n"
            "export default defineConfig({\n"
            "  plugins: [vue()],\n"
            "  server: { port: 3000 }\n"
            "});\n"
        )

        files["src/App.vue"] = (
            "<script setup lang=\"ts\">\n"
            "import { ref } from 'vue';\n\n"
            "const count = ref(0);\n"
            f"const projectName = '{project_name}';\n"
            "</script>\n\n"
            "<template>\n"
            "  <main class=\"min-h-screen flex items-center justify-center p-6 bg-slate-50\">\n"
            "    <div class=\"max-w-xl w-full bg-white rounded-3xl p-8 shadow-xl border border-slate-200\">\n"
            "      <h1 class=\"text-2xl font-bold text-slate-900\">{{ projectName }}</h1>\n"
            "      <p class=\"text-slate-500 text-sm mt-1\">Vue 3.5 Composition API with Material 3 Theme</p>\n"
            "      <div class=\"mt-6 flex items-center gap-4\">\n"
            "        <button\n"
            "          @click=\"count++\"\n"
            "          class=\"px-5 py-2.5 rounded-full bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition-colors\"\n"
            "        >\n"
            "          Clicked {{ count }} times\n"
            "        </button>\n"
            "      </div>\n"
            "    </div>\n"
            "  </main>\n"
            "</template>\n"
        )

        files["src/main.ts"] = (
            "import { createApp } from 'vue';\n"
            "import App from './App.vue';\n"
            "import './style.css';\n\n"
            "createApp(App).mount('#app');\n"
        )

        files["src/style.css"] = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"
        files["index.html"] = (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "  <head>\n"
            "    <meta charset=\"UTF-8\" />\n"
            f"    <title>{project_name}</title>\n"
            "  </head>\n"
            "  <body>\n"
            "    <div id=\"app\"></div>\n"
            "    <script type=\"module\" src=\"/src/main.ts\"></script>\n"
            "  </body>\n"
            "</html>\n"
        )

    elif norm_fw == "svelte":
        files["package.json"] = json.dumps({
            "name": project_name,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "svelte": "^5.0.0"
            },
            "devDependencies": {
                "@sveltejs/vite-plugin-svelte": "^4.0.0",
                "typescript": "^5.7.2",
                "vite": "^6.0.3"
            }
        }, indent=2)

        files["src/App.svelte"] = (
            "<script lang=\"ts\">\n"
            "  let count = $state(0);\n"
            "</script>\n\n"
            "<main class=\"container\">\n"
            f"  <h1>{project_name}</h1>\n"
            "  <p>Svelte 5 Runes ($state) • Material 3 Design</p>\n"
            "  <button onclick={() => count++}>\n"
            "    Count: {count}\n"
            "  </button>\n"
            "</main>\n\n"
            "<style>\n"
            "  .container {\n"
            "    font-family: system-ui, sans-serif;\n"
            "    max-width: 600px;\n"
            "    margin: 4rem auto;\n"
            "    padding: 2rem;\n"
            "    border-radius: 1.5rem;\n"
            "    background: #f8f9fa;\n"
            "  }\n"
            "  button {\n"
            "    padding: 0.6rem 1.2rem;\n"
            "    border-radius: 9999px;\n"
            "    background: #006495;\n"
            "    color: white;\n"
            "    border: none;\n"
            "    cursor: pointer;\n"
            "  }\n"
            "</style>\n"
        )
        files["src/main.ts"] = (
            "import { mount } from 'svelte';\n"
            "import App from './App.svelte';\n\n"
            "const app = mount(App, {\n"
            "  target: document.getElementById('app')!,\n"
            "});\n\n"
            "export default app;\n"
        )

    elif norm_fw == "vanilla":
        files["package.json"] = json.dumps({
            "name": project_name,
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview"
            },
            "devDependencies": {
                "typescript": "^5.7.2",
                "vite": "^6.0.3"
            }
        }, indent=2)

        files["src/index.ts"] = (
            "import './styles.css';\n\n"
            "class M3AppCard extends HTMLElement {\n"
            "  connectedCallback() {\n"
            "    this.innerHTML = `\n"
            "      <div class=\"m3-card\">\n"
            f"        <h1>{project_name}</h1>\n"
            "        <p>Vanilla Autonomous Custom Elements + Material 3</p>\n"
            "        <button id=\"counter-btn\" class=\"m3-button\">Clicks: 0</button>\n"
            "      </div>\n"
            "    `;\n\n"
            "    let count = 0;\n"
            "    const btn = this.querySelector('#counter-btn');\n"
            "    btn?.addEventListener('click', () => {\n"
            "      count++;\n"
            "      if (btn) btn.textContent = `Clicks: ${count}`;\n"
            "    });\n"
            "  }\n"
            "}\n\n"
            "customElements.define('m3-app-card', M3AppCard);\n"
        )

        files["src/styles.css"] = (
            "body {\n"
            "  font-family: Roboto, system-ui, sans-serif;\n"
            "  margin: 0;\n"
            "  display: flex;\n"
            "  justify-content: center;\n"
            "  align-items: center;\n"
            "  min-height: 100vh;\n"
            f"  background-color: {theme_data['background']};\n"
            "}\n\n"
            ".m3-card {\n"
            f"  background: {theme_data['surface']};\n"
            f"  color: {theme_data['on_surface']};\n"
            "  padding: 2rem;\n"
            "  border-radius: 28px;\n"
            "  box-shadow: 0 4px 20px rgba(0,0,0,0.08);\n"
            f"  border: 1px solid {theme_data['outline']};\n"
            "}\n\n"
            ".m3-button {\n"
            f"  background: {theme_data['primary']};\n"
            f"  color: {theme_data['on_primary']};\n"
            "  border: none;\n"
            "  border-radius: 20px;\n"
            "  padding: 10px 24px;\n"
            "  font-weight: 600;\n"
            "  cursor: pointer;\n"
            "}\n"
        )

        files["index.html"] = (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "  <head>\n"
            "    <meta charset=\"UTF-8\" />\n"
            f"    <title>{project_name}</title>\n"
            "  </head>\n"
            "  <body>\n"
            "    <m3-app-card></m3-app-card>\n"
            "    <script type=\"module\" src=\"/src/index.ts\"></script>\n"
            "  </body>\n"
            "</html>\n"
        )

    elif norm_fw == "flutter":
        clean_pkg = project_name.lower().replace('-', '_')
        files["pubspec.yaml"] = (
            f"name: {clean_pkg}\n"
            "description: \"Polyglot Studio Exported Flutter App\"\n"
            "version: 1.0.0+1\n"
            "environment:\n"
            "  sdk: '>=3.0.0 <4.0.0'\n\n"
            "dependencies:\n"
            "  flutter:\n"
            "    sdk: flutter\n"
            "  cupertino_icons: ^1.0.8\n\n"
            "dev_dependencies:\n"
            "  flutter_test:\n"
            "    sdk: flutter\n"
            "  flutter_lints: ^4.0.0\n\n"
            "flutter:\n"
            "  uses-material-design: true\n"
        )

        files["lib/main.dart"] = (
            "import 'package:flutter/material.dart';\n\n"
            "void main() {\n"
            "  runApp(const MyApp());\n"
            "}\n\n"
            "class MyApp extends StatelessWidget {\n"
            "  const MyApp({super.key});\n\n"
            "  @override\n"
            "  Widget build(BuildContext context) {\n"
            "    return MaterialApp(\n"
            f"      title: '{project_name}',\n"
            "      theme: ThemeData(\n"
            "        useMaterial3: true,\n"
            "        colorSchemeSeed: const Color(0xFF006495),\n"
            "        brightness: Brightness.light,\n"
            "      ),\n"
            "      darkTheme: ThemeData(\n"
            "        useMaterial3: true,\n"
            "        colorSchemeSeed: const Color(0xFF006495),\n"
            "        brightness: Brightness.dark,\n"
            "      ),\n"
            f"      home: const MyHomePage(title: '{project_name}'),\n"
            "    );\n"
            "  }\n"
            "}\n\n"
            "class MyHomePage extends StatefulWidget {\n"
            "  const MyHomePage({super.key, required this.title});\n"
            "  final String title;\n\n"
            "  @override\n"
            "  State<MyHomePage> createState() => _MyHomePageState();\n"
            "}\n\n"
            "class _MyHomePageState extends State<MyHomePage> {\n"
            "  int _counter = 0;\n\n"
            "  void _incrementCounter() {\n"
            "    setState(() {\n"
            "      _counter++;\n"
            "    });\n"
            "  }\n\n"
            "  @override\n"
            "  Widget build(BuildContext context) {\n"
            "    return Scaffold({\n"
            "      appBar: AppBar(\n"
            "        backgroundColor: Theme.of(context).colorScheme.inversePrimary,\n"
            "        title: Text(widget.title),\n"
            "      ),\n"
            "      body: Center(\n"
            "        child: Column(\n"
            "          mainAxisAlignment: MainAxisAlignment.center,\n"
            "          children: <Widget>[\n"
            "            const Text('Polyglot Material 3 Flutter Application:'),\n"
            "            Text(\n"
            "              '$_counter',\n"
            "              style: Theme.of(context).textTheme.headlineMedium,\n"
            "            ),\n"
            "          ],\n"
            "        ),\n"
            "      ),\n"
            "      floatingActionButton: FloatingActionButton(\n"
            "        onPressed: _incrementCounter,\n"
            "        tooltip: 'Increment',\n"
            "        child: const Icon(Icons.add),\n"
            "      ),\n"
            "    );\n"
            "  }\n"
            "}\n"
        )

    else:
        # Generic scaffold
        files["README.md"] = f"# {project_name}\n\nExported for framework `{norm_fw}` with theme `{theme}`.\n"
        files["src/index.js"] = f"console.log('Project {project_name} initialized for {norm_fw}');\n"

    # Always ensure a manifest is present
    manifest = {
        "project_name": project_name,
        "framework": norm_fw,
        "theme": theme,
        "theme_tokens": theme_data,
        "file_count": len(files),
        "generator_version": "0.1.0",
    }
    files["project.manifest.json"] = json.dumps(manifest, indent=2)

    return files


# ---------------------------------------------------------------------------
# Project Validator
# ---------------------------------------------------------------------------

def validate_project_scaffold(
    project_path: Union[str, Path],
    framework: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect and validate an exported project directory against best practices."""
    p = Path(project_path)
    if not p.exists() or not p.is_dir():
        return {
            "valid": False,
            "score": 0,
            "error": f"Path '{project_path}' does not exist or is not a directory.",
            "checks": [],
        }

    checks: List[Dict[str, Any]] = []
    score = 100

    # Check 1: Manifest exists
    has_manifest = (p / "project.manifest.json").exists()
    checks.append({
        "name": "Project Manifest",
        "description": "Checks for project.manifest.json metadata file",
        "passed": has_manifest,
        "weight": 15,
    })
    if not has_manifest:
        score -= 15

    # Check 2: README exists
    has_readme = (p / "README.md").exists()
    checks.append({
        "name": "Documentation",
        "description": "Checks for README.md with getting started instructions",
        "passed": has_readme,
        "weight": 10,
    })
    if not has_readme:
        score -= 10

    # Check 3: Package descriptor (package.json or pubspec.yaml or Package.swift)
    has_package = (p / "package.json").exists() or (p / "pubspec.yaml").exists() or (p / "Package.swift").exists()
    checks.append({
        "name": "Dependency Configuration",
        "description": "Checks for package.json or native package descriptor",
        "passed": has_package,
        "weight": 25,
    })
    if not has_package:
        score -= 25

    # Check 4: Source files
    has_src = (p / "src").exists() or (p / "lib").exists() or any(p.glob("*.tsx")) or any(p.glob("*.vue")) or any(p.glob("*.ts"))
    checks.append({
        "name": "Source Code Tree",
        "description": "Checks for src/ or lib/ directory with components",
        "passed": has_src,
        "weight": 25,
    })
    if not has_src:
        score -= 25

    # Check 5: Build configuration (vite.config, tsconfig, etc.)
    has_config = (p / "vite.config.ts").exists() or (p / "vite.config.js").exists() or (p / "tsconfig.json").exists() or (p / "tailwind.config.js").exists()
    checks.append({
        "name": "Build Toolchain",
        "description": "Checks for TypeScript and bundler configuration",
        "passed": has_config,
        "weight": 25,
    })
    if not has_config:
        score -= 25

    total_files = len(list(p.rglob("*")))

    return {
        "valid": score >= 70,
        "score": max(0, score),
        "target_framework": framework or "auto-detected",
        "total_files": total_files,
        "project_path": str(p.resolve()),
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Diagnostics Provider
# ---------------------------------------------------------------------------

def get_system_diagnostics(verbose: bool = False) -> Dict[str, Any]:
    """Collect multi-OS environment, toolchain, and framework diagnostic data."""
    tools = ["node", "npm", "pnpm", "yarn", "bun", "cargo", "flutter", "swift", "git", "python3"]
    toolchain_status = {}

    for tool in tools:
        cmd_path = shutil.which(tool)
        toolchain_status[tool] = {
            "available": cmd_path is not None,
            "path": cmd_path or "not found",
        }

    diag = {
        "exporter_version": "0.1.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
        },
        "supported_frameworks_count": len(FRAMEWORK_CATALOG),
        "theme_presets_count": len(THEME_PRESETS),
        "toolchain": toolchain_status,
        "environment_clean": True,
    }

    if verbose:
        diag["framework_catalog"] = FRAMEWORK_CATALOG
        diag["theme_presets"] = THEME_PRESETS

    return diag


# ---------------------------------------------------------------------------
# MCP Tool Registry & JSON-RPC Protocol Server
# ---------------------------------------------------------------------------

class MCPServer:
    """Production Model Context Protocol (MCP) server over stdio with JSON-RPC 2.0."""

    def __init__(self, server_name: str = "polyglot-framework-exporter", version: str = "0.1.0") -> None:
        self.server_name = server_name
        self.version = version
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}

        # Register core MCP tools
        self._register_default_tools()
        self._register_default_resources()

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Register a tool with its JSON Schema and execution handler."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
        self._tool_handlers[name] = handler

    def _register_default_tools(self) -> None:
        # Tool 1: exporter_generate
        self.register_tool(
            name="exporter_generate",
            description="Generate full production project files or deterministic ZIP bundle for specified target framework and theme.",
            input_schema={
                "type": "object",
                "properties": {
                    "framework": {
                        "type": "string",
                        "description": "Target framework (e.g., react, vue, svelte, solid, angular, astro, qwik, nextjs, remix, vanilla, flutter, swiftui, compose).",
                        "enum": list(FRAMEWORK_CATALOG.keys()),
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of the project directory and package (default: 'my-app').",
                        "default": "my-app",
                    },
                    "theme": {
                        "type": "string",
                        "description": "Material 3 color theme preset (system, light, dark, ocean, emerald, crimson, amber, purple).",
                        "default": "system",
                    },
                    "options": {
                        "type": "object",
                        "description": "Generation options such as typescript (boolean), styling (string), include_routing (boolean).",
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format: 'files' (JSON file tree), 'zip_base64' (in-memory ZIP as base64 string), or 'zip_disk' (writes ZIP to disk).",
                        "enum": ["files", "zip_base64", "zip_disk"],
                        "default": "files",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional local filesystem directory to export project files or ZIP directly.",
                    },
                },
                "required": ["framework"],
            },
            handler=self._handle_exporter_generate,
        )

        # Tool 2: exporter_supported_frameworks
        self.register_tool(
            name="exporter_supported_frameworks",
            description="Return metadata, versions, templates, and capabilities of all supported target frameworks.",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by framework category (all, spa, meta, native, static, web).",
                        "default": "all",
                    }
                },
            },
            handler=self._handle_supported_frameworks,
        )

        # Tool 3: exporter_convert_html
        self.register_tool(
            name="exporter_convert_html",
            description="Transpile arbitrary HTML/Tailwind markup into idiomatic framework component code (React, Vue, Svelte, Solid, Angular, Vanilla, Flutter, SwiftUI, Compose).",
            input_schema={
                "type": "object",
                "properties": {
                    "html_code": {
                        "type": "string",
                        "description": "Raw HTML markup snippet or complete component to convert.",
                    },
                    "target_framework": {
                        "type": "string",
                        "description": "Target framework identifier.",
                        "enum": list(FRAMEWORK_CATALOG.keys()),
                    },
                    "component_name": {
                        "type": "string",
                        "description": "Desired component class/function name (default: 'ConvertedComponent').",
                        "default": "ConvertedComponent",
                    },
                    "options": {
                        "type": "object",
                        "description": "Conversion options: typescript (bool), theme (str), scoped_styles (bool).",
                    },
                },
                "required": ["html_code", "target_framework"],
            },
            handler=self._handle_convert_html,
        )

        # Tool 4: exporter_validate_scaffold
        self.register_tool(
            name="exporter_validate_scaffold",
            description="Validate an exported project directory against best practices, required configs, and file structure.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the exported project directory on disk.",
                    },
                    "framework": {
                        "type": "string",
                        "description": "Target framework to check specific conventions against.",
                    },
                },
                "required": ["project_path"],
            },
            handler=self._handle_validate_scaffold,
        )

        # Tool 5: exporter_diagnostics
        self.register_tool(
            name="exporter_diagnostics",
            description="Multi-OS diagnostics check reporting Python runtime, OS architecture, toolchain presence, and exporter health.",
            input_schema={
                "type": "object",
                "properties": {
                    "verbose": {
                        "type": "boolean",
                        "description": "Whether to return verbose diagnostic catalog information.",
                        "default": False,
                    }
                },
            },
            handler=self._handle_diagnostics,
        )

    def _register_default_resources(self) -> None:
        self._resources["polyglot://frameworks"] = {
            "uri": "polyglot://frameworks",
            "name": "Supported Framework Catalog",
            "description": "Complete JSON metadata catalog of all supported frameworks and capabilities.",
            "mimeType": "application/json",
        }
        self._resources["polyglot://themes"] = {
            "uri": "polyglot://themes",
            "name": "Material 3 Theme Presets",
            "description": "Color tokens and palette specifications influenced by Material 3 presets.",
            "mimeType": "application/json",
        }

    # -----------------------------------------------------------------------
    # Tool Handler Implementations
    # -----------------------------------------------------------------------

    def _handle_exporter_generate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        framework = args.get("framework", "react").lower()
        project_name = args.get("project_name", "my-app")
        theme = args.get("theme", "system")
        options = args.get("options", {}) or {}
        output_format = args.get("output_format", "files")
        output_dir = args.get("output_dir")

        if framework not in FRAMEWORK_CATALOG:
            if framework not in ("generic", "react", "vue", "svelte", "solid", "angular", "astro", "qwik", "nextjs", "remix", "vanilla", "flutter", "swiftui", "compose"):
                return {
                    "error": f"Unsupported framework '{framework}'. Supported: {', '.join(FRAMEWORK_CATALOG.keys())}"
                }

        file_tree = generate_project_scaffold(
            framework=framework,
            project_name=project_name,
            theme=theme,
            options=options,
        )

        # Handle write to output_dir if specified
        written_files = []
        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            for rel_path, content in file_tree.items():
                dest = out_p / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                written_files.append(str(dest.resolve()))

        # Handle output formats
        if output_format == "zip_base64":
            zip_bytes = build_zip_bundle(
                file_tree=file_tree,  # type: ignore[arg-type]
                project_name=project_name,
                framework=framework,
                theme=theme,
                deterministic=True,
            )
            b64_zip = base64.b64encode(zip_bytes if isinstance(zip_bytes, bytes) else zip_bytes.read_bytes()).decode("ascii")
            return {
                "project_name": project_name,
                "framework": framework,
                "theme": theme,
                "output_format": "zip_base64",
                "zip_size_bytes": len(b64_zip),
                "zip_base64": b64_zip,
                "file_count": len(file_tree),
                "files": sorted(file_tree.keys()),
            }

        elif output_format == "zip_disk":
            zip_target = Path(output_dir or ".") / f"{project_name}.zip"
            build_zip_bundle(
                file_tree=file_tree,  # type: ignore[arg-type]
                project_name=project_name,
                framework=framework,
                theme=theme,
                output_path=zip_target,
                deterministic=True,
            )
            return {
                "project_name": project_name,
                "framework": framework,
                "theme": theme,
                "output_format": "zip_disk",
                "zip_path": str(zip_target.resolve()),
                "file_count": len(file_tree),
                "files": sorted(file_tree.keys()),
            }

        return {
            "project_name": project_name,
            "framework": framework,
            "theme": theme,
            "file_count": len(file_tree),
            "files": file_tree,
            "written_to_disk": len(written_files) > 0,
            "output_directory": str(Path(output_dir).resolve()) if output_dir else None,
        }

    def _handle_supported_frameworks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cat_filter = args.get("category", "all").lower()
        if cat_filter == "all":
            results = FRAMEWORK_CATALOG
        else:
            results = {k: v for k, v in FRAMEWORK_CATALOG.items() if v.get("category") == cat_filter}

        return {
            "count": len(results),
            "category_filter": cat_filter,
            "frameworks": results,
            "available_categories": ["all", "spa", "meta", "native", "static", "web"],
        }

    def _handle_convert_html(self, args: Dict[str, Any]) -> Dict[str, Any]:
        html_code = args.get("html_code", "")
        target_fw = args.get("target_framework", "react")
        component_name = args.get("component_name", "ConvertedComponent")
        options = args.get("options", {})

        if not html_code:
            return {"error": "Parameter 'html_code' cannot be empty."}

        return HTMLTranspiler.transpile(
            html_code=html_code,
            framework=target_fw,
            component_name=component_name,
            options=options,
        )

    def _handle_validate_scaffold(self, args: Dict[str, Any]) -> Dict[str, Any]:
        project_path = args.get("project_path", ".")
        framework = args.get("framework")
        return validate_project_scaffold(project_path, framework)

    def _handle_diagnostics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        verbose = args.get("verbose", False)
        return get_system_diagnostics(verbose)

    # -----------------------------------------------------------------------
    # JSON-RPC 2.0 Dispatch & Protocol Engine
    # -----------------------------------------------------------------------

    def handle_request(self, request_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming JSON-RPC 2.0 request or notification and return response."""
        req_id = request_dict.get("id")
        method = request_dict.get("method")
        params = request_dict.get("params", {})

        # Handle notifications (no id)
        if req_id is None:
            if method == "notifications/initialized":
                logger.info("Client MCP session initialized successfully.")
            return None

        # Standard MCP Methods
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                        "logging": {},
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.version,
                    },
                },
            }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": list(self._tools.values())},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self._tool_handlers:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found.",
                    },
                }

            try:
                handler = self._tool_handlers[tool_name]
                result_obj = handler(arguments)
                is_error = isinstance(result_obj, dict) and "error" in result_obj

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_obj, indent=2),
                            }
                        ],
                        "isError": is_error,
                    },
                }
            except Exception as ex:
                logger.error(f"Error executing tool '{tool_name}': {traceback.format_exc()}")
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Tool Execution Error: {str(ex)}\n\n{traceback.format_exc()}",
                            }
                        ],
                        "isError": True,
                    },
                }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": list(self._resources.values())},
            }

        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "polyglot://frameworks":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(FRAMEWORK_CATALOG, indent=2),
                            }
                        ]
                    },
                }
            elif uri == "polyglot://themes":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(THEME_PRESETS, indent=2),
                            }
                        ]
                    },
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Resource URI '{uri}' not found."},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not recognized by MCP Server.",
                },
            }

    def run_stdio(self) -> None:
        """Run the MCP server over standard input and output streams.

        Handles line-delimited JSON and Content-Length framed JSON-RPC messages.
        Flushes stdout immediately after each response.
        """
        logger.info(f"Starting {self.server_name} v{self.version} MCP server on stdio...")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                # Handle LSP style header if present
                if line.startswith("Content-Length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                        # Read blank line
                        sys.stdin.readline()
                        body = sys.stdin.read(content_length)
                        req_obj = json.loads(body)
                    except Exception as e:
                        logger.error(f"Failed to parse Content-Length frame: {e}")
                        continue
                else:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        req_obj = json.loads(line_str)
                    except json.JSONDecodeError as jde:
                        logger.error(f"JSON Parse Error: {jde}")
                        err_resp = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Parse error"},
                        }
                        sys.stdout.write(json.dumps(err_resp) + "\n")
                        sys.stdout.flush()
                        continue

                response = self.handle_request(req_obj)
                if response is not None:
                    response_json = json.dumps(response)
                    sys.stdout.write(response_json + "\n")
                    sys.stdout.flush()

            except (KeyboardInterrupt, SystemExit):
                logger.info("MCP server shutting down gracefully.")
                break
            except Exception as e:
                logger.error(f"Unhandled MCP loop error: {traceback.format_exc()}")


def run_mcp_server() -> None:
    """Entrypoint function to run the MCP Server."""
    server = MCPServer()
    server.run_stdio()
