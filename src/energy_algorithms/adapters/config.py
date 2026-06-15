"""ENTSO-E API configuration.

Live data access is enabled by setting ``ENTSOE_API_KEY`` in the
environment. Without it, demos fall back to offline data.

A repo-root ``.env`` file is loaded as a local-dev convenience. Loading is
skipped when ``ENERGY_ALGORITHMS_SKIP_DOTENV`` is set, so tests can assert the
no-token default deterministically, and it never overrides a variable already
present in the environment.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo root: src/energy_algorithms/adapters/config.py -> parents[3]
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _load_dotenv(env_path: Path = _ENV_PATH) -> None:
    """Load ``KEY=VALUE`` pairs from a ``.env`` file into ``os.environ``.

    Parameters
    ----------
    env_path : Path
        Path to the ``.env`` file. Defaults to the repo-root ``.env``.

    Notes
    -----
    - No-op when ``ENERGY_ALGORITHMS_SKIP_DOTENV`` is set in the environment.
    - Uses ``setdefault``: an existing environment variable always wins.
    """
    if os.getenv("ENERGY_ALGORITHMS_SKIP_DOTENV"):
        return
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)


_load_dotenv()

# ENTSO-E Transparency Platform API security token.
ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY", "").strip()

# Default bidding zone for demos
DEFAULT_AREA_CODE = "10YBE----------2"  # Belgium
