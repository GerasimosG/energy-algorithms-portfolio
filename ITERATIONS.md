# ITERATIONS — Energy Algorithms

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
