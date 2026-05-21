"""Tests for domain/__init__.py — module exports."""

from __future__ import annotations

from energy_algorithms import domain


def test_domain_has_all_attribute() -> None:
    """Domain module has __all__ defined."""
    assert hasattr(domain, "__all__")
    assert isinstance(domain.__all__, list)


def test_domain_exports_markets() -> None:
    """markets is exported in __all__."""
    assert "markets" in domain.__all__
    assert hasattr(domain, "markets")


def test_domain_exports_optimization() -> None:
    """optimization is exported in __all__."""
    assert "optimization" in domain.__all__
    assert hasattr(domain, "optimization")


def test_domain_exports_trading() -> None:
    """trading is exported in __all__ (may fail import gracefully)."""
    assert "trading" in domain.__all__
    # trading may or may not be importable; the __init__.py handles
    # ImportError gracefully via try/except.
    trading = getattr(domain, "trading", None)
    # Either it's available or it's None (ImportError was caught)


def test_domain_exports_hooks() -> None:
    """Hook names are exported."""
    for name in ("HookRegistry", "register_hook", "run_hooks", "clear_hooks",
                  "PRE_SOLVE", "POST_SOLVE", "POST_EXTRACT"):
        assert name in domain.__all__
        assert hasattr(domain, name), f"{name} not accessible on domain"


def test_domain_exports_options() -> None:
    """Option functions are exported."""
    for name in ("get_option", "set_option", "reset_options", "get_options_dict"):
        assert name in domain.__all__
        assert hasattr(domain, name), f"{name} not accessible on domain"


def test_all_exports_are_accessible() -> None:
    """Every name in __all__ is accessible as an attribute on the domain module."""
    for name in domain.__all__:
        assert hasattr(domain, name), f"__all__ entry '{name}' is not accessible"
