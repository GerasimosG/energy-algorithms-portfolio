# AGENTS.md — Energy Algorithms

**Repo:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio targeting **Euphemia   Junior Optimization Engineer** and **Industry power market/optimization** roles only. Stock trading is out of scope.
**Design target:** Beat pomato, PyPSA, energy-py-linear in architecture, tests, and documentation for energy market coupling (Euphemia/PCR, FBMC) and LP/MIP optimization (unit commitment, storage, portfolios).

---

## Identity & Strategy

This repo is **GerryBerry's public portfolio** demonstrating optimization modeling,
energy market domain knowledge (Euphemia/PCR), and algorithmic trading.

The **markets module** (`domain/markets/`) is the hero piece — PCR social welfare,
FBMC with PTDF/RAM, block orders (linked + exclusive), multi-zone ATC coupling,
intraday order books.

**Target audiences:** Euphemia   (Euphemia algorithm), Industry (Power market optimization).
**Out of scope:** Stock/crypto trading, generic quant finance.

See `README.md` for full portfolio intro, interview prep, competitor comparisons, and edge-case talking points.
See `CONTRIBUTING.md` for coding standards, skill-first protocols, and edge-case test matrix.

---

## Architecture: Hexagonal (Ports & Adapters)

```
Energy_Algorithms/
├── src/
│   └── energy_algorithms/          # Main package (pip-installable)
│       ├── domain/                 # ★ Pure business logic — NO I/O, NO solver imports
│       │   ├── markets/            #   ★ HERO — PCR, FBMC, block orders, intraday, LODF, GSK
│       │   ├── optimization/       #   LP/MIP — UC, storage, assets, stochastic, invariants
│       │   └── trading/            #   Backtesting, risk metrics, strategies
│       ├── ports/                  # Abstract interfaces (ABCs / Protocols)
│       │   └── solver.py           #   SolverPort — domain depends on this, not PuLP
│       ├── adapters/               # Concrete implementations of ports
│       │   ├── pulp_solver.py      #   PuLPSolverAdapter(SolverPort)
│       │   ├── entsoe_client.py    #   ENTSO-E Transparency Platform REST client
│       │   └── config.py           #   App config (ENTSOE_API_KEY env lookup)
│       ├── application/            # Use-case orchestrators — wires domain + adapters
│       └── infrastructure/         # Backward-compat re-exports (canonical in domain/)
├── tests/                          # 571 collected, 94% coverage, 90% gate
├── knowledge/                      # Theory, Q&A, interview prep (12 files)
├── pyproject.toml                  # Package config (src layout, ruff, mypy, pytest)
└── FRAMEWORK.md                    # Auto-updatable deep docs (24KB)
```

### Layering Rules

1. **Domain** — stdlib + numpy + scipy + pulp only. **Never** imports adapters or application.
2. **Ports** — stdlib + typing only. Define contracts (ABCs, Protocols). Zero dependencies.
3. **Adapters** — implement ports. May import domain for type hints. **May do I/O.**
4. **Application** — orchestrates domain + ports + adapters. Entry points for use cases.
5. **Infrastructure** — backward-compat re-exports. New code imports from `domain/` directly.

---

## Critical Conventions

### Code Style
- **`src` layout** — pip-installable: `pip install -e ".[dev]"`
- **Absolute imports only** — `from energy_algorithms.domain.markets import ...`
- **`from __future__ import annotations`** — 1st line after docstring in every `.py` file (57/57 files)
- **Type hints** — all functions. Use `X | None`, `list[X]`. NumPy-style docstrings.
- **Ruff isort** — stdlib → third-party → first-party. Run `ruff check --fix` before commits.
- **`__all__`** exported in every `__init__.py`. No magic numbers.
- **Conventional commits** — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `style:`

### Design Patterns
- **Solve chain** — `formulate() → solve() → validate() → extract()`
- **SolverPort DI** — domain receives solver via dependency injection, never imports PuLP directly
- **Asset pattern** — `Asset._constraints()`, `Asset._objective()`, `Asset._post_solve()` lifecycle
- **Physical invariants** — post-solve validation via `assert_invariants()`
- **Known-optimal tests** — every optimization test has pre-computed correct values
- **Graceful fallback** — ENTSO-E falls back to demo data; solver falls back to CBC
- **No module-level mutable state** (except `OPTIONS` dict); every test is independent

---

## Commands

```bash
# Install
conda env create -f environment.yml        # Primary
pip install -e ".[dev]"                    # Fallback

# Test
pytest tests/ -v                           # All tests
pytest tests/ -v -m "not slow and not pc"  # Fast only (Pi-friendly)
pytest tests/test_pcr_model.py -v          # Single file

# RAM-bounded coverage gate (preferred for laptops)
python -m coverage erase
for f in tests/test_*.py; do
    PYTHONPATH="$(pwd)/src" python -m pytest "$f" -m "not slow and not pc" \
      --cov=energy_algorithms --cov-append --cov-report= --cov-fail-under=0 -q
done
PYTHONPATH="$(pwd)/src" python -m coverage report --fail-under=90

# Lint
ruff check src/ tests/ && ruff check --fix src/ tests/
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

## What We've Learned (Don't Repeat These)

1. **Demand zero is not a no-op** — Zero demand scenarios produce valid (empty) solutions. Test explicitly.
2. **Block orders at the marginal price** — A block at MCP should be accepted.
3. **Horizon-end constraints for UC** — Min up/down can't extend beyond horizon. Use `min(remaining_hours, min_up)`.
4. **Surplus is area between curves** — `numpy.trapz()`, never `sum(p * q)`.
5. **No tracked API tokens** — `ENTSOE_API_KEY` from environment only. Tests use demo fallback.
6. **Bidirectional ATC corridors** — One signed flow variable; never treat tuple order as physical direction.
7. **Grid search for strategy params** — Fixed params may lose on recent data. Grid-search over parameter ranges.
8. **Known-optimal > "solves without error"** — Every optimization test needs a pre-computed correct answer.
9. **Coverage is memory-heavy** — Use file-by-file coverage append loop; mock expensive demo deps in coverage tests.
10. **Backward compat during refactors** — Keep re-export stubs in old location so tree isn't broken mid-iteration.
