# ITERATIONS — Energy Algorithms

## 2026-04-30 17:30 CEST — AGENTS.md overhaul + CI fix + ruff auto-cleanup

**What changed:**
- **📝 AGENTS.md** — Complete rewrite distilling all learnings from 25+ iterations:
  - Architecture diagram matching current hexagonal layout (with backward-compat infra/ layer)
  - Critical conventions: 13 design principles, 6 design patterns, 5 state management rules
  - Edge-case matrix: 14 must-test scenarios with exact test locations
  - Interview checklist: 22 validated items across 5 categories — all ✅
  - Rote-learned lessons: 10 concrete "don't repeat this" items from real bug fixes
  - Competitor scorecard: pomato, PyPSA, energy-py-linear mapped vs this repo
  - Documentation trilogy (README + ITERATIONS + FRAMEWORK.md) codified as mandatory
- **🐛 CI fix** — Workflow was installing `.[test]` but pyproject.toml defines `dev`, not `test`. Fixed to `.[dev]`.
- **🧹 Ruff auto-cleanup** — 106 auto-fixes applied across all 62 .py files (import ordering, unused imports, f-strings without placeholders, `Optional[X]` → `X | None`, `typing` → `collections.abc`)
- **52 remaining lint issues** (E402 in demo scripts, E741 `l` variable name, F841 unused vars, UP035) — documented but deferred

**Tests:** 232 passing, 2 skipped (unchanged)
**Git:** Pushed to main (`d40e199`)
**Fixes:** 1 CI bug, 106 code style issues

**What changed:**
- **📆 Multi-day coupling** (`energy_markets/multi_day.py`) — Extends FBMC to multiple days with storage carry-over. Battery SoC from day D transfers to day D+1. 8 tests.
- **🎲 Renewable uncertainty** (`lp_optimization/stochastic.py`) — Monte Carlo wind/solar scenario generation. Scenario UC solver. VSS + EVPI computation. 11 tests.
- **🔴 ENTSO-E live pipeline** (`energy_data/live_demo.py`) — Fetches real Belgian market data via stored API key. PCR model integrates real prices. Graceful fallback to demo data. 13 tests.
- **🐳 Dockerfile** — Multi-stage build (builder + runtime). Reproducible environment. Installs all deps from pyproject.toml + optional HiGHS.
- **📦 .dockerignore** — Excludes venv, pycache, git, IDE files.

**New files:** `energy_markets/multi_day.py`, `lp_optimization/stochastic.py`, `energy_data/live_demo.py`, `Dockerfile`, `.dockerignore`, `tests/test_multi_day.py`, `tests/test_stochastic.py`, `tests/test_live_demo.py`
**Tests:** 185 → 217 (+32)
**Git:** Pending push

## 2026-04-30 10:15 CEST — Knowledge base: 12 files, 3,610 lines across all domains

**What changed:**
- **📚 `knowledge/` directory** — Comprehensive theory, Q&A, and self-assessment curriculum:
  - `market-coupling.md` (720L): PCR, Euphemia, ATC vs FBMC, loop flows, non-convexities
  - `fbmc-ptdf.md` (1,087L): PTDF deep dive, LODF computation, CBCO screening, GSK strategies
  - `block-orders.md` (218L): Linked, exclusive, MCP vs IP pricing, make-whole payments
  - `optimization-theory.md` (263L): LP/MIP, simplex, duality, branch and bound, solver internals
  - `unit-commitment.md` (184L): 8 constraints, initial conditions, horizon-end, ramp/capacity coupling
  - `storage-optimization.md` (174L): SoC dynamics, efficiency trap, OneInterval pattern, SpillAsset
  - `backtesting.md` (163L): Look-ahead bias, 7 risk metrics, vectorized engine, Kelly criterion
  - `entsoe.md` (159L): Transparency Platform, bidding zones, PSR types, pipeline architecture
  - `competitor-analysis.md` (156L): pomato, PyPSA, energy-py-linear gap analysis with resolution status
  - `interview-qa.md` (216L): 20 questions with GOOD and EXCEPTIONAL answers for Euphemia   and Industry
  - `quiz.md` (199L): 50 questions across 8 domains with full answer key
  - `README.md` (71L): Index, how-to-use guide, quick reference

**Git:** Pushed to `GerasimosG/Energy_Algorithms` (private) (`decb94e`)

## 2026-04-30 09:15 CEST — ALL P1/P2/P3 competitor gaps implemented + production polish

**What changed:**
- **🔴 P1: LODF impact screening** (`energy_markets/lodf_utils.py`) — LODF matrix computation from PTDF, N-1 contingency CBCO screening. Reduces security constraints by up to 95% (pomato technique).
- **🔴 P1: GSK strategies** (`energy_markets/gsk.py`) — Flat, gmax, and dynamic Generation Shift Key strategies for zonal→nodal mapping. Demo compares all three.
- **🔴 P1: OneInterval asset pattern** (`lp_optimization/assets.py`) — Asset base class with 3 lifecycle hooks (_constraints, _objective, _post_solve). BatteryAsset, GeneratorAsset, SpillAsset. build_site() assembles LP.
- **🟡 P2: Known-optimal tests** — 13 battery lifecycle tests verify charge/discharge logic, SoC bounds, energy balance. Build site tests verify multi-asset dispatch.
- **🟡 P2: Physical invariant validation** (`lp_optimization/invariants.py`) — Energy balance, SoC bounds, power limit checkers. assert_invariants() runs battery post-solve.
- **🟡 P2: Accessor pattern** — All assets expose .variables, .results, .net_power for clean post-solve extraction.
- **🟡 P2: Hook registry** (`lp_optimization/hooks.py`) — PRE_SOLVE/POST_SOLVE/POST_EXTRACT hooks with register/run/clear. Applied to UC demo.
- **🟢 P3: Solver-agnostic config** (`lp_optimization/solver_config.py`) — get_solver() with CBC default, HiGHS/Gurobi/CPLEX support with graceful fallback.
- **🟢 P3: Centralized options** (`lp_optimization/options.py`) — Global OPTIONS dict with get/set/reset. Controls solver cfg, tolerances, verbosity.
- **🟢 P3: Descriptive metadata** (`lp_optimization/metadata.py`) — VariableRegistry, ModelMetadata, get_model_summary() for LP introspection.
- **🟢 P3: Spill asset** — Penalty-cost slack supply guaranteeing LP feasibility (energy-py-linear pattern).
- **🟢 P3: extra_functionality hook** — Applied to scheduling.py demonstrating pre/post-solve hook injection.

**New files:** `lp_optimization/assets.py`, `lp_optimization/invariants.py`, `lp_optimization/hooks.py`, `lp_optimization/options.py`, `lp_optimization/metadata.py`, `lp_optimization/solver_config.py`, `energy_markets/lodf_utils.py`, `energy_markets/gsk.py`, `tests/test_assets.py`, `tests/test_invariants.py`, `tests/test_hooks.py`, `tests/test_options.py`, `tests/test_metadata.py`, `tests/test_solver_config.py`, `tests/test_lodf.py`, `tests/test_gsk.py`
**Tests:** 51 → 185 (+134!)
**Git:** Pending push

## 2026-04-30 08:45 CEST — P1: FBMC flow-based coupling + ENTSO-E API config

**What changed:**
- **📡 FBMC flow-based coupling** (`energy_markets/fbmc.py`) — New module implementing Flow-Based Market Coupling with PTDF matrix constraints. The real algorithm Euphemia uses for Pan-European market coupling (upgrade from ATC):
  - PTDF-based flow constraints: `flow_l = Σ(PTDF[l,n] · net_position[n])` constrained by RAM
  - Captures loop flows that ATC cannot model
  - 3-zone triangle demo shows binding Hydro_Gas line (100%) and loop flow on Hydro_Diesel
  - Input validation: PTDF row sum ≈ 0, shape matching, non-negative RAM
  - Follows standard solve chain (formulate → solve → validate → extract)
- **🔑 ENTSO-E API key** (`energy_data/config.py`) — Stored API token for live data access. Exported via `energy_data.__init__`.
- **📋 11 new FBMC tests** — 2-zone simple/binding, 3-zone loop/binding, zero RAM, zero demand, order invariance, 5 validation edge cases
- **demo.py** — Section 6 now includes FBMC demo with formatted output

**New files:** `energy_markets/fbmc.py`, `energy_data/config.py`, `tests/test_fbmc.py`
**Tests:** 40 → 51 (+11)
**Git:** Pushed to `GerasimosG/Energy_Algorithms` (private) (`76fb9b9`)

## 2026-04-30 01:40 CEST — Framework documentation, competitor gap analysis, auto-update

**What changed:**
- **📖 FRAMEWORK.md** (350+ lines, 24KB) — Comprehensive framework documentation:
  - Architecture overview with ASCII diagram
  - Data flow and solve pipeline with timing benchmarks (measured on rPi 4)
  - Module deep-dives with mathematical formulations for all 11 modules
  - Competitor comparison tables vs pomato, PyPSA, energy-py-linear
  - Benchmark methodology with competitor numbers to beat (pomato's 98% CBCO reduction, PyPSA's 60+ tests)
  - Edge case documentation across all modules
  - Iteration history table (auto-updatable)
  - Extension guide for adding new modules
- **🤖 Auto-update script** (`scripts/update_framework_metrics.sh`):
  - Counts modules, files, lines, tests
  - Runs benchmarks on all solve functions
  - Regenerates FRAMEWORK.md metrics header
  - Can be used as pre-commit hook
- **📋 Competitor gap analysis** (FRAMEWORK.md section):
  - pomato: P1=FBMC coupling + LODF impact screening, P2=Clarkson + GSK strategies
  - energy-py-linear: P1=OneInterval pattern, P2=known-optimal tests + invariant validation
  - PyPSA: P2=accessor pattern, P3=solver-agnostic config + extra_functionality hook
- **README** updated with Framework Documentation section linking to FRAMEWORK.md

**New files:** `FRAMEWORK.md`, `scripts/update_framework_metrics.sh`
**Git:** Pushed to `GerasimosG/Energy_Algorithms` (private)

## 2026-04-30 00:15 CEST — 5 pending items implemented: BESS, intraday, ENTSO-E, type hints, notebook

**What changed:**
- **🔋 BESS storage optimization** (`lp_optimization/storage.py`): Battery energy storage LP maximizing revenue over 24h price forecast. Charge at low prices, discharge at high. SoC constraints, efficiency losses, power limits. Demo: 100MWh/25MW battery, €7,773 revenue.
- **⏱️ Intraday trading simulation** (`energy_markets/intraday.py`): Continuous intraday electricity market with order book matching. Price-time priority matching, partial fills, VWAP. OrderBook class with `add()`, `_match()`, `get_depth()`. Demo: 20 orders, 16 trades, 110 MW volume.
- **📡 ENTSO-E data pipeline** (`energy_data/`): Full ENTSO-E Transparency Platform REST API client (`EntsoeClient`). XML parsing for day-ahead prices, generation mix, load forecasts. Supports all 27 EU bidding zones. Demo with realistic Belgian market data (no API key needed). PSR type mapping for 20 generation types.
- **🔤 Type hints**: All functions across all modules confirmed to have complete parameter and return type annotations (no changes needed — already well-typed).
- **📓 Notebook walkthrough** (`notebooks/walkthrough.ipynb`): 24-cell Jupyter notebook demonstrating all modules. Setup, energy markets (PCR, blocks, multi-zone, intraday), LP/MIP (transportation, portfolio, UC, BESS), backtesting, ENTSO-E data. Ready for Euphemia   interview review.
- **pyproject.toml**: Added `energy_data*` to package includes.

**New files:** `lp_optimization/storage.py`, `energy_markets/intraday.py`, `energy_data/` (3 files), `notebooks/walkthrough.ipynb`, `tests/test_energy_data.py`
**Tests:** 26 → 40 (+14: 4 storage + 5 intraday + 5 energy_data)
**Git:** Pending push

## 2026-04-29 23:55 CEST — Final polish: LICENSE, README whitepaper expansion, checklist cleanup

**What changed:**
- **LICENSE** — Added MIT license file (README badge now resolves correctly)
- **README expansion** — Rewrote "Energy Markets Module" section as mini-whitepaper:
  - Mathematical problem formulation (objective function, constraints, notation)
  - Algorithm walkthrough (5-step clearing process)
  - Implementation → Real Euphemia mapping table with gap analysis
  - "Why This Matters for Euphemia  " section with domain fluency, MIP competence, gap honesty
  - Cross-reference to `EUPHEMIA_INTERVIEW.md`
- **AGENTS.md** — Updated Euphemia   Interview Readiness Checklist: all items now ✅, added LICENSE entry, corrected test count (16 → 26), stale CI/CD and whitepaper items resolved

**Tests:** 26/26 passing
**Git:** Pushed to `GerasimosG/Energy_Algorithms` (private)

## 2026-04-29 23:30 CEST — Re-audit + Public repo research + Major polish

**What changed:**
- **📊 Public repo research** — Studied PyPSA (1965★) and POMATO for best practices:
  - Badges: CI, Python version, license in README
  - Module-level `__init__.py` with `__all__` exports
  - NumPy-style docstrings with Parameters/Returns sections
  - GitHub Actions CI workflow (test.yml)
  - Reference to academic publications and related tools
  - Known limitations documented transparently

- **🔧 Critical fixes applied:**
  - `market_clearing.py`: Surplus shading now uses area-between-curves (was rectangles) — H3 fixed
  - `demo.py`: Status check before `report()` — M2 fixed
  - All `__init__.py`: Populated with `__all__` exports and docstrings — M3 fixed

- **🌍 Multi-zone coupling** (`energy_markets/multi_zone.py`):
  - LP with ATC-constrained inter-zonal flows
  - 3-zone demo: cheap North exports → expensive South imports
  - Directly relevant to Euphemia's 25+ zone coupling

- **📝 Euphemia   interview prep** (`energy_markets/EUPHEMIA_INTERVIEW.md`):
  - Euphemia concept mapping (social welfare, block orders, IP pricing, PUN)
  - Interview question bank with answer points
  - Known limitations documented for interview transparency

- **🧪 Tests expanded:** 16 → 26 tests
  - New `tests/test_optimization.py`: transportation (3), portfolio (3), UC (4)
  - All 26 tests passing

- **📋 README overhaul:**
  - Badges (CI, Python versions, license)
  - Architecture diagram with file listing
  - Performance metrics table
  - Known limitations section
  - References to PyPSA and POMATO
  - Private status notice

- **⚙️ CI workflow** (`.github/workflows/test.yml`):
  - Python 3.11, 3.12, 3.13 matrix
  - Tests + demo verification steps

**Audit findings:** 3 remaining issues fixed (H3, M2, M3), 2 low-prio remain (L2 tolerance, L3 type hints)
**Tests:** 26 passing (+10 from previous)
**Git:** Pending push to `GerasimosG/Energy_Algorithms` (private)

## 2026-04-29 22:00 CEST — Major overhaul: PCR fixes, UC fixes, tests, polish

**What changed:**
- **energy_markets/pcr_model.py** — Added `group` parameter to block orders. Linked blocks (same group) share binary values. Exclusive blocks (`excl_*`) use `sum <= 1`. MCP now includes block prices. Energy balance changed from `>=` to `==`.
- **energy_markets/block_orders.py** — Rewritten to use group mechanism. Exclusive comparison uses identical supply curves.
- **energy_markets/demo.py** — Updated for new API.
- **lp_optimization/scheduling.py** — Split reserve from demand (separate constraints), added `init_status`/`init_uptime`/`init_downtime` parameters, fixed horizon-end min up/down.
- **tests/** — Added 16 pytest tests covering PCR model (clearing, blocks, groups, edge cases) and backtester (metrics, engine).
- **pyproject.toml** — Added for pip-installable package.
- **strategies/momentum.py** — Threshold now parameterized.
- **AGENTS.md** — Updated with full status.
- **Model config** — Set `model.default: deepseek-v4-pro` on `opencode-go`.

**Bugs fixed:** 10 (5 critical, 3 high, 2 medium)
**Tests added:** 16 (all passing)
**Git:** Pushed to `GerasimosG/Energy_Algorithms` (private)

## 2026-04-29 20:00 CEST — Code audit + 5 critical bug fixes

- 5 critical/high bugs fixed (portfolio risk, MCP, trade log, store counter, Sortino)
- AGENTS.md created with issue tracker
- All modules verified working

## 2026-04-29 19:30 CEST — Initial build

- Full optimization portfolio built from scratch
- energy_markets, lp_optimization, backtester, strategies, market_data
- Pushed to GerasimosG/optimization-portfolio (later renamed to Energy_Algorithms)
