"""ENTSO-E API configuration.

Live data access is enabled by setting ``ENTSOE_API_KEY`` in the
environment. Without it, demos fall back to offline data.
"""
from __future__ import annotations

import os
from pathlib import Path

# Load .env file if available (local dev convenience)
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k, _v)

# ENTSO-E Transparency Platform API security token.
ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY", "").strip()

# Default bidding zone for demos
DEFAULT_AREA_CODE = "10YBE----------2"  # Belgium
