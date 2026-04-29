# ITERATIONS — Energy Algorithms

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
