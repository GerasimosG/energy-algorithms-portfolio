"""Tests for european_coupling — European Market Coupling Demo.

Tests individual functions including build_demand_curve (pure),
solve_coupling (via multi_zone), and mocked fetch/run paths.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── build_demand_curve ──────────────────────────────────────────────


def test_build_demand_curve_returns_three_blocks():
    """build_demand_curve returns 3 demand blocks for sufficient inputs."""
    from energy_algorithms.application.european_coupling import build_demand_curve

    # 24 prices should give 3 blocks
    prices = [float(i) for i in range(24)]
    blocks = build_demand_curve(prices, "TEST")
    assert len(blocks) == 3
    for b in blocks:
        assert "price" in b
        assert "qty" in b
        assert b["qty"] > 0


def test_build_demand_curve_empty_returns_fallback():
    """build_demand_curve returns fallback block for empty prices."""
    from energy_algorithms.application.european_coupling import build_demand_curve

    blocks = build_demand_curve([], "TEST")
    assert len(blocks) == 1
    assert blocks[0] == {"price": 100, "qty": 1000}


def test_build_demand_curve_single_price():
    """build_demand_curve handles single price gracefully."""
    from energy_algorithms.application.european_coupling import build_demand_curve

    blocks = build_demand_curve([50.0], "TEST")
    assert len(blocks) >= 1
    for b in blocks:
        assert b["price"] >= 40
        assert b["qty"] > 0


def test_build_demand_curve_two_prices():
    """build_demand_curve handles two prices."""
    from energy_algorithms.application.european_coupling import build_demand_curve

    blocks = build_demand_curve([30.0, 100.0], "TEST")
    assert len(blocks) >= 1
    assert all(b["qty"] > 0 for b in blocks)


def test_build_demand_curve_high_prices():
    """build_demand_curve with high prices produces high bid prices."""
    from energy_algorithms.application.european_coupling import build_demand_curve

    blocks = build_demand_curve([200.0, 250.0, 300.0, 350.0], "TEST")
    assert len(blocks) >= 1
    for b in blocks:
        assert b["price"] > 200


# ── fetch_european_prices ──────────────────────────────────────────


def test_fetch_european_prices_mocked():
    """fetch_european_prices returns price dict from mocked client."""
    from energy_algorithms.application.european_coupling import fetch_european_prices

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [{"hour": h, "price_eur_mwh": 50.0 + h} for h in range(1, 25)],
    }

    prices = fetch_european_prices(mock_client, "2024-01-01")
    assert isinstance(prices, dict)
    assert len(prices) == 6  # BE, FR, DE, NL, ES, PL
    for code in ["BE", "FR", "DE", "NL", "ES", "PL"]:
        assert code in prices
        assert prices[code] > 0


def test_fetch_european_prices_handles_empty():
    """fetch_european_prices returns 0.0 for zones with no prices."""
    from energy_algorithms.application.european_coupling import fetch_european_prices

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [],
    }

    prices = fetch_european_prices(mock_client, "2024-01-01")
    for code in ["BE", "FR", "DE", "NL", "ES", "PL"]:
        assert prices[code] == 0.0


def test_fetch_european_prices_mixed():
    """fetch_european_prices handles some zones having data and some not."""
    from energy_algorithms.application.european_coupling import fetch_european_prices

    mock_client = MagicMock()

    # First call succeeds, second returns empty
    call_count = [0]

    def side_effect(eic, date):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                "status": "ok",
                "prices": [{"hour": h, "price_eur_mwh": 50.0} for h in range(1, 25)],
            }
        return {"status": "ok", "prices": []}

    mock_client.fetch_day_ahead_prices.side_effect = side_effect

    prices = fetch_european_prices(mock_client, "2024-01-01")
    # At least one zone should have data
    assert any(v > 0 for v in prices.values())


# ── solve_coupling / run_european_coupling ──────────────────────────


def test_run_european_coupling_uses_multi_zone(monkeypatch):
    """run_european_coupling returns a tuple with result dict."""
    from energy_algorithms.application import european_coupling

    # Mock EntsoeClient to avoid real API calls
    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [{"hour": h, "price_eur_mwh": 50.0} for h in range(1, 25)],
    }

    monkeypatch.setattr(
        european_coupling, "EntsoeClient", lambda **kw: mock_client
    )

    # Mock solve_multi_zone to return a known result
    fake_result = {
        "status": "Optimal",
        "welfare": 1000000,
        "flows": {"FR→BE": 500.0, "BE→NL": 300.0},
        "zones": {
            "FR": {"mcp": 45.0, "supply_cleared_mw": 8000, "demand_cleared_mw": 7500},
            "BE": {"mcp": 48.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
            "DE": {"mcp": 50.0, "supply_cleared_mw": 10000, "demand_cleared_mw": 9500},
            "NL": {"mcp": 47.0, "supply_cleared_mw": 5000, "demand_cleared_mw": 4800},
            "ES": {"mcp": 44.0, "supply_cleared_mw": 7000, "demand_cleared_mw": 6800},
            "PL": {"mcp": 55.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
        },
    }
    monkeypatch.setattr(
        european_coupling, "solve_multi_zone", lambda *a, **kw: fake_result
    )

    result, real_prices, atc = european_coupling.run_european_coupling()
    assert result["status"] == "Optimal"
    assert isinstance(real_prices, dict)
    assert isinstance(atc, dict)
    assert len(atc) > 0


def test_run_european_coupling_handles_no_prices(monkeypatch):
    """run_european_coupling handles when ENTSO-E returns no prices."""
    from energy_algorithms.application import european_coupling

    mock_client = MagicMock()
    mock_client.fetch_day_ahead_prices.return_value = {
        "status": "ok",
        "prices": [],
    }
    monkeypatch.setattr(european_coupling, "EntsoeClient", lambda **kw: mock_client)

    fake_result = {"status": "Optimal", "welfare": 0, "flows": {}, "zones": {}}
    monkeypatch.setattr(
        european_coupling, "solve_multi_zone", lambda *a, **kw: fake_result
    )

    result, real_prices, atc = european_coupling.run_european_coupling()
    # All prices should be 0
    assert all(v == 0.0 for v in real_prices.values())
    assert len(atc) == 0  # No ATC if all prices are 0


# ── print_results ───────────────────────────────────────────────────


def test_print_results_optimal(capsys):
    """print_results prints optimal result with zone and flow details."""
    from energy_algorithms.application.european_coupling import print_results

    result = {
        "status": "Optimal",
        "welfare": 1500000,
        "flows": {"FR→BE": 500.0, "BE→NL": 300.0},
        "zones": {
            "FR": {"mcp": 45.0, "supply_cleared_mw": 8000, "demand_cleared_mw": 7500},
            "BE": {"mcp": 48.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
            "DE": {"mcp": 50.0, "supply_cleared_mw": 10000, "demand_cleared_mw": 9500},
            "NL": {"mcp": 47.0, "supply_cleared_mw": 5000, "demand_cleared_mw": 4800},
            "ES": {"mcp": 44.0, "supply_cleared_mw": 7000, "demand_cleared_mw": 6800},
            "PL": {"mcp": 55.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
        },
    }
    real_prices = {
        "FR": 45.0, "BE": 50.0, "DE": 55.0, "NL": 48.0, "ES": 42.0, "PL": 60.0,
    }
    atc = {("FR", "BE"): 3500, ("BE", "NL"): 2400}

    print_results(result, real_prices, atc)
    captured = capsys.readouterr()
    assert "OPTIMAL" in captured.out
    assert "Social Welfare" in captured.out
    assert "ZONE-LEVEL RESULTS" in captured.out
    assert "INTER-ZONAL FLOWS" in captured.out
    assert "PRICE CONVERGENCE ANALYSIS" in captured.out


def test_print_results_non_optimal(capsys):
    """print_results handles non-optimal status."""
    from energy_algorithms.application.european_coupling import print_results

    result = {"status": "Infeasible"}
    print_results(result, {}, {})
    captured = capsys.readouterr()
    assert "Solve failed" in captured.out


def test_print_results_binding_flow(capsys):
    """print_results marks flows with >95% utilisation as binding."""
    from energy_algorithms.application.european_coupling import print_results

    result = {
        "status": "Optimal",
        "welfare": 500000,
        "flows": {"FR→BE": 3400.0},  # 3400/3500 = 97% — binding
        "zones": {
            "FR": {"mcp": 45.0, "supply_cleared_mw": 8000, "demand_cleared_mw": 7500},
            "BE": {"mcp": 48.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
            "DE": {"mcp": 50.0, "supply_cleared_mw": 10000, "demand_cleared_mw": 9500},
            "NL": {"mcp": 47.0, "supply_cleared_mw": 5000, "demand_cleared_mw": 4800},
            "ES": {"mcp": 44.0, "supply_cleared_mw": 7000, "demand_cleared_mw": 6800},
            "PL": {"mcp": 55.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
        },
    }
    real_prices = {"FR": 45.0, "BE": 50.0, "DE": 55.0, "NL": 48.0, "ES": 42.0, "PL": 60.0}
    atc = {("FR", "BE"): 3500}

    print_results(result, real_prices, atc)
    captured = capsys.readouterr()
    assert "BINDING" in captured.out


# ── main() ──────────────────────────────────────────────────────────


def test_main_runs(monkeypatch, capsys):
    """main() runs and prints results."""
    from energy_algorithms.application import european_coupling

    # Mock the full chain
    fake_result = {
        "status": "Optimal",
        "welfare": 1000000,
        "flows": {"FR→BE": 500.0},
        "zones": {
            "FR": {"mcp": 45.0, "supply_cleared_mw": 8000, "demand_cleared_mw": 7500},
            "BE": {"mcp": 48.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
            "DE": {"mcp": 50.0, "supply_cleared_mw": 10000, "demand_cleared_mw": 9500},
            "NL": {"mcp": 47.0, "supply_cleared_mw": 5000, "demand_cleared_mw": 4800},
            "ES": {"mcp": 44.0, "supply_cleared_mw": 7000, "demand_cleared_mw": 6800},
            "PL": {"mcp": 55.0, "supply_cleared_mw": 6000, "demand_cleared_mw": 5800},
        },
    }
    fake_prices = {"FR": 45.0, "BE": 50.0, "DE": 55.0, "NL": 48.0, "ES": 42.0, "PL": 60.0}
    fake_atc = {("FR", "BE"): 3500}

    monkeypatch.setattr(
        european_coupling,
        "run_european_coupling",
        lambda: (fake_result, fake_prices, fake_atc),
    )

    european_coupling.main()
    captured = capsys.readouterr()
    assert "OPTIMAL" in captured.out


def test_main_runs_with_no_prices(monkeypatch, capsys):
    """main() handles case where no real prices exist."""
    from energy_algorithms.application import european_coupling

    monkeypatch.setattr(
        european_coupling,
        "run_european_coupling",
        lambda: (
            {"status": "Optimal", "welfare": 0, "flows": {}, "zones": {}},
            {"FR": 0.0, "BE": 0.0, "DE": 0.0, "NL": 0.0, "ES": 0.0, "PL": 0.0},
            {},
        ),
    )

    european_coupling.main()
    captured = capsys.readouterr()
    # Should at least not crash
    assert "OPTIMAL" in captured.out or "Solve failed" not in captured.out
