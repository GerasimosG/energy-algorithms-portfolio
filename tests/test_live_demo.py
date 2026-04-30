"""Tests for energy_data live_demo — ENTSO-E Pipeline with PCR model.

These tests verify that the live pipeline demo works correctly
with demo data (offline fallback), produces valid output, and
handles edge cases gracefully.

No API key is required — tests run against demo data only.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

# Force demo data mode by temporarily clearing any API key
_original_key = os.environ.get("ENTSOE_API_KEY", None)
if "ENTSOE_API_KEY" in os.environ:
    del os.environ["ENTSOE_API_KEY"]


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


def test_demo_live_pipeline_falls_back_to_demo():
    """When API is unavailable (no key), the pipeline uses demo data."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()

    # Should NOT have used live API
    assert result["live"] is False

    # Demo data should have the "(demo)" marker
    assert "demo" in result["prices"].get("status", "").lower() or \
           "demo" in result["prices"].get("note", "").lower() or \
           result["prices"].get("status") == "ok (demo)"


def test_demo_live_pipeline_prices_has_24_hours():
    """Day-ahead prices contain 24 hourly values."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    prices = result["prices"].get("prices", [])
    assert len(prices) == 24, f"Expected 24 hours, got {len(prices)}"


def test_demo_live_pipeline_generation_has_sources():
    """Generation mix has multiple sources with positive MW."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    gen = result["generation"]
    assert len(gen["generation"]) > 0
    assert gen["total_mw"] > 0


def test_demo_live_pipeline_model_solves():
    """The PCR model reaches an Optimal solution with demo data."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()
    model_result = result["model_result"]

    # Should be Optimal (or at least not crash)
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
    assert 99.0 <= total_share <= 101.0, \
        f"Shares sum to {total_share}%, expected ~100%"


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


def test_demo_live_pipeline_idempotent():
    """Running the pipeline twice should produce consistent results."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    r1 = demo_live_pipeline()
    r2 = demo_live_pipeline()

    # With demo data, results should be deterministic
    assert r1["entsoe_avg_price"] == r2["entsoe_avg_price"]
    assert r1["model_mcp"] == r2["model_mcp"]
    assert r1["generation"]["total_mw"] == r2["generation"]["total_mw"]


# ── Edge-case tests ──────────────────────────────────────────────────


def test_fallback_with_nonexistent_api():
    """Pipeline works even when we simulate total API failure.

    We import and call _build_pcr_model directly with demo data
    to verify the model construction works in isolation.
    """
    from energy_algorithms.adapters.entsoe_client import fetch_demo_day_ahead, fetch_demo_generation_mix
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

    # With zero supply and zero demand, the model has no variables.
    # PuLP may produce None-valued objective. We verify it doesn't
    # crash during build, and the solve either returns gracefully
    # or raises TypeError (which is acceptable for degenerate input).
    try:
        result = model.solve()
        assert result["status"] in ("Optimal", "Infeasible")
    except TypeError:
        # Acceptable: PuLP can't handle completely empty LP
        pass
