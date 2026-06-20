# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-20

### Added
- Interactive Plotly dashboard (`scripts/generate_dashboard.py` → `docs/dashboard.html`): six linked
  panels (price heatmap, price-duration curve, PCR model vs market, social welfare, **live BESS
  dispatch** running the real `solve_storage`, hour-of-day strategy), standalone via Plotly CDN.
- Reproducible committed sample dataset under `data/` (`sample_entsoe_prices.csv`,
  `sample_entsoe_summary.csv`, `sample_bt_hourly.csv`, `README.md`) + shared resolver
  `scripts/_viz_data.py`, so every figure and the dashboard reproduce from a fresh clone.
- Shared visual identity `scripts/_viz_theme.py` (one palette/template across matplotlib + Plotly).
- `tests/test_dashboard.py` — 8 smoke tests for the dashboard panels and HTML output.
- `plotly` added to the `dev` extra plus a new `viz` extra.
- README front-page "Interactive dashboard" section; refreshed `FRAMEWORK.md`.

### Changed
- `scripts/generate_figures.py` refactored onto `_viz_data`/`_viz_theme`; fig4 corrected to show
  fuel marginal cost vs CO₂ price with the coal→gas switching point.
- `infrastructure/solver_config.py`: the default `PuLPSolverAdapter` wiring is now an explicit
  module-top-level import (was a hidden lazy in-function import); verified no import cycle.
- README architecture narrative corrected to the honest version (the domain builds PuLP models and
  routes solving through `solve_model()` → `SolverPort`).

### Fixed
- `domain/optimization/storage.py` and `domain/markets/gsk.py`: `from __future__ import annotations`
  was trapped inside the module docstring (inert) — moved to a real statement after the docstring.
- README: "Microsservices" → "Microservices"; test/coverage figures updated (600 tests, 92.63%).
- `scripts/update_framework_metrics.sh`: removed a hardcoded developer-machine Python path; now
  resolves the interpreter portably via `command -v`.

## [0.4.1] - 2026-06-11

### Fixed
- pyproject.toml version bumped to 0.4.0 (was 0.3.0 — mismatch with CHANGELOG)
- Dockerfile: replaced obsolete module paths (`energy_markets/`, etc.) with `src/` layout
- Dockerfile: added `pip install -e .` step so imports resolve at runtime
- CI: lint check now includes `scripts/` directory
- scripts/: fixed 6 ruff lint errors (duplicate variable, unsorted imports, unused import/F-string)
- docs/BENCHMARK_REPORT.md: corrected mypy status from ✅ to 🟡 (60 pre-existing errors)
- Added CODE_OF_CONDUCT.md and SECURITY.md for public repo professionalism

## [0.4.0] - 2026-06-05

### Added
- 4 benchmark figures for README (price profiles, daily trends, HOD P&L, CO₂ impact)
- `scripts/generate_figures.py` — standalone figure generator from CSV data

### Fixed
- README benchmarks section now displays actual figures instead of broken image placeholders

## [0.3.0] - 2026-04-30

### Added
- Multi-day coupling (storage carry-over)
- Stochastic programming with VSS + EVPI
- ENTSO-E live pipeline with Docker
- Knowledge base: 12 files, 3,610 lines
- All P1/P2/P3 competitor gaps implemented
- FBMC flow-based coupling
- Framework documentation (FRAMEWORK.md, 24KB)
- BESS storage optimization (100MWh/25MW battery)
- Intraday trading simulation with order book matching
- ENTSO-E data pipeline (client, XML parsing, 27 EU zones)
- Demo data fallback for all pipelines
- Jupyter notebook walkthrough (24 cells)
- LODF impact screening (N-1 contingency CBCO reduction)
- GSK strategies (flat, gmax, dynamic)
- OneInterval asset pattern (Asset, BatteryAsset, GeneratorAsset, SpillAsset)
- Known-optimal tests (13 battery lifecycle, build site)
- Physical invariant validation (energy balance, SoC bounds)
- Accessor pattern (assets expose .variables, .results, .net_power)
- Hook registry (PRE_SOLVE / POST_SOLVE / POST_EXTRACT)
- Solver-agnostic config (CBC default, HiGHS/Gurobi/CPLEX fallback)
- Centralized options dict (get/set/reset)
- Descriptive metadata (VariableRegistry, ModelMetadata)
- Spill asset for LP feasibility guarantee
- GitHub Actions CI workflow (Python 3.11/3.12/3.13 matrix)
-  interview prep guide
- Multi-zone ATC coupling (3-zone demo)
- Enterprise-grade README with whitepaper, badges, architecture

### Changed
- Hexagonal architecture (ports/adapters)
- 10 architecture violations fixed
- 106 ruff auto-fixes applied
- AGENTS.md comprehensive rewrite (25+ iterations distilled)
- PCR model: surplus shading uses area-between-curves (was rectangles)
- PCR model: `group` parameter for block orders, linked/exclusive blocks
- PCR model: energy balance `>=` → `==`, MCP includes block prices
- Block orders rewritten with group mechanism
- Unit commitment: split reserve from demand, horizon-end min up/down
- All `__init__.py` populated with `__all__` exports and docstrings
- Demo scripts: status check before report(), updated for new APIs
- README overhaul with badges, architecture diagram, performance metrics
- Model config set to `deepseek-v4-pro` on `opencode-go`
- pyproject.toml: added `energy_data*` to package includes

### Fixed
- CI: 'test' extra → 'dev' in workflow
- 47 E402 module-level import issues
- Duplicate hooks/options in infrastructure/
- 5 critical/high bugs (portfolio risk, MCP, trade log, store counter, Sortino)
- Demo script: status check before `report()` — M2 fixed
- Surplus shading: rectangles → area-between-curves — H3 fixed
- All `__init__.py`: populated with `__all__` and docstrings — M3 fixed
- 52 lint issues documented (E402, E741, F841, UP035) — deferred
- Empty model handling in zero-supply/zero-demand edge cases

## [0.2.0] - 2026-04-29

### Added
- PCR social welfare maximization with block orders (linked + exclusive)
- Multi-zone ATC coupling (LP with inter-zonal flow constraints)
- Unit commitment with 8 constraint types (min up/down, ramp, reserve)
- Portfolio optimization (LP + SciPy SLSQP variants)
- Transportation problem (LP)
- Backtesting engine with 7 risk metrics (Sharpe, Sortino, Calmar, etc.)
- Momentum strategy with parameterized threshold
- Mean reversion strategy
- SMA crossover strategy
- Market data fetching (Yahoo Finance, CSV, SQLite)
- AGENTS.md with issue tracker and  readiness checklist
- Comprehensive test suite (16+ tests covering PCR, blocks, backtester)
- pyproject.toml for pip-installable package

### Changed
- Major overhaul: PCR model fixes, UC fixes, test infrastructure
- PCR model: binary variable sharing for linked blocks
- Scheduling: init_status/init_uptime/init_downtime parameters
- Energy balance added to all markets

### Fixed
- 10 bugs (5 critical, 3 high, 2 medium)
- Block order exclusive comparison uses identical supply curves
- Horizon-edge min up/down constraints

## [0.1.0] - 2026-04-29

### Added
- Initial build of full optimization portfolio
- Energy markets module (PCR, block orders)
- LP optimization module (transportation, portfolio, UC)
- Backtester with metrics engine
- Trading strategies (momentum, mean reversion, SMA crossover)
- Market data adapters (Yahoo Finance, SQLite)
- Docker setup with multi-stage build
- MIT License
- Basic README

### Notes
- Repository initially named `optimization-portfolio`, later renamed to `Energy_Algorithms`
