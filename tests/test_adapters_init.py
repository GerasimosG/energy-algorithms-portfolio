"""Tests for adapters/__init__.py.

Covers the try/except ImportError block that handles optional
yfinance import failures, and verifies that all expected
symbols are exported.
"""
from __future__ import annotations

import sys

import pytest


def test_all_imports_available():
    """All re-exported symbols are importable from adapters."""
    from energy_algorithms.adapters import (
        ENTSOE_API_KEY,
        EntsoeClient,
        PuLPSolverAdapter,
        fetch_batch,
        fetch_demo_day_ahead,
        fetch_demo_generation_mix,
        fetch_ticker,
        get_connection,
        get_summary,
        get_ticker_data,
        init_db,
        insert_ohlcv,
    )

    assert PuLPSolverAdapter is not None
    assert EntsoeClient is not None
    assert fetch_demo_day_ahead is not None
    assert fetch_demo_generation_mix is not None
    assert get_connection is not None
    assert init_db is not None
    assert insert_ohlcv is not None
    assert get_ticker_data is not None
    assert get_summary is not None
    assert isinstance(ENTSOE_API_KEY, str)
    assert fetch_batch is None or callable(fetch_batch)
    assert fetch_ticker is None or callable(fetch_ticker)


def test_all_exports_defined():
    """The __all__ list contains all expected exports."""
    from energy_algorithms.adapters import __all__

    expected = [
        "PuLPSolverAdapter",
        "ENTSOE_API_KEY",
        "EntsoeClient",
        "fetch_demo_day_ahead",
        "fetch_demo_generation_mix",
        "fetch_ticker",
        "fetch_batch",
        "get_connection",
        "init_db",
        "insert_ohlcv",
        "get_ticker_data",
        "get_summary",
    ]
    for name in expected:
        assert name in __all__, f"{name!r} missing from __all__"


def test_direct_reimport():
    """Re-importing adapters module works (tests __all__ consistency)."""
    import energy_algorithms.adapters as adapters

    for name in adapters.__all__:
        assert hasattr(adapters, name), f"adapter module missing attr {name!r}"


class TestImportFallback:
    """Tests for the try/except ImportError on yfinance.

    When yfinance_fetcher cannot be imported, the fallback sets
    fetch_batch and fetch_ticker to None. We test this by
    monkeypatching __import__ to raise ImportError for the
    specific submodule, then force a re-import.
    """

    def test_yfinance_import_error_sets_fetch_to_none(self, monkeypatch):
        """Simulate yfinance_fetcher ImportError and verify fallback."""
        import builtins
        import importlib

        _cached_modules = {}
        # Pop only modules that actually exist in sys.modules
        for key in list(sys.modules.keys()):
            if "yfinance_fetcher" in key:
                _cached_modules[key] = sys.modules.pop(key)
        for key in list(sys.modules.keys()):
            if "energy_algorithms.adapters" in key and key not in _cached_modules:
                _cached_modules[key] = sys.modules.pop(key)

        _original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if "yfinance_fetcher" in name:
                raise ImportError(f"No module named {name!r}")
            return _original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _mock_import)

        import energy_algorithms.adapters.__init__ as adapters_init

        assert adapters_init.fetch_batch is None, (
            "fetch_batch should be None after ImportError fallback"
        )
        assert adapters_init.fetch_ticker is None, (
            "fetch_ticker should be None after ImportError fallback"
        )

        # Restore cached modules so other tests don't break
        for key, mod in _cached_modules.items():
            if mod is not None:
                sys.modules[key] = mod
