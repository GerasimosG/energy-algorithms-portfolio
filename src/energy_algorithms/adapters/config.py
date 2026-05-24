"""ENTSO-E API configuration.

Live data access is enabled by setting ``ENTSOE_API_KEY`` in the
environment. Without it, demos fall back to offline data.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from energy_algorithms.adapters.entsoe_client import EntsoeClient

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


def create_entsoe_client(timeout: int = 30) -> EntsoeClient:
    """Factory: create an EntsoeClient from the environment API key.

    Reads ``ENTSOE_API_KEY`` from the config module so callers don't
    need to import both config and the client class.

    Parameters
    ----------
    timeout : int
        Request timeout in seconds (default 30).

    Returns
    -------
    EntsoeClient
        Configured client ready to query the ENTSO-E API.
    """
    from energy_algorithms.adapters.entsoe_client import EntsoeClient

    return EntsoeClient(api_key=ENTSOE_API_KEY, timeout=timeout)
