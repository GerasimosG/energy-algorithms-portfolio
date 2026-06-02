# AGENTS.md — Energy Algorithms

**Repo:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio for **Euphemia  ** (Euphemia/PCR) and **Industry** (power market optimization).
**Design target:** Beat pomato, PyPSA, energy-py-linear in architecture, tests, and docs.

**Out of scope:** Stock/crypto trading, generic quant finance.

---

## Architecture: Hexagonal (Ports & Adapters)

```
Energy_Algorithms/
├── src/
│   └── energy_algorithms/
│       ├── domain/                    # ★ Pure business logic — NO I/O, NO solver hardcoding
│       │   ├── markets/               #   ★ HERO — PCR, FBMC, block orders, intraday, coupling_utils
│       │   ├── optimization/          #   LP/MIP — UC, storage, assets, stochastic, invariants
│       │   └── trading/               #   Backtesting, risk metrics, strategies
│       ├── ports/solver.py            # SolverPort — ABC that domain depends on
│       ├── adapters/                  # Concrete implementations (pulp_solver, entsoe_client, ...)
│       ├── application/               # Use-case orchestrators — wires domain + adapters
│       │   ├── data_loader.py         # Shared demo utilities (price loading, grid search)
│       │   └── *_demo.py              # Entry-point demos
│       └── infrastructure/            # Backward-compat re-exports (canonical in domain/)
├── tests/                             # **568 tests, 94% coverage, 90% gate**
├── knowledge/                         # Theory, Q&A, interview prep, competitor analysis
├── notebooks/                         # Jupyter walkthrough (24-cell)
├── pyproject.toml                     # Package config (src layout, ruff, mypy, pytest)
├── FRAMEWORK.md                       # Auto-updatable deep docs: 518 lines
├── ITERATIONS.md                      # Iteration log (latest first)
└── README.md                          # Portfolio intro + interview prep
```

### Layering Rules
1. **Domain** — stdlib + numpy + scipy + pulp only. Never imports adapters.
2. **Ports** — stdlib + typing only. Define contracts.
3. **Adapters** — implement ports. May do I/O.
4. **Application** — orchestrates domain + ports + adapters.
5. **Infrastructure** — backward-compat re-exports.

---

## Critical Conventions

### Code Style
- **`src` layout** — `pip install -e ".[dev]"`
- **Absolute imports only** — `from energy_algorithms.domain.markets import ...`
- **`from __future__ import annotations`** — 1st line of every `.py` file
- **Type hints on all functions** — `X | None` not `Optional[X]`, `list[X]` not `List[X]`
- **NumPy-style docstrings** — Parameters / Returns / Raises on every public function
- **`__all__`** in every `__init__.py`
- **Ruff isort** — run `ruff check --fix` before commits
- **Conventional commits** — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `style:`

### Design Patterns
- **Solve chain** — `formulate() → solve() → validate() → extract()`
- **SolverPort DI** — domain receives solver via injection, never imports PuLP directly
- **Known-optimal tests** — every optimization test has pre-computed correct values
- **Graceful fallback** — ENTSO-E falls back to demo data; solver falls back to CBC
- **No module-level mutable state** (except `OPTIONS` dict); every test independent

### What We've Learned
- **Demand zero is not a no-op** — zero solutions are valid, test explicitly
- **Surplus is area between curves** — `numpy.trapz()`, never `sum(p * q)`
- **Bidirectional ATC** — one signed flow variable, never treat tuple order as direction
- **Coverage is memory-heavy** — use file-by-file append loop for Pi; mock expensive deps
- **Backward compat during refactors** — keep re-export stubs in old locations

---

## Commands

```bash
# Install
pip install -e ".[dev]"                    # Dev deps
pip install -e ".[live]"                   # + ENTSO-E live data

# Test
pytest tests/ -v                           # All tests
pytest tests/ -v -m "not slow and not pc"  # Pi-friendly only
pytest tests/ --cov=energy_algorithms      # Coverage

# RAM-bounded coverage gate (Pi/laptop-safe)
python -m coverage erase
for f in tests/test_*.py; do
    PYTHONPATH="$(pwd)/src" python -m pytest "$f" -m "not slow and not pc" \
      --cov=energy_algorithms --cov-append --cov-report= --cov-fail-under=0 -q
done
PYTHONPATH="$(pwd)/src" python -m coverage report --fail-under=90

# Lint
ruff check src/ tests/
mypy src/

# Demos
ea-markets    ea-optimization    ea-trading    ea-live
```

---

## Git Workflow

```bash
git checkout main && git pull
git checkout -b feat/<description>
pytest tests/ -v && ruff check src/ tests/ && mypy src/   # MUST pass
git add -A && git commit -m "feat: <description>"
git push -u origin <branch>
```

**SSH key:** `id_ed25519`. Run `ssh-add ~/.ssh/id_ed25519` if auth fails.

---

## Documentation Trilogy (Mandatory Per Iteration)

1. **`README.md`** — User-facing: what changed, why
2. **`ITERATIONS.md`** — Dev-facing: prepend entry (date, time CEST, summary, files, test count)
3. **`FRAMEWORK.md`** — Technical deep-dive: run `scripts/update_framework_metrics.sh`

---

## Status

**Tests:** 568 passing, 3 skipped, 0 failing, **94% coverage** (90% gate).
**Shared utilities:** `coupling_utils.py` (4 market coupling modules), `data_loader.py` (3 demo files).
**Lint:** Ruff clean, mypy clean.
**Key remaining gap:** 10 domain files still call `pulp.PULP_CBC_CMD()` directly instead of going through `SolverPort`.
