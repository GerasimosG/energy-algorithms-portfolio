"""Lightweight coverage tests for demo orchestration and adapter edges."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd


class DummyAxis:
    """Minimal matplotlib axis double for demo plotting paths."""

    transAxes = object()

    def plot(self, *args, **kwargs) -> None:
        pass

    def fill_between(self, *args, **kwargs) -> None:
        pass

    def axhline(self, *args, **kwargs) -> None:
        pass

    def set_title(self, *args, **kwargs) -> None:
        pass

    def set_ylabel(self, *args, **kwargs) -> None:
        pass

    def set_xlabel(self, *args, **kwargs) -> None:
        pass

    def grid(self, *args, **kwargs) -> None:
        pass

    def text(self, *args, **kwargs) -> None:
        pass


def fake_backtest_result(sharpe: float = 1.2) -> dict:
    """Return the result shape expected by demo modules."""
    return {
        "equity_curve": pd.Series([100_000.0, 101_000.0, 102_000.0]),
        "total_return": 0.02,
        "sharpe": sharpe,
        "max_drawdown": -0.01,
        "n_trades": 2,
        "win_rate": 0.5,
    }


def test_risk_metrics_cover_positive_and_degenerate_paths() -> None:
    """Risk metrics handle normal returns and no-edge cases."""
    from energy_algorithms.domain.trading import risk_metrics as rm

    returns = np.array([0.02, -0.01, 0.03, -0.02, 0.01])
    equity = np.array([100.0, 102.0, 101.0, 104.0, 103.0])

    metrics = rm.compute_all(returns, equity)
    assert set(metrics) == {"sharpe", "sortino", "max_drawdown", "calmar", "var_95", "var_99", "kelly"}
    assert rm.sharpe_ratio(np.array([0.0])) == 0.0
    assert rm.sortino_ratio(np.array([0.01, 0.02])) == 0.0
    assert rm.kelly_fraction(np.array([0.01, 0.02])) == 0.0


def test_stochastic_value_metrics_small_case() -> None:
    """VSS and EVPI run on a tiny deterministic stochastic UC instance."""
    from energy_algorithms.domain.optimization.stochastic import compute_evpi, compute_vss

    demand = [50.0, 60.0]
    wind = np.array([10.0, 15.0])
    solar = np.array([5.0, 0.0])
    generators = [
        {"name": "Gas", "min_output": 0.0, "max_output": 100.0, "cost_per_mwh": 50.0},
    ]

    assert compute_vss(demand, wind, solar, generators, n_scenarios=2, std_pct=0.0) >= 0.0
    assert compute_evpi(demand, wind, solar, generators, n_scenarios=2, std_pct=0.0) >= 0.0


def test_yfinance_fetcher_success_empty_retry_and_batch(monkeypatch) -> None:
    """YFinance adapter covers success, empty data, exception, and batch filtering."""
    from energy_algorithms.adapters import yfinance_fetcher as yfmod

    class FakeTicker:
        calls = 0

        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def history(self, period: str, interval: str) -> pd.DataFrame:
            FakeTicker.calls += 1
            if self.ticker == "EMPTY":
                return pd.DataFrame()
            if self.ticker == "ERR":
                raise RuntimeError("network down")
            return pd.DataFrame(
                {
                    "Date": pd.date_range("2024-01-01", periods=2),
                    "Open": [1.0, 2.0],
                    "High": [2.0, 3.0],
                    "Low": [0.5, 1.5],
                    "Close": [1.5, 2.5],
                    "Volume": [100, 200],
                }
            )

    monkeypatch.setattr(yfmod.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(yfmod.time, "sleep", lambda _delay: None)

    rows = yfmod.fetch_ticker("OK", retries=1, delay=0)
    assert rows and rows[0]["ticker"] == "OK"
    assert yfmod.fetch_ticker("EMPTY", retries=1, delay=0) is None
    assert yfmod.fetch_ticker("ERR", retries=1, delay=0) is None

    batch = yfmod.fetch_batch(["OK", "EMPTY"], delay=0)
    assert list(batch) == ["OK"]


def test_market_data_demo_main_with_fake_adapters(monkeypatch, capsys) -> None:
    """Market data demo stores fetched records and prints a DB summary."""
    from energy_algorithms.application import market_data_demo as demo

    fake_conn = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(demo, "fetch_batch", lambda tickers, period: {"AAPL": [{"ticker": "AAPL"}]})
    monkeypatch.setattr(demo, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(demo, "init_db", lambda conn: None)
    monkeypatch.setattr(demo, "insert_ohlcv", lambda conn, records: len(records))
    monkeypatch.setattr(
        demo,
        "get_summary",
        lambda conn: {
            "total_rows": 1,
            "tickers": [{"ticker": "AAPL", "rows": 1, "first": "2024-01-01", "last": "2024-01-01"}],
        },
    )

    demo.main()
    assert "Storage Summary" in capsys.readouterr().out


def test_optimization_demo_main_with_fake_domain(monkeypatch, capsys) -> None:
    """Optimization demo covers all reporting branches with fake results."""
    from energy_algorithms.application import optimization_demo as demo

    monkeypatch.setattr(
        demo,
        "demo_transportation",
        lambda: {"status": "Optimal", "total_cost": 12.0, "allocations": {"A->B": 3.0}},
    )
    monkeypatch.setattr(
        demo,
        "demo_portfolio",
        lambda: {
            "status": "Optimal",
            "weights": np.array([0.2, 0.0, 0.3, 0.0, 0.5, 0.0]),
            "return": 0.12,
            "risk": 0.08,
            "n_assets_selected": 3,
        },
    )
    monkeypatch.setattr(
        demo,
        "demo_uc",
        lambda: {
            "status": "Optimal",
            "total_cost": 100.0,
            "schedule": {
                "t=0": {"_online": ["Coal"], "_demand": 50.0, "Coal": 50.0, "Gas": 0.0, "Wind": 0.0},
                "t=1": {"_online": ["Gas"], "_demand": 60.0, "Coal": 0.0, "Gas": 60.0, "Wind": 0.0},
            },
        },
    )

    demo.main()
    assert "All three LP/MIP problems solved" in capsys.readouterr().out


def test_trading_demo_main_with_small_fake_backtest(monkeypatch, capsys, tmp_path) -> None:
    """Trading demo runs without real data, DB writes, or plot files."""
    from energy_algorithms.application import trading_demo as demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    axes = [DummyAxis(), DummyAxis(), DummyAxis()]

    monkeypatch.setattr(demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(demo, "_best_sma_params", lambda prices: (1, 2))
    monkeypatch.setattr(demo, "sma_crossover", lambda prices, fast, slow: np.array([0, 1, 1]))
    monkeypatch.setattr(demo, "backtest", lambda prices, signal: fake_backtest_result())
    monkeypatch.setattr(demo, "compute_all", lambda returns, equity: {"sharpe": 1.0, "max_drawdown": -0.01})
    monkeypatch.setattr(demo.plt, "subplots", lambda *a, **kw: (object(), axes))
    monkeypatch.setattr(demo.plt, "tight_layout", lambda: None)
    monkeypatch.setattr(demo.plt, "savefig", lambda *a, **kw: None)
    monkeypatch.setattr(demo.plt, "close", lambda: None)
    monkeypatch.setattr(demo.os.path, "dirname", lambda path: str(tmp_path))

    demo.main()
    assert "Backtester + risk metrics demo complete" in capsys.readouterr().out


def test_strategies_demo_main_with_small_fake_backtest(monkeypatch, capsys, tmp_path) -> None:
    """Strategies demo compares all strategies using cheap fake backtests."""
    from energy_algorithms.application import strategies_demo as demo

    prices = np.array([100.0, 101.0, 102.0])
    dates = pd.date_range("2024-01-01", periods=3)
    axes = [DummyAxis(), DummyAxis(), DummyAxis()]

    monkeypatch.setattr(demo, "_load_prices", lambda ticker: (prices, dates))
    monkeypatch.setattr(
        demo,
        "_best_params",
        lambda prices: {
            "sma": {"fast": 1, "slow": 2},
            "mr": {"window": 2, "n_std": 1.0},
            "mom": {"lookback": 1, "hold": 1, "threshold": 0.01},
        },
    )
    monkeypatch.setattr(demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 1]))
    monkeypatch.setattr(demo, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, -1]))
    monkeypatch.setattr(demo, "momentum", lambda prices, **kwargs: np.array([0, 1, 0]))
    monkeypatch.setattr(demo, "backtest", lambda prices, signal: fake_backtest_result())
    monkeypatch.setattr(demo.plt, "subplots", lambda *a, **kw: (object(), axes))
    monkeypatch.setattr(demo.plt, "tight_layout", lambda: None)
    monkeypatch.setattr(demo.plt, "savefig", lambda *a, **kw: None)
    monkeypatch.setattr(demo.plt, "close", lambda: None)
    monkeypatch.setattr(demo.os.path, "dirname", lambda path: str(tmp_path))

    demo.main()
    assert "All 3 strategies compared" in capsys.readouterr().out


def test_tradepro_demo_main_with_fake_engines(monkeypatch, capsys) -> None:
    """TradePro main covers success paths without running backtrader."""
    from energy_algorithms.application import tradepro_demo as demo

    monkeypatch.setattr(demo.os.path, "exists", lambda path: True)
    monkeypatch.setattr(demo, "run_backtrader_hod", lambda: {"Sharpe": 1.0, "Trades": 2})
    monkeypatch.setattr(demo, "run_backtrader_solar", lambda: {"Sharpe": 0.5, "Trades": 1})
    monkeypatch.setattr(
        demo,
        "run_openspace_simulation",
        lambda: (
            {
                "avg_mcp": 50.0,
                "min_mcp": 40.0,
                "max_mcp": 60.0,
                "total_welfare": 1000.0,
                "generator_profits": {"Solar": 10.0},
            },
            {"avg_mcp": 55.0, "generator_profits": {"Speculator": 20.0}},
        ),
    )

    demo.main()
    assert "VERDICT" in capsys.readouterr().out


def test_markets_demo_main_with_fake_market_components(monkeypatch, capsys, tmp_path) -> None:
    """Markets demo covers PCR, block order, stack, and FBMC reporting."""
    from energy_algorithms.application import markets_demo as demo

    class FakePCR:
        def __init__(self, zone: str) -> None:
            self.zone = zone

        def add_supply(self, *args) -> None:
            pass

        def add_demand(self, *args) -> None:
            pass

        def add_block(self, *args) -> None:
            pass

        def solve(self) -> dict:
            return {"status": "Optimal"}

        def report(self) -> None:
            print(f"report {self.zone}")

    block_result = {
        "status": "Optimal",
        "welfare": 100.0,
        "mcp": 42.0,
        "orders": {"blocks": {"B1": {"accepted": True}}},
    }
    fbmc_result = {
        "status": "Optimal",
        "welfare": 200.0,
        "zones": {
            "Hydro_North": {"supply_cleared_mw": 1.0, "demand_cleared_mw": 2.0, "net_position_mw": -1.0, "mcp": 10.0},
            "Gas_Center": {"supply_cleared_mw": 3.0, "demand_cleared_mw": 1.0, "net_position_mw": 2.0, "mcp": 20.0},
            "Diesel_South": {"supply_cleared_mw": 2.0, "demand_cleared_mw": 2.0, "net_position_mw": 0.0, "mcp": 30.0},
        },
        "branch_flows": [{"branch": "A", "flow_mw": 5.0, "ram_forward": 10.0, "utilization_pct": 50.0}],
    }

    monkeypatch.setattr(demo, "PCRModel", FakePCR)
    monkeypatch.setattr(demo, "run_all", lambda: [("case", block_result)])
    monkeypatch.setattr(demo, "run_exclusive", lambda: {"result": block_result, "recommendation": "Gas"})
    monkeypatch.setattr(demo, "demo_clearing", lambda: {"clearing_price": 50.0, "clearing_volume": 100.0})
    monkeypatch.setattr(demo, "plot_supply_demand_stack", lambda *args: None)
    monkeypatch.setattr(demo, "solve_fbmc", lambda *args: fbmc_result)
    monkeypatch.setattr(demo.os.path, "dirname", lambda path: str(tmp_path))

    demo.main()
    assert "Energy markets module complete" in capsys.readouterr().out


def test_live_backtest_demo_with_fake_strategy_stack(monkeypatch, capsys) -> None:
    """Live backtest demo covers parameter loops with synthetic small prices."""
    from energy_algorithms.application import live_backtest as demo

    monkeypatch.setattr(demo, "_load_or_fetch", lambda ticker: np.array([100.0, 101.0, 99.0, 102.0]))
    monkeypatch.setattr(demo, "momentum", lambda prices, **kwargs: np.array([0, 1, 1, 0]))
    monkeypatch.setattr(demo, "mean_reversion", lambda prices, **kwargs: np.array([0, -1, 0, 1]))
    monkeypatch.setattr(demo, "sma_crossover", lambda prices, **kwargs: np.array([0, 1, 0, 1]))
    monkeypatch.setattr(demo, "backtest", lambda prices, signal: fake_backtest_result(float(np.sum(signal))))

    result = demo.demo_live_backtest()
    assert set(result) == {"Momentum", "Mean Reversion", "SMA Crossover"}
    assert "Best risk-adjusted" in capsys.readouterr().out

