"""SolidStart 1.0 (SolidJS) Framework Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready SolidStart 1.0 + SolidJS + Vinxi + TypeScript
+ Tailwind CSS project with fine-grained reactivity, Master Theme tokens, and zero Virtual DOM overhead.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class SolidStartGenerator:
    """Generates a complete SolidStart 1.0 (SolidJS) full-stack web application."""

    name = "solidstart"
    display_name = "SolidStart 1.0 (SolidJS)"
    description = "Fine-grained reactive, high-performance meta-framework powered by Solid.js and Vinxi/Vite with zero Virtual DOM."

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
            "version": ast.version,
            "type": "module",
            "scripts": {
                "dev": "vinxi dev",
                "build": "vinxi build",
                "start": "vinxi start",
                "test": "vitest"
            },
            "dependencies": {
                "@solidjs/meta": "^0.29.4",
                "@solidjs/router": "^0.15.2",
                "@solidjs/start": "^1.0.10",
                "solid-js": "^1.9.4",
                "vinxi": "^0.5.1"
            },
            "devDependencies": {
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.3",
                "vitest": "^3.0.4"
            }
        }, indent=2)

        # 2. app.config.ts (Vinxi / SolidStart config)
        files["app.config.ts"] = (
            'import { defineConfig } from "@solidjs/start/config";\n\n'
            "export default defineConfig({\n"
            "  server: {\n"
            '    preset: "node-server",\n'
            "  },\n"
            "});\n"
        )

        # 3. tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "target": "ESNext",
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "allowSyntheticDefaultImports": True,
                "esModuleInterop": True,
                "jsx": "preserve",
                "jsxImportSource": "solid-js",
                "strict": True,
                "isolatedModules": True,
                "noEmit": True,
                "types": ["vinxi/types/client"]
            },
            "include": ["src/**/*", "app.config.ts"]
        }, indent=2)

        # 4. tailwind.config.mjs
        files["tailwind.config.mjs"] = (
            "/** @type {import('tailwindcss').Config} */\n"
            "export default {\n"
            '  content: ["./src/**/*.{js,jsx,ts,tsx}"],\n'
            "  theme: {\n"
            "    extend: {\n"
            "      colors: {\n"
            f'        primary: "{theme.accent_primary}",\n'
            f'        secondary: "{theme.accent_secondary}",\n'
            f'        accent: "{theme.accent_primary}",\n'
            f'        surface: "{theme.bg_surface}",\n'
            f'        background: "{theme.bg_primary}",\n'
            "      },\n"
            "      fontFamily: {\n"
            f'        sans: ["{theme.font_sans}", "sans-serif"],\n'
            "      },\n"
            "    },\n"
            "  },\n"
            "  plugins: [],\n"
            "};\n"
        )

        # 5. postcss.config.cjs
        files["postcss.config.cjs"] = (
            "module.exports = {\n"
            "  plugins: {\n"
            "    tailwindcss: {},\n"
            "    autoprefixer: {},\n"
            "  },\n"
            "};\n"
        )

        # 6. src/app.css
        files["src/app.css"] = (
            "@tailwind base;\n"
            "@tailwind components;\n"
            "@tailwind utilities;\n\n"
            f"{theme.to_css_string()}\n\n"
            "body {\n"
            "  background-color: var(--bg-primary, #0f172a);\n"
            "  color: var(--text-primary, #f8fafc);\n"
            "  font-family: var(--font-sans, sans-serif);\n"
            "  margin: 0;\n"
            "  padding: 0;\n"
            "  min-height: 100vh;\n"
            "}\n"
        )

        # 7. src/entry-client.tsx
        files["src/entry-client.tsx"] = (
            'import { mount, StartClient } from "@solidjs/start/client";\n\n'
            'mount(() => <StartClient />, document.getElementById("app")!);\n'
        )

        # 8. src/entry-server.tsx
        files["src/entry-server.tsx"] = (
            'import { createHandler, StartServer } from "@solidjs/start/server";\n\n'
            "export default createHandler(() => (\n"
            "  <StartServer\n"
            "    document={({ assets, children, scripts }) => (\n"
            '      <html lang="en">\n'
            "        <head>\n"
            '          <meta charset="utf-8" />\n'
            '          <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            '          <link rel="icon" href="/favicon.ico" />\n'
            "          {assets}\n"
            "        </head>\n"
            '        <body id="app">\n'
            "          {children}\n"
            "          {scripts}\n"
            "        </body>\n"
            "      </html>\n"
            "    )}\n"
            "  />\n"
            "));\n"
        )

        # 9. src/app.tsx
        files["src/app.tsx"] = (
            'import { MetaProvider, Title } from "@solidjs/meta";\n'
            'import { Router } from "@solidjs/router";\n'
            'import { FileRoutes } from "@solidjs/start/router";\n'
            'import { Suspense } from "solid-js";\n'
            'import Header from "~/components/Header";\n'
            'import Footer from "~/components/Footer";\n'
            'import "./app.css";\n\n'
            "export default function App() {\n"
            "  return (\n"
            "    <MetaProvider>\n"
            f'      <Title>{html.escape(ast.title)}</Title>\n'
            "      <Router\n"
            "        root={(props) => (\n"
            '          <div class="min-h-screen flex flex-col">\n'
            f'            <Header title="{html.escape(ast.title)}" />\n'
            '            <main class="flex-1">\n'
            "              <Suspense>{props.children}</Suspense>\n"
            "            </main>\n"
            f'            <Footer title="{html.escape(ast.title)}" />\n'
            "          </div>\n"
            "        )}\n"
            "      >\n"
            "        <FileRoutes />\n"
            "      </Router>\n"
            "    </MetaProvider>\n"
            "  );\n"
            "}\n"
        )

        # 10. src/components/Header.tsx
        files["src/components/Header.tsx"] = (
            'import { A } from "@solidjs/router";\n\n'
            "interface HeaderProps {\n"
            "  title: string;\n"
            "}\n\n"
            "export default function Header(props: HeaderProps) {\n"
            "  return (\n"
            '    <header class="border-b border-white/10 bg-surface/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">\n'
            '      <A href="/" class="text-xl font-bold tracking-tight text-primary flex items-center gap-2">\n'
            '        <span>⚡</span>\n'
            "        <span>{props.title}</span>\n"
            "      </A>\n"
            '      <nav class="flex items-center gap-6 text-sm font-medium text-white/70">\n'
            '        <A href="/" class="hover:text-primary transition-colors">Home</A>\n'
            '        <A href="/features" class="hover:text-primary transition-colors">Features</A>\n'
            '        <A href="/pricing" class="hover:text-primary transition-colors">Pricing</A>\n'
            "      </nav>\n"
            "    </header>\n"
            "  );\n"
            "}\n"
        )

        # 11. src/components/Footer.tsx
        files["src/components/Footer.tsx"] = (
            "interface FooterProps {\n"
            "  title: string;\n"
            "}\n\n"
            "export default function Footer(props: FooterProps) {\n"
            "  return (\n"
            '    <footer class="border-t border-white/10 py-8 px-6 text-center text-sm text-white/50 bg-surface">\n'
            f'      <p>© {ast.version.split(".")[0] or "2025"} {html.escape(ast.title)}. Built with SolidStart 1.0 & Solid.js.</p>\n'
            "    </footer>\n"
            "  );\n"
            "}\n"
        )

        # 12. src/components/Hero.tsx
        hero_component = ast.get_section("hero")
        hero_data = hero_component.data if hero_component else {}
        hero_title = hero_data.get("title", ast.title)
        hero_sub = hero_data.get("subtitle", ast.description)

        files["src/components/Hero.tsx"] = (
            'import { createSignal } from "solid-js";\n\n'
            "export default function Hero() {\n"
            "  const [count, setCount] = createSignal(0);\n\n"
            "  return (\n"
            '    <section class="py-20 px-6 text-center max-w-4xl mx-auto">\n'
            f'      <h1 class="text-5xl font-extrabold tracking-tight text-primary sm:text-6xl mb-6">{html.escape(hero_title)}</h1>\n'
            f'      <p class="text-xl text-white/70 mb-10 max-w-2xl mx-auto">{html.escape(hero_sub)}</p>\n'
            '      <div class="flex items-center justify-center gap-4">\n'
            '        <button\n'
            '          onClick={() => setCount((c) => c + 1)}\n'
            '          class="px-6 py-3 rounded-lg bg-primary text-black font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"\n'
            "        >\n"
            '          Reactive Clicks: {count()}\n'
            "        </button>\n"
            '        <a href="#features" class="px-6 py-3 rounded-lg border border-white/20 font-medium hover:bg-white/5 transition-colors">\n'
            "          Explore Capabilities\n"
            "        </a>\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        )

        # 13. src/components/Features.tsx
        feat_component = ast.get_section("features")
        features_items = feat_component.data.get("items", []) if feat_component else [
            {"icon": "⚡", "title": "Zero Virtual DOM", "description": "Compiles directly to real DOM nodes for peak performance."},
            {"icon": "🎯", "title": "Fine-Grained Signals", "description": "Only updates the exact DOM elements that depend on state."},
            {"icon": "🚀", "title": "Vinxi & Vite Powered", "description": "Sub-millisecond HMR with universal full-stack server routing."},
        ]

        files["src/components/Features.tsx"] = (
            'import { For } from "solid-js";\n\n'
            f"const FEATURES = {json.dumps(features_items, indent=2)};\n\n"
            "export default function Features() {\n"
            "  return (\n"
            '    <section id="features" class="py-16 px-6 max-w-6xl mx-auto">\n'
            '      <div class="text-center mb-12">\n'
            '        <h2 class="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-3">Key Capabilities</h2>\n'
            '        <p class="text-white/60">Engineered for maximal throughput, minimal bundle size, and developer delight.</p>\n'
            "      </div>\n"
            '      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">\n'
            "        <For each={FEATURES}>\n"
            "          {(feat) => (\n"
            '            <div class="p-6 rounded-xl bg-surface border border-white/10 hover:border-primary/50 transition-colors shadow-sm">\n'
            '              <div class="text-3xl mb-4">{feat.icon || "✨"}</div>\n'
            '              <h3 class="text-xl font-semibold mb-2 text-white">{feat.title}</h3>\n'
            '              <p class="text-sm text-white/60 leading-relaxed">{feat.description}</p>\n'
            "            </div>\n"
            "          )}\n"
            "        </For>\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        )

        # 14. src/routes/index.tsx
        files["src/routes/index.tsx"] = (
            'import Hero from "~/components/Hero";\n'
            'import Features from "~/components/Features";\n\n'
            "export default function Home() {\n"
            "  return (\n"
            '    <div class="space-y-12 pb-24">\n'
            "      <Hero />\n"
            "      <Features />\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        )

        # 15. src/routes/[...404].tsx
        files["src/routes/[...404].tsx"] = (
            'import { A } from "@solidjs/router";\n\n'
            "export default function NotFound() {\n"
            "  return (\n"
            '    <div class="text-center py-32 px-6">\n'
            '      <h1 class="text-6xl font-black text-primary mb-4">404</h1>\n'
            '      <p class="text-xl text-white/70 mb-8">Page not found.</p>\n'
            '      <A href="/" class="px-6 py-3 rounded-lg bg-primary text-black font-semibold hover:opacity-90 transition-opacity">\n'
            "        Return Home\n"
            "      </A>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        )

        # 16. README.md
        files["README.md"] = (
            f"# {ast.title} (SolidStart 1.0)\n\n"
            f"{ast.description}\n\n"
            f"> Generated automatically by **polyglot-framework-exporter** with Master Theme tokens (`{theme.name}`).\n\n"
            "## Architecture\n\n"
            "- **Meta-Framework**: [SolidStart 1.0](https://start.solidjs.com)\n"
            "- **Reactive Engine**: [SolidJS 1.9](https://www.solidjs.com) (Fine-grained reactive signals, zero VDOM)\n"
            "- **Full-Stack Bundler**: [Vinxi](https://vinxi.dev) / Vite\n"
            "- **Styling**: Tailwind CSS + Master Theme tokens\n"
            "- **Language**: TypeScript 5.7\n\n"
            "## Getting Started\n\n"
            "```bash\n"
            "# Install dependencies\n"
            "npm install\n"
            "# or bun install / pnpm install\n\n"
            "# Start local dev server\n"
            "npm run dev\n\n"
            "# Build production server bundle\n"
            "npm run build\n\n"
            "# Run production server\n"
            "npm start\n"
            "```\n"
        )

        # Write to disk if output_dir provided
        if output_dir:
            out_path = Path(output_dir)
            ensure_directory(out_path)
            for rel_path, content in files.items():
                dest = safe_join(out_path, rel_path)
                ensure_directory(dest.parent)
                atomic_write_text(dest, content)

        return files
