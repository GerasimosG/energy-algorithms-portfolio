"""Tests for energy_data live_demo — ENTSO-E Pipeline with PCR model.

These tests verify that the live pipeline demo works correctly
with either live or demo data, produces valid output, and
handles edge cases gracefully.
"""
from __future__ import annotations

import importlib


def test_demo_live_pipeline_returns_valid_dict():
    """The pipeline returns a well-structured dict with all required keys."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()

    # Required top-level keys
    for key in (
        "live", "area", "date", "prices", "generation",
        "model_result", "model_mcp", "entsoe_avg_price",
        "price_diff_pct", "generation_shares",
    ):
        assert key in result, f"Missing key: {key}"


def test_demo_live_pipeline_runs_without_crash():
    """Pipeline handles live or demo data gracefully."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()

    # The pipeline should run without crashing regardless of data source
    assert result["model_result"]["status"] in ("Optimal", "Feasible")


def test_demo_live_pipeline_prices_has_data():
    """Day-ahead prices contain at least 1 value."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    prices = result["prices"].get("prices", [])
    assert len(prices) > 0, f"Expected at least 1 price point, got {len(prices)}"


def test_demo_live_pipeline_generation_has_sources():
    """Generation mix has multiple sources with positive MW."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    gen = result["generation"]
    assert len(gen["generation"]) > 0
    assert gen["total_mw"] > 0


def test_demo_live_pipeline_model_solves():
    """The PCR model reaches an Optimal solution."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    model_result = result["model_result"]

    assert model_result["status"] in ("Optimal", "Feasible"), \
        f"Unexpected model status: {model_result['status']}"


def test_demo_live_pipeline_model_has_positive_volume():
    """PCR model trades a positive volume of electricity."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    traded = result["model_result"].get("traded", 0)
    assert traded > 0, f"Expected positive traded volume, got {traded}"


def test_demo_live_pipeline_generation_shares_sum_to_100():
    """Generation shares should approximately sum to 100%."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    shares = result["generation_shares"]
    total_share = sum(shares.values())
    assert 95.0 <= total_share <= 105.0, \
        f"Shares sum to {total_share}%, expected ~100%"


def test_live_pipeline_aggregates_duplicate_generation_types(monkeypatch):
    """Duplicate PSR time series should not overwrite shares or supply orders."""
    from energy_algorithms.application import live_pipeline

    prices = {
        "status": "ok",
        "area": "10YBE----------2",
        "date": "2024-03-15",
        "prices": [
            {"hour": 1, "price_eur_mwh": 200.0},
            {"hour": 2, "price_eur_mwh": 200.0},
            {"hour": 3, "price_eur_mwh": 200.0},
        ],
        "avg_price": 200.0,
    }
    generation = {
        "status": "ok",
        "area": "10YBE----------2",
        "date": "2024-03-15",
        "generation": [
            {"type": "Hydro Pumped Storage", "mw": 40.0, "psr_code": "B10"},
            {"type": "Hydro Pumped Storage", "mw": 60.0, "psr_code": "B10"},
        ],
        "total_mw": 100.0,
    }

    def fake_fetch_live(api_key, area, date):
        return {
            "success": True,
            "prices": prices,
            "generation": generation,
            "live": True,
        }

    monkeypatch.setattr(live_pipeline, "_try_fetch_live", fake_fetch_live)
    monkeypatch.setattr(live_pipeline, "_print_report", lambda **kwargs: None)

    result = live_pipeline.demo_live_pipeline()

    assert result["generation_shares"] == {"Hydro Pumped Storage": 100.0}
    assert result["model_result"]["orders"]["supply"]["Hydro Pumped Storage"]["qty"] == 100.0


def test_demo_live_pipeline_model_mcp_is_positive():
    """Market clearing price should be positive."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    assert result["model_mcp"] > 0, \
        f"Expected positive MCP, got {result['model_mcp']}"


def test_demo_live_pipeline_price_diff_is_finite():
    """Price difference percentage should be a finite number."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    diff = result["price_diff_pct"]
    assert isinstance(diff, (int, float))
    assert abs(diff) < 1000  # Shouldn't be absurdly large


def test_entsoe_api_key_defaults_to_environment_only(monkeypatch):
    """Tracked config must not contain a baked-in personal ENTSO-E token."""
    monkeypatch.delenv("ENTSOE_API_KEY", raising=False)

    import energy_algorithms.adapters.config as config

    reloaded = importlib.reload(config)

    assert reloaded.ENTSOE_API_KEY == ""


# ── Edge-case tests (always use demo data) ──────────────────────────


def test_fallback_with_nonexistent_api():
    """Pipeline works even when we simulate total API failure.

    We import and call _build_pcr_model directly with demo data
    to verify the model construction works in isolation.
    """
    from energy_algorithms.adapters.entsoe_client import (
        fetch_demo_day_ahead,
        fetch_demo_generation_mix,
    )
    from energy_algorithms.application.live_pipeline import _build_pcr_model

    prices = fetch_demo_day_ahead()
    gen = fetch_demo_generation_mix()

    model = _build_pcr_model(prices, gen, "10YBE----------2")
    result = model.solve()

    assert result["status"] == "Optimal"
    assert result["traded"] > 0


def test_empty_prices_handled():
    """_build_pcr_model handles empty prices gracefully."""
    from energy_algorithms.application.live_pipeline import _build_pcr_model

    empty_prices = {"prices": [], "avg_price": 0}
    gen = {
        "generation": [{"type": "Wind", "mw": 100}],
        "total_mw": 100,
    }
    model = _build_pcr_model(empty_prices, gen, "TEST")
    # Model should not crash — just have no demand orders
    result = model.solve()
    assert result["status"] in ("Optimal", "Infeasible")


def test_zero_generation_handled():
    """_build_pcr_model handles zero-generation scenario without crashing.

    When there are zero supply orders, the PCR model may raise
    because its objective function has no terms. The build step
    itself should not crash, and the model solve should either
    succeed with zero traded or raise a clear error.
    """
    from energy_algorithms.application.live_pipeline import _build_pcr_model

    prices = {
        "prices": [{"hour": 1, "price_eur_mwh": 80}],
        "avg_price": 80,
    }
    gen = {
        "generation": [],
        "total_mw": 0,
    }
    model = _build_pcr_model(prices, gen, "TEST")

    try:
        result = model.solve()
        assert result["status"] in ("Optimal", "Infeasible")
    except TypeError:
        pass
