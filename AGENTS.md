# AGENTS.md — Energy Algorithms

**Repo:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio for Euphemia   Junior Optimization Engineer & energy/quant roles
**Design target:** Beat pomato, PyPSA, energy-py-linear in architecture, tests, and documentation

---

## Identity & Strategy

This repo is **GerryBerry's public portfolio** demonstrating optimization modeling,
energy market domain knowledge (Euphemia/PCR), and algorithmic trading.

The **markets module** (`domain/markets/`) is the hero piece — PCR social welfare,
FBMC with PTDF/RAM, block orders (linked + exclusive), multi-zone ATC coupling,
intraday order books. This differentiates it from generic quant repos.

**Target audiences:**
- **Euphemia  ** — Euphemia algorithm (Pan-European market coupling)
- **Industry** — Power market optimization, portfolio management
- **Quant finance** — Backtesting, risk metrics, signal strategies

**Competitor strategy:** Identify gaps in existing frameworks (pomato, PyPSA, energy-py-linear),
prioritize by impact (P1 > P2 > P3), implement with tests + docs simultaneously.

---

## Architecture: Hexagonal (Ports & Adapters)

```
Energy_Algorithms/
├── src/
│   └── energy_algorithms/          # Main package (pip-installable)
│       ├── domain/                 # ★ Pure business logic — NO I/O, NO solver imports
│       │   ├── __init__.py         #   Re-exports hooks, options from domain/
│       │   ├── hooks.py            #   Lifecycle: PRE_SOLVE / POST_SOLVE / POST_EXTRACT
│       │   ├── options.py          #   Global OPTIONS dict (get/set/reset)
│       │   ├── markets/            #   ★ HERO MODULE — PCR, FBMC, block orders, intraday
│       │   ├── optimization/       #   LP/MIP — UC, storage, assets, stochastic, invariants
│       │   └── trading/            #   Backtesting, risk metrics, strategies
│       ├── ports/                  # Abstract interfaces (ABCs / Protocols)
│       │   └── solver.py           #   SolverPort — domain depends on this, not PuLP
│       ├── adapters/               # Concrete implementations of ports
│       │   ├── pulp_solver.py      #   PuLPSolverAdapter(SolverPort) — wraps PuLP CBC solve()
│       │   ├── entsoe_client.py    #   ENTSO-E Transparency Platform REST client
│       │   ├── yfinance_fetcher.py #   Yahoo Finance data fetcher
│       │   ├── sqlite_store.py     #   SQLite persistence adapter
│       │   └── config.py           #   App config (API keys, ENTSOE_TOKEN)
│       ├── application/            # Use-case orchestrators — wires domain + adapters
│       │   ├── live_pipeline.py    #   ENTSO-E live data → PCR market clearing
│       │   ├── live_backtest.py    #   Live market data → backtest
│       │   └── *_demo.py           #   Entry-point demos for each domain
│       └── infrastructure/         # Backward-compat re-exports (canonical in domain/)
│           ├── hooks.py            #   Identical copy; domain/hooks.py is canonical
│           ├── options.py          #   Identical copy; domain/options.py is canonical
│           ├── metadata.py         #   Model introspection (VariableRegistry, ModelMetadata)
│           └── solver_config.py    #   Solver-agnostic factory (CBC, HiGHS, Gurobi, CPLEX)
├── tests/                          # One test file per module — mirrors src layout
├── knowledge/                      # Theory, Q&A, interview prep, competitor analysis
├── notebooks/                      # Jupyter walkthrough (24-cell Euphemia   interview tour)
├── scripts/                        # update_framework_metrics.sh
├── pyproject.toml                  # Package config (src layout, ruff, mypy, pytest)
├── conftest.py                     # CBC solver symlink for cross-platform compat
├── FRAMEWORK.md                    # Auto-updatable deep docs: 24KB, 518 lines
├── ITERATIONS.md                   # Iteration log (latest first)
├── AGENTS.md                       # This file
└── README.md                       # Portfolio intro + whitepaper + interview prep
```

### Layering Rules

1. **Domain** — stdlib + numpy + scipy + pulp only. **Never** imports adapters or application.
2. **Ports** — stdlib + typing only. Define contracts (ABCs, Protocols). Zero dependencies.
3. **Adapters** — implement ports. May import domain for type hints. **May do I/O.**
4. **Application** — orchestrates domain + ports + adapters. Entry points for use cases.
5. **Infrastructure** — backward-compat re-exports. New code imports from `domain/` directly.

---

## Critical Conventions (Distilled from 25+ Iterations)

### Code Style

- **`src` layout** — pip-installable at repo root: `pip install -e ".[dev]"`
- **Underscore dirs** — valid Python package names: `energy_algorithms`, `domain/markets`
- **Absolute imports only** — `from energy_algorithms.domain.markets import ...` — no `sys.path` hacks
- **`from __future__ import annotations`** — 1st line of every `.py` file (69 files verified)
- **Type hints** — all functions: parameters + return. Use `X | None` not `Optional[X]`. Standard library generics: `list[X]` not `List[X]`.
- **Ruff isort** — import order: stdlib → third-party → first-party. Run `ruff check --fix` before commits.
- **Docstrings** — NumPy-style (`Parameters` / `Returns` / `Raises` sections). Every public function.
- **`__all__`** — exported in every `__init__.py`. Names only (no docstrings in `__all__`).
- **No magic numbers** — named constants: `ACCEPTANCE_TOLERANCE = 0.001`
- **No bare `except:`** — always catch specific exceptions. `except Exception` if you must.
- **Conventional commits** — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `style:`

### Design Patterns

- **Solve chain** — Every optimization module follows: `formulate() → solve() → validate() → extract()`
- **SolverPort DI** — `solve_unit_commitment(..., solver: SolverPort | None = None)` — domain code receives solver via dependency injection, never imports PuLP directly
- **Asset pattern** — `Asset._constraints()`, `Asset._objective()`, `Asset._post_solve()` lifecycle hooks. `build_site()` assembles LP from asset list.
- **Physical invariants** — Post-solve: verify energy balance, SoC bounds, power limits via `assert_invariants()`
- **Known-optimal tests** — Every optimization has tests with known-correct output values (not just "solves without error")
- **Accessor pattern** — Assets expose `.variables`, `.results`, `.net_power` for clean post-solve extraction
- **Hook registry** — `register_hook(PRE_SOLVE | POST_SOLVE | POST_EXTRACT, fn)` — decoupled lifecycle extensions
- **Options dict** — `get_option('solver.time_limit')` — global, importable, testable
- **Graceful fallback** — ENTSO-E pipeline falls back to demo data when live fetch fails. Solver config falls back to CBC when HiGHS/Gurobi not installed.

### State Management

- **No module-level mutable state** (except OPTIONS dict which is intentional and tested)
- **Every test is independent** — no shared state, no test ordering dependencies
- **Seeds for reproducibility** — all stochastic tests use `random_seed` or `numpy.random.seed()`
- **Idempotent config** — `config.py` reads once; `ENTS`O_E_TOKEN` from environment or file

### Edge Cases (Must-Test)

| Domain | Edge Case | Where Tested |
|--------|-----------|-------------|
| PCR / Market clearing | Zero demand → zero trades | `test_pcr_model.py::test_no_trades_zero_demand` |
| PCR / Market clearing | All blocks rejected | `test_pcr_model.py::test_block_rejected` |
| FBMC | Zero RAM on all lines | `test_fbmc.py::test_zero_ram` |
| FBMC | Zero demand | `test_fbmc.py::test_zero_demand` |
| FBMC | Order invariance (swap leads) | `test_fbmc.py::test_order_invariance_symmetric` |
| UC binding | Min up/down at horizon edge | `test_optimization.py::test_uc_horizon_edge` |
| Storage | Full charge/discharge cycles | `test_assets.py::test_battery_full_cycle` |
| Storage | 0% initial SoC | `test_assets.py::test_battery_basic` |
| Stochastic | Zero renewable scenarios | `test_stochastic.py::test_zero_renewables` |
| Solver config | Unknown solver → fallback | `test_solver_config.py::test_unknown_solver_defaults` |
| LODF | All PTDF zero → zero LODF | `test_lodf.py` |
| GSK | Identical generators → flat = gmax | `test_gsk.py` |
| Intraday | Empty order book match | `test_energy_data.py` (part of intraday section) |
| Multi-day | Single day boundary | `test_multi_day.py::test_single_day` |

---

## Interview-Centric Design

**Principle:** Every decision should be explainable in a 45-minute interview.

1. **"Why PuLP not Gurobi?"** → PuLP is frictionless for open-source portfolios. We document tradeoffs (CBC vs Gurobi vs CPLEX) in README and solver_config.py.
2. **"Why hexagonal architecture?"** → Ports/adapters means we can swap solvers without touching domain logic. Demonstrated by `PuLPSolverAdapter` and `SolverPort`.
3. **"Why is FBMC better than ATC?"** → Flow-based captures loop flows, uses full network PTDF, enables 3× more cross-zonal capacity. Demonstrated by `fbmc.py` 3-zone loop flow demo.
4. **"How do you test optimization code?"** → Known-optimal values, property-based invariants, edge-case matrix. 232 tests covering all 18 modules.
5. **"Tell me about a bug you fixed."** → Surplus shading fix (rectangles → area-between-curves), MCP wasn't including block prices, min up/down at horizon edge, UC reserve/demand were conflated.

### Interview Checklist (Euphemia   & Industry)

**Markets:**
- ✅ PCR social welfare maximization with supply/demand curves
- ✅ Block orders: linked (same group binary) + exclusive (sum ≤ 1)
- ✅ FBMC flow-based coupling: PTDF constraints, RAM, loop flows
- ✅ Multi-zone ATC coupling (3-zone demo)
- ✅ Intraday continuous trading: order book, price-time priority, partial fills
- ✅ Multi-day coupling: storage carry-over between days

**Optimization:**
- ✅ Unit commitment MIP: min up/down, ramp rates, reserve, initial conditions, horizon-edge handling
- ✅ BESS storage LP: charge/discharge, SoC dynamics, efficiency, power limits
- ✅ Stochastic programming: Monte Carlo renewables, scenario UC, VSS + EVPI
- ✅ Transportation LP: supply/demand balance, arc capacity
- ✅ Portfolio optimization: mean-variance (scipy), max Sharpe, min variance
- ✅ Asset pattern: OneInterval lifecycle, build_site() assembly, SpillAsset feasibility

**Infrastructure:**
- ✅ Solver-agnostic: SolverPort ABC, PuLPSolverAdapter, get_solver() with fallback
- ✅ LODF contingency screening: PTDF→LODF, N-1 CBCO, 95% constraint reduction
- ✅ GSK strategies: flat, gmax, dynamic zonal→nodal mapping
- ✅ Hooks: PRE_SOLVE / POST_SOLVE / POST_EXTRACT lifecycle
- ✅ Options: centralized configuration dict
- ✅ Metadata: variable registry, model summary

**Engineering:**
- ✅ 232 passing tests (2 skipped for uninstalled solvers)
- ✅ CI/CD: GitHub Actions (3 Python versions), tests + demos
- ✅ Dockerfile: multi-stage, reproducible environment
- ✅ Knowledge base: 12 files, 3,610 lines across all domains
- ✅ FRAMEWORK.md: 24KB auto-updatable deep docs
- ✅ MIT License, badges, conventional commits, clean git history

---

## Commands

```bash
# Install
pip install -e ".[dev]"         # Dev + testing tools
pip install -e ".[live]"         # + requests for ENTSO-E live
pip install -e ".[docs]"        # + Sphinx for API docs

# Test
pytest tests/ -v                             # All tests
pytest tests/ -v -m "not slow and not pc"    # Fast tests only (Pi-friendly)
pytest tests/test_pcr_model.py -v            # Single file
pytest tests/ --cov=energy_algorithms        # Coverage report
pytest tests/ -v -k "stochastic"            # Keyword match

# Lint & Type Check
ruff check src/ tests/
ruff check --fix src/ tests/
mypy src/

# Demos
ea-markets            # Energy markets demo (PCR, FBMC, block orders)
ea-optimization       # LP/MIP optimization demo (UC, storage, portfolio)
ea-trading            # Trading backtest demo
ea-live               # ENTSO-E live pipeline (requires ENTSOE_TOKEN)

# Or direct:
python -m energy_algorithms.application.markets_demo
python -m energy_algorithms.application.live_pipeline
```

---

## Git Workflow

```bash
# 1. Pull latest
git checkout main && git pull

# 2. Branch (feature/fix/refactor/docs/test/chore)
git checkout -b feat/<description>

# 3. Verify before commit
pytest tests/ -v          # MUST pass
ruff check src/ tests/    # MUST be clean
mypy src/                  # MUST pass

# 4. Commit & push
git add -A
git commit -m "feat: <description>"
git push -u origin <branch>

# 5. Create PR (if contributing to main)
gh pr create --title "<type>: <description>" --body "## Summary..."
```

**SSH key:** `id_ed25519` is the account key. Run `ssh-add ~/.ssh/id_ed25519` if auth fails.

---

## Documentation Trilogy (Mandatory Per Iteration)

Every significant change updates these three files simultaneously:

1. **`README.md`** — User-facing: what changed, why, how it fits the portfolio story
2. **`ITERATIONS.md`** — Dev-facing: prepend new entry (date, time CEST, summary, files, test count)
3. **`FRAMEWORK.md`** — Technical deep-dive: run `scripts/update_framework_metrics.sh` to refresh

---

## What We've Learned (Don't Repeat These)

1. **Demand zero is not a no-op** — Zero demand scenarios produce valid (empty) solutions. Tests must verify this explicitly.
2. **Block orders at the marginal price** — A block at MCP should be accepted. Tests with exact MCP price verify this.
3. **Horizon-end constraints for UC** — Min up/down can't extend beyond the horizon. `min(remaining_hours, min_up)` guards this.
4. **Surplus is area between curves, not rectangles** — `numpy.trapz()` or integration, never `sum(p * q)`.
5. **Shared mutable state breaks tests** — Every test creates fresh model instances. `OPTIONS` dict is the only mutable global and has `reset_options()`.
6. **Solver CBC on cross-platform** — `shutil.which("cbc")` + symlink trick in conftest.py avoids hardcoded paths.
7. **Type-hint ALL the things** — `from __future__ import annotations` + `X | None` syntax. Catches real bugs (e.g., passing `str` instead of `int` to a parameter).
8. **Inverses must verify** — `LODF[i,j]*LODF[j,i]` should approximate identity. PTDF row sums ≈ 0. Test these.
9. **Known-optimal > "solves without error"** — Every optimization test should have a pre-computed correct answer.
10. **Backward compat during refactors** — When moving code, keep re-export stubs in the old location so the working tree isn't broken mid-iteration.

---

## Competitor Scorecard

| Capability | pomato | PyPSA | energy-py-linear | This Repo |
|---|---|---|---|---|
| FBMC (PTDF + RAM) | ✅ | ✅ | ❌ | ✅ |
| LODF impact screening | ✅ (98% reduction) | ❌ | ❌ | ✅ (95%) |
| GSK strategies | ✅ (Clarkson) | ❌ | ❌ | ✅ (flat/gmax/dynamic) |
| OneInterval asset pattern | ❌ | ✅ | ✅ | ✅ |
| Known-optimal tests | ❌ | ❌ | ✅ | ✅ |
| Physical invariants | ❌ | ❌ | ✅ | ✅ |
| Hexagonal architecture | ❌ | ❌ | ❌ | ✅ |
| 200+ passing tests | ❌ (~25) | ✅ (60+) | ❌ (~30) | ✅ (232) |
| Interview-focused docs | ❌ | ❌ | ❌ | ✅ |
| Stochastic + EVPI | ❌ | ✅ | ❌ | ✅ |
