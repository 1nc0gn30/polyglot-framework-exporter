"""Nuxt 3 Framework Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Nuxt 3 (Vue 3) repository with
TypeScript, Tailwind CSS, Master Theme styling tokens, and reactive Vue components.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class NuxtGenerator:
    """Generates a complete Nuxt 3 project with Master Theme integration."""

    name = "nuxt"
    display_name = "Nuxt 3 (Vue 3)"
    description = "Next-generation fullstack Vue 3 & Nuxt 3 application with Tailwind CSS."

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
            "type": "module",
            "version": ast.version,
            "scripts": {
                "build": "nuxt build",
                "dev": "nuxt dev",
                "generate": "nuxt generate",
                "preview": "nuxt preview",
                "postinstall": "nuxt prepare"
            },
            "dependencies": {
                "@nuxtjs/tailwindcss": "^6.12.2",
                "nuxt": "^3.15.1",
                "vue": "^3.5.13",
                "vue-router": "^4.5.0"
            },
            "devDependencies": {
                "tailwindcss": "^3.4.17",
                "typescript": "^5.7.3"
            }
        }, indent=2)

        # 2. nuxt.config.ts
        files["nuxt.config.ts"] = f"""// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({{
  modules: ['@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css'],
  compatibilityDate: '2025-01-01',
  app: {{
    head: {{
      title: '{html.escape(ast.title)}',
      htmlAttrs: {{
        lang: '{ast.lang}',
        class: '{ "dark" if theme.is_dark else "" }'
      }},
      meta: [
        {{ charset: 'utf-8' }},
        {{ name: 'viewport', content: 'width=device-width, initial-scale=1' }},
        {{ name: 'description', content: '{html.escape(ast.description)}' }}
      ],
      link: [
        {{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }},
        {{ rel: 'preconnect', href: 'https://fonts.googleapis.com' }},
        {{ rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }},
        {{ rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@400;600;700&family=Outfit:wght@400;600;700&display=swap' }}
      ]
    }}
  }}
}});
"""

        # 3. tailwind.config.ts
        files["tailwind.config.ts"] = f"""import type {{ Config }} from 'tailwindcss';

export default <Partial<Config>>{{
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
}};
"""

        # 4. tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "extends": "./.nuxt/tsconfig.json"
        }, indent=2)

        # 5. assets/css/main.css
        files["assets/css/main.css"] = f"""@tailwind base;
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

        # 6. app.vue
        files["app.vue"] = """<template>
  <div class="min-h-screen flex flex-col bg-bg-primary text-text-primary antialiased selection:bg-accent-primary selection:text-bg-primary">
    <NuxtPage />
  </div>
</template>
"""

        # 7. Components
        nav = ast.navigation
        brand_name = nav.brand_name if nav else "Polyglot"
        links = nav.links if nav else []
        cta = nav.cta if nav else {"label": "Get Started", "href": "#"}

        files["components/Navbar.vue"] = f"""<script setup lang="ts">
const links = {json.dumps(links)};
const cta = {json.dumps(cta)};
const brandName = "{brand_name}";
</script>

<template>
  <header class="sticky top-0 z-50 backdrop-blur-md bg-bg-primary/80 border-b border-border-color transition-colors">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center gap-2 text-xl font-heading font-bold text-text-primary tracking-tight hover:opacity-90">
        <span class="w-8 h-8 rounded-lg bg-accent-primary text-bg-primary flex items-center justify-center font-mono font-bold text-sm">P</span>
        <span>{{ brandName }}</span>
      </NuxtLink>

      <nav class="hidden md:flex items-center gap-6 text-sm font-medium text-text-secondary">
        <NuxtLink
          v-for="(link, idx) in links"
          :key="idx"
          :to="link.href"
          class="hover:text-accent-primary transition-colors"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>

      <div class="flex items-center gap-3">
        <NuxtLink
          v-if="cta"
          :to="cta.href"
          class="px-4 py-2 rounded-lg text-sm font-semibold bg-accent-primary text-bg-primary hover:opacity-90 transition-all shadow-sm"
        >
          {{ cta.label }}
        </NuxtLink>
      </div>
    </div>
  </header>
</template>
"""

        hero_sec = ast.get_section("hero")
        h_data = hero_sec.data if hero_sec else {}
        files["components/Hero.vue"] = f"""<script setup lang="ts">
const title = "{h_data.get('title', 'Universal Full-Stack Application')}";
const subtitle = "{h_data.get('subtitle', 'Build once, export anywhere.')}";
const badge = "{h_data.get('badge', 'v2.0 Universal Engine')}";
const pCta = {json.dumps(h_data.get('primary_cta', {'label': 'Get Started', 'href': '#'}))};
const sCta = {json.dumps(h_data.get('secondary_cta', {'label': 'Learn More', 'href': '#'}))};
const codeSnippet = "{h_data.get('code_snippet', 'npx create-polyglot-app')}";
const highlights = {json.dumps(h_data.get('highlights', []))};
</script>

<template>
  <section class="relative pt-24 pb-20 overflow-hidden border-b border-border-color">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
      <div v-if="badge" class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-accent-primary/10 text-accent-primary border border-accent-primary/20 mb-8 animate-pulse">
        <span>✨</span> {{ badge }}
      </div>
      <h1 class="text-4xl sm:text-6xl font-heading font-extrabold tracking-tight text-text-primary max-w-4xl mx-auto leading-tight sm:leading-none">
        {{ title }}
      </h1>
      <p class="mt-6 text-lg sm:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed">
        {{ subtitle }}
      </p>

      <div class="mt-10 flex flex-wrap items-center justify-center gap-4">
        <NuxtLink :to="pCta.href" class="px-6 py-3 rounded-xl font-semibold bg-accent-primary text-bg-primary hover:opacity-95 shadow-lg shadow-accent-primary/20 transition-all transform hover:-translate-y-0.5">
          {{ pCta.label }}
        </NuxtLink>
        <NuxtLink :to="sCta.href" class="px-6 py-3 rounded-xl font-semibold bg-bg-surface text-text-primary border border-border-color hover:bg-bg-surface-hover transition-all">
          {{ sCta.label }}
        </NuxtLink>
      </div>

      <div v-if="codeSnippet" class="mt-10 max-w-md mx-auto">
        <div class="p-3 rounded-xl bg-bg-secondary border border-border-color flex items-center justify-between text-xs font-mono text-text-secondary">
          <span class="truncate">$ {{ codeSnippet }}</span>
          <span class="px-2 py-1 bg-bg-surface rounded border border-border-subtle text-xs">CLI Ready</span>
        </div>
      </div>

      <div v-if="highlights.length > 0" class="mt-12 flex flex-wrap justify-center items-center gap-6 text-xs text-text-muted">
        <div v-for="(hl, idx) in highlights" :key="idx" class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-accent-primary"></span>
          <span>{{ hl }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        feat_sec = ast.get_section("features")
        f_data = feat_sec.data if feat_sec else {}
        files["components/Features.vue"] = f"""<script setup lang="ts">
const title = "{f_data.get('title', 'Core Features')}";
const subtitle = "{f_data.get('subtitle', 'Engineered for exceptional developer velocity.')}";
const items = {json.dumps(f_data.get('items', []))};
</script>

<template>
  <section id="features" class="py-24 bg-bg-secondary/40 border-b border-border-color">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
          {{ title }}
        </h2>
        <p class="mt-4 text-base text-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div
          v-for="(item, idx) in items"
          :key="idx"
          class="p-6 rounded-2xl bg-bg-surface border border-border-color hover:border-accent-primary/40 transition-all duration-300 shadow-card hover:-translate-y-1 group"
        >
          <div class="w-12 h-12 rounded-xl bg-accent-primary/10 text-accent-primary flex items-center justify-center font-mono font-bold text-lg mb-4 group-hover:scale-110 transition-transform">
            ⚡
          </div>
          <h3 class="text-lg font-semibold text-text-primary mb-2 flex items-center justify-between">
            <span>{{ item.title }}</span>
            <span v-if="item.badge" class="text-xs px-2 py-0.5 rounded bg-accent-primary/10 text-accent-primary font-mono">{{ item.badge }}</span>
          </h3>
          <p class="text-sm text-text-secondary leading-relaxed">
            {{ item.description }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        price_sec = ast.get_section("pricing")
        p_data = price_sec.data if price_sec else {}
        files["components/Pricing.vue"] = f"""<script setup lang="ts">
const title = "{p_data.get('title', 'Predictable Pricing')}";
const subtitle = "{p_data.get('subtitle', 'Choose the plan tailored to your team.')}";
const tiers = {json.dumps(p_data.get('tiers', []))};
</script>

<template>
  <section id="pricing" class="py-24 border-b border-border-color">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
          {{ title }}
        </h2>
        <p class="mt-4 text-base text-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
        <div
          v-for="(tier, idx) in tiers"
          :key="idx"
          :class="[
            'p-8 rounded-2xl bg-bg-surface border flex flex-col justify-between transition-all duration-300 relative',
            tier.is_popular ? 'border-accent-primary shadow-xl ring-1 ring-accent-primary' : 'border-border-color'
          ]"
        >
          <div v-if="tier.is_popular" class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold bg-accent-primary text-bg-primary uppercase tracking-wide">
            Most Popular
          </div>
          <div>
            <h3 class="text-xl font-bold text-text-primary">{{ tier.name }}</h3>
            <p class="text-sm text-text-secondary mt-2 min-h-[40px]">{{ tier.description }}</p>
            <div class="mt-6 flex items-baseline gap-1">
              <span class="text-4xl font-extrabold text-text-primary tracking-tight">{{ tier.price }}</span>
              <span class="text-sm text-text-muted">{{ tier.period }}</span>
            </div>

            <ul class="mt-8 space-y-3 text-sm text-text-secondary">
              <li v-for="(feat, fIdx) in tier.features" :key="fIdx" class="flex items-center gap-3">
                <span class="text-accent-primary font-bold">✓</span>
                <span>{{ feat }}</span>
              </li>
            </ul>
          </div>

          <div class="mt-8 pt-6 border-t border-border-subtle">
            <NuxtLink
              :to="tier.cta_href || '#'"
              :class="[
                'block w-full text-center py-3 rounded-xl font-semibold transition-all',
                tier.is_popular ? 'bg-accent-primary text-bg-primary hover:opacity-90' : 'bg-bg-secondary text-text-primary hover:bg-bg-surface-hover border border-border-color'
              ]"
            >
              {{ tier.cta_label || 'Get Started' }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        stats_sec = ast.get_section("stats")
        st_data = stats_sec.data if stats_sec else {}
        files["components/Stats.vue"] = f"""<script setup lang="ts">
const metrics = {json.dumps(st_data.get('metrics', []))};
</script>

<template>
  <section class="py-16 bg-bg-secondary/30 border-b border-border-color">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
        <div v-for="(m, idx) in metrics" :key="idx" class="p-4">
          <div class="text-4xl sm:text-5xl font-extrabold font-heading text-accent-primary tracking-tight">
            {{ m.value }}
          </div>
          <div class="mt-2 text-sm font-semibold text-text-primary">{{ m.label }}</div>
          <div v-if="m.description" class="text-xs text-text-muted mt-1">{{ m.description }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        test_sec = ast.get_section("testimonials")
        t_data = test_sec.data if test_sec else {}
        files["components/Testimonials.vue"] = f"""<script setup lang="ts">
const title = "{t_data.get('title', 'Loved by Developers')}";
const subtitle = "{t_data.get('subtitle', 'See why engineering teams rely on our platform.')}";
const items = {json.dumps(t_data.get('items', []))};
</script>

<template>
  <section class="py-24 border-b border-border-color">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-16">
        <h2 class="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
          {{ title }}
        </h2>
        <p class="mt-4 text-base text-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div
          v-for="(item, idx) in items"
          :key="idx"
          class="p-6 rounded-2xl bg-bg-surface border border-border-color flex flex-col justify-between shadow-card"
        >
          <p class="text-sm text-text-secondary leading-relaxed italic">
            "{{ item.quote }}"
          </p>
          <div class="mt-6 pt-4 border-t border-border-subtle flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-accent-primary/20 text-accent-primary font-bold flex items-center justify-center text-sm">
              {{ item.author.charAt(0) }}
            </div>
            <div>
              <div class="text-sm font-semibold text-text-primary">{{ item.author }}</div>
              <div class="text-xs text-text-muted">{{ item.role }}, {{ item.company }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        faq_sec = ast.get_section("faq")
        faq_data = faq_sec.data if faq_sec else {}
        files["components/FAQ.vue"] = f"""<script setup lang="ts">
import {{ ref }} from 'vue';

const title = "{faq_data.get('title', 'Frequently Asked Questions')}";
const subtitle = "{faq_data.get('subtitle', 'Got questions? We have answers.')}";
const items = {json.dumps(faq_data.get('items', []))};
const openIdx = ref<number | null>(null);

function toggle(idx: number) {{
  openIdx.value = openIdx.value === idx ? null : idx;
}}
</script>

<template>
  <section id="faq" class="py-24 bg-bg-secondary/40 border-b border-border-color">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-heading font-bold text-text-primary tracking-tight sm:text-4xl">
          {{ title }}
        </h2>
        <p class="mt-4 text-base text-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <div class="space-y-4">
        <div
          v-for="(item, idx) in items"
          :key="idx"
          class="p-6 rounded-xl bg-bg-surface border border-border-color transition-colors"
        >
          <button
            type="button"
            @click="toggle(idx)"
            class="w-full flex justify-between items-center font-semibold text-text-primary cursor-pointer text-left"
          >
            <span>{{ item.question }}</span>
            <span :class="['text-accent-primary transition-transform duration-300', openIdx === idx ? 'rotate-180' : '']">
              ↓
            </span>
          </button>
          <div v-if="openIdx === idx" class="mt-4 text-sm text-text-secondary leading-relaxed border-t border-border-subtle pt-4">
            {{ item.answer }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        cta_sec = ast.get_section("cta")
        cta_data = cta_sec.data if cta_sec else {}
        files["components/CTA.vue"] = f"""<script setup lang="ts">
const title = "{cta_data.get('title', 'Ready to Get Started?')}";
const subtitle = "{cta_data.get('subtitle', 'Join thousands of builders today.')}";
const pCta = {json.dumps(cta_data.get('primary_cta', {'label': 'Start Building', 'href': '#'}))};
</script>

<template>
  <section class="py-20 relative overflow-hidden bg-accent-primary text-bg-primary">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
      <h2 class="text-3xl sm:text-5xl font-heading font-extrabold tracking-tight">
        {{ title }}
      </h2>
      <p class="mt-4 text-lg max-w-2xl mx-auto opacity-90">
        {{ subtitle }}
      </p>
      <div class="mt-8 flex justify-center gap-4">
        <NuxtLink :to="pCta.href" class="px-8 py-3.5 rounded-xl font-bold bg-bg-primary text-text-primary hover:opacity-90 shadow-xl transition-all">
          {{ pCta.label }}
        </NuxtLink>
      </div>
    </div>
  </section>
</template>
"""

        code_sec = ast.get_section("code_viewer")
        c_data = code_sec.data if code_sec else {}
        files["components/CodeViewer.vue"] = f"""<script setup lang="ts">
import {{ ref, computed }} from 'vue';

const title = "{c_data.get('title', 'Inspect Code Output')}";
const subtitle = "{c_data.get('subtitle', 'Clean, idiomatic output in every framework.')}";
const tabs = {json.dumps(c_data.get('tabs', []))};
const activeIdx = ref(0);
const copied = ref(false);

const activeTab = computed(() => tabs[activeIdx.value] || {{ code: '// Generated Code' }});

function copyCode() {{
  if (activeTab.value.code) {{
    navigator.clipboard.writeText(activeTab.value.code);
    copied.value = true;
    setTimeout(() => {{ copied.value = false; }}, 2000);
  }}
}}
</script>

<template>
  <section class="py-24 border-b border-border-color">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center mb-12">
        <h2 class="text-3xl font-heading font-bold text-text-primary tracking-tight">
          {{ title }}
        </h2>
        <p class="mt-3 text-base text-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <div class="rounded-2xl bg-bg-secondary border border-border-color overflow-hidden shadow-2xl">
        <div class="flex items-center justify-between px-4 py-3 bg-bg-surface border-b border-border-color">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-red-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-yellow-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-green-500/80"></span>
          </div>
          <div class="flex gap-2">
            <button
              v-for="(tab, idx) in tabs"
              :key="idx"
              @click="activeIdx = idx"
              :class="[
                'px-3 py-1 rounded text-xs font-mono transition-colors',
                activeIdx === idx ? 'bg-accent-primary text-bg-primary font-bold' : 'text-text-muted hover:text-text-primary'
              ]"
            >
              {{ tab.filename }}
            </button>
          </div>
          <button
            @click="copyCode"
            class="px-2 py-1 bg-bg-surface hover:bg-bg-surface-hover text-xs font-mono rounded border border-border-subtle text-text-secondary hover:text-accent-primary"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
        <div class="p-6 font-mono text-xs text-text-secondary overflow-x-auto leading-relaxed">
          <pre><code>{{ activeTab.code }}</code></pre>
        </div>
      </div>
    </div>
  </section>
</template>
"""

        footer = ast.footer
        f_brand = footer.brand_name if footer else "Polyglot"
        f_tagline = footer.tagline if footer else "Universal AST Exporter."
        f_cols = footer.columns if footer else []
        f_copy = footer.copyright if footer else "© 2026 Polyglot."
        files["components/Footer.vue"] = f"""<script setup lang="ts">
const columns = {json.dumps(f_cols)};
const brandName = "{f_brand}";
const tagline = "{f_tagline}";
const copyright = "{f_copy}";
</script>

<template>
  <footer class="bg-bg-secondary border-t border-border-color py-16 text-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-8">
        <div class="col-span-2">
          <div class="font-heading font-bold text-lg text-text-primary">{{ brandName }}</div>
          <p class="mt-2 text-text-muted max-w-sm text-xs leading-relaxed">{{ tagline }}</p>
        </div>
        <div v-for="(col, idx) in columns" :key="idx">
          <h4 class="font-semibold text-text-primary mb-3 text-xs uppercase tracking-wider">{{ col.title }}</h4>
          <ul class="space-y-2 text-xs text-text-secondary">
            <li v-for="(link, lIdx) in col.links" :key="lIdx">
              <NuxtLink :to="link.href" class="hover:text-accent-primary transition-colors">
                {{ link.label }}
              </NuxtLink>
            </li>
          </ul>
        </div>
      </div>
      <div class="mt-12 pt-8 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between text-xs text-text-muted gap-4">
        <div>{{ copyright }}</div>
        <div class="flex gap-4">
          <span>Powered by Nuxt 3 & Vue 3</span>
        </div>
      </div>
    </div>
  </footer>
</template>
"""

        # 8. pages/index.vue
        files["pages/index.vue"] = """<template>
  <div>
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
  </div>
</template>
"""

        # 9. public/favicon.svg
        files["public/favicon.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="#4f46e5"/>
  <path d="M30 70 L50 30 L70 70 Z" fill="#ffffff"/>
</svg>"""

        # 10. Deployment Manifests & Readme
        files["netlify.toml"] = """[build]
  command = "npm run build"
  publish = ".output/public"
"""
        files["vercel.json"] = json.dumps({"framework": "nuxtjs"}, indent=2)

        files["README.md"] = f"""# {ast.title} (Nuxt 3)

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
