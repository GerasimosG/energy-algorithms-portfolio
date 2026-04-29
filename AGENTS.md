# AGENTS.md — Energy Algorithms

**Repo:** `/home/gerryberrypi/optimization-portfolio/`
**Remote:** `git@github.com:GerasimosG/Energy_Algorithms.git`
**Purpose:** Public portfolio for Euphemia   Junior Optimization Engineer & energy/quant roles (currently private)

## Skills

When working on this repo, load these skills:

- `writing-plans` — plan before coding
- `test-driven-development` — RED-GREEN-REFACTOR
- `systematic-debugging` — understand before fixing
- `github-pr-workflow` — branch, commit, PR, merge

## Identity

This repo is GerryBerry's public portfolio demonstrating optimization modeling, energy market domain knowledge (Euphemia/PCR), and algorithmic trading. The **energy_markets** module is the hero piece — what differentiates this from generic quant repos. Targeted at **Euphemia  ** (Euphemia algorithm) and **Industry** (power market optimization) roles.

## Architecture

```
Energy_Algorithms/
├── energy_markets/     ★ HERO — PCR social welfare LP, block orders, market stack
├── lp_optimization/      Core LP/MIP — transportation, portfolio, unit commitment
├── backtester/           Vectorized backtesting engine + risk metrics
├── strategies/           3 signal-based trading strategies
├── market_data/          yfinance → SQLite pipeline
├── tests/                Unit tests (pytest)
└── notebooks/            Jupyter exploration
```

## Critical Conventions

- **Underscore** directory names for valid Python packages
- Import via `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))`
- Timezone: **Europe/Brussels** (CET/CEST)
- Run: `.venv/bin/python -m energy_markets.demo`
- **Repo kept private** for now per user instruction

## Status After Audit (2026-04-29 23:30 CEST)

### ✅ Fixed (13 issues resolved)

| # | What | Fix |
|---|------|-----|
| 1 | Linked blocks not linked | Added `group` parameter, equality constraints on shared group binary vars |
| 2 | MCP ignores block orders | MCP = max(accepted_supply_prices + accepted_block_prices) |
| 3 | Energy balance `>=` | Changed to `==` (exact match) |
| 4 | Exclusive blocks | Group mechanism: `sum(b_i) <= 1` for `excl_*` groups |
| 5 | Reserve/demand conflated | Split into energy_balance `==` and reserve `>=` constraints |
| 6 | No UC initial conditions | Added `init_status`, min up/down from t=0 |
| 7 | Horizon-end UC constraints | Min up/down enforced through final period |
| 8 | Zero unit tests | `tests/` with 26 pytest tests (3 modules) |
| 9 | No pyproject.toml | Added with dependencies, pytest config |
| 10 | Hardcoded momentum threshold | Parameterized as `threshold=` arg |
| 11 | Surplus shading wrong | Proper area-between-curves shading |
| 12 | Demo ignores non-optimal | Status check before report() |
| 13 | Empty `__init__.py` | All modules have `__all__` exports |

### 🆕 New in This Iteration

- **Multi-zone coupling** (`multi_zone.py`): ATC-constrained inter-zonal LP
- **Euphemia   interview prep** (`EUPHEMIA_INTERVIEW.md`): Euphemia concepts + question bank
- **CI workflow** (`.github/workflows/test.yml`): Python 3.11-3.13 matrix
- **README**: Badges, architecture, metrics table, known limitations, references
- **Tests**: 26 total (was 16) — transportation, portfolio, UC all tested

### 🟡 Remaining Low-Priority

- Hardcoded acceptance tolerance 0.001 (cosmetic)
- Incomplete type hints (cosmetic)
- `__init__.py` exports for all modules (done ✓)
- IP pricing documentation added (done ✓ in EUPHEMIA_INTERVIEW.md)

## Euphemia   Interview Readiness Checklist

- ✅ LP/MIP formulation (PuLP, scipy)
- ✅ Energy market domain (PCR, Euphemia, block orders)
- ✅ Linked + exclusive block constraints
- ✅ Unit commitment with min up/down, ramp rates
- ✅ Portfolio optimization (mean-variance with scipy)
- ✅ Backtesting with correct risk metrics
- ✅ Vectorized engine (no look-ahead bias)
- ✅ Unit tests (pytest, 26 tests passing)
- ✅ Clean git history with meaningful commits
- ✅ pyproject.toml for pip-installable package
- ✅ CI/CD pipeline (`.github/workflows/test.yml`, Python 3.11–3.13)
- ✅ README with Euphemia whitepaper-style depth (problem formulation, algorithm walkthrough)
- ✅ LICENSE (MIT)

## Git Workflow

```bash
git remote set-url origin git@github.com:GerasimosG/Energy_Algorithms.git
git add -A && git commit -m "message"
git push origin main
```

**Key:** `id_ed25519` is the account SSH key. Run `ssh-add ~/.ssh/id_ed25519` if auth fails.

## Model Setting

`model.default` set to `deepseek-v4-pro` on `opencode-go` provider. Takes effect on next session (`/new`).
