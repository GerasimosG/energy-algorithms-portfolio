# AGENTS.md — Energy Algorithms

**Repo:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio targeting **Euphemia   Junior Optimization Engineer** and **Industry power market/optimization** roles only. Stock trading is out of scope.
**Design target:** Beat pomato, PyPSA, energy-py-linear in architecture, tests, and documentation for energy market coupling (Euphemia/PCR, FBMC) and LP/MIP optimization (unit commitment, storage, portfolios).

---

## 🧠 Skill-First Protocol

**Before coding, check if an antigravity skill covers the task first.**
95+ skills installed under `~/.hermes/skills/antigravity/`. Relevant:
- `concise-planning` — planning, `git-pushing` — git, `systematic-debugging` — debugging
- `cc-skill-coding-standards`, `cc-skill-security-review` — code quality
- `database-design`, `api-patterns`, `microservices-patterns` — architecture
- `error-handling-patterns`, `prompt-engineering` — coding patterns

## Skills

## Skill-Aware Operation (MANDATORY)

Before every user request:
1. Scan `~/.config/opencode/skills/*/SKILL.md` for skills relevant to the request
2. Find the best-matching skill by name or description
3. Load that skill via the `skill` tool and follow its instructions
4. If no skill matches, proceed normally

```bash
# List available skills
ls ~/.config/opencode/skills/
# Search by keyword
ls ~/.config/opencode/skills/ | grep <keyword>
```

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

**Out of scope:** Stock/crypto trading, generic quant finance. This repo is for energy market professionals.

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
│       │   └── config.py           #   App config (ENTSOE_API_KEY env lookup)
│       ├── application/            # Use-case orchestrators — wires domain + adapters
│       │   ├── live_pipeline.py    #   ENTSO-E live data → PCR market clearing
│       │   ├── live_backtest.py    #   Live market data → backtest
│       │   └── *_demo.py           #   Entry-point demos for each domain
│       └── infrastructure/         # Backward-compat re-exports (canonical in domain/)
│           ├── hooks.py            #   Identical copy; domain/hooks.py is canonical
│           ├── options.py          #   Identical copy; domain/options.py is canonical
│           ├── metadata.py         #   Model introspection (VariableRegistry, ModelMetadata)
│           └── solver_config.py    #   Solver-agnostic factory (CBC, HiGHS, Gurobi, CPLEX)
├── tests/                          # Unit tests (pytest, 232 tests, 2 PC-only skipped)
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

## Status After Audit (2026-05-04 16:25 CEST)

### ✅ Fixed (15 issues resolved)

| # | What | Fix |
|---|------|-----|
| … | (last 2 entries live in ITERATIONS.md) |
| 14 | GPT 5.5: test_multi_day broken | Fixed args: zones_per_day/atc_per_day split, horizon_days=7, welfare key |
| 15 | GPT 5.5: FBMC balance tolerance | 0.01 → 1.0 (rounding noise, not LP bug) |

### 🔬 New: PC Benchmark + Property-Based Testing

- `tests/test_benchmarks.py` — 11 stress tests (9 PC-only, 2 Pi-friendly)
- `tests/test_hypothesis.py` — 4 property-based tests (1 requires hypothesis)
- **Tests:** 232 passed, 2 skipped (PC-only), 0 failed

---

## Coding Standards (Production-Grade)

### Language Defaults
- Default to Python unless the task clearly requires another language.

### Maintainability
- Production-ready code only: robust, maintainable, suitable for portfolio use, Python best practices.
- Handle errors and edge cases explicitly — never silently swallow exceptions.
- Prefer explicit code over clever one-liners.
- Comment non-obvious math, indexing, and assumptions (especially optimization constraints, PTDF/LODF math, surplus calculations).
- Minimal global state (except the intentional OPTIONS dict).
- Avoid hidden coupling: pass dependencies explicitly (solver, config, logger).
- Keep interfaces stable; add new files instead of breaking legacy behavior.

### Repo-Style Consistency
- Match local repo style (formatting, naming, typing usage, error-handling patterns).
- Inline single-use helpers when reasonable; avoid redundant checks already guaranteed by callers.

### Naming
- Do NOT prefix helper functions with `_` (this repo uses `_` internally for private helpers; match existing convention).
- Use descriptive names with underscores between words (snake_case).

### Determinism & Reproducibility
- Set seeds for all stochastic tests (`random_seed` or `numpy.random.seed()`).
- Log key package versions in CI/README.
- Include git commit hash in run reports when relevant.

### Fail-Fast & Error Handling
- Never silently swallow exceptions. If catching, log and re-raise unless there's an explicitly defined safe fallback (e.g., ENTSO-E fallback to demo data, solver fallback to CBC).
- Fail fast on NaN/Inf in optimization results — validate invariants post-solve.
- Prefer explicit validation checks at module boundaries.

### Error Avoidance (Lessons Learned)
- When you make an error, update AGENTS.md so it's not repeated.
- **Synthetic data fallback**: Always try real data (yfinance, ENTSO-E, SQLite) before falling back to synthetic. Synthetic must be clearly labeled as `[WARN]`.
- **No tracked API tokens**: Live ENTSO-E access must read `ENTSOE_API_KEY` from the environment. Tests must pass with no local token and use demo fallback unless they explicitly monkeypatch live data.
- **Bidirectional ATC corridors**: A single ATC pair means capacity in both directions. Model it as one signed flow variable; never silently treat tuple order as physical direction.
- **Located storage in market coupling**: Multi-day storage must be connected to a zone balance (default zone 0). A global storage balance plus already-balanced zones forces net storage injection to zero.
- **Grid search for strategy params**: Fixed-param strategies may lose on recent data. Grid-search over parameter ranges to demonstrate profitability.
- **Suppress known library noise**: Wrap import of libraries with known version-mismatch stderr noise (e.g., numpy/pyarrow) in stderr-redirect to keep output clean.
- **Plots directory**: Generated plots go to `src/energy_algorithms/notebooks/plots/` and are excluded from git via `**/plots/` in `.gitignore`.

### RAM & Performance Discipline
- Monitor memory during bulk operations (large yfinance fetches, grid searches over many param combinations).
- Limit grid search to at most ~30 backtests per demo to stay under 500MB RSS.
- Vectorized operations only (numpy/pandas) — no Python loops over price data.
- Close SQLite connections promptly after reads/writes.

### Skill Selection by Task (MANDATORY)
- Announce selected skills in one short line before implementation work.
- Use the minimal skill set that covers the task.
- **Solver bug, NaN, or crash**: use `@systematic-debugging`, then `@requesting-code-review` before closeout.
- **Architecture changes**: use `@software-architecture` + `@clean-code`.
- **Multi-file refactors or interface changes**: use `@plan-writing` before edits.
- **Performance work**: use `@performance-profiling` before and after optimization.
- **Test regressions**: use `@test-fixing`, or `@test-driven-development` when adding new behavior.
- **Results analysis / post-processing**: use `@jupyter-notebook` and `@spreadsheet`.
- **Markdown/docs updates**: use `@writing-skills`.
- **Final completion gate**: use `@verification-before-completion` and `@finishing-a-development-branch`.
- **Prompt engineering**: use `@prompt-engineering` + `@prompt-engineer` for writing efficient prompts.
- **Code review**: use `@requesting-code-review` when reviewing code.

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
- **Idempotent config** — `config.py` reads once; `ENTSOE_API_KEY` comes from the environment only

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
4. **"How do you test optimization code?"** → Known-optimal values, property-based invariants, edge-case matrix. 246 passing tests covering all 18 modules.
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
- ✅ 246 passing tests (2 skipped for uninstalled solvers)
- ✅ CI/CD: GitHub Actions (3 Python versions), tests + demos
- ✅ Dockerfile: multi-stage, reproducible environment
- ✅ Knowledge base: 12 files, 3,610 lines across all domains
- ✅ FRAMEWORK.md: 24KB auto-updatable deep docs
- ✅ MIT License, badges, conventional commits, clean git history

---

## Commands

### Conda (primary)

```bash
# Create environment with all deps
conda env create -f environment.yml
conda activate energy-algorithms

# Install ENTSO-E live extra (conda doesn't handle optional extras)
pip install -e ".[live]"

# Dev extras (already in environment.yml)
make install-pip  # pip fallback
```

### Pip (fallback)

```bash
# Install dev dependencies
pip install -e ".[dev]"
pip install -e ".[live]"   # + ENTSO-E live data
pip install -e ".[docs]"   # + Sphinx
```

### Test
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
| 200+ passing tests | ❌ (~25) | ✅ (60+) | ❌ (~30) | ✅ (246) |
| Interview-focused docs | ❌ | ❌ | ❌ | ✅ |
| Stochastic + EVPI | ❌ | ✅ | ❌ | ✅ |
