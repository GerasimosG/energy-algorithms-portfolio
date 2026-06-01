"""Application layer — use-case orchestrators.

Wires domain logic through ports and adapters
to fulfil end-to-end use cases (market clearing,
unit commitment dispatch, live ENTSO-E pipeline, backtesting).
"""
from __future__ import annotations

from energy_algorithms.application.european_coupling import main as european_main
from energy_algorithms.application.live_backtest import demo_live_backtest
from energy_algorithms.application.live_pipeline import demo_live_pipeline
from energy_algorithms.application.markets_demo import main as markets_main
from energy_algorithms.application.optimization_demo import main as optimization_main
from energy_algorithms.application.trading_demo import main as trading_main

__all__ = [
    "demo_live_pipeline",
    "european_main",
    "markets_main",
    "optimization_main",
    "trading_main",
    "demo_live_backtest",
]
