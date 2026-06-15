"""Integration tests — full pipeline tests.

These tests validate that the complete ENTSO-E live pipeline works
end-to-end, including data fetching (with demo fallback), PCR model
construction, solving, and output formatting. No API key required.
"""
from __future__ import annotations

import os

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _ensure_demo_mode() -> None:
    """Force demo data mode by removing any ENTSOE_API_KEY."""
    if "ENTSOE_API_KEY" in os.environ:
        del os.environ["ENTSOE_API_KEY"]


# ── Helper: isolated data fetch tests ─────────────────────────────────


def test_demo_day_ahead_returns_24_prices() -> None:
    """Fetch demo day-ahead prices directly from the adapter."""
    from energy_algorithms.adapters.entsoe_client import fetch_demo_day_ahead

    prices = fetch_demo_day_ahead()
    assert len(prices["prices"]) == 24


def test_demo_generation_mix_has_positive_total() -> None:
    """Fetch demo generation mix directly from the adapter."""
    from energy_algorithms.adapters.entsoe_client import fetch_demo_generation_mix

    gen_mix = fetch_demo_generation_mix()
    assert len(gen_mix["generation"]) > 0
    assert gen_mix["total_mw"] > 0


# ── Full pipeline integration tests ───────────────────────────────────


@pytest.mark.slow
def test_full_pipeline_with_demo_data() -> None:
    """Test the full pipeline with demo data (no API key needed).

    Validates that:
    - The pipeline returns a complete result dict
    - Demo data is used (not live)
    - Prices contain 24 hours
    - Generation has positive MW
    - PCR model solves successfully (Optimal or Feasible)
    - Traded volume is positive
    - Market clearing price is positive
    """
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    result = demo_live_pipeline()

    # Structure checks
    for key in (
        "live",
        "area",
        "date",
        "prices",
        "generation",
        "model_result",
        "model_mcp",
        "entsoe_avg_price",
        "price_diff_pct",
        "generation_shares",
    ):
        assert key in result, f"Missing top-level key: {key}"

    # Demo fallback
    assert result["live"] is False

    # Data quality
    assert len(result["prices"]["prices"]) == 24
    assert result["generation"]["total_mw"] > 0
    assert len(result["generation"]["generation"]) > 0

    # Model quality
    assert result["model_result"]["status"] in ("Optimal", "Feasible")
    assert result["model_result"].get("traded", 0) > 0
    assert result["model_mcp"] > 0

    # Generation shares sum to ~100%
    total_share = sum(result["generation_shares"].values())
    assert 99.0 <= total_share <= 101.0, f"Generation shares sum to {total_share}%"


@pytest.mark.slow
def test_pipeline_idempotent() -> None:
    """Running the pipeline twice yields the same results with demo data."""
    from energy_algorithms.application.live_pipeline import demo_live_pipeline

    r1 = demo_live_pipeline()
    r2 = demo_live_pipeline()

    assert r1["entsoe_avg_price"] == r2["entsoe_avg_price"]
    assert r1["model_mcp"] == r2["model_mcp"]
    assert r1["generation"]["total_mw"] == r2["generation"]["total_mw"]
    assert r1["model_result"]["status"] == r2["model_result"]["status"]


# ── Adapter-level integration ─────────────────────────────────────────


def test_build_pcr_model_from_demo_data() -> None:
    """Build a PCR model directly from demo data (isolated pipeline step)."""
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
