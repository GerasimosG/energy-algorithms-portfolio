# FRAMEWORK — Energy Algorithms architecture

A concise map of how the codebase is wired. For the user-facing tour see [`README.md`](README.md);
for contribution rules and the layering contract see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Hexagonal layers

```
application/      use-case demos + CLIs (ea-markets, ea-optimization, ea-trading, …)
   │  orchestrates
   ▼
domain/           pure problem logic — builds PuLP models, no I/O
   markets/       pcr_model, block_orders, fbmc, gsk, lodf_utils, multi_zone, multi_day,
                  intraday, coupling_utils, market_clearing
   optimization/  storage (BESS), ancillary (FCR+aFRR), scheduling (UC), assets, invariants,
                  portfolio, stochastic, transportation
   trading/       backtest_engine, risk_metrics, momentum, mean_reversion, sma_crossover,
                  energy_strategies
   adequacy/      metrics (LOLE/EENS/margin/duration curve), monte_carlo (forced-outage
                  sampling) — pure numpy, no LP, no I/O
   (root)         emissions, hooks, options
   │  solves via
   ▼
infrastructure/   solver_config (solve_model facade), experiment_tracker, metadata
   │  delegates to
   ▼
adapters/         pulp_solver (SolverPort impl), entsoe_client, sqlite_store, bt_feeds,
                  bt_strategies, market_simulation, yfinance_fetcher, antares_io, config
   │  implements
   ▼
ports/            solver.py — SolverPort ABC + SolverResult (the contract)
```

## The solve pipeline (honest version)

Each domain solve site does **not** import a concrete solver. It builds a `pulp.LpProblem`
(PuLP is the modelling DSL) and calls one facade:

```
domain/*  →  infrastructure.solver_config.solve_model(prob, solver=…, solver_id=…)
          →  adapters.pulp_solver.PuLPSolverAdapter (a ports.SolverPort)
          →  ports.solver.SolverResult  (status, objective, variables, time)
```

- **Default backend:** PuLP/CBC. Swap with `solver_id="highs" | "gurobi" | "cplex" | "glpk"`
  (graceful fallback to CBC with a warning if not installed — see `get_solver`).
- **Injection:** pass any `SolverPort` via `solver=` to bypass the default entirely.
- **Why infrastructure, not ports, holds `solve_model`:** `solve_model` is a convenience facade that
  *wires* the default adapter. Infrastructure is an outer layer, so it may depend on adapters; the
  adapter import is explicit at module top-level (`adapters.pulp_solver` imports only `ports.solver`,
  so there is no cycle). Domain code routes solving through this facade — never through a concrete
  solver — per the architecture rules in `CONTRIBUTING.md`.

This is the accurate description. The domain is decoupled from the *solver backend*, not from PuLP
as a modelling library — a deliberate, common trade-off.

## Data & visualization pipeline

```
adapters/entsoe_client.py  →  data/ (cache, gitignored)  →  scripts/_viz_data.py
                                                          →  scripts/generate_figures.py    → docs/fig*.png
                                                          →  scripts/generate_dashboard.py  → docs/dashboard.html
```

- A small committed sample (`data/sample_*.csv`) makes every figure + the dashboard reproducible on a
  fresh clone. `scripts/_viz_theme.py` is the one shared visual identity (matplotlib + Plotly).
- The dashboard's BESS panel runs the real `domain.optimization.storage.solve_storage`, so the chart
  is a live optimisation, not a static asset.

## Testing

- 622 tests under `tests/`, ~92.8% coverage, 90% gate enforced in CI (`--cov-fail-under=90`).
- Markers: `slow` (>5s) and `pc` (PC-only stress sizes) — skip with `-m "not slow and not pc"` in
  resource-constrained environments.
- `conftest.py` skips the `.env` auto-loader for the whole session so tests never depend on a local
  ENTSO-E token and are deterministic on any machine.

## Extending

| To add… | Touch |
|---|---|
| A new market/optimization model | a `domain/<area>/` module that builds a PuLP problem and calls `solve_model`; a `tests/test_*.py` |
| A new solver backend | register it in `infrastructure/solver_config.py` (`_SOLVER_REGISTRY` / resolver) — adapter already generic |
| A non-PuLP modelling backend | a new `ports.SolverPort` adapter under `adapters/`, wired in `solver_config` |
| A new chart | a panel builder in `scripts/generate_dashboard.py` (or figure in `generate_figures.py`) using `_viz_data` + `_viz_theme` |
| A new adequacy metric/scenario | a function in `domain/adequacy/` (pure numpy) + a `tests/test_*.py`; surface it via `scripts/build_warehouse.py` or `generate_adequacy_figures.py` |
