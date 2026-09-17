#!/usr/bin/env python3
"""Main execution entrypoint for python -m polyglot_framework_exporter."""

from __future__ import annotations

import sys
from polyglot_framework_exporter.cli import main

if __name__ == "__main__":
    sys.exit(main())
