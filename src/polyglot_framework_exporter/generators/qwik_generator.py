"""Qwik City Framework Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Qwik City 1.x projects
with TypeScript, resumability ($ syntax), signals, Vite bundler,
Tailwind CSS, and Master Theme tokens.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class QwikGenerator:
    """Generates a complete Qwik City project with Master Theme integration."""

    name = "qwik"
    display_name = "Qwik City (Resumable SSR/SPA)"
    description = "Ultra-fast resumable web application powered by Qwik City and Vite."

    def generate(
        self,
        ast: ProjectAST,
        output_dir: Optional[Union[str, Path]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        theme = ast.get_theme()
        files: Dict[str, str] = {}
        pkg_name = ast.title.lower().replace(" ", "-").replace("_", "-")

        # 1. package.json
        files["package.json"] = json.dumps({
            "name": pkg_name,
            "description": ast.description,
            "version": ast.version,
            "engines": {
                "node": "^18.17.0 || ^20.3.0 || >=21.0.0"
            },
            "private": True,
            "type": "module",
            "scripts": {
                "build": "qwik build",
                "build.client": "vite build",
                "build.preview": "vite build --ssr src/entry.preview.tsx",
                "build.types": "tsc --incremental --noEmit",
                "dev": "vite --port 5173",
                "dev.debug": "node --inspect-brk ./node_modules/vite/bin/vite.js --port 5173",
                "fmt": "prettier --write --ignore-unknown \"./src/**/*.{ts,tsx,css}\"",
                "preview": "qwik build preview && vite preview --port 4173",
                "start": "vite --open --port 5173",
                "qwik": "qwik"
            },
            "devDependencies": {
                "@builder.io/qwik": "^1.12.0",
                "@builder.io/qwik-city": "^1.12.0",
                "@types/node": "^22.10.7",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.3",
                "vite": "^6.0.7",
                "vite-tsconfig-paths": "^5.1.4"
            }
        }, indent=2)

        # 2. tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "allowJs": False,
                "target": "ES2022",
                "module": "ESNext",
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "jsx": "react-jsx",
                "jsxImportSource": "@builder.io/qwik",
                "strict": True,
                "moduleResolution": "bundler",
                "noEmit": True,
                "skipLibCheck": True,
                "isolatedModules": True,
                "esModuleInterop": True,
                "resolveJsonModule": True,
                "paths": {
                    "~/*": ["./src/*"]
                }
            },
            "include": ["src"]
        }, indent=2)

        # 3. vite.config.ts
        files["vite.config.ts"] = """import { defineConfig } from "vite";
import { qwikVite } from "@builder.io/qwik/optimizer";
import { qwikCity } from "@builder.io/qwik-city/vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig(() => {
  return {
    plugins: [qwikCity(), qwikVite(), tsconfigPaths()],
    preview: {
      headers: {
        "Cache-Control": "public, max-age=600",
      },
    },
  };
});
"""

        # 4. tailwind.config.js & postcss.config.js
        files["tailwind.config.js"] = """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        theme: {
          bg: 'var(--bg-primary)',
          surface: 'var(--bg-surface)',
          text: 'var(--text-primary)',
          muted: 'var(--text-muted)',
          accent: 'var(--accent-primary)',
          border: 'var(--border-color)',
        }
      }
    },
  },
  plugins: [],
};
"""

        files["postcss.config.js"] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

        # 5. src/global.css
        css_vars = theme.to_css_string()
        files["src/global.css"] = f"""@tailwind base;
@tailwind components;
@tailwind utilities;

{css_vars}

body {{
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans), system-ui, sans-serif;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}}
"""

        # 6. src/root.tsx
        files["src/root.tsx"] = f"""import {{ component$ }} from "@builder.io/qwik";
import {{
  QwikCityProvider,
  RouterOutlet,
  ServiceWorkerRegister,
}} from "@builder.io/qwik-city";
import "./global.css";

export default component$(() => {{
  return (
    <QwikCityProvider>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{html.escape(ast.title)}</title>
        <meta name="description" content="{html.escape(ast.description)}" />
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      </head>
      <body lang="en" class="min-h-screen flex flex-col selection:bg-cyan-500 selection:text-black">
        <RouterOutlet />
        <ServiceWorkerRegister />
      </body>
    </QwikCityProvider>
  );
}});
"""

        # 7. src/entry.ssr.tsx
        files["src/entry.ssr.tsx"] = """/**
 * WHAT IS THIS FILE?
 *
 * SSR entry point, in all cases the application is rendered outside the browser, this
 * entry point will be the common one.
 */
import { isDev } from "@builder.io/qwik/build";
import {
  renderToStream,
  type RenderToStreamOptions,
} from "@builder.io/qwik/server";
import { manifest } from "@qwik-client-manifest";
import Root from "./root";

export default function (opts: RenderToStreamOptions) {
  return renderToStream(<Root />, {
    manifest,
    ...opts,
    containerAttributes: {
      lang: "en-us",
      ...opts.containerAttributes,
    },
    serverData: {
      ...opts.serverData,
    },
  });
}
"""

        # 8. src/routes/layout.tsx
        nav_sec = ast.get_section("navbar")
        nav_links = (nav_sec.data if nav_sec else {}).get("links", [
            {"label": "Features", "href": "#features"},
            {"label": "Pricing", "href": "#pricing"},
            {"label": "Docs", "href": "#docs"},
        ])
        nav_items_jsx = "\n".join(
            f'              <a href="{l.get("href", "#")}" class="text-sm font-medium hover:text-[var(--accent-primary)] transition-colors">{html.escape(l.get("label", ""))}</a>'
            for l in nav_links
        )

        files["src/routes/layout.tsx"] = f"""import {{ component$, Slot }} from "@builder.io/qwik";

export default component$(() => {{
  return (
    <div class="min-h-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {{/* Header */}}
      <header class="sticky top-0 z-50 backdrop-blur-md bg-[var(--bg-primary)]/80 border-b border-[var(--border-subtle)]">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <span class="text-2xl">🚀</span>
            <span class="font-bold text-lg tracking-tight">{html.escape(ast.title)}</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-[var(--badge-bg)] text-[var(--badge-text)] font-mono border border-[var(--border-subtle)]">Qwik City</span>
          </div>
          <nav class="hidden md:flex items-center space-x-6">
{nav_items_jsx}
          </nav>
          <div>
            <a href="#explore" class="px-4 py-2 rounded-lg text-sm font-semibold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-all shadow-sm">
              Get Started
            </a>
          </div>
        </div>
      </header>

      {{/* Main content slot */}}
      <main class="flex-grow">
        <Slot />
      </main>

      {{/* Footer */}}
      <footer class="border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)] py-8 text-center text-sm text-[var(--text-muted)]">
        <p>© {{new Date().getFullYear()}} {html.escape(ast.title)}. Built with Qwik City & Polyglot Exporter.</p>
      </footer>
    </div>
  );
}});
"""

        # 9. src/routes/index.tsx
        hero_sec = ast.get_section("hero")
        hero_title = (hero_sec.data if hero_sec else {}).get("title", ast.title)
        hero_sub = (hero_sec.data if hero_sec else {}).get("subtitle", ast.description)

        feat_sec = ast.get_section("features")
        feat_items = (feat_sec.data if feat_sec else {}).get("items", [
            {"title": "Resumable Architecture", "description": "Zero JS execution on initial hydration, instant page load.", "icon": "⚡"},
            {"title": "Fine-Grained Signals", "description": "Reactivity down to exact DOM nodes without virtual DOM diffing.", "icon": "🎯"},
            {"title": "Vite-Powered Optimizer", "description": "Automatic code-splitting and progressive prefetching.", "icon": "📦"},
        ])

        price_sec = ast.get_section("pricing")
        price_tiers = (price_sec.data if price_sec else {}).get("tiers", [
            {"name": "Starter", "price": "$0", "description": "For hobbyists and explorers", "features": ["Full Qwik City components", "Standard themes", "Community support"]},
            {"name": "Pro", "price": "$29/mo", "description": "For high-traffic production apps", "features": ["Edge hydration", "All 6 Master Themes", "Priority support"]},
        ])

        # Feature cards JSX
        feat_cards = []
        for f in feat_items:
            icon = f.get("icon", "✨")
            ftitle = f.get("title", "Feature")
            fdesc = f.get("description", "")
            feat_cards.append(f"""          <div class="p-6 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--accent-primary)] hover:bg-[var(--bg-surface-hover)] transition-all shadow-sm">
            <div class="text-3xl mb-3">{icon}</div>
            <h3 class="text-lg font-bold mb-2">{html.escape(ftitle)}</h3>
            <p class="text-sm text-[var(--text-muted)] leading-relaxed">{html.escape(fdesc)}</p>
          </div>""")
        feat_cards_jsx = "\n".join(feat_cards)

        # Pricing cards JSX
        price_cards = []
        for p in price_tiers:
            pname = p.get("name", "Tier")
            pprice = p.get("price", "$0")
            pdesc = p.get("description", "")
            pfeats = p.get("features", [])
            pfeat_li = "".join(f'<li class="flex items-center space-x-2"><span>✓</span><span>{html.escape(pf)}</span></li>' for pf in pfeats)
            price_cards.append(f"""          <div class="p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col justify-between">
            <div>
              <h3 class="text-xl font-bold">{html.escape(pname)}</h3>
              <p class="text-sm text-[var(--text-muted)] mt-1">{html.escape(pdesc)}</p>
              <div class="text-3xl font-extrabold my-4">{html.escape(pprice)}</div>
              <ul class="space-y-2 text-sm text-[var(--text-secondary)]">
                {pfeat_li}
              </ul>
            </div>
            <button class="mt-6 w-full py-2.5 rounded-lg text-sm font-semibold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-colors">
              Choose {html.escape(pname)}
            </button>
          </div>""")
        price_cards_jsx = "\n".join(price_cards)

        files["src/routes/index.tsx"] = f"""import {{ component$, useSignal }} from "@builder.io/qwik";
import type {{ DocumentHead }} from "@builder.io/qwik-city";

export default component$(() => {{
  const counter = useSignal(0);
  const activeTab = useSignal("overview");

  return (
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-20">
      {{/* Hero Section */}}
      <section class="text-center max-w-3xl mx-auto pt-8 pb-12">
        <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--badge-bg)] text-[var(--badge-text)] border border-[var(--border-subtle)] mb-6">
          <span>✨ Resumable High-Performance App</span>
        </div>
        <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 bg-gradient-to-r from-[var(--text-primary)] via-[var(--accent-primary)] to-[var(--accent-secondary)] bg-clip-text text-transparent">
          {html.escape(hero_title)}
        </h1>
        <p class="text-lg text-[var(--text-secondary)] leading-relaxed mb-8">
          {html.escape(hero_sub)}
        </p>
        <div class="flex items-center justify-center space-x-4">
          <button
            onClick$={{() => counter.value++}}
            class="px-6 py-3 rounded-xl font-bold bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:bg-[var(--btn-primary-hover)] transition-transform active:scale-95 shadow-md flex items-center space-x-2"
          >
            <span>⚡ Interactive Signal:</span>
            <span class="px-2 py-0.5 rounded bg-black/20 font-mono">{{counter.value}}</span>
          </button>
          <a
            href="#features"
            class="px-6 py-3 rounded-xl font-semibold border border-[var(--border-color)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] transition-colors"
          >
            Explore Features
          </a>
        </div>
      </section>

      {{/* Features Section */}}
      <section id="features" class="space-y-8">
        <div class="text-center max-w-2xl mx-auto">
          <h2 class="text-3xl font-bold tracking-tight">Built for Unmatched Speed</h2>
          <p class="text-[var(--text-muted)] mt-2">Zero hydration cost with Qwik's surgical execution model.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
{feat_cards_jsx}
        </div>
      </section>

      {{/* Pricing Section */}}
      <section id="pricing" class="space-y-8">
        <div class="text-center max-w-2xl mx-auto">
          <h2 class="text-3xl font-bold tracking-tight">Simple, Transparent Pricing</h2>
          <p class="text-[var(--text-muted)] mt-2">Scale from local prototypes to worldwide edge delivery.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
{price_cards_jsx}
        </div>
      </section>
    </div>
  );
}});

export const head: DocumentHead = {{
  title: {json.dumps(ast.title)},
  meta: [
    {{
      name: "description",
      content: {json.dumps(ast.description)},
    }},
  ],
}};
"""

        # 10. public/favicon.svg
        files["public/favicon.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="#18B6F6"/>
  <path d="M9 16L16 7L23 16L16 25Z" fill="#AC7FF4"/>
</svg>"""

        # 11. README.md
        files["README.md"] = f"""# {ast.title} (Qwik City)

> {ast.description}

This project was exported with [Polyglot Framework Exporter](https://github.com/polyglot-framework/polyglot-framework-exporter) using the **Qwik City** generator and the **{theme.display_name}** theme.

## 🚀 Getting Started

Ensure you have Node.js 18.17+ installed.

```bash
# Install dependencies
npm install
# or
pnpm install
# or
bun install

# Start local development server
npm run dev
```

Visit [http://localhost:5173/](http://localhost:5173/) to view your application.

## 🏗️ Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview
```

## 🎨 Theme Tokens
- **Theme**: {theme.display_name} ({theme.name})
- **Accent Primary**: `{theme.accent_primary}`
- **Background**: `{theme.bg_primary}`
"""

        # Write to disk if output_dir specified
        if output_dir:
            base = Path(output_dir)
            ensure_directory(base)
            for rel_path, content in files.items():
                dest = safe_join(base, rel_path)
                ensure_directory(dest.parent)
                atomic_write_text(dest, content)

        return files
