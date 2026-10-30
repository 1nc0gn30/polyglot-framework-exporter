#!/usr/bin/env python3
"""Polyglot Framework Exporter Standalone Production Server on Port 8126.

Provides real REST API endpoints:
  - /health & /api/health
  - /api/frameworks
  - /api/diagnostics
  - /api/deploy-configs
  - /api/download-zip
  - /api/export
and serves the standalone Polyglot Studio from public/.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from polyglot_framework_exporter.ui_server import run_ui_server

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polyglot Framework Exporter Standalone Workstation")
    parser.add_argument("--port", type=int, default=8126, help="Port to listen on (default: 8126)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    args = parser.parse_args()

    print(f"Starting Polyglot Framework Exporter Server on {args.host}:{args.port}...")
    run_ui_server(host=args.host, port=args.port, open_browser=False)
