# AGENTS.md — Energy Algorithms

**Repo:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio for Euphemia   Junior Optimization Engineer & energy/quant roles (currently private)

## Skills

When working on this repo, load these skills:

- `writing-plans` — plan before coding
- `test-driven-development` — RED-GREEN-REFACTOR
- `systematic-debugging` — understand before fixing
- `github-pr-workflow` — branch, commit, PR, merge

## Identity

This repo is GerryBerry's public portfolio demonstrating optimization modeling,
energy market domain knowledge (Euphemia/PCR), and algorithmic trading.
The **domain/markets** module is the hero piece — what differentiates this
from generic quant repos. Targeted at **Euphemia  ** (Euphemia algorithm)
and **Industry** (power market optimization) roles.

## Architecture (Hexagonal / Ports & Adapters)

```
Energy_Algorithms/
├── src/
│   └── energy_algorithms/          # Main package (pip-installable)
│       ├── domain/                 # Pure business logic — NO I/O
│       │   ├── markets/            # ★ HERO — PCR, block orders, FBMC, intraday
│       │   ├── optimization/       # Core LP/MIP — UC, storage, portfolio, assets
│       │   └── trading/            # Backtest engine, risk metrics, signal strategies
│       ├── ports/                  # Abstract interfaces (ABCs / Protocols)
│       │   └── solver.py           # SolverPort — domain depends on this, not PuLP
│       ├── adapters/               # Concrete implementations of ports
│       │   ├── entsoe_client.py    # ENTSO-E Transparency Platform adapter
│       │   ├── yfinance_fetcher.py # Yahoo Finance data adapter
│       │   ├── sqlite_store.py     # SQLite persistence adapter
│       │   └── config.py           # Application configuration
│       ├── application/            # Use-case orchestrators (wire domain + adapters)
│       │   ├── live_pipeline.py    # ENTSO-E live PCR pipeline
│       │   ├── live_backtest.py    # Live market data → backtest
│       │   ├── markets_demo.py     # Markets demo entry point
│       │   ├── optimization_demo.py# Optimization demo entry point
│       │   └── trading_demo.py     # Trading demo entry point
│       └── infrastructure/         # Cross-cutting concerns
│           ├── hooks.py            # Lifecycle hooks (pre/post solve)
│           ├── options.py          # Global configuration options
│           ├── metadata.py         # Model introspection
│           └── solver_config.py    # Solver-agnostic factory
├── tests/                          # Mirrors src layout
├── scripts/                        # CLI entry points
├── pyproject.toml                  # Package config (src layout)
├── conftest.py                     # Pytest config (CBC solver symlink)
└── AGENTS.md                       # This file
```

### Layering Rules

1. **Domain** — imports ONLY stdlib, numpy, scipy, pulp (and ports). Never imports adapters or application.
2. **Ports** — abstract; import only stdlib + typing. Define contracts (ABCs, Protocols).
3. **Adapters** — implement ports. May import domain for type hints. May do I/O.
4. **Application** — orchestrates domain + ports + adapters. Entry point for use cases.
5. **Infrastructure** — cross-cutting utilities imported by domain modules.

## Critical Conventions

- **`src` layout** — pip-installable with `pip install -e ".[dev]"`
- **Underscore** directory names for valid Python packages (`energy_algorithms`)
- **Package imports** — always `from energy_algorithms.domain.markets import ...` (absolute imports, no `sys.path` hacks)
- **Time zone** — Europe/Brussels (CET/CEST)
- **Imports** — use `ruff` (isort rules) for consistent ordering: stdlib → third-party → first-party
- **Type hints** — use `from __future__ import annotations` and standard library generics (no `Optional[x]`, use `x | None`)
- **Public API** — every `__init__.py` exports `__all__`
- **Solvers** — domain code depends on `SolverPort` ABC, not on `pulp.PULP_CBC_CMD` directly (adapter pattern)
- **Configuration** — API keys stored in `config.py`; never commit secrets
- **Conventional commits** — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- **Branch naming** — `feat/<desc>`, `fix/<desc>`, `refactor/<desc>`

## Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run only fast tests (skip PC-scale benchmarks)
pytest tests/ -v -m "not slow and not pc"

# Run all tests including benchmarks
pytest tests/ -v

# Run specific test file
pytest tests/test_pcr_model.py -v

# Type check
mypy src/

# Lint
ruff check src/ tests/

# Run application demos
ea-markets          # Energy markets demo
ea-optimization     # LP optimization demo
ea-trading          # Trading backtest demo
ea-live             # ENTSO-E live pipeline

# Or directly
python -m energy_algorithms.application.markets_demo
```

## Test Stats

- **232 passing**, 2 skipped (solver fallback tests require uninstalled solvers)
- Markers: `slow` (>5s), `pc` (>1GB RAM), none (fast unit tests)

## Git Workflow (Update Trilogy)

```bash
# 1. Branch
git checkout main && git pull
git checkout -b <type>/<description>

# 2. Commit (with verification)
pytest tests/ -v          # MUST pass before commit
git add -A
git commit -m "<type>: <description>"

# 3. PR
git push -u origin <branch>
gh pr create --title "<type>: <description>" --body "$(cat <<'EOF'
## Summary
...
EOF
)"
```

**Key:** `id_ed25519` is the account SSH key. Run `ssh-add ~/.ssh/id_ed25519` if auth fails.

## Euphemia   Interview Readiness Checklist

- ✅ LP/MIP formulation (PuLP, scipy)
- ✅ Energy market domain (PCR/Euphemia, block orders)
- ✅ Linked + exclusive block constraints
- ✅ Unit commitment with min up/down, ramp rates
- ✅ Portfolio optimization (mean-variance)
- ✅ Backtesting with correct risk metrics
- ✅ Vectorized engine (no look-ahead bias)
- ✅ Flow-based market coupling (FBMC: PTDF + RAM)
- ✅ LODF contingency screening (N-1 security)
- ✅ Multi-day / multi-zone market coupling
- ✅ Stochastic programming (VSS, EVPI)
- ✅ Solver-agnostic architecture (SolverPort ABC)
- ✅ Lifecycle hooks + options + metadata
- ✅ Hexagonal architecture (ports & adapters)
- ✅ 232 pytest tests passing
- ✅ src layout with pyproject.toml
- ✅ CI/CD (GitHub Actions, Python 3.11–3.13)
- ✅ Conventional commits + clean git history
- ✅ README with Euphemia whitepaper-style depth
- ✅ LICENSE (MIT)
