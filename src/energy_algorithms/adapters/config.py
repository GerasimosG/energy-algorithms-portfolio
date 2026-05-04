"""ENTSO-E API configuration.

Live data access is enabled by setting ``ENTSOE_API_KEY`` in the
environment. Without it, demos fall back to offline data.
"""
from __future__ import annotations

import os

# ENTSO-E Transparency Platform API security token.
ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY", "").strip()

# Default bidding zone for demos
DEFAULT_AREA_CODE = "10YBE----------2"  # Belgium
