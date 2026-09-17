"""Universal AST & Semantic Transpiler for polyglot-framework-exporter.

Converts raw semantic HTML, Markdown with frontmatter, or JSON schemas into
structured Component Trees (ProjectAST) supporting all 6 Master Themes:
- Material 3 Light (Google Influenced) (`light_material` / `google_material_3`)
- Obsidian Gold (`obsidian_gold`)
- Midnight Neon (`midnight_neon`)
- Acid Grid (`acid_grid`)
- Ultraviolet Glass (`ultraviolet_glass`)
- Retro Terminal (`retro_terminal`)

Built with 100% Python Standard Library (no third-party dependencies).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .compat import read_text_safely


# ==============================================================================
# Theme Definitions & Master Design Tokens
# ==============================================================================

@dataclass
class ThemeConfig:
    """Design tokens and styling configuration for a Master Theme."""
    name: str
    display_name: str
    description: str
    is_dark: bool
    bg_primary: str
    bg_secondary: str
    bg_surface: str
    bg_surface_hover: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_primary: str
    accent_secondary: str
    accent_glow: str
    border_color: str
    border_subtle: str
    badge_bg: str
    badge_text: str
    btn_primary_bg: str
    btn_primary_text: str
    btn_primary_hover: str
    btn_secondary_bg: str
    btn_secondary_text: str
    btn_secondary_hover: str
    font_sans: str
    font_heading: str
    font_mono: str
    card_shadow: str
    container_max_w: str = "max-w-7xl"

    def to_css_variables(self) -> Dict[str, str]:
        """Convert theme tokens to CSS Custom Properties dictionary."""
        return {
            "--bg-primary": self.bg_primary,
            "--bg-secondary": self.bg_secondary,
            "--bg-surface": self.bg_surface,
            "--bg-surface-hover": self.bg_surface_hover,
            "--text-primary": self.text_primary,
            "--text-secondary": self.text_secondary,
            "--text-muted": self.text_muted,
            "--accent-primary": self.accent_primary,
            "--accent-secondary": self.accent_secondary,
            "--accent-glow": self.accent_glow,
            "--border-color": self.border_color,
            "--border-subtle": self.border_subtle,
            "--badge-bg": self.badge_bg,
            "--badge-text": self.badge_text,
            "--btn-primary-bg": self.btn_primary_bg,
            "--btn-primary-text": self.btn_primary_text,
            "--btn-primary-hover": self.btn_primary_hover,
            "--btn-secondary-bg": self.btn_secondary_bg,
            "--btn-secondary-text": self.btn_secondary_text,
            "--btn-secondary-hover": self.btn_secondary_hover,
        }

    def to_css_string(self) -> str:
        """Format CSS variables block for injection into stylesheets."""
        lines = [":root {"]
        for k, v in self.to_css_variables().items():
            lines.append(f"  {k}: {v};")
        lines.append(f"  --font-sans: {self.font_sans};")
        lines.append(f"  --font-heading: {self.font_heading};")
        lines.append(f"  --font-mono: {self.font_mono};")
        lines.append("}")
        return "\n".join(lines)


THEMES: Dict[str, ThemeConfig] = {
    "light_material": ThemeConfig(
        name="light_material",
        display_name="Material 3 Light (Google Influenced)",
        description="Clean, modern palette influenced by Google Material Design 3 with pastel slate, indigo accents and high contrast readability.",
        is_dark=False,
        bg_primary="#f8fafc",
        bg_secondary="#f1f5f9",
        bg_surface="#ffffff",
        bg_surface_hover="#f8fafc",
        text_primary="#0f172a",
        text_secondary="#334155",
        text_muted="#64748b",
        accent_primary="#4f46e5",
        accent_secondary="#0ea5e9",
        accent_glow="rgba(79, 70, 229, 0.15)",
        border_color="#e2e8f0",
        border_subtle="#cbd5e1",
        badge_bg="#e0e7ff",
        badge_text="#3730a3",
        btn_primary_bg="#4f46e5",
        btn_primary_text="#ffffff",
        btn_primary_hover="#4338ca",
        btn_secondary_bg="#f1f5f9",
        btn_secondary_text="#0f172a",
        btn_secondary_hover="#e2e8f0",
        font_sans="Inter, Roboto, -apple-system, sans-serif",
        font_heading="Inter, Roboto, sans-serif",
        font_mono="ui-monospace, SFMono-Regular, Menlo, monospace",
        card_shadow="0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    ),
    "google_material_3": ThemeConfig(
        name="google_material_3",
        display_name="Material 3 Light (Google Influenced)",
        description="Alias for light_material.",
        is_dark=False,
        bg_primary="#f8fafc",
        bg_secondary="#f1f5f9",
        bg_surface="#ffffff",
        bg_surface_hover="#f8fafc",
        text_primary="#0f172a",
        text_secondary="#334155",
        text_muted="#64748b",
        accent_primary="#4f46e5",
        accent_secondary="#0ea5e9",
        accent_glow="rgba(79, 70, 229, 0.15)",
        border_color="#e2e8f0",
        border_subtle="#cbd5e1",
        badge_bg="#e0e7ff",
        badge_text="#3730a3",
        btn_primary_bg="#4f46e5",
        btn_primary_text="#ffffff",
        btn_primary_hover="#4338ca",
        btn_secondary_bg="#f1f5f9",
        btn_secondary_text="#0f172a",
        btn_secondary_hover="#e2e8f0",
        font_sans="Inter, Roboto, -apple-system, sans-serif",
        font_heading="Inter, Roboto, sans-serif",
        font_mono="ui-monospace, SFMono-Regular, Menlo, monospace",
        card_shadow="0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    ),
    "obsidian_gold": ThemeConfig(
        name="obsidian_gold",
        display_name="Obsidian Gold",
        description="Deep obsidian black surfaces with metallic gold and warm amber accents, luxury typography, and subtle golden glows.",
        is_dark=True,
        bg_primary="#09090b",
        bg_secondary="#121215",
        bg_surface="#18181b",
        bg_surface_hover="#27272a",
        text_primary="#fafafa",
        text_secondary="#d4d4d8",
        text_muted="#a1a1aa",
        accent_primary="#eab308",
        accent_secondary="#ca8a04",
        accent_glow="rgba(234, 179, 8, 0.25)",
        border_color="#3f3f46",
        border_subtle="#27272a",
        badge_bg="rgba(234, 179, 8, 0.15)",
        badge_text="#fef08a",
        btn_primary_bg="#eab308",
        btn_primary_text="#09090b",
        btn_primary_hover="#facc15",
        btn_secondary_bg="#27272a",
        btn_secondary_text="#fafafa",
        btn_secondary_hover="#3f3f46",
        font_sans="'Plus Jakarta Sans', Inter, sans-serif",
        font_heading="'Plus Jakarta Sans', Georgia, sans-serif",
        font_mono="'JetBrains Mono', monospace",
        card_shadow="0 10px 30px -10px rgba(0, 0, 0, 0.7), 0 0 1px 1px rgba(234, 179, 8, 0.1)",
    ),
    "midnight_neon": ThemeConfig(
        name="midnight_neon",
        display_name="Midnight Neon",
        description="Cyberpunk-inspired deep midnight palette with radiant cyan and electric magenta glows against deep space backdrops.",
        is_dark=True,
        bg_primary="#030712",
        bg_secondary="#0f172a",
        bg_surface="#111827",
        bg_surface_hover="#1f2937",
        text_primary="#f8fafc",
        text_secondary="#cbd5e1",
        text_muted="#94a3b8",
        accent_primary="#06b6d4",
        accent_secondary="#ec4899",
        accent_glow="rgba(6, 182, 212, 0.35)",
        border_color="#1e293b",
        border_subtle="#334155",
        badge_bg="rgba(6, 182, 212, 0.15)",
        badge_text="#67e8f9",
        btn_primary_bg="#06b6d4",
        btn_primary_text="#030712",
        btn_primary_hover="#22d3ee",
        btn_secondary_bg="#1e293b",
        btn_secondary_text="#f8fafc",
        btn_secondary_hover="#334155",
        font_sans="'Space Grotesk', Inter, sans-serif",
        font_heading="'Space Grotesk', sans-serif",
        font_mono="'Fira Code', monospace",
        card_shadow="0 0 20px -5px rgba(6, 182, 212, 0.25)",
    ),
    "acid_grid": ThemeConfig(
        name="acid_grid",
        display_name="Acid Grid",
        description="High-contrast neo-brutalist dark aesthetic with stark lime-400 borders, technical monospace typography, and dense modular grid layouts.",
        is_dark=True,
        bg_primary="#050505",
        bg_secondary="#0a0a0a",
        bg_surface="#121212",
        bg_surface_hover="#1c1c1c",
        text_primary="#f5f5f5",
        text_secondary="#d4d4d4",
        text_muted="#737373",
        accent_primary="#bef264",
        accent_secondary="#a3e635",
        accent_glow="rgba(190, 242, 100, 0.3)",
        border_color="#262626",
        border_subtle="#404040",
        badge_bg="#bef264",
        badge_text="#050505",
        btn_primary_bg="#bef264",
        btn_primary_text="#050505",
        btn_primary_hover="#d9f99d",
        btn_secondary_bg="#171717",
        btn_secondary_text="#f5f5f5",
        btn_secondary_hover="#262626",
        font_sans="'JetBrains Mono', monospace",
        font_heading="'JetBrains Mono', monospace",
        font_mono="'JetBrains Mono', monospace",
        card_shadow="4px 4px 0px 0px #bef264",
    ),
    "ultraviolet_glass": ThemeConfig(
        name="ultraviolet_glass",
        display_name="Ultraviolet Glass",
        description="Cosmic deep violet backdrop with frosted glassmorphic panels, celestial gradients, and glowing blur highlights.",
        is_dark=True,
        bg_primary="#0b0416",
        bg_secondary="#150a2b",
        bg_surface="rgba(30, 15, 55, 0.65)",
        bg_surface_hover="rgba(45, 25, 80, 0.8)",
        text_primary="#faf5ff",
        text_secondary="#e9d5ff",
        text_muted="#c084fc",
        accent_primary="#a855f7",
        accent_secondary="#38bdf8",
        accent_glow="rgba(168, 85, 247, 0.4)",
        border_color="rgba(168, 85, 247, 0.25)",
        border_subtle="rgba(168, 85, 247, 0.15)",
        badge_bg="rgba(168, 85, 247, 0.2)",
        badge_text="#e9d5ff",
        btn_primary_bg="#a855f7",
        btn_primary_text="#ffffff",
        btn_primary_hover="#9333ea",
        btn_secondary_bg="rgba(255, 255, 255, 0.08)",
        btn_secondary_text="#faf5ff",
        btn_secondary_hover="rgba(255, 255, 255, 0.15)",
        font_sans="'Outfit', 'Plus Jakarta Sans', sans-serif",
        font_heading="'Outfit', sans-serif",
        font_mono="'Fira Code', monospace",
        card_shadow="0 8px 32px 0 rgba(168, 85, 247, 0.15)",
    ),
    "retro_terminal": ThemeConfig(
        name="retro_terminal",
        display_name="Retro Terminal",
        description="Authentic CRT phosphor green terminal experience with scanlines, monospace glyphs, retro cursor accents, and terminal chrome.",
        is_dark=True,
        bg_primary="#0c100c",
        bg_secondary="#080c08",
        bg_surface="#131b13",
        bg_surface_hover="#1a251a",
        text_primary="#86efac",
        text_secondary="#4ade80",
        text_muted="#22c55e",
        accent_primary="#22c55e",
        accent_secondary="#eab308",
        accent_glow="rgba(34, 197, 94, 0.4)",
        border_color="#166534",
        border_subtle="#14532d",
        badge_bg="rgba(34, 197, 94, 0.15)",
        badge_text="#86efac",
        btn_primary_bg="#22c55e",
        btn_primary_text="#0c100c",
        btn_primary_hover="#4ade80",
        btn_secondary_bg="#131b13",
        btn_secondary_text="#86efac",
        btn_secondary_hover="#1a251a",
        font_sans="'VT323', 'Courier New', monospace",
        font_heading="'VT323', 'Courier New', monospace",
        font_mono="'Courier New', monospace",
        card_shadow="0 0 15px rgba(34, 197, 94, 0.2)",
    ),
}

THEME_ALIASES: Dict[str, str] = {
    "light": "light_material",
    "material_light": "light_material",
    "material": "light_material",
    "google": "light_material",
    "google_material": "light_material",
    "dark": "obsidian_gold",
    "system": "obsidian_gold",
    "gold": "obsidian_gold",
    "neon": "midnight_neon",
    "cyberpunk": "midnight_neon",
    "acid": "acid_grid",
    "brutalist": "acid_grid",
    "glass": "ultraviolet_glass",
    "violet": "ultraviolet_glass",
    "terminal": "retro_terminal",
    "matrix": "retro_terminal",
}

DEFAULT_THEME = "obsidian_gold"


def get_theme(name: Optional[str]) -> ThemeConfig:
    """Resolve theme by name with safe fallback to DEFAULT_THEME."""
    if not name:
        return THEMES[DEFAULT_THEME]
    norm_name = name.lower().strip().replace("-", "_")
    resolved = THEME_ALIASES.get(norm_name, norm_name)
    return THEMES.get(resolved, THEMES.get(norm_name, THEMES[DEFAULT_THEME]))


# ==============================================================================
# Structured Component Models
# ==============================================================================

@dataclass
class LinkItem:
    label: str
    href: str = "#"
    is_cta: bool = False
    external: bool = False


@dataclass
class NavigationComponent:
    brand_name: str = "Polyglot"
    brand_icon: str = "sparkles"
    links: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"label": "Features", "href": "#features"},
        {"label": "Pricing", "href": "#pricing"},
        {"label": "FAQ", "href": "#faq"},
    ])
    cta: Dict[str, str] = field(default_factory=lambda: {
        "label": "Get Started",
        "href": "#cta"
    })


@dataclass
class HeroComponent:
    title: str = "Universal Full-Stack Application Framework"
    subtitle: str = "Design once in semantic AST, export seamlessly into 9 enterprise production-ready frameworks."
    badge: str = "v2.0 Universal Polyglot Engine"
    primary_cta: Dict[str, str] = field(default_factory=lambda: {
        "label": "Export Now",
        "href": "#pricing"
    })
    secondary_cta: Dict[str, str] = field(default_factory=lambda: {
        "label": "View Architecture",
        "href": "#features"
    })
    image_url: str = ""
    code_snippet: str = "polyglot export --framework nextjs --theme obsidian_gold"
    highlights: List[str] = field(default_factory=lambda: [
        "9 Target Frameworks",
        "Zero Runtime Dependencies",
        "Production Ready",
        "100% Type-Safe"
    ])


@dataclass
class FeatureItem:
    title: str
    description: str
    icon: str = "zap"
    badge: str = ""
    link: str = ""


@dataclass
class FeaturesComponent:
    title: str = "Engineered for Velocity & Precision"
    subtitle: str = "Everything you need to ship world-class software across modern web and desktop ecosystems."
    badge: str = "Capabilities"
    items: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "icon": "layers",
            "title": "Universal AST Transpilation",
            "description": "Transforms HTML, Markdown, or JSON into deterministic semantic component trees with zero bloat.",
            "badge": "Core"
        },
        {
            "icon": "palette",
            "title": "6 Master Themes",
            "description": "Pre-tuned design systems spanning Obsidian Gold, Midnight Neon, Acid Grid, and Material 3.",
            "badge": "Design"
        },
        {
            "icon": "cpu",
            "title": "Zero External Dependencies",
            "description": "Pure standard library architecture ensures ultra-fast cold starts and unbreakable portability.",
            "badge": "Performance"
        },
        {
            "icon": "monitor",
            "title": "Cross-Platform Desktop & Web",
            "description": "Generate clean Tauri v2 and Electron desktop shells alongside Next.js, Astro, Nuxt, and SvelteKit apps.",
            "badge": "Cross-Platform"
        },
        {
            "icon": "shield",
            "title": "Atomic & Safe Writes",
            "description": "Built-in anti-path traversal protection and crash-proof atomic writes ensure rock-solid disk operations.",
            "badge": "Security"
        },
        {
            "icon": "rocket",
            "title": "One-Click Deployments",
            "description": "Bundles ready-to-deploy netlify.toml and vercel.json configs for instant preview and production builds.",
            "badge": "DevOps"
        },
    ])
    columns: int = 3


@dataclass
class PricingTier:
    name: str
    price: str
    period: str = "/month"
    description: str = ""
    features: List[str] = field(default_factory=list)
    is_popular: bool = False
    cta_label: str = "Get Started"
    cta_href: str = "#"


@dataclass
class PricingComponent:
    title: str = "Simple, Predictable Pricing"
    subtitle: str = "Choose the plan that best fits your development cadence and deployment footprint."
    badge: str = "Pricing"
    tiers: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "name": "Starter",
            "price": "$0",
            "period": "free forever",
            "description": "Ideal for indie hackers, hobbyists, and rapid prototypes.",
            "features": ["3 Framework Exports", "Standard Themes", "Single-Page AST", "Community Discord"],
            "is_popular": False,
            "cta_label": "Start Free",
            "cta_href": "#"
        },
        {
            "name": "Pro Developer",
            "price": "$29",
            "period": "/month",
            "description": "Built for professional engineers building multi-target products.",
            "features": ["All 9 Framework Targets", "All 6 Master Themes", "Desktop Tauri & Electron", "Atomic Deploy Hooks", "Priority Support"],
            "is_popular": True,
            "cta_label": "Upgrade to Pro",
            "cta_href": "#"
        },
        {
            "name": "Enterprise",
            "price": "$199",
            "period": "/month",
            "description": "Custom pipelines, bespoke design tokens, and dedicated SLA.",
            "features": ["Custom Design Tokens", "Bespoke Generators", "CI/CD Pipeline Integration", "Dedicated Slack Channel", "Enterprise SLA"],
            "is_popular": False,
            "cta_label": "Contact Sales",
            "cta_href": "#"
        }
    ])


@dataclass
class StatItem:
    value: str
    label: str
    change: str = ""
    description: str = ""


@dataclass
class StatsComponent:
    title: str = "Proven Track Record"
    subtitle: str = "Numbers that reflect unmatched speed, portability, and reliability."
    metrics: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"value": "9+", "label": "Framework Targets", "change": "+3 this quarter", "description": "Web & Desktop support"},
        {"value": "< 10ms", "label": "Transpile Latency", "change": "Ultra Fast", "description": "Pure stdlib parsing"},
        {"value": "100%", "label": "Type Safety", "change": "Zero Errors", "description": "TypeScript & Rust ready"},
        {"value": "0", "label": "External Deps", "change": "Clean", "description": "Zero security vulnerabilities"},
    ])


@dataclass
class TestimonialItem:
    quote: str
    author: str
    role: str
    company: str
    avatar_url: str = ""
    rating: int = 5


@dataclass
class TestimonialsComponent:
    title: str = "Loved by Developers Worldwide"
    subtitle: str = "Hear how teams accelerate their multi-platform delivery with Polyglot Framework Exporter."
    items: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "quote": "Polyglot saved our team hundreds of hours rebuilding web apps into Tauri desktop shells. One command and everything just works.",
            "author": "Elena Rostova",
            "role": "Head of Engineering",
            "company": "Nexus Labs",
            "avatar_url": "",
            "rating": 5
        },
        {
            "quote": "The Obsidian Gold theme is stunning. Our Next.js and Astro landing pages share identical fidelity without maintaining two codebases.",
            "author": "Marcus Vance",
            "role": "Lead Architect",
            "company": "Aether Dynamics",
            "avatar_url": "",
            "rating": 5
        },
        {
            "quote": "Having zero Python runtime dependencies makes CI/CD a dream. It runs instantaneously on any Linux, macOS, or Windows runner.",
            "author": "Sarah Lin",
            "role": "Principal DevOps",
            "company": "CloudForge",
            "avatar_url": "",
            "rating": 5
        }
    ])


@dataclass
class FAQItem:
    question: str
    answer: str
    category: str = "General"


@dataclass
class FAQComponent:
    title: str = "Frequently Asked Questions"
    subtitle: str = "Everything you need to know about transpilation, themes, and framework export."
    items: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "question": "Which frameworks are currently supported?",
            "answer": "Polyglot exports complete projects for Astro 5, Next.js 15 (App Router), Vite + React 19, SvelteKit 2 (Svelte 5), Nuxt 3, Deno Fresh, Remix / React Router v7, Tauri v2, and Electron Forge."
        },
        {
            "question": "Can I switch themes after exporting?",
            "answer": "Yes! All styling is structured via Master Theme CSS Custom Properties and Tailwind configuration tokens. You can swap theme tokens seamlessly."
        },
        {
            "question": "Are there external runtime requirements?",
            "answer": "No. The core generator and transpiler run entirely on Python's standard library (Python 3.8+). No pip installs required to generate projects."
        },
        {
            "question": "How are desktop apps structured?",
            "answer": "Tauri v2 generates a Rust cargo crate with tauri.conf.json and bundled frontend. Electron generates modern main/preload processes with contextIsolation enabled."
        }
    ])


@dataclass
class CTAComponent:
    title: str = "Ready to Build Across Every Framework?"
    subtitle: str = "Export your application into 9 modern frameworks in under 2 seconds. Free & open source."
    badge: str = "Get Started Today"
    primary_cta: Dict[str, str] = field(default_factory=lambda: {
        "label": "Start Exporting",
        "href": "#pricing"
    })
    secondary_cta: Dict[str, str] = field(default_factory=lambda: {
        "label": "Explore Documentation",
        "href": "https://github.com"
    })
    background_style: str = "gradient"


@dataclass
class CodeTab:
    filename: str
    language: str
    code: str


@dataclass
class CodeViewerComponent:
    title: str = "Code Once. Export Anywhere."
    subtitle: str = "Inspect the exact source output generated for each supported framework target."
    tabs: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "filename": "astro.config.mjs",
            "language": "javascript",
            "code": """import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind({ applyBaseStyles: false })],
});"""
        },
        {
            "filename": "app/page.tsx",
            "language": "typescript",
            "code": """import Hero from '@/components/Hero';
import Features from '@/components/Features';
import Pricing from '@/components/Pricing';

export default function Page() {
  return (
    <main className="min-h-screen bg-bg-primary text-text-primary">
      <Hero />
      <Features />
      <Pricing />
    </main>
  );
}"""
        },
        {
            "filename": "src-tauri/tauri.conf.json",
            "language": "json",
            "code": """{
  "productName": "Polyglot App",
  "version": "1.0.0",
  "identifier": "com.polyglot.app",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:1420"
  }
}"""
        }
    ])


@dataclass
class FooterComponent:
    brand_name: str = "Polyglot Framework Exporter"
    tagline: str = "Universal AST transpilation for multi-target modern software engineering."
    columns: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "title": "Frameworks",
            "links": [
                {"label": "Next.js", "href": "#"},
                {"label": "Astro", "href": "#"},
                {"label": "Vite React", "href": "#"},
                {"label": "SvelteKit", "href": "#"},
                {"label": "Nuxt", "href": "#"},
            ]
        },
        {
            "title": "Desktop",
            "links": [
                {"label": "Tauri v2", "href": "#"},
                {"label": "Electron", "href": "#"},
                {"label": "Deno Fresh", "href": "#"},
                {"label": "Remix", "href": "#"},
            ]
        },
        {
            "title": "Resources",
            "links": [
                {"label": "Documentation", "href": "#"},
                {"label": "Theme System", "href": "#"},
                {"label": "AST Specification", "href": "#"},
                {"label": "GitHub Repository", "href": "#"},
            ]
        }
    ])
    social_links: List[Dict[str, str]] = field(default_factory=lambda: [
        {"platform": "github", "href": "https://github.com", "icon": "github"},
        {"platform": "twitter", "href": "https://x.com", "icon": "twitter"},
        {"platform": "discord", "href": "https://discord.com", "icon": "discord"},
    ])
    copyright: str = "© 2026 Polyglot Framework Exporter. All rights reserved."


@dataclass
class CustomComponent:
    component_name: str
    raw_html: str = ""
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentNode:
    """A single node inside the ProjectAST component tree."""
    id: str
    type: str  # "hero", "features", "pricing", "stats", "testimonials", "faq", "cta", "code_viewer", "custom"
    data: Dict[str, Any]
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "order": self.order,
        }


# ==============================================================================
# Universal Project AST
# ==============================================================================

@dataclass
class ProjectAST:
    """Universal Abstract Syntax Tree representing a full-fidelity application."""
    title: str = "Polyglot App"
    description: str = "Modern full-stack application built with Polyglot Framework Exporter."
    author: str = "Polyglot Core"
    version: str = "1.0.0"
    theme: str = "obsidian_gold"
    theme_name: Optional[str] = None
    lang: str = "en"
    navigation: Optional[NavigationComponent] = field(default_factory=NavigationComponent)
    sections: List[ComponentNode] = field(default_factory=list)
    footer: Optional[FooterComponent] = field(default_factory=FooterComponent)
    meta_tags: Dict[str, str] = field(default_factory=lambda: {
        "viewport": "width=device-width, initial-scale=1.0",
        "og:type": "website",
    })
    custom_css: str = ""
    custom_js: str = ""

    def __post_init__(self) -> None:
        if self.theme_name and (not self.theme or self.theme == DEFAULT_THEME):
            self.theme = self.theme_name
        elif not self.theme_name:
            self.theme_name = self.theme

    def get_theme(self) -> ThemeConfig:
        """Get the resolved ThemeConfig for this AST."""
        return get_theme(self.theme)

    def add_section(self, node: ComponentNode) -> ProjectAST:
        """Append a section node."""
        node.order = len(self.sections)
        self.sections.append(node)
        return self

    def get_section(self, section_type: str) -> Optional[ComponentNode]:
        """Find the first section matching the given type."""
        for sec in self.sections:
            if sec.type == section_type:
                return sec
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ProjectAST to standard dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "theme": self.theme,
            "lang": self.lang,
            "navigation": asdict(self.navigation) if self.navigation else None,
            "sections": [s.to_dict() for s in self.sections],
            "footer": asdict(self.footer) if self.footer else None,
            "meta_tags": self.meta_tags,
            "custom_css": self.custom_css,
            "custom_js": self.custom_js,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectAST:
        """Construct ProjectAST from dictionary schema."""
        title = data.get("title", "Polyglot App")
        description = data.get("description", "Polyglot Application")
        author = data.get("author", "Polyglot Core")
        version = data.get("version", "1.0.0")
        theme = data.get("theme", DEFAULT_THEME)
        lang = data.get("lang", "en")
        meta_tags = data.get("meta_tags", {"viewport": "width=device-width, initial-scale=1.0"})
        custom_css = data.get("custom_css", "")
        custom_js = data.get("custom_js", "")

        nav_data = data.get("navigation")
        navigation = NavigationComponent(**nav_data) if isinstance(nav_data, dict) else (NavigationComponent() if nav_data is None else None)

        footer_data = data.get("footer")
        footer = FooterComponent(**footer_data) if isinstance(footer_data, dict) else (FooterComponent() if footer_data is None else None)

        sections: List[ComponentNode] = []
        raw_sections = data.get("sections", [])
        for idx, sec in enumerate(raw_sections):
            if isinstance(sec, dict):
                sec_id = sec.get("id", f"sec_{idx}")
                sec_type = sec.get("type", "custom")
                sec_data = sec.get("data", {})
                sections.append(ComponentNode(id=sec_id, type=sec_type, data=sec_data, order=idx))

        # If no sections provided, populate with rich standard default sections
        if not sections:
            sections = [
                ComponentNode(id="hero", type="hero", data=asdict(HeroComponent()), order=0),
                ComponentNode(id="features", type="features", data=asdict(FeaturesComponent()), order=1),
                ComponentNode(id="code_viewer", type="code_viewer", data=asdict(CodeViewerComponent()), order=2),
                ComponentNode(id="stats", type="stats", data=asdict(StatsComponent()), order=3),
                ComponentNode(id="pricing", type="pricing", data=asdict(PricingComponent()), order=4),
                ComponentNode(id="testimonials", type="testimonials", data=asdict(TestimonialsComponent()), order=5),
                ComponentNode(id="faq", type="faq", data=asdict(FAQComponent()), order=6),
                ComponentNode(id="cta", type="cta", data=asdict(CTAComponent()), order=7),
            ]

        return cls(
            title=title,
            description=description,
            author=author,
            version=version,
            theme=theme,
            lang=lang,
            navigation=navigation,
            sections=sections,
            footer=footer,
            meta_tags=meta_tags,
            custom_css=custom_css,
            custom_js=custom_js,
        )

    def to_semantic_html(self) -> str:
        """Render complete semantic HTML5 document representation."""
        theme_cfg = self.get_theme()
        body_sections = []

        # Navigation
        if self.navigation:
            nav_links = "".join([f'        <a href="{html.escape(l.get("href", "#"))}" class="nav-link">{html.escape(l.get("label", ""))}</a>\n' for l in self.navigation.links])
            cta_html = f'<a href="{html.escape(self.navigation.cta.get("href", "#"))}" class="btn-cta">{html.escape(self.navigation.cta.get("label", "Get Started"))}</a>' if self.navigation.cta else ""
            body_sections.append(f"""  <header class="site-header">
    <nav class="container">
      <div class="brand">{html.escape(self.navigation.brand_name)}</div>
      <div class="nav-menu">
{nav_links}      </div>
      <div class="nav-actions">
        {cta_html}
      </div>
    </nav>
  </header>""")

        # Main content sections
        main_content = []
        for sec in self.sections:
            stype = sec.type
            sdata = sec.data

            if stype == "hero":
                title = html.escape(sdata.get("title", ""))
                subtitle = html.escape(sdata.get("subtitle", ""))
                badge = html.escape(sdata.get("badge", ""))
                badge_html = f'<span class="badge">{badge}</span>\n' if badge else ""
                p_cta = sdata.get("primary_cta", {})
                s_cta = sdata.get("secondary_cta", {})
                main_content.append(f"""    <section id="{sec.id}" class="hero-section">
      <div class="container">
        {badge_html}
        <h1 class="hero-title">{title}</h1>
        <p class="hero-subtitle">{subtitle}</p>
        <div class="hero-actions">
          <a href="{html.escape(p_cta.get('href', '#'))}" class="btn btn-primary">{html.escape(p_cta.get('label', 'Get Started'))}</a>
          <a href="{html.escape(s_cta.get('href', '#'))}" class="btn btn-secondary">{html.escape(s_cta.get('label', 'Learn More'))}</a>
        </div>
      </div>
    </section>""")

            elif stype == "features":
                title = html.escape(sdata.get("title", "Features"))
                subtitle = html.escape(sdata.get("subtitle", ""))
                items = sdata.get("items", [])
                cards = []
                for it in items:
                    cards.append(f"""        <div class="feature-card">
          <div class="feature-icon">{html.escape(it.get('icon', 'zap'))}</div>
          <h3>{html.escape(it.get('title', ''))}</h3>
          <p>{html.escape(it.get('description', ''))}</p>
        </div>""")
                cards_html = "\n".join(cards)
                main_content.append(f"""    <section id="{sec.id}" class="features-section">
      <div class="container">
        <h2 class="section-title">{title}</h2>
        <p class="section-subtitle">{subtitle}</p>
        <div class="features-grid">
{cards_html}
        </div>
      </div>
    </section>""")

            elif stype == "pricing":
                title = html.escape(sdata.get("title", "Pricing"))
                subtitle = html.escape(sdata.get("subtitle", ""))
                tiers = sdata.get("tiers", [])
                tier_cards = []
                for t in tiers:
                    feats = "".join([f'            <li>{html.escape(f)}</li>\n' for f in t.get("features", [])])
                    pop_cls = " popular" if t.get("is_popular") else ""
                    tier_cards.append(f"""        <div class="pricing-card{pop_cls}">
          <h3>{html.escape(t.get('name', ''))}</h3>
          <div class="price-val">{html.escape(t.get('price', '$0'))}<span class="period">{html.escape(t.get('period', '/mo'))}</span></div>
          <p class="pricing-desc">{html.escape(t.get('description', ''))}</p>
          <ul class="pricing-features">
{feats}          </ul>
          <a href="{html.escape(t.get('cta_href', '#'))}" class="btn btn-primary">{html.escape(t.get('cta_label', 'Choose Plan'))}</a>
        </div>""")
                tiers_html = "\n".join(tier_cards)
                main_content.append(f"""    <section id="{sec.id}" class="pricing-section">
      <div class="container">
        <h2 class="section-title">{title}</h2>
        <p class="section-subtitle">{subtitle}</p>
        <div class="pricing-grid">
{tiers_html}
        </div>
      </div>
    </section>""")

            elif stype == "stats":
                metrics = sdata.get("metrics", [])
                stat_items = []
                for m in metrics:
                    stat_items.append(f"""        <div class="stat-card">
          <div class="stat-value">{html.escape(m.get('value', ''))}</div>
          <div class="stat-label">{html.escape(m.get('label', ''))}</div>
          <div class="stat-desc">{html.escape(m.get('description', ''))}</div>
        </div>""")
                stats_html = "\n".join(stat_items)
                main_content.append(f"""    <section id="{sec.id}" class="stats-section">
      <div class="container">
        <div class="stats-grid">
{stats_html}
        </div>
      </div>
    </section>""")

            elif stype == "testimonials":
                title = html.escape(sdata.get("title", "Testimonials"))
                subtitle = html.escape(sdata.get("subtitle", ""))
                items = sdata.get("items", [])
                t_cards = []
                for it in items:
                    t_cards.append(f"""        <div class="testimonial-card">
          <blockquote class="quote">"{html.escape(it.get('quote', ''))}"</blockquote>
          <div class="author-info">
            <strong>{html.escape(it.get('author', ''))}</strong>
            <span>{html.escape(it.get('role', ''))}, {html.escape(it.get('company', ''))}</span>
          </div>
        </div>""")
                t_html = "\n".join(t_cards)
                main_content.append(f"""    <section id="{sec.id}" class="testimonials-section">
      <div class="container">
        <h2 class="section-title">{title}</h2>
        <p class="section-subtitle">{subtitle}</p>
        <div class="testimonials-grid">
{t_html}
        </div>
      </div>
    </section>""")

            elif stype == "faq":
                title = html.escape(sdata.get("title", "FAQ"))
                subtitle = html.escape(sdata.get("subtitle", ""))
                items = sdata.get("items", [])
                faq_items = []
                for it in items:
                    faq_items.append(f"""        <details class="faq-item">
          <summary>{html.escape(it.get('question', ''))}</summary>
          <div class="faq-answer"><p>{html.escape(it.get('answer', ''))}</p></div>
        </details>""")
                faq_html = "\n".join(faq_items)
                main_content.append(f"""    <section id="{sec.id}" class="faq-section">
      <div class="container">
        <h2 class="section-title">{title}</h2>
        <p class="section-subtitle">{subtitle}</p>
        <div class="faq-list">
{faq_html}
        </div>
      </div>
    </section>""")

            elif stype == "cta":
                title = html.escape(sdata.get("title", ""))
                subtitle = html.escape(sdata.get("subtitle", ""))
                p_cta = sdata.get("primary_cta", {})
                s_cta = sdata.get("secondary_cta", {})
                main_content.append(f"""    <section id="{sec.id}" class="cta-section">
      <div class="container">
        <h2>{title}</h2>
        <p>{subtitle}</p>
        <div class="cta-actions">
          <a href="{html.escape(p_cta.get('href', '#'))}" class="btn btn-primary">{html.escape(p_cta.get('label', 'Get Started'))}</a>
          <a href="{html.escape(s_cta.get('href', '#'))}" class="btn btn-secondary">{html.escape(s_cta.get('label', 'Learn More'))}</a>
        </div>
      </div>
    </section>""")

            elif stype == "code_viewer":
                title = html.escape(sdata.get("title", "Code"))
                subtitle = html.escape(sdata.get("subtitle", ""))
                tabs = sdata.get("tabs", [])
                tab_headers = []
                tab_panes = []
                for i, tab in enumerate(tabs):
                    active_cls = " active" if i == 0 else ""
                    tab_headers.append(f'<button class="tab-btn{active_cls}">{html.escape(tab.get("filename", "code"))}</button>')
                    tab_panes.append(f'<pre class="tab-pane{active_cls}"><code>{html.escape(tab.get("code", ""))}</code></pre>')
                main_content.append(f"""    <section id="{sec.id}" class="code-viewer-section">
      <div class="container">
        <h2 class="section-title">{title}</h2>
        <p class="section-subtitle">{subtitle}</p>
        <div class="code-viewer">
          <div class="code-tabs">{"".join(tab_headers)}</div>
          <div class="code-content">{"".join(tab_panes)}</div>
        </div>
      </div>
    </section>""")

            elif stype == "custom":
                raw_html = sdata.get("raw_html", "")
                main_content.append(f"""    <section id="{sec.id}" class="custom-section">
      <div class="container">
{raw_html}
      </div>
    </section>""")

        body_sections.append(f"  <main>\n" + "\n\n".join(main_content) + "\n  </main>")

        # Footer
        if self.footer:
            cols = []
            for c in self.footer.columns:
                clinks = "".join([f'            <li><a href="{html.escape(l.get("href", "#"))}">{html.escape(l.get("label", ""))}</a></li>\n' for l in c.get("links", [])])
                cols.append(f"""        <div class="footer-col">
          <h4>{html.escape(c.get('title', ''))}</h4>
          <ul>
{clinks}          </ul>
        </div>""")
            cols_html = "\n".join(cols)
            body_sections.append(f"""  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-brand">
          <h3>{html.escape(self.footer.brand_name)}</h3>
          <p>{html.escape(self.footer.tagline)}</p>
        </div>
{cols_html}
      </div>
      <div class="footer-bottom">
        <p>{html.escape(self.footer.copyright)}</p>
      </div>
    </div>
  </footer>""")

        css_vars = theme_cfg.to_css_string()
        return f"""<!DOCTYPE html>
<html lang="{html.escape(self.lang)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(self.title)}</title>
  <meta name="description" content="{html.escape(self.description)}">
  <meta name="author" content="{html.escape(self.author)}">
  <style>
{css_vars}
    body {{
      margin: 0;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-sans);
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 1.5rem;
    }}
{self.custom_css}
  </style>
</head>
<body>
{"\n".join(body_sections)}
</body>
</html>"""


# ==============================================================================
# HTML Semantic Parser
# ==============================================================================

class HTMLSemanticParser(HTMLParser):
    """Parses raw HTML5 semantic markup into a structured ProjectAST."""

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self.in_title = False
        self.in_nav = False
        self.in_header = False
        self.in_footer = False
        self.in_section = False
        self.current_section_type = ""
        self.current_section_id = ""
        self.current_text = []
        self.current_tag = ""
        self.current_attrs: Dict[str, str] = {}
        
        # Parsed elements
        self.nav_links: List[Dict[str, str]] = []
        self.nav_brand = ""
        self.nav_cta: Dict[str, str] = {}
        self.sections: List[ComponentNode] = []
        self.footer_brand = ""
        self.footer_links: List[Dict[str, str]] = []
        
        # Working item buffer for sub-elements
        self.active_cards: List[Dict[str, Any]] = []
        self.active_card: Optional[Dict[str, Any]] = None
        self.in_card = False
        self.card_text = []
        self.section_headings: List[Tuple[str, str]] = []  # (tag, text)
        self.section_paragraphs: List[str] = []
        self.section_buttons: List[Dict[str, str]] = []
        self.section_code_blocks: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        self.current_tag = tag
        self.current_attrs = attr_dict
        cls_str = attr_dict.get("class", "").lower()
        id_str = attr_dict.get("id", "").lower()

        if tag == "title":
            self.in_title = True
        elif tag == "meta" and attr_dict.get("name", "").lower() == "description":
            self.description = attr_dict.get("content", "")
        elif tag in ("header", "nav") or "header" in cls_str or "nav" in cls_str:
            self.in_nav = True
        elif tag == "footer" or "footer" in cls_str:
            self.in_footer = True
        elif tag == "section" or "section" in cls_str or "hero" in cls_str or "features" in cls_str or "pricing" in cls_str:
            self.in_section = True
            self.current_section_id = id_str or f"sec_{len(self.sections)}"
            # Classify section type based on class or ID
            if "hero" in cls_str or "hero" in id_str:
                self.current_section_type = "hero"
            elif "feature" in cls_str or "feature" in id_str:
                self.current_section_type = "features"
            elif "price" in cls_str or "pricing" in id_str:
                self.current_section_type = "pricing"
            elif "stat" in cls_str or "stat" in id_str:
                self.current_section_type = "stats"
            elif "testim" in cls_str or "testim" in id_str or "review" in cls_str:
                self.current_section_type = "testimonials"
            elif "faq" in cls_str or "faq" in id_str or "question" in cls_str:
                self.current_section_type = "faq"
            elif "cta" in cls_str or "cta" in id_str or "callout" in cls_str:
                self.current_section_type = "cta"
            elif "code" in cls_str or "code" in id_str:
                self.current_section_type = "code_viewer"
            else:
                self.current_section_type = "generic"
            self.section_headings = []
            self.section_paragraphs = []
            self.section_buttons = []
            self.active_cards = []
            self.section_code_blocks = []

        if self.in_section:
            if "card" in cls_str or "tier" in cls_str or "item" in cls_str or "col" in cls_str or tag == "details":
                self.in_card = True
                self.active_card = {"tag": tag, "classes": cls_str, "title": "", "description": "", "text": "", "badge": "", "price": "", "features": []}
                self.card_text = []

        if tag == "a" and self.in_nav:
            label = attr_dict.get("title", "")
            href = attr_dict.get("href", "#")
            is_cta = "btn" in cls_str or "cta" in cls_str
            self.nav_links.append({"label": label, "href": href, "is_cta": is_cta})

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag in ("header", "nav") and self.in_nav:
            self.in_nav = False
        elif tag == "footer" and self.in_footer:
            self.in_footer = False
        elif (tag == "section" or self.in_section) and tag in ("section", "div", "main"):
            if tag == "section" or (tag == "div" and self.in_section and not self.in_card):
                self._commit_section()
                self.in_section = False

        if self.in_card and (tag in ("div", "details", "article", "li")):
            if self.active_card is not None:
                self.active_card["text"] = " ".join(self.card_text).strip()
                self.active_cards.append(self.active_card)
                self.active_card = None
            self.in_card = False

    def handle_data(self, data: str) -> None:
        txt = data.strip()
        if not txt:
            return

        if self.in_title:
            self.title += txt
        elif self.in_nav:
            if self.nav_links and not self.nav_links[-1]["label"]:
                self.nav_links[-1]["label"] = txt
            elif not self.nav_brand:
                self.nav_brand = txt
        elif self.in_card and self.active_card is not None:
            self.card_text.append(txt)
            if self.current_tag in ("h2", "h3", "h4", "summary") and not self.active_card.get("title"):
                self.active_card["title"] = txt
            elif self.current_tag in ("p", "span") and not self.active_card.get("description") and self.active_card.get("title"):
                self.active_card["description"] = txt
            elif "$" in txt or "€" in txt or "£" in txt or "/mo" in txt:
                self.active_card["price"] = txt
            elif self.current_tag == "li":
                self.active_card["features"].append(txt)
        elif self.in_section:
            if self.current_tag in ("h1", "h2", "h3", "h4"):
                self.section_headings.append((self.current_tag, txt))
            elif self.current_tag == "p":
                self.section_paragraphs.append(txt)
            elif self.current_tag in ("button", "a"):
                self.section_buttons.append({"label": txt, "href": self.current_attrs.get("href", "#")})
            elif self.current_tag in ("code", "pre"):
                self.section_code_blocks.append(txt)

    def _commit_section(self) -> None:
        """Heuristically normalize collected section elements into typed AST node."""
        stype = self.current_section_type
        h1 = self.section_headings[0][1] if self.section_headings else "Section"
        p1 = self.section_paragraphs[0] if self.section_paragraphs else ""

        # Auto-detect if generic
        if stype == "generic":
            if any("$" in c.get("price", "") or "$" in c.get("text", "") for c in self.active_cards):
                stype = "pricing"
            elif len(self.active_cards) >= 3:
                stype = "features"
            elif self.section_code_blocks:
                stype = "code_viewer"
            elif self.section_buttons and len(self.section_headings) <= 1:
                stype = "hero" if len(self.sections) == 0 else "cta"

        if stype == "hero":
            data = asdict(HeroComponent(
                title=h1,
                subtitle=p1 or "Engineered for excellence.",
                primary_cta=self.section_buttons[0] if self.section_buttons else {"label": "Get Started", "href": "#"},
                secondary_cta=self.section_buttons[1] if len(self.section_buttons) > 1 else {"label": "Learn More", "href": "#"}
            ))
        elif stype == "features":
            items = []
            for c in self.active_cards:
                items.append({
                    "icon": "zap",
                    "title": c.get("title") or "Feature Item",
                    "description": c.get("description") or c.get("text") or "Feature description.",
                    "badge": c.get("badge", "")
                })
            if not items:
                items = asdict(FeaturesComponent())["items"]
            data = asdict(FeaturesComponent(title=h1, subtitle=p1, items=items))
        elif stype == "pricing":
            tiers = []
            for c in self.active_cards:
                tiers.append({
                    "name": c.get("title") or "Tier",
                    "price": c.get("price") or "$29",
                    "period": "/month",
                    "description": c.get("description") or "",
                    "features": c.get("features") or ["Full Access", "Standard Support"],
                    "is_popular": "popular" in c.get("classes", ""),
                    "cta_label": "Choose Plan",
                    "cta_href": "#"
                })
            if not tiers:
                tiers = asdict(PricingComponent())["tiers"]
            data = asdict(PricingComponent(title=h1, subtitle=p1, tiers=tiers))
        elif stype == "stats":
            metrics = []
            for c in self.active_cards:
                metrics.append({
                    "value": c.get("title") or "100%",
                    "label": c.get("description") or "Metric",
                    "change": "",
                    "description": ""
                })
            if not metrics:
                metrics = asdict(StatsComponent())["metrics"]
            data = asdict(StatsComponent(title=h1, subtitle=p1, metrics=metrics))
        elif stype == "faq":
            items = []
            for c in self.active_cards:
                items.append({
                    "question": c.get("title") or "Question",
                    "answer": c.get("description") or c.get("text") or "Answer",
                    "category": "General"
                })
            if not items:
                items = asdict(FAQComponent())["items"]
            data = asdict(FAQComponent(title=h1, subtitle=p1, items=items))
        elif stype == "cta":
            data = asdict(CTAComponent(
                title=h1,
                subtitle=p1,
                primary_cta=self.section_buttons[0] if self.section_buttons else {"label": "Get Started", "href": "#"}
            ))
        elif stype == "code_viewer":
            tabs = []
            for i, code in enumerate(self.section_code_blocks):
                tabs.append({"filename": f"example_{i+1}.ts", "language": "typescript", "code": code})
            if not tabs:
                tabs = asdict(CodeViewerComponent())["tabs"]
            data = asdict(CodeViewerComponent(title=h1, subtitle=p1, tabs=tabs))
        else:
            data = {"raw_html": f"<h2>{html.escape(h1)}</h2><p>{html.escape(p1)}</p>"}

        node = ComponentNode(id=self.current_section_id, type=stype, data=data, order=len(self.sections))
        self.sections.append(node)


# ==============================================================================
# Markdown Semantic Parser
# ==============================================================================

class MarkdownSemanticParser:
    """Parses Markdown with optional YAML/JSON frontmatter into a ProjectAST."""

    @classmethod
    def parse(cls, content: str) -> ProjectAST:
        frontmatter: Dict[str, Any] = {}
        body = content

        # Check for YAML/JSON frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_raw = parts[1].strip()
                body = parts[2].strip()
                # Parse simple YAML key-values without external libs
                for line in fm_raw.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        frontmatter[k] = v

        title = frontmatter.get("title", "")
        description = frontmatter.get("description", "")
        theme = frontmatter.get("theme", DEFAULT_THEME)

        # Parse sections based on markdown headers
        sections: List[ComponentNode] = []
        current_header = ""
        current_level = 0
        current_lines: List[str] = []

        def flush_section():
            if not current_header and not current_lines:
                return
            h_clean = current_header.lower()
            text_block = "\n".join(current_lines).strip()
            
            # Infer section type
            if "feature" in h_clean:
                # Extract bullet points as feature items
                items = []
                for line in current_lines:
                    line = line.strip()
                    if line.startswith(("-", "*", "+")):
                        bullet = line.lstrip("-*+ ").strip()
                        if ":" in bullet:
                            btitle, bdesc = bullet.split(":", 1)
                            items.append({"icon": "zap", "title": btitle.strip(), "description": bdesc.strip()})
                        else:
                            items.append({"icon": "zap", "title": bullet, "description": ""})
                if not items:
                    items = asdict(FeaturesComponent())["items"]
                sections.append(ComponentNode(
                    id=f"features_{len(sections)}",
                    type="features",
                    data=asdict(FeaturesComponent(title=current_header, subtitle="", items=items)),
                    order=len(sections)
                ))
            elif "price" in h_clean or "pricing" in h_clean:
                sections.append(ComponentNode(
                    id=f"pricing_{len(sections)}",
                    type="pricing",
                    data=asdict(PricingComponent(title=current_header, subtitle="")),
                    order=len(sections)
                ))
            elif "faq" in h_clean or "question" in h_clean:
                sections.append(ComponentNode(
                    id=f"faq_{len(sections)}",
                    type="faq",
                    data=asdict(FAQComponent(title=current_header, subtitle="")),
                    order=len(sections)
                ))
            elif "code" in h_clean or "snippet" in h_clean or "```" in text_block:
                # Extract code blocks
                code_matches = re.findall(r"```(\w*)\n(.*?)```", text_block, re.DOTALL)
                tabs = []
                for lang, c in code_matches:
                    tabs.append({"filename": f"example.{lang or 'ts'}", "language": lang or "typescript", "code": c.strip()})
                if not tabs:
                    tabs = asdict(CodeViewerComponent())["tabs"]
                sections.append(ComponentNode(
                    id=f"code_{len(sections)}",
                    type="code_viewer",
                    data=asdict(CodeViewerComponent(title=current_header, tabs=tabs)),
                    order=len(sections)
                ))
            elif len(sections) == 0:
                # First section defaults to Hero
                p = text_block.split("\n\n")[0] if text_block else ""
                sections.append(ComponentNode(
                    id="hero",
                    type="hero",
                    data=asdict(HeroComponent(title=current_header or "Welcome", subtitle=p)),
                    order=0
                ))
            else:
                sections.append(ComponentNode(
                    id=f"cta_{len(sections)}",
                    type="cta",
                    data=asdict(CTAComponent(title=current_header, subtitle=text_block[:200])),
                    order=len(sections)
                ))

        for line in body.splitlines():
            if line.startswith("#"):
                flush_section()
                match = re.match(r"^(#+)\s*(.*)", line)
                if match:
                    current_level = len(match.group(1))
                    current_header = match.group(2).strip()
                    if not title and current_level == 1:
                        title = current_header
                    current_lines = []
            else:
                current_lines.append(line)

        flush_section()

        ast = ProjectAST(
            title=title or "Polyglot Markdown Site",
            description=description or "Converted from Markdown.",
            theme=theme,
            sections=sections if sections else ProjectAST.from_dict({}).sections
        )
        return ast


# ==============================================================================
# Universal Transpiler Entrypoint
# ==============================================================================

def transpile(source: Union[str, Dict[str, Any], Path], theme: Optional[str] = None) -> ProjectAST:
    """Universal transpilation helper.
    
    Accepts:
    - Dict schema
    - JSON string or file
    - HTML semantic markup string or file
    - Markdown content string or file
    
    Returns a validated, typed ProjectAST.
    """
    if isinstance(source, dict):
        ast = ProjectAST.from_dict(source)
        if theme:
            ast.theme = theme
        return ast

    content = ""
    if isinstance(source, Path) or (isinstance(source, str) and (source.endswith((".html", ".md", ".json", ".htm")) and "\n" not in source)):
        content = read_text_safely(source)
    elif isinstance(source, str):
        content = source

    content_trimmed = content.strip()

    # 1. Try parsing as JSON
    if (content_trimmed.startswith("{") and content_trimmed.endswith("}")) or (content_trimmed.startswith("[") and content_trimmed.endswith("]")):
        try:
            parsed = json.loads(content_trimmed)
            if isinstance(parsed, dict):
                ast = ProjectAST.from_dict(parsed)
                if theme:
                    ast.theme = theme
                return ast
        except json.JSONDecodeError:
            pass

    # 2. Try parsing as HTML
    if "<html" in content_trimmed.lower() or "<section" in content_trimmed.lower() or "<div" in content_trimmed.lower() or "<header" in content_trimmed.lower():
        parser = HTMLSemanticParser()
        try:
            parser.feed(content_trimmed)
            parser.close()
            ast = ProjectAST(
                title=parser.title or "Polyglot App",
                description=parser.description or "Transpiled from HTML",
                theme=theme or DEFAULT_THEME,
                navigation=NavigationComponent(brand_name=parser.nav_brand or "Polyglot", links=parser.nav_links) if parser.nav_links else NavigationComponent(),
                sections=parser.sections if parser.sections else ProjectAST.from_dict({}).sections
            )
            return ast
        except Exception:
            pass

    # 3. Fallback: Parse as Markdown
    ast = MarkdownSemanticParser.parse(content_trimmed)
    if theme:
        ast.theme = theme
    return ast
