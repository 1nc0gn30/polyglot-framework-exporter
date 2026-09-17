"""Electron Desktop Framework Generator for polyglot-framework-exporter.

Generates complete, runnable, production-ready Electron desktop application
with modern security practices (contextIsolation, preload contextBridge),
standalone Master Theme CSS styling, and zero external runtime dependencies.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..compat import atomic_write_text, ensure_directory, safe_join
from ..transpiler import ProjectAST, get_theme


class ElectronGenerator:
    """Generates a complete Electron desktop project with Master Theme integration."""

    name = "electron"
    display_name = "Electron Forge (Desktop)"
    description = "Secure, cross-platform native desktop application with Electron, contextIsolation, and modern UI."

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
            "version": ast.version,
            "description": ast.description,
            "main": "main.js",
            "scripts": {
                "start": "electron .",
                "pack": "electron-builder --dir",
                "dist": "electron-builder"
            },
            "build": {
                "appId": f"com.polyglot.{ast.title.lower().replace(' ', '')}",
                "productName": ast.title,
                "directories": {
                    "output": "dist"
                },
                "files": [
                    "main.js",
                    "preload.js",
                    "renderer.js",
                    "styles.css",
                    "index.html",
                    "package.json"
                ]
            },
            "devDependencies": {
                "electron": "^33.2.1",
                "electron-builder": "^25.1.8"
            }
        }, indent=2)

        # 2. main.js (Secure Modern Electron Main Process)
        files["main.js"] = f"""const {{ app, BrowserWindow, ipcMain, nativeTheme }} = require('electron');
const path = require('path');

// Set native theme according to Master Theme
nativeTheme.themeSource = '{ "dark" if theme.is_dark else "light" }';

function createWindow() {{
  const mainWindow = new BrowserWindow({{
    width: 1280,
    height: 840,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '{theme.bg_primary}',
    title: "{ast.title} (Desktop)",
    webPreferences: {{
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    }},
    autoHideMenuBar: true,
    show: false,
  }});

  mainWindow.loadFile('index.html');

  mainWindow.once('ready-to-show', () => {{
    mainWindow.show();
  }});

  // Handle external links safely
  mainWindow.webContents.setWindowOpenHandler(({{ url }}) => {{
    require('electron').shell.openExternal(url);
    return {{ action: 'deny' }};
  }});
}}

app.whenReady().then(() => {{
  createWindow();

  app.on('activate', () => {{
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  }});
}});

app.on('window-all-closed', () => {{
  if (process.platform !== 'darwin') app.quit();
}});

// IPC handlers
ipcMain.handle('app:get-info', () => ({{
  name: '{ast.title}',
  version: '{ast.version}',
  platform: process.platform,
  theme: '{theme.name}'
}}));
"""

        # 3. preload.js (Secure contextBridge)
        files["preload.js"] = """const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('polyglotAPI', {
  getAppInfo: () => ipcRenderer.invoke('app:get-info'),
  platform: process.platform,
});
"""

        # 4. styles.css
        files["styles.css"] = f"""/* Master Theme CSS Variables */
{theme.to_css_string()}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  user-select: none;
}}

.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}}

/* Header & Navigation */
.site-header {{
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background-color: rgba(9, 9, 11, 0.85);
  border-bottom: 1px solid var(--border-color);
}}

.nav-container {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 4rem;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--text-primary);
  text-decoration: none;
}}

.brand-icon {{
  width: 2rem;
  height: 2rem;
  background-color: var(--accent-primary);
  color: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  font-family: var(--font-mono);
  font-weight: bold;
  font-size: 0.875rem;
}}

.nav-links {{
  display: flex;
  gap: 1.5rem;
}}

.nav-links a {{
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s;
}}

.nav-links a:hover {{
  color: var(--accent-primary);
}}

/* Buttons */
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.625rem 1.25rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.875rem;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}}

.btn-primary {{
  background-color: var(--btn-primary-bg);
  color: var(--btn-primary-text);
}}

.btn-primary:hover {{
  background-color: var(--btn-primary-hover);
  transform: translateY(-1px);
}}

.btn-secondary {{
  background-color: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border-color: var(--border-color);
}}

.btn-secondary:hover {{
  background-color: var(--btn-secondary-hover);
}}

/* Badge */
.badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  background-color: var(--badge-bg);
  color: var(--badge-text);
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  border: 1px solid var(--border-subtle);
}}

/* Hero Section */
.hero-section {{
  padding: 6rem 0 5rem;
  text-align: center;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}}

.hero-title {{
  font-family: var(--font-heading);
  font-size: 3.5rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.1;
  max-width: 900px;
  margin: 0 auto;
}}

.hero-subtitle {{
  font-size: 1.125rem;
  color: var(--text-secondary);
  max-width: 650px;
  margin: 1.5rem auto 0;
}}

.hero-actions {{
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 2.5rem;
}}

.code-box {{
  max-width: 450px;
  margin: 2.5rem auto 0;
  padding: 0.75rem 1rem;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-secondary);
}}

/* Grid & Cards */
.features-section, .pricing-section, .testimonials-section, .stats-section, .faq-section, .code-section {{
  padding: 5rem 0;
  border-bottom: 1px solid var(--border-color);
}}

.section-header {{
  text-align: center;
  max-width: 600px;
  margin: 0 auto 3.5rem;
}}

.section-title {{
  font-family: var(--font-heading);
  font-size: 2.25rem;
  font-weight: 700;
}}

.section-subtitle {{
  margin-top: 0.75rem;
  color: var(--text-secondary);
  font-size: 1rem;
}}

.features-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 2rem;
}}

.card {{
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  padding: 1.75rem;
  box-shadow: {theme.card_shadow};
  transition: transform 0.2s, border-color 0.2s;
}}

.card:hover {{
  transform: translateY(-2px);
  border-color: var(--accent-primary);
}}

.feature-icon {{
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background-color: var(--badge-bg);
  color: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  margin-bottom: 1rem;
}}

/* Pricing */
.pricing-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}}

.pricing-card {{
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
}}

.pricing-card.popular {{
  border-color: var(--accent-primary);
}}

.price-value {{
  font-size: 2.5rem;
  font-weight: 800;
  margin: 1rem 0;
}}

.price-value span {{
  font-size: 0.875rem;
  color: var(--text-muted);
}}

.feature-list {{
  list-style: none;
  margin: 1.5rem 0;
  space-y: 0.75rem;
}}

.feature-list li {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}}

.feature-list li::before {{
  content: "✓";
  color: var(--accent-primary);
  font-weight: bold;
}}

/* Stats */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  text-align: center;
}}

.stat-value {{
  font-family: var(--font-heading);
  font-size: 3rem;
  font-weight: 800;
  color: var(--accent-primary);
}}

.stat-label {{
  font-weight: 600;
  margin-top: 0.5rem;
}}

/* Code Viewer */
.code-window {{
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}}

.code-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}}

.window-dots {{
  display: flex;
  gap: 0.375rem;
}}

.dot {{
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 9999px;
}}

.dot-red {{ background-color: #ef4444; }}
.dot-yellow {{ background-color: #eab308; }}
.dot-green {{ background-color: #22c55e; }}

.code-pre {{
  padding: 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-secondary);
  overflow-x: auto;
  line-height: 1.7;
}}

/* FAQ */
.faq-list {{
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}}

.faq-item {{
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  background-color: var(--bg-surface);
  padding: 1.25rem;
  cursor: pointer;
}}

.faq-question {{
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}}

.faq-answer {{
  display: none;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
  font-size: 0.875rem;
  color: var(--text-secondary);
}}

.faq-item.open .faq-answer {{
  display: block;
}}

/* CTA */
.cta-banner {{
  padding: 5rem 0;
  background-color: var(--accent-primary);
  color: var(--bg-primary);
  text-align: center;
}}

.cta-banner h2 {{
  font-size: 2.75rem;
  font-weight: 800;
}}

.cta-banner p {{
  font-size: 1.125rem;
  margin-top: 1rem;
  opacity: 0.9;
}}

/* Footer */
.site-footer {{
  padding: 4rem 0 2rem;
  background-color: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  font-size: 0.875rem;
}}

.footer-grid {{
  display: grid;
  grid-template-columns: 2fr repeat(3, 1fr);
  gap: 2rem;
  margin-bottom: 3rem;
}}

.footer-bottom {{
  padding-top: 2rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 0.75rem;
}}
"""

        # 5. renderer.js (Interactive client logic)
        files["renderer.js"] = """document.addEventListener('DOMContentLoaded', () => {
  // FAQ accordion handler
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    item.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      faqItems.forEach(i => i.classList.remove('open'));
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });

  // Code copy button
  const copyBtn = document.getElementById('copy-code-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const code = document.querySelector('.code-pre code').innerText;
      navigator.clipboard.writeText(code).then(() => {
        copyBtn.innerText = 'Copied!';
        setTimeout(() => { copyBtn.innerText = 'Copy'; }, 2000);
      });
    });
  }

  // Load app info from preload bridge if available
  if (window.polyglotAPI) {
    window.polyglotAPI.getAppInfo().then(info => {
      console.log('Polyglot Electron Shell running:', info);
    });
  }
});
"""

        # 6. index.html (Complete semantic HTML shell)
        nav = ast.navigation
        brand_name = nav.brand_name if nav else "Polyglot"
        links = nav.links if nav else []
        cta = nav.cta if nav else {"label": "Get Started", "href": "#"}
        nav_links_html = "".join([f'<a href="{html.escape(l.get("href", "#"))}">{html.escape(l.get("label", ""))}</a>' for l in links])

        hero_sec = ast.get_section("hero")
        h_data = hero_sec.data if hero_sec else {}
        p_cta = h_data.get("primary_cta", {"label": "Get Started", "href": "#"})
        s_cta = h_data.get("secondary_cta", {"label": "Learn More", "href": "#"})

        feat_sec = ast.get_section("features")
        f_data = feat_sec.data if feat_sec else {}
        feat_cards = []
        for it in f_data.get("items", []):
            feat_cards.append(f"""        <div class="card">
          <div class="feature-icon">⚡</div>
          <h3>{html.escape(it.get("title", ""))}</h3>
          <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.875rem;">{html.escape(it.get("description", ""))}</p>
        </div>""")

        price_sec = ast.get_section("pricing")
        p_data = price_sec.data if price_sec else {}
        price_cards = []
        for t in p_data.get("tiers", []):
            pop_cls = " popular" if t.get("is_popular") else ""
            feats = "".join([f'<li>{html.escape(f)}</li>' for f in t.get("features", [])])
            price_cards.append(f"""        <div class="card pricing-card{pop_cls}">
          <div>
            <h3>{html.escape(t.get("name", ""))}</h3>
            <p style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.25rem;">{html.escape(t.get("description", ""))}</p>
            <div class="price-value">{html.escape(t.get("price", "$0"))} <span>{html.escape(t.get("period", "/mo"))}</span></div>
            <ul class="feature-list">
              {feats}
            </ul>
          </div>
          <a href="{html.escape(t.get('cta_href', '#'))}" class="btn btn-primary" style="width: 100%; margin-top: 1.5rem;">{html.escape(t.get('cta_label', 'Choose Plan'))}</a>
        </div>""")

        stats_sec = ast.get_section("stats")
        st_data = stats_sec.data if stats_sec else {}
        stat_items = []
        for m in st_data.get("metrics", []):
            stat_items.append(f"""        <div>
          <div class="stat-value">{html.escape(m.get("value", ""))}</div>
          <div class="stat-label">{html.escape(m.get("label", ""))}</div>
        </div>""")

        code_sec = ast.get_section("code_viewer")
        c_data = code_sec.data if code_sec else {}
        code_str = c_data.get("tabs", [{}])[0].get("code", "// Generated Code") if c_data.get("tabs") else "// Generated Code"

        faq_sec = ast.get_section("faq")
        faq_data = faq_sec.data if faq_sec else {}
        faq_items = []
        for it in faq_data.get("items", []):
            faq_items.append(f"""        <div class="faq-item">
          <div class="faq-question">
            <span>{html.escape(it.get("question", ""))}</span>
            <span>↓</span>
          </div>
          <div class="faq-answer">
            {html.escape(it.get("answer", ""))}
          </div>
        </div>""")

        cta_sec = ast.get_section("cta")
        cta_data = cta_sec.data if cta_sec else {}

        footer = ast.footer
        f_brand = footer.brand_name if footer else "Polyglot"
        f_tagline = footer.tagline if footer else "Universal AST Exporter."
        f_cols = footer.columns if footer else []
        f_copy = footer.copyright if footer else "© 2026 Polyglot."
        cols_html = []
        for col in f_cols:
            clinks = "".join([f'<li><a href="{html.escape(l.get("href", "#"))}" style="color: var(--text-secondary); text-decoration: none;">{html.escape(l.get("label", ""))}</a></li>' for l in col.get("links", [])])
            cols_html.append(f"""        <div>
          <h4 style="font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.75rem;">{html.escape(col.get("title", ""))}</h4>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem;">
            {clinks}
          </ul>
        </div>""")

        files["index.html"] = f"""<!DOCTYPE html>
<html lang="{ast.lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(ast.title)}</title>
  <link rel="stylesheet" href="styles.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@400;600;700&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <!-- Header -->
  <header class="site-header">
    <div class="container nav-container">
      <a href="#" class="brand">
        <span class="brand-icon">P</span>
        <span>{brand_name} (Desktop)</span>
      </a>
      <nav class="nav-links">
        {nav_links_html}
      </nav>
      <div>
        <a href="{html.escape(cta.get('href', '#'))}" class="btn btn-primary">{html.escape(cta.get('label', 'Get Started'))}</a>
      </div>
    </div>
  </header>

  <!-- Hero -->
  <section class="hero-section">
    <div class="container">
      <div class="badge">✨ {html.escape(h_data.get('badge', 'Desktop Edition'))}</div>
      <h1 class="hero-title">{html.escape(h_data.get('title', 'Universal Full-Stack Application'))}</h1>
      <p class="hero-subtitle">{html.escape(h_data.get('subtitle', 'Build once, export anywhere.'))}</p>
      <div class="hero-actions">
        <a href="{html.escape(p_cta.get('href', '#'))}" class="btn btn-primary">{html.escape(p_cta.get('label', 'Get Started'))}</a>
        <a href="{html.escape(s_cta.get('href', '#'))}" class="btn btn-secondary">{html.escape(s_cta.get('label', 'Learn More'))}</a>
      </div>
      <div class="code-box">
        <span>$ {html.escape(h_data.get('code_snippet', 'electron .'))}</span>
        <span class="badge" style="margin: 0; padding: 0.125rem 0.5rem;">Native Process</span>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section class="features-section" id="features">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">{html.escape(f_data.get('title', 'Core Capabilities'))}</h2>
        <p class="section-subtitle">{html.escape(f_data.get('subtitle', 'Engineered for exceptional velocity.'))}</p>
      </div>
      <div class="features-grid">
{"".join(feat_cards)}
      </div>
    </div>
  </section>

  <!-- Code Viewer -->
  <section class="code-section">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">{html.escape(c_data.get('title', 'Generated Code'))}</h2>
        <p class="section-subtitle">{html.escape(c_data.get('subtitle', 'Native execution across operating systems.'))}</p>
      </div>
      <div class="code-window">
        <div class="code-header">
          <div class="window-dots">
            <div class="dot dot-red"></div>
            <div class="dot dot-yellow"></div>
            <div class="dot dot-green"></div>
          </div>
          <button id="copy-code-btn" class="btn btn-secondary" style="padding: 0.25rem 0.75rem; font-size: 0.75rem;">Copy</button>
        </div>
        <pre class="code-pre"><code>{html.escape(code_str)}</code></pre>
      </div>
    </div>
  </section>

  <!-- Stats -->
  <section class="stats-section">
    <div class="container">
      <div class="stats-grid">
{"".join(stat_items)}
      </div>
    </div>
  </section>

  <!-- Pricing -->
  <section class="pricing-section" id="pricing">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">{html.escape(p_data.get('title', 'Predictable Plans'))}</h2>
        <p class="section-subtitle">{html.escape(p_data.get('subtitle', 'Flexible pricing for every stage.'))}</p>
      </div>
      <div class="pricing-grid">
{"".join(price_cards)}
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="faq-section" id="faq">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">{html.escape(faq_data.get('title', 'Frequently Asked Questions'))}</h2>
        <p class="section-subtitle">{html.escape(faq_data.get('subtitle', 'Everything you need to know.'))}</p>
      </div>
      <div class="faq-list">
{"".join(faq_items)}
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-banner">
    <div class="container">
      <h2>{html.escape(cta_data.get('title', 'Ready to Build?'))}</h2>
      <p>{html.escape(cta_data.get('subtitle', 'Start exporting today.'))}</p>
      <div style="margin-top: 2rem;">
        <a href="{html.escape(cta_data.get('primary_cta', {}).get('href', '#'))}" class="btn" style="background: var(--bg-primary); color: var(--text-primary); padding: 0.875rem 2rem; font-size: 1rem;">
          {html.escape(cta_data.get('primary_cta', {}).get('label', 'Get Started Free'))}
        </a>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div>
          <div class="brand">{f_brand}</div>
          <p style="color: var(--text-muted); font-size: 0.75rem; margin-top: 0.5rem;">{f_tagline}</p>
        </div>
{"".join(cols_html)}
      </div>
      <div class="footer-bottom">
        <div>{f_copy}</div>
        <div>Powered by Electron Forge & Polyglot Exporter</div>
      </div>
    </div>
  </footer>

  <script src="renderer.js"></script>
</body>
</html>
"""

        # 7. README.md
        files["README.md"] = f"""# {ast.title} (Electron Desktop Application)

Exported with **Polyglot Framework Exporter** using the **{theme.display_name}** theme.

## 🚀 Quickstart

```bash
# Install dependencies
npm install

# Start Electron desktop application
npm start

# Package for current OS (macOS .dmg, Linux .AppImage, Windows .exe)
npm run dist
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
