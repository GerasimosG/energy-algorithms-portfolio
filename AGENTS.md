# AGENTS.md — Optimization Portfolio

**Repo:** `/home/gerryberrypi/optimization-portfolio/`
**Remote:** `git@github.com:GerasimosG/optimization-portfolio.git`
**Purpose:** Public portfolio for Euphemia   Junior Optimization Engineer & energy/quant roles

## Identity

This repo is GerryBerry's public portfolio demonstrating optimization modeling, energy market domain knowledge (Euphemia/PCR), and algorithmic trading. The **energy_markets** module is the hero piece — it's what differentiates this from generic quant repos.

## Architecture

```
optimization-portfolio/
├── energy_markets/     ★ HERO — PCR social welfare LP, block orders, market stack
├── lp_optimization/      Core LP/MIP — transportation, portfolio, unit commitment
├── backtester/           Vectorized backtesting engine + risk metrics
├── strategies/           3 signal-based trading strategies
├── market_data/          yfinance → SQLite pipeline
└── notebooks/            Jupyter exploration
```

## Critical Conventions

### Directory Names
Use **underscores** for module directories (valid Python package names). No hyphens.

### Import Strategy
Each demo.py adds the repo root to sys.path with:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
```

### Running
```bash
.venv/bin/python -m energy_markets.demo    # From repo root
```

### Timezone
All timestamps: Europe/Brussels (CET/CEST).

## Known Issues (from code audit 2026-04-29)

### Critical — Fix Before Push
1. **portfolio.py:81-95** — Risk constraint is completely missing. PuLP can't do QP. Either use scipy.optimize or implement MAD linearization.
2. **market_clearing.py** — `find_equilibrium()` returns wrong MCP when supply is below demand (returns €120 instead of €80).
3. **engine.py:59-80** — Trade log mislabels flat transitions as trades.
4. **store.py:72-73** — `conn.total_changes > 0` falsely counts duplicates.

### High — Fix Before Taking Public
5. **block_orders.py** — "Linked blocks" aren't actually linked. Each block has independent binary variable.
6. **metrics.py:20-23** — Sortino uses `np.std(downside)` instead of downside deviation.
7. **engine.py:44-48** — Same-day signal/return creates forward-looking bias. Shift signals by one period.
8. **PCR model** — MCP calculation ignores block orders entirely.

### Medium
9. **scheduling.py:72** — Reserve margin conflated with demand in single constraint.
10. **scheduling.py:53-55** — No initial conditions, min up/down bypassable at t=0.
11. **portfolio.py** — Docstring claims risk constraint exists but it doesn't.
12. **momentum.py:42** — Hardcoded 2% threshold, not parameterized.

## Requirements for Euphemia   Role Readiness

### Must-Have (blocking)
- [ ] Fix portfolio risk constraint (use scipy QP or MAD)
- [ ] Fix market_clearing equilibrium MCP calculation
- [ ] Fix engine.py trade log (flat transitions)
- [ ] Fix store.py total_changes counter
- [ ] Add proper linked block constraint to PCRModel
- [ ] Add error handling for NaN volume in store.py
- [ ] Shift signals by 1 period to remove look-ahead bias

### Nice-to-Have
- [ ] Write unit tests (currently zero test coverage)
- [ ] Add pyproject.toml for `pip install -e .`
- [ ] Parameterize momentum threshold
- [ ] Add terminal constraints for UC horizon-end
- [ ] Add notebooks/energy-markets-demo.ipynb
- [ ] Clean up comment drift in portfolio.py

## Git Workflow

```bash
# Commit per module with descriptive messages
git add energy_markets/ && git commit -m "energy_markets: PCR model, block orders, market clearing"
git push origin main
```

## Model Configuration

The agent currently runs on `opencode-go` provider with `deepseek-v4-flash`. For model overrides, verify model ID exists on provider before setting. The `deepseek-v4-pro-max` model ID may not exist on this provider — use `hermes model` to check available models interactively.
