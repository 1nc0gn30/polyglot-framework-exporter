"""Remix (React Router v7 / Vite) Framework Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Remix Vite application with
React 19, TypeScript, Tailwind CSS, Master Theme styling tokens, and interactive components.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class RemixGenerator:
    """Generates a complete Remix / React Router v7 project with Master Theme integration."""

    name = "remix"
    display_name = "Remix / React Router v7"
    description = "Fullstack web framework built on Web Fetch Standards and Vite."

    def generate(
        self,
        ast: ProjectAST,
        output_dir: Optional[Union[str, Path]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        theme = ast.get_theme()
        files: Dict[str, str] = {}

        # 1. package.json
        files["package.json"] = json.dumps({
            "name": ast.title.lower().replace(" ", "-"),
            "private": True,
            "sideEffects": False,
            "type": "module",
            "version": ast.version,
            "scripts": {
                "build": "remix vite:build",
                "dev": "remix vite:dev",
                "start": "remix-serve ./build/server/index.js",
                "typecheck": "tsc"
            },
            "dependencies": {
                "@remix-run/node": "^2.15.2",
                "@remix-run/react": "^2.15.2",
                "@remix-run/serve": "^2.15.2",
                "isbot": "^5.1.22",
                "lucide-react": "^0.469.0",
                "react": "^19.0.0",
                "react-dom": "^19.0.0"
            },
            "devDependencies": {
                "@remix-run/dev": "^2.15.2",
                "@types/react": "^19.0.7",
                "@types/react-dom": "^19.0.3",
                "autoprefixer": "^10.4.20",
                "postcss": "^8.4.49",
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.3",
                "vite": "^6.0.7",
                "vite-tsconfig-paths": "^5.1.4"
            }
        }, indent=2)

        # 2. vite.config.ts
        files["vite.config.ts"] = """import { vitePlugin as remix } from "@remix-run/dev";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [
    remix({
      future: {
        v3_fetcherPersist: true,
        v3_relativeSplatPath: true,
        v3_throwAbortReason: true,
      },
    }),
    tsconfigPaths(),
  ],
});
"""

        # 3. tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "include": [
                "**/*.ts",
                "**/*.tsx",
                "**/.server/**/*.ts",
                "**/.server/**/*.tsx",
                "**/.client/**/*.ts",
                "**/.client/**/*.tsx"
            ],
            "compilerOptions": {
                "lib": ["DOM", "DOM.Iterable", "ES2022"],
                "types": ["@remix-run/node", "vite/client"],
                "isolatedModules": True,
                "esModuleInterop": True,
                "jsx": "react-jsx",
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "resolveJsonModule": True,
                "target": "ES2022",
                "strict": True,
                "allowJs": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "baseUrl": ".",
                "paths": {
                    "~/*": ["./app/*"]
                },
                "noEmit": True
            }
        }, indent=2)

        # 4. tailwind.config.ts & postcss.config.js
        files["tailwind.config.ts"] = f"""import type {{ Config }} from 'tailwindcss';

export default {{
  content: ['./app/**/*.{{js,jsx,ts,tsx}}'],
  darkMode: 'class',
  theme: {{
    extend: {{
      colors: {{
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-surface': 'var(--bg-surface)',
        'bg-surface-hover': 'var(--bg-surface-hover)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'accent-primary': 'var(--accent-primary)',
        'accent-secondary': 'var(--accent-secondary)',
        'border-color': 'var(--border-color)',
        'border-subtle': 'var(--border-subtle)',
      }},
      fontFamily: {{
        sans: ['var(--font-sans)', 'sans-serif'],
        heading: ['var(--font-heading)', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      }},
      boxShadow: {{
        'card': '{theme.card_shadow}',
      }},
    }},
  }},
  plugins: [],
}} satisfies Config;
"""

        files["postcss.config.js"] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

        # 5. app/tailwind.css
        files["app/tailwind.css"] = f"""@tailwind base;
@tailwind components;
@tailwind utilities;

{theme.to_css_string()}

@layer base {{
  body {{
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: var(--font-sans);
    overflow-x: hidden;
  }}
}}

.glow-effect {{
  box-shadow: 0 0 50px -10px var(--accent-glow);
}}
"""

        # 6. app/root.tsx
        files["app/root.tsx"] = f"""import type {{ LinksFunction, MetaFunction }} from "@remix-run/node";
import {{
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
}} from "@remix-run/react";

import stylesheet from "~/tailwind.css?url";

export const links: LinksFunction = () => [
  {{ rel: "stylesheet", href: stylesheet }},
  {{ rel: "icon", type: "image/svg+xml", href: "/favicon.svg" }},
  {{ rel: "preconnect", href: "https://fonts.googleapis.com" }},
  {{ rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" }},
  {{
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@400;600;700&family=Outfit:wght@400;600;700&display=swap",
  }},
];

export const meta: MetaFunction = () => [
  {{ title: "{html.escape(ast.title)}" }},
  {{ name: "description", content: "{html.escape(ast.description)}" }},
  {{ name: "viewport", content: "width=device-width, initial-scale=1" }},
];

export function Layout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="{ast.lang}" className="{ 'dark' if theme.is_dark else '' }">
      <head>
        <meta charSet="utf-8" />
        <Meta />
        <Links />
      </head>
      <body className="min-h-screen flex flex-col bg-bg-primary text-text-primary antialiased selection:bg-accent-primary selection:text-bg-primary">
        {{children}}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}}

export default function App() {{
  return <Outlet />;
}}
"""

        # 7. Components
        nav = ast.navigation
        brand_name = nav.brand_name if nav else "Polyglot"
        links = nav.links if nav else []
        cta = nav.cta if nav else {"label": "Get Started", "href": "#"}

        files["app/components/Navbar.tsx"] = f"""import React from 'react';
import {{ Link }} from '@remix-run/react';

interface NavLink {{
  label: string;
  href: string;
}}

const links: NavLink[] = {json.dumps(links)};
const cta = {json.dumps(cta)};

export default function Navbar() {{
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-bg-primary/80 border-b border-border-color transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-xl font-heading font-bold text-text-primary tracking-tight hover:opacity-90">
          <span className="w-8 h-8 rounded-lg bg-accent-primary text-bg-primary flex items-center justify-center font-mono font-bold text-sm">P</span>
          <span>{brand_name}</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-text-secondary">
          {{links.map((link, idx) => (
            <Link key={{idx}} to={{link.href}} className="hover:text-accent-primary transition-colors">
              {{link.label}}
            </Link>
          ))}}
        </nav>

        <div className="flex items-center gap-3">
          {{cta && (
            <Link to={{cta.href}} className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent-primary text-bg-primary hover:opacity-90 transition-all shadow-sm">
              {{cta.label}}
            </Link>
          )}}
        </div>
      </div>
    </header>
  );
}}
"""

        hero_sec = ast.get_section("hero")
        h_data = hero_sec.data if hero_sec else {}
        files["app/components/Hero.tsx"] = f"""import React from 'react';
import {{ Link }} from '@remix-run/react';

export default function Hero() {{
  const title = "{h_data.get('title', 'Universal Full-Stack Application')}";
  const subtitle = "{h_data.get('subtitle', 'Build once, export anywhere.')}";
  const badge = "{h_data.get('badge', 'v2.0 Universal Engine')}";
  const pCta = {json.dumps(h_data.get('primary_cta', {'label': 'Get Started', 'href': '#'}))};
  const sCta = {json.dumps(h_data.get('secondary_cta', {'label': 'Learn More', 'href': '#'}))};
  const codeSnippet = "{h_data.get('code_snippet', 'npx create-polyglot-app')}";
  const highlights: string[] = {json.dumps(h_data.get('highlights', []))};

  return (
    <section className="relative pt-24 pb-20 overflow-hidden border-b border-border-color">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        {{badge && (
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-accent-primary/10 text-accent-primary border border-accent-primary/20 mb-8 animate-pulse">
            <span>✨</span> {{badge}}
          </div>
        )}}
        <h1 className="text-4xl sm:text-6xl font-heading font-extrabold tracking-tight text-text-primary max-w-4xl mx-auto leading-tight sm:leading-none">
          {{title}}
        </h1>
        <p className="mt-6 text-lg sm:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed">
          {{subtitle}}
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link to={{pCta.href}} className="px-6 py-3 rounded-xl font-semibold bg-accent-primary text-bg-primary hover:opacity-95 shadow-lg shadow-accent-primary/20 transition-all transform hover:-translate-y-0.5">
            {{pCta.label}}
          </Link>
          <Link to={{sCta.href}} className="px-6 py-3 rounded-xl font-semibold bg-bg-surface text-text-primary border border-border-color hover:bg-bg-surface-hover transition-all">
            {{sCta.label}}
          </Link>
        </div>

        {{codeSnippet && (
          <div className="mt-10 max-w-md mx-auto">
            <div className="p-3 rounded-xl bg-bg-secondary border border-border-color flex items-center justify-between text-xs font-mono text-text-secondary">
              <span className="truncate">$ {{codeSnippet}}</span>
              <span className="px-2 py-1 bg-bg-surface rounded border border-border-subtle text-xs">CLI Ready</span>
            </div>
          </div>
        )}}

        {{highlights.length > 0 && (
          <div className="mt-12 flex flex-wrap justify-center items-center gap-6 text-xs text-text-muted">
            {{highlights.map((hl, idx) => (
              <div key={{idx}} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-primary"></span>
                <span>{{hl}}</span>
              </div>
            ))}}
          </div>
        )}}
      </div>
    </section>
  );
}}
"""

        feat_sec = ast.get_section("features")
        f_data = feat_sec.data if feat_sec else {}
        files["app/components/Features.tsx"] = f"""import React from 'react';

interface FeatureItem {{
  title: string;
  description: string;
  badge?: string;
  icon?: string;
}}

const items: FeatureItem[] = {json.dumps(f_data.get('items', []))};

export default function Features() {{
  const title = "{f_data.get('title', 'Core Features')}";
  const subtitle = "{f_data.get('subtitle', 'Engineered for exceptional developer velocity.')}";

  return (
    <section id="features" className="py-24 bg-bg-secondary/40 border-b border-border-color">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
            {{title}}
          </h2>
          <p className="mt-4 text-base text-text-secondary">
            {{subtitle}}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {{items.map((item, idx) => (
            <div key={{idx}} className="p-6 rounded-2xl bg-bg-surface border border-border-color hover:border-accent-primary/40 transition-all duration-300 shadow-card hover:-translate-y-1 group">
              <div className="w-12 h-12 rounded-xl bg-accent-primary/10 text-accent-primary flex items-center justify-center font-mono font-bold text-lg mb-4 group-hover:scale-110 transition-transform">
                ⚡
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2 flex items-center justify-between">
                <span>{{item.title}}</span>
                {{item.badge && <span className="text-xs px-2 py-0.5 rounded bg-accent-primary/10 text-accent-primary font-mono">{{item.badge}}</span>}}
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                {{item.description}}
              </p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

        price_sec = ast.get_section("pricing")
        p_data = price_sec.data if price_sec else {}
        files["app/components/Pricing.tsx"] = f"""import React from 'react';
import {{ Link }} from '@remix-run/react';

interface PricingTier {{
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  is_popular?: boolean;
  cta_label?: string;
  cta_href?: string;
}}

const tiers: PricingTier[] = {json.dumps(p_data.get('tiers', []))};

export default function Pricing() {{
  const title = "{p_data.get('title', 'Predictable Pricing')}";
  const subtitle = "{p_data.get('subtitle', 'Choose the plan tailored to your team.')}";

  return (
    <section id="pricing" className="py-24 border-b border-border-color">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
            {{title}}
          </h2>
          <p className="mt-4 text-base text-text-secondary">
            {{subtitle}}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          {{tiers.map((tier, idx) => (
            <div key={{idx}} className={{`p-8 rounded-2xl bg-bg-surface border flex flex-col justify-between transition-all duration-300 relative ${{tier.is_popular ? 'border-accent-primary shadow-xl ring-1 ring-accent-primary' : 'border-border-color'}}`}}>
              {{tier.is_popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold bg-accent-primary text-bg-primary uppercase tracking-wide">
                  Most Popular
                </div>
              )}}
              <div>
                <h3 className="text-xl font-bold text-text-primary">{{tier.name}}</h3>
                <p className="text-sm text-text-secondary mt-2 min-h-[40px]">{{tier.description}}</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-extrabold text-text-primary tracking-tight">{{tier.price}}</span>
                  <span className="text-sm text-text-muted">{{tier.period}}</span>
                </div>

                <ul className="mt-8 space-y-3 text-sm text-text-secondary">
                  {{tier.features.map((feat, fIdx) => (
                    <li key={{fIdx}} className="flex items-center gap-3">
                      <span className="text-accent-primary font-bold">✓</span>
                      <span>{{feat}}</span>
                    </li>
                  ))}}
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-border-subtle">
                <Link to={{tier.cta_href || '#'}} className={{`block w-full text-center py-3 rounded-xl font-semibold transition-all ${{tier.is_popular ? 'bg-accent-primary text-bg-primary hover:opacity-90' : 'bg-bg-secondary text-text-primary hover:bg-bg-surface-hover border border-border-color'}}`}}>
                  {{tier.cta_label || 'Get Started'}}
                </Link>
              </div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

        stats_sec = ast.get_section("stats")
        st_data = stats_sec.data if stats_sec else {}
        files["app/components/Stats.tsx"] = f"""import React from 'react';

interface MetricItem {{
  value: string;
  label: string;
  description?: string;
}}

const metrics: MetricItem[] = {json.dumps(st_data.get('metrics', []))};

export default function Stats() {{
  return (
    <section className="py-16 bg-bg-secondary/30 border-b border-border-color">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {{metrics.map((m, idx) => (
            <div key={{idx}} className="p-4">
              <div className="text-4xl sm:text-5xl font-extrabold font-heading text-accent-primary tracking-tight">
                {{m.value}}
              </div>
              <div className="mt-2 text-sm font-semibold text-text-primary">{{m.label}}</div>
              {{m.description && <div className="text-xs text-text-muted mt-1">{{m.description}}</div>}}
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

        test_sec = ast.get_section("testimonials")
        t_data = test_sec.data if test_sec else {}
        files["app/components/Testimonials.tsx"] = f"""import React from 'react';

interface TestimonialItem {{
  quote: string;
  author: string;
  role: string;
  company: string;
}}

const items: TestimonialItem[] = {json.dumps(t_data.get('items', []))};

export default function Testimonials() {{
  const title = "{t_data.get('title', 'Loved by Developers')}";
  const subtitle = "{t_data.get('subtitle', 'See why engineering teams rely on our platform.')}";

  return (
    <section className="py-24 border-b border-border-color">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
            {{title}}
          </h2>
          <p className="mt-4 text-base text-text-secondary">
            {{subtitle}}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {{items.map((item, idx) => (
            <div key={{idx}} className="p-6 rounded-2xl bg-bg-surface border border-border-color flex flex-col justify-between shadow-card">
              <p className="text-sm text-text-secondary leading-relaxed italic">
                "{{item.quote}}"
              </p>
              <div className="mt-6 pt-4 border-t border-border-subtle flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent-primary/20 text-accent-primary font-bold flex items-center justify-center text-sm">
                  {{item.author.charAt(0)}}
                </div>
                <div>
                  <div className="text-sm font-semibold text-text-primary">{{item.author}}</div>
                  <div className="text-xs text-text-muted">{{item.role}}, {{item.company}}</div>
                </div>
              </div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

        faq_sec = ast.get_section("faq")
        faq_data = faq_sec.data if faq_sec else {}
        files["app/components/FAQ.tsx"] = f"""import React, {{ useState }} from 'react';

interface FAQItem {{
  question: string;
  answer: string;
}}

const items: FAQItem[] = {json.dumps(faq_data.get('items', []))};

export default function FAQ() {{
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const title = "{faq_data.get('title', 'Frequently Asked Questions')}";
  const subtitle = "{faq_data.get('subtitle', 'Got questions? We have answers.')}";

  const toggle = (idx: number) => {{
    setOpenIdx(openIdx === idx ? null : idx);
  }};

  return (
    <section id="faq" className="py-24 bg-bg-secondary/40 border-b border-border-color">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
            {{title}}
          </h2>
          <p className="mt-4 text-base text-text-secondary">
            {{subtitle}}
          </p>
        </div>

        <div className="space-y-4">
          {{items.map((item, idx) => (
            <div key={{idx}} className="p-6 rounded-xl bg-bg-surface border border-border-color transition-colors">
              <button
                type="button"
                onClick={{() => toggle(idx)}}
                className="w-full flex justify-between items-center font-semibold text-text-primary cursor-pointer text-left"
              >
                <span>{{item.question}}</span>
                <span className={{`text-accent-primary transition-transform duration-300 ${{openIdx === idx ? 'rotate-180' : ''}}`}}>
                  ↓
                </span>
              </button>
              {{openIdx === idx && (
                <div className="mt-4 text-sm text-text-secondary leading-relaxed border-t border-border-subtle pt-4">
                  {{item.answer}}
                </div>
              )}}
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""

        cta_sec = ast.get_section("cta")
        cta_data = cta_sec.data if cta_sec else {}
        files["app/components/CTA.tsx"] = f"""import React from 'react';
import {{ Link }} from '@remix-run/react';

export default function CTA() {{
  const title = "{cta_data.get('title', 'Ready to Get Started?')}";
  const subtitle = "{cta_data.get('subtitle', 'Join thousands of builders today.')}";
  const pCta = {json.dumps(cta_data.get('primary_cta', {'label': 'Start Building', 'href': '#'}))};

  return (
    <section className="py-20 relative overflow-hidden bg-accent-primary text-bg-primary">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        <h2 className="text-3xl sm:text-5xl font-heading font-extrabold tracking-tight">
          {{title}}
        </h2>
        <p className="mt-4 text-lg max-w-2xl mx-auto opacity-90">
          {{subtitle}}
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link to={{pCta.href}} className="px-8 py-3.5 rounded-xl font-bold bg-bg-primary text-text-primary hover:opacity-90 shadow-xl transition-all">
            {{pCta.label}}
          </Link>
        </div>
      </div>
    </section>
  );
}}
"""

        code_sec = ast.get_section("code_viewer")
        c_data = code_sec.data if code_sec else {}
        files["app/components/CodeViewer.tsx"] = f"""import React, {{ useState }} from 'react';

interface CodeTab {{
  filename: string;
  language: string;
  code: string;
}}

const tabs: CodeTab[] = {json.dumps(c_data.get('tabs', []))};

export default function CodeViewer() {{
  const [activeIdx, setActiveIdx] = useState(0);
  const [copied, setCopied] = useState(false);
  const title = "{c_data.get('title', 'Inspect Code Output')}";
  const subtitle = "{c_data.get('subtitle', 'Clean, idiomatic output in every framework.')}";

  const activeTab = tabs[activeIdx] || {{ code: '// Generated Code' }};

  const copyCode = () => {{
    if (activeTab.code) {{
      navigator.clipboard.writeText(activeTab.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }}
  }};

  return (
    <section className="py-24 border-b border-border-color">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-heading font-bold text-text-primary tracking-tight">
            {{title}}
          </h2>
          <p className="mt-3 text-base text-text-secondary">
            {{subtitle}}
          </p>
        </div>

        <div className="rounded-2xl bg-bg-secondary border border-border-color overflow-hidden shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 bg-bg-surface border-b border-border-color">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/80"></span>
              <span className="w-3 h-3 rounded-full bg-yellow-500/80"></span>
              <span className="w-3 h-3 rounded-full bg-green-500/80"></span>
            </div>
            <div className="flex gap-2">
              {{tabs.map((tab, idx) => (
                <button
                  key={{idx}}
                  onClick={{() => setActiveIdx(idx)}}
                  className={{`px-3 py-1 rounded text-xs font-mono transition-colors ${{activeIdx === idx ? 'bg-accent-primary text-bg-primary font-bold' : 'text-text-muted hover:text-text-primary'}}`}}
                >
                  {{tab.filename}}
                </button>
              ))}}
            </div>
            <button
              onClick={{copyCode}}
              className="px-2 py-1 bg-bg-surface hover:bg-bg-surface-hover text-xs font-mono rounded border border-border-subtle text-text-secondary hover:text-accent-primary"
            >
              {{copied ? 'Copied!' : 'Copy'}}
            </button>
          </div>
          <div className="p-6 font-mono text-xs text-text-secondary overflow-x-auto leading-relaxed">
            <pre><code>{{activeTab.code}}</code></pre>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""

        footer = ast.footer
        f_brand = footer.brand_name if footer else "Polyglot"
        f_tagline = footer.tagline if footer else "Universal AST Exporter."
        f_cols = footer.columns if footer else []
        f_copy = footer.copyright if footer else "© 2026 Polyglot."
        files["app/components/Footer.tsx"] = f"""import React from 'react';
import {{ Link }} from '@remix-run/react';

interface FooterColumn {{
  title: string;
  links: {{ label: string; href: string }}[];
}}

const columns: FooterColumn[] = {json.dumps(f_cols)};

export default function Footer() {{
  return (
    <footer className="bg-bg-secondary border-t border-border-color py-16 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          <div className="col-span-2">
            <div className="font-heading font-bold text-lg text-text-primary">{f_brand}</div>
            <p className="mt-2 text-text-muted max-w-sm text-xs leading-relaxed">{f_tagline}</p>
          </div>
          {{columns.map((col, idx) => (
            <div key={{idx}}>
              <h4 className="font-semibold text-text-primary mb-3 text-xs uppercase tracking-wider">{{col.title}}</h4>
              <ul className="space-y-2 text-xs text-text-secondary">
                {{col.links.map((link, lIdx) => (
                  <li key={{lIdx}}>
                    <Link to={{link.href}} className="hover:text-accent-primary transition-colors">
                      {{link.label}}
                    </Link>
                  </li>
                ))}}
              </ul>
            </div>
          ))}}
        </div>
        <div className="mt-12 pt-8 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between text-xs text-text-muted gap-4">
          <div>{f_copy}</div>
          <div className="flex gap-4">
            <span>Powered by Remix & React Router v7</span>
          </div>
        </div>
      </div>
    </footer>
  );
}}
"""

        # 8. app/routes/_index.tsx
        files["app/routes/_index.tsx"] = """import Navbar from "~/components/Navbar";
import Hero from "~/components/Hero";
import Features from "~/components/Features";
import CodeViewer from "~/components/CodeViewer";
import Stats from "~/components/Stats";
import Pricing from "~/components/Pricing";
import Testimonials from "~/components/Testimonials";
import FAQ from "~/components/FAQ";
import CTA from "~/components/CTA";
import Footer from "~/components/Footer";

export default function Index() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Features />
        <CodeViewer />
        <Stats />
        <Pricing />
        <Testimonials />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </>
  );
}
"""

        # 9. public/favicon.svg
        files["public/favicon.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#4f46e5"/>
  <path d="M30 70 L50 30 L70 70 Z" fill="#ffffff"/>
</svg>"""

        # 10. Deployment Manifests & Readme
        files["netlify.toml"] = """[build]
  command = "npm run build"
  publish = "build/client"
"""
        files["vercel.json"] = json.dumps({"framework": "remix"}, indent=2)

        files["README.md"] = f"""# {ast.title} (Remix / React Router v7)

Exported with **Polyglot Framework Exporter** using the **{theme.display_name}** theme.

## 🚀 Quickstart

```bash
# Install dependencies
npm install

# Start local dev server
npm run dev

# Build production bundle
npm run build
```
"""

        # Save to disk if output_dir provided
        if output_dir:
            out_path = Path(output_dir)
            ensure_directory(out_path)
            for rel_path, content in files.items():
                dest = safe_join(out_path, rel_path)
                atomic_write_text(dest, content)

        return files
