# Energy Algorithms

> **Note:** The original long-form README (with the full Euphemia   + Industry interview Q&A, Euphemia algorithm walkthrough, and known-limitations table) is preserved at [`docs/README_LEGACY.md`](docs/README_LEGACY.md) for reference. The interview Q&A is now in [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md).

[![Tests](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml/badge.svg)](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Energy domain optimisation portfolio** — social-welfare market clearing (PCR/Euphemia), BESS storage + ancillary services (FCR/aFRR), unit commitment, backtesting. Hexagonal architecture (ports/adapters). Built for **Euphemia  ** (Junior Optimization Engineer) and **Industry Belgium** (Algorithmic Trader, Short-Term Power, Uccle).

> **Why this repo exists:** I want to show, not tell. Each module corresponds to a JD bullet — `domain/markets/pcr_model.py` is "translates Euphemia into a working LP", `domain/optimization/ancillary.py` is "BESS joint FCR+aFRR bidding", `adapters/entsoe_client.py` is "reliable market data pipeline".

---

## What it does — at a glance

| Capability | Module | Why it matters |
|---|---|---|
| **Social welfare clearing** (PCR / Euphemia-style) | `domain/markets/pcr_model.py` | The algorithm Euphemia   maintains. LP with binary block orders, MCP, surpluses |
| **Flow-based market coupling** (FBMC) | `domain/markets/fbmc.py`, `lodf_utils.py` | Real European coupling: PTDF × net position ≤ RAM |
| **Multi-zone ATC coupling** | `domain/markets/multi_zone.py` | Cross-border flows: BE↔FR↔DE↔NL |
| **BESS + FCR + aFRR joint bidding** | `domain/optimization/ancillary.py` ⭐ new | INDUSTRY: ancillary services revenue stacking |
| **BESS energy arbitrage** | `domain/optimization/storage.py` | INDUSTRY: hour-of-day, +€143/MWh spread documented |
| **Unit commitment** (MIP) | `domain/optimization/scheduling.py` | Euphemia  : min up/down, ramps, reserve margin |
| **Continuous intraday order book** | `domain/markets/intraday.py` | INDUSTRY: price-time priority, cross-border |
| **7-metric backtesting engine** | `domain/trading/backtest_engine.py` | INDUSTRY: Sharpe, Sortino, VaR95/99, Calmar, Kelly, MaxDD, CVaR |
| **3 signal strategies** | `domain/trading/` | INDUSTRY: hour-of-day, solar duck, calendar spread |
| **ENTSO-E live data + cache** | `adapters/entsoe_client.py` | INDUSTRY: 26 days of real Belgian data |
| **ML experiment tracking** | `infrastructure/experiment_tracker.py` | INDUSTRY: track signal research runs in SQLite |
| **Solver-agnostic core** | `ports/solver.py`, `infrastructure/solver_config.py` | All 11 domain files route through `solve_model()` — swap CBC↔HiGHS↔Gurobi by config |

**578 tests passing, 92.55% coverage, 90% gate enforced in CI.** 3 Python versions (3.11/3.12/3.13).

---

## Quick start

```bash
git clone git@github.com:GerasimosG/Energy_Algorithms.git
cd Energy_Algorithms
pip install -e ".[dev]"

# Showcase demos
python -m energy_algorithms.application.markets_demo        # PCR, block orders, FBMC
python -m energy_algorithms.application.optimization_demo   # BESS, UC, FCR+aFRR
python -m energy_algorithms.application.trading_demo        # Backtesting, signals
python -m energy_algorithms.application.industry_demo          # INDUSTRY: 26-day Belgian data
python -m energy_algorithms.application.energy_data_demo    # ENTSO-E pipeline

# Tests
pytest tests/ -v                                            # 578 tests
pytest tests/ --cov=energy_algorithms --cov-fail-under=90   # coverage gate
```

CLIs after install: `ea-markets`, `ea-optimization`, `ea-trading`, `ea-live`, `ea-experiments`.

---

## Architecture — hexagonal, solver-agnostic

```
src/energy_algorithms/
├── domain/                ★ pure business logic — no I/O, no solver hardcoding
│   ├── markets/           PCR, FBMC, block orders, intraday, multi-zone
│   ├── optimization/      UC, BESS, ancillary, portfolio, stochastic
│   └── trading/           backtesting, signals, risk metrics
├── ports/                 SolverPort — domain depends on this ABC, not on PuLP
├── adapters/              pulp_solver, entsoe_client, sqlite_store, bt_feeds
├── application/           use-case demos (markets, optimization, trading, industry)
└── infrastructure/        solver_config, experiment_tracker, metadata
```

**Why this matters:** every LP/MIP in the codebase is a PuLP problem that goes through `solve_model()`. Swapping solvers is a one-line config. **All 11 domain files route through the SolverPort.** That's the cleanest "production-grade" signal a portfolio can show.

---

## Microsservices / infrastructure shipped

| Service | Module | Status |
|---|---|---|
| **Solver service** | `infrastructure/solver_config.py` | ✅ All 11 domain files route through SolverPort |
| **ENTSO-E data caching** | `adapters/entsoe_client.py` | ✅ JSON disk cache with TTL, auto-disabled under pytest |
| **ML experiment tracker** | `infrastructure/experiment_tracker.py` | ✅ SQLite + CLI (`ea-experiments list/show/compare/export`) |
| **Backtesting engine** | `domain/trading/backtest_engine.py` | ✅ 7 risk metrics, walk-forward, signal-shift anti-look-ahead |
| **Coupling utilities** | `domain/markets/coupling_utils.py` | ✅ Shared by 4 market coupling modules |

The first three are the **production services** a trading desk or optimisation team would actually stand up. They sit behind a `port` (hexagonal) so swapping the implementation (e.g. MLflow for the tracker) is a 1-file change.

---

## Documentation

- **[`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md)** — full Euphemia   + Industry interview Q&A, edge cases, "exceptional" answers (50+ questions)
- **[`docs/BENCHMARK_REPORT.md`](docs/BENCHMARK_REPORT.md)** — comparison vs PyPSA / POMATO / energy-py-linear with 4 plots
- **[`knowledge/`](knowledge/)** — 12-file curriculum: theory, Q&A, market coupling, UC, storage, backtesting, ENTSO-E
- **[`ITERATIONS.md`](ITERATIONS.md)** — development history (latest first)
- **[`FRAMEWORK.md`](FRAMEWORK.md)** — deep architecture + iteration metrics
- **[`AGENTS.md`](AGENTS.md)** — repo conventions for AI agents

---

## Test status

```bash
pytest tests/ -v --tb=short
# ============= 578 passed, 3 skipped, 0 failed in ~50s ==============
```

```bash
PYTHONPATH="$(pwd)/src" python -m coverage report
# Required test coverage of 90% reached. Total coverage: 92.55%
```

RAM-bounded coverage loop is documented in `AGENTS.md` for Pi/laptop-safe runs.

---

## Honest scope

| Built | Not built (and how I'd address in interview) |
|---|---|
| Day-ahead (PCR/FBMC) | mFRR bidding — TSO-specific rules, LP with reserve constraints, would extend `ancillary.py` |
| BESS arbitrage | Real-time telemetry — would add MQTT consumer as new adapter, with pre-approved fallback ramp schedule |
| FCR (symmetric) + aFRR (capacity-only) | Wind/solar stochastic scenarios — already have `stochastic.py` with VSS/EVPI; would add ECMWF ensemble adapter |
| Backtesting (7 risk metrics) | Live execution simulator — would add a "shadow mode" wrapper that runs alongside the trader |
| ENTSO-E data + cache | Production monitoring dashboards — would add Prometheus metrics (P&L, fills, API latency) + Grafana |
| CBC + HiGHS solvers (config) | Gurobi/CPLEX at scale — config-stubs exist; presolve tuning is the gap |

The list above is real. I'd rather be honest about it than pretend otherwise.

---

## References

- [EUPHEMIA Public Description](https://www.epexspot.com/en/euphemia) — PCR market coupling
- [ENTSO-E SAFA Appendix A](https://www.entsoe.eu/) — ancillary services definitions
- [Elia Ancillary Services](https://www.elia.be/) — Belgian market design
- [Kiesel & Paraschiv (2021)](https://doi.org/) — value of liquidity in intraday reserve markets

## Author

Gerasimos (Gerry) Giachos — built for **Euphemia  ** (Junior Optimization Engineer) and **Industry Belgium** (Algorithmic Trader, Short-Term Power, Uccle).
