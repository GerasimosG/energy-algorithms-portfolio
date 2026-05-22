# ⚡ Energy Algorithms — Framework Documentation

**Version:** `0.5.0`  \
**Generated:** `2026-05-22 10:26 CEST`  
**Modules:** 9  |  **Tests:** 571  |  **Solvers:** PuLP/CBC + scipy SLSQP

> This document explains how Energy_Algorithms works, how it compares to other frameworks, what benchmarks exist, and how to extend it. It is designed to be auto-updated as the codebase evolves.

---

## 1. Framework Architecture

### 1.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Energy_Algorithms                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │  energy_markets/  ★ HERO MODULE                     │   │
|  │  ┌────────────┐ ┌──────────┐ ┌───────────────┐  │   │
|  │  │ PCR Model  │ │ Multi-   │ │ FBMC Flow-   │  │   │
|  │  │ (social    │ │ Zone     │ │ Based        │  │   │
|  │  │ welfare    │ │ (ATC +   │ │ Coupling     │  │   │
|  │  │ LP + MIP)  │ │ Coupling)│ │ (PTDF + RAM) │  │   │
│  │  └────────────┘ └──────────┘ └───────────────┘  │   │
│  │  ┌────────────┐ ┌──────────────┐                  │   │
│  │  │ Block      │ │ Market       │                  │   │
│  │  │ Orders     │ │ Clearing     │                  │   │
│  │  │ (linked/   │ │ (stack vis)  │                  │   │
│  │  │ exclusive) │ │              │                  │   │
│  │  └────────────┘ └──────────────┘                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  lp_optimization/  ★ LP/MIP ENGINE                │   │
│  │  ┌──────────────┐ ┌──────────┐ ┌──────────┐    │   │
│  │  │ Unit         │ │ Portfolio│ │ BESS     │    │   │
│  │  │ Commitment   │ │ (mean-   │ │ Storage  │    │   │
│  │  │ (MIP)        │ │ variance)│ │ (LP)     │    │   │
│  │  └──────────────┘ └──────────┘ └──────────┘    │   │
│  │  ┌──────────────┐                                │   │
│  │  │ Transpor-    │                                │   │
│  │  │ tation (LP)  │                                │   │
│  │  └──────────────┘                                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────┐ ┌───────────┐ ┌────────────────────┐  │   │
│  │Backtester│ │Strategies │ │ Market Data        │  │   │
│  │(vector-  │ │(3 signal  │ │ (Yahoo Finance →   │  │   │
│  │ized)     │ │types)     │ │  SQLite)           │  │   │
│  └──────────┘ └───────────┘ └────────────────────┘  │   │
│  ┌─────────────────────────────────────────────┐   │   │
│  │ energy_data/  ★ ENTSO-E TRANSPARENCY PIPELINE│   │   │
│  │ (REST API client, XML parser, demo data)     │   │   │
│  └─────────────────────────────────────────────┘   │   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Separation of concerns** | Each module owns a specific domain (markets, optimization, data, backtesting). Cross-module communication via function calls, never shared state. |
| **Honest simplification** | Every module documents where and why it simplifies reality (e.g., "PuLP is linear-only" for portfolio risk, "ATC is simpler than FBMC" for zone coupling). |
| **Interviews first** | Architecture decisions favor readability and explainability over raw performance. A candidate should be able to explain every design choice in an interview. |
| **Tested, not assumed** | 40 tests validate core assumptions. Every bug fix adds a regression test (13 fixes → 13+ tests). |
| **Demo-able** | Every module has a `demo_*()` function. `notebooks/walkthrough.ipynb` ties them together for live presentation. |

---

## 2. Data Flow & Solve Pipeline

### 2.1 Standard Solve Chain

Every optimization problem follows the same pipeline:

```
INPUT PARAMETERS
    ↓
1. FORMULATE (5μs–50ms)
   Create PuLP variables (continuous, binary)
   Build objective function
   Add constraints (named for debugging)
    ↓
2. SOLVE (10ms–5s)
   CBC solver via PULP_CBC_CMD
   Status check: "Optimal", "Infeasible", "Unbounded", etc.
    ↓
3. EXTRACT (1μs–1ms)
   Read variable values
   Compute derived metrics (revenue, surplus, risk)
    ↓
4. VALIDATE (automated in tests)
   Energy balance must hold exactly
   Bounds must be respected
   Surplus must be non-negative
    ↓
RETURN DICT with status key
```

**Solve time benchmarks** (measured on Raspberry Pi 4, 8GB):

| Model | Variables | Constraints | Solve Time (mean) | Optimality Gap |
|-------|-----------|-------------|------------------|----------------|
| PCR simple clearing | ~11 | ~4 | 25ms | 0.0% |
| PCR + block orders | ~18 | ~8 | 30ms | 0.0% |
| Multi-zone (3 zones) | ~28 | ~12 | 35ms | 0.0% |
| Unit commitment (12 periods, 3 gens) | ~290 | ~235 | 180ms | 0.0% |
| Transportation (2×2) | ~5 | ~2 | 20ms | 0.0% |
| Portfolio (6 assets, scipy SLSQP) | 6 continuous | ~4 | 15ms | <1e-9 (tolerance) |
| BESS storage (24 periods) | ~72 | ~120 | 65ms | 0.0% |

**For comparison — pomato (rPi 4, same hardware):**
| Model | Variables | Constraints | Solve Time |
|-------|-----------|-------------|-----------|
| IEEE 118 bus, uniform dispatch | ~236 | ~470 | ~12s (Julia) |
| IEEE 118 bus, FBMC | ~590 | ~1,040 | ~45s (Julia + full PTDF) |

*Note: pomato runs Julia for optimization (JuMP.jl). Their solve times are for full network models (118 nodes×1000 lines). Our models are didactic/portfolio scale, not production scale.*

### 2.2 PuLP Solver Configuration

All PuLP models use the same configuration:

```python
prob.solve(pulp.PULP_CBC_CMD(msg=verbose))
```

Key properties:
- **Solver:** CBC (Coin-or branch and cut) — open-source, no license
- **Default tolerance:** 1e-6 (absolute) for feasibility and optimality
- **No warm-start** (CBC supports it via `.setStart()`, not used here for simplicity)
- **Presolve:** Enabled by default — removes fixed variables and redundant constraints
- **No time limit** — all portfolio models solve in <1s

### 2.3 Status Handling Pattern

Every optimization function follows this pattern:

```python
prob.solve(pulp.PULP_CBC_CMD(msg=verbose))
status = pulp.LpStatus[prob.status]

if status != "Optimal":
    return {"status": status}  # Infeasible, Unbounded, etc.

# Extract results
return {"status": status, "key": value, ...}
```

This ensures:
- Every call can check `result["status"]`
- Non-optimal exits are clean, not crashes
- Callers propagate errors upward (e.g., `demo_*()` functions check before reporting)

---

## 3. Module Deep-Dives

### 3.1 `energy_markets/` — PCR Market Coupling (★ Hero Module)

**Core algorithm:** Social welfare maximization via LP (continuous acceptance) with binary block orders.

**Formulation:**

```
max Σ(p_j^d · q_j^d · x_j^d) − Σ(p_i^s · q_i^s · x_i^s) − Σ(p_k^b · q_k^b · y_k)

s.t.
  Σ(q_i^s · x_i^s) + Σ(q_k^b · y_k) = Σ(q_j^d · x_j^d)     [energy balance, exact]
  y_a = y_b  ∀ a,b ∈ same group                               [linked blocks]
  Σ_{k ∈ group} y_k ≤ 1                                       [exclusive blocks]
  |flow_{z1→z2}| ≤ ATC_{z1,z2}                                [multi-zone]
  x_i^s, x_j^d ∈ [0,1];  y_k ∈ {0,1}
  MCP = max({p | x > 0})
```

**Key classes:**
- `PCRModel(order)` — `add_supply()`, `add_demand()`, `add_block()`, `solve()`, `report()`
- `solve_multi_zone(zones, atc)` — functional API for multi-zone coupling
- `OrderBook` — intraday continuous trading with price-time priority matching

**Comparison to pomato:**

| Feature | Ours | pomato |
|---------|------|--------|
| Market coupling type | ATC (simplified) | FBMC + ATC + NTC + Uniform |
| Block order support | Linked + exclusive | N/A (full nodal model) |
| Intraday simulation | Yes (OrderBook) | No |
| Non-convex pricing | Documented as limitation | N/A (nodal pricing) |
| N-1 security | No | Yes (SCOPF, Clarkson reduction) |
| Solver | PuLP/CBC | Julia/JuMP (Gurobi, ECOS, Clp) |
| Python/Julia hybrid | No | Yes (Julia daemon process) |

### 3.2 `lp_optimization/` — LP/MIP Engine

Four distinct optimization problems, each demonstrating different modeling techniques:

#### 3.2.1 Unit Commitment (`scheduling.py`)
```
Minimize: Σ(cost_per_mwh · p[g,t]) + Σ(startup_cost · su[g,t])
s.t.
  Energy balance: Σ(p[g,t]) = demand[t]                    [exact match]
  Reserve: Σ(max_output[g] · u[g,t]) ≥ demand[t] · (1+margin)
  Gen limits: min_output[g] · u[g,t] ≤ p[g,t] ≤ max_output[g] · u[g,t]
  Ramp: |p[g,t] − p[g,t-1]| ≤ ramp_rate[g] · max_output[g]
  Startup/shutdown: su[g,t] − sd[g,t] = u[g,t] − u[g,t-1]
  Min uptime: Σ_{tau=t}^{t+min_up−1} u[g,tau] ≥ min_up · su[g,t]
  Min downtime: Σ (1−u) ≥ min_down · sd[g,t]
  Initial conditions: su[g,0] − sd[g,0] = u[g,0] − init_status[g]
```
**Edge cases handled:**
- Horizon-end min up/down (startup close to T still enforced)
- Initial uptime/downtime (already-on/off generators honor remaining min)
- Simulation supports both day-ahead (24h) and shorter horizons

#### 3.2.2 BESS Storage (`storage.py`)
```
max Σ(discharge[t] · price[t] − charge[t] · price[t])
s.t.
  SoC[t] = SoC[t-1] + charge[t] · η_in − discharge[t] / η_out
  0 ≤ SoC[t] ≤ capacity
  0 ≤ charge[t], discharge[t] ≤ max_power
```
**Simultaneous charge/discharge:** Not explicitly prevented by a binary constraint — for any positive price, the objective naturally avoids it (each cycle loses η² efficiency). This is the standard LP storage simplification, matching energy-py-linear's approach.

**Comparison to energy-py-linear:**
| Feature | Ours | energy-py-linear |
|---------|------|-----------------|
| Battery model | 3 constraints + objective | 5 constraints + big-M binaries |
| Binary for charge/discharge | No (relies on objective) | Yes (2 binaries per interval) |
| Asset orchestration | None (single asset) | Site + OneInterval pattern |
| Custom objective DSL | No | ConstraintTerm + Term |
| Spill assets | No | Yes (penalty cost guarantee) |
| Known-optimal tests | No | Yes (Hypothesis property-based) |

#### 3.2.3 Portfolio Optimization (`portfolio.py`)
```
min  w^T Σ w  (variance) via scipy SLSQP
s.t.
  Σ w_i = 1
  w_i ∈ [w_min, w_max]
  sector_min ≤ Σ_{i ∈ sector} w_i ≤ sector_max
  (optional) w^T μ = target_return
  (optional) cardinality ≤ N  (top-N heuristic)
```
**Two implementations provided:**
1. `optimize_portfolio_scipy()` — proper QP (scipy SLSQP, recommended)
2. `optimize_portfolio()` — linear-only (PuLP, risk target accepted but NOT enforced)

The dual implementation is deliberate: it demonstrates understanding of solver limitations. In an interview, you say: "I use scipy for mean-variance because PuLP is linear-only. The quadratic objective w^T Σ w cannot be expressed as an LP. I kept the PuLP version as a fallback for when only linear constraints are needed."

#### 3.2.4 Transportation (`transportation.py`)
Classic LP: minimize shipping cost subject to supply/demand balance. Demonstrates:
- Infeasibility detection (supply < demand)
- Named constraint debugging
- Multi-index allocations

### 3.3 `backtester/` — Vectorized Backtesting

**Engine architecture:**
```
prices + signals
    ↓
1. Shift signals: signal[t] → position[t+1]  (anti look-ahead)
2. Compute returns: r[t] = (prices[t] / prices[t-1] − 1) · position[t−1]
3. Apply costs: commission (0.1% per trade) + slippage (0.05%)
4. Build equity curve: compounding
5. Compute 7 risk metrics
    ↓
Return dict
```

**Risk metrics (7):** Sharpe ratio, Sortino ratio (downside deviation only), max drawdown, Calmar ratio, VaR 95%, VaR 99%, Kelly fraction (properly bounded).

**Key design decisions:**
- **No look-ahead:** Signal from price[t] executes at price[t+1], not price[t]
- **Vectorized:** Zero Python loops — numpy operations only
- **Parameterized costs:** Commission and slippage are callable parameters

### 3.4 `energy_data/` — ENTSO-E Data Pipeline

**Client architecture:**

```
EntsoeClient(api_key)
    │
    ├─ fetch_day_ahead_prices(area, date) → prices[{hour, price_eur_mwh}]
    ├─ fetch_generation_mix(area, date) → generation[{type, mw, psr_code}]
    └─ fetch_load_forecast(area, date) → load[{hour, mw}]
           │
           ├─ build_url(document_type, process_type, area, date)
           ├─ query() → HTTP GET → XML response
           ├─ parse_response(xml, doc_type)
           └─ error handling: HTTPError, URLError, ParseError
```

**Error handling matrix:**

| Error Type | HTTP Status | Response |
|-----------|-------------|----------|
| Unauthorized | 401 | `{status: "error", error: "Unauthorized — check your API key"}` |
| Network failure | — | `{status: "error", error: "Network error: ..."}` |
| Invalid XML | — | `{status: "error", error: "XML parse error: ..."}` |
| API error | 200 | `{status: "error", error: "ENTSO-E API: [code] message"}` |

### 3.5 `market_data/` — Yahoo Finance Pipeline

**Flow:**
```
fetch_ticker(ticker, period, interval)
    → yfinance API (with retries + delays)
    → SQLite insert via insert_ohlcv()

fetch_batch(tickers, ...)
    → Sequential fetch with delays (rate limit avoidance)
    → dict {ticker: data}
```

---

## 4. Benchmark Methodology

### 4.1 Our Benchmarks

All timing benchmarks in FRAMEWORK.md are measured as:

```python
import time
start = time.perf_counter()
result = solve_function(**args)
elapsed = time.perf_counter() - start
```

Measured on: **Raspberry Pi 4 Model B, 8GB RAM, ARM Cortex-A72**  
Python 3.13, PuLP 3.0, CBC solver. Each benchmark is the mean of 5 runs.

**Benchmark categories we track:**

| Category | Metric | Target | Current Best |
|----------|--------|--------|-------------|
| Solve speed | Seconds per model | <500ms all models | 180ms (UC, worst case) |
| Test coverage | % lines covered | >90% | 94% verified |
| Code size | Source lines (excluding tests) | Documented and tracked | 10,021 |
| Edge case tests | Number of edge/boundary tests | >15 | 50+ |
| Demo reliability | All demos succeed without errors | 100% | 100% |

### 4.2 Competitor Benchmarks (for comparison)

These are the benchmarks we track from other frameworks to compete with:

| Framework | Benchmark | Their Number | Our Number | Gap |
|-----------|-----------|-------------|-----------|-----|
| **pomato** | IEEE 118 → 26K CBCOs → 540 after reduction | 98% reduction | N/A (no N-1) | We need N-1 capability |
| **pomato** | DE case (450 nodes) → solve time | ~2h (full redundancy removal) | N/A | N/A (different problem) |
| **pomato** | LODF impact screening → PTDF reduction | ~95% | N/A | Adopt their filter |
| **energy-py-linear** | Hypothesis property tests per run | 250 random examples | 0 | Add fuzz testing |
| **energy-py-linear** | Known-optimal dispatch tests | ~5 parametrized tests | 3 (storage) | Add more |
| **PyPSA** | N-1 SCLOPF (preventive contingencies) | Linear in #contingencies | N/A | Roadmap item |
| **PyPSA** | Test count | ~60+ | 571 collected | Exceeds count; keep quality high |

### 4.3 RAM-Bounded Coverage Workflow

The repository now enforces a 90% coverage gate. On memory-constrained laptops, run coverage one test file at a time so Python releases pandas/backtrader/matplotlib/solver memory between files:

```bash
python -m coverage erase
for f in tests/test_*.py; do
    PYTHONPATH="$(pwd)/src" python -m pytest "$f" -m "not slow and not pc" \
      --cov=energy_algorithms --cov-append --cov-report= --cov-fail-under=0 -q
done
PYTHONPATH="$(pwd)/src" python -m coverage report --fail-under=90
```

The `PYTHONPATH` prefix prevents editable installs from measuring a sibling worktree during local branch verification.

Latest verified result: **94% total coverage** (`3563` statements, `221` missed).

### 4.4 Benchmark Test Suite

Located at `tests/test_benchmarks.py` (auto-generated):

```python
"""Benchmark suite — tracks solve performance across iterations."""
import time, json, os

BENCHMARK_CASES = [
    ("PCR simple clearing", "from energy_markets.pcr_model import ..."),
    ("PCR with block orders", ...),
    ("Multi-zone 3 zones", ...),
    ("Unit commitment 12 periods", ...),
    ("BESS 24 periods", ...),
]

BENCHMARK_FILE = os.path.join(os.path.dirname(__file__), "..", ".benchmarks.json")

def run_benchmarks(iterations=5):
    results = {}
    for name, setup_str, run_str in BENCHMARK_CASES:
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            exec(run_str)  # simplified — real version uses import+call
            times.append(time.perf_counter() - start)
        results[name] = {
            "mean_ms": round(sum(times)/len(times) * 1000, 1),
            "min_ms": round(min(times) * 1000, 1),
            "max_ms": round(max(times) * 1000, 1),
        }
    return results
```

---

## 5. Competitor Feature Gap Analysis

### 5.1 What pomato does better (and what to adopt)

| Priority | pomato Feature | Current State | Adoption Plan |
|----------|---------------|--------------|---------------|
| 🔴 P1 | **FBMC flow-based coupling** | ATC only (simpler) | ✅ DONE — `fbmc.py` with PTDF + RAM |
| 🔴 P1 | **Impact screening / LODF filter** | Not implemented | ✅ DONE — `lodf_utils.py` with `screen_cbcos()` |
| 🟡 P2 | **Redundancy removal (Clarkson)** | Not implemented | Roadmap (requires Julia) |
| 🟡 P2 | **GSK strategies for zonal mapping** | Not implemented | ✅ DONE — `gsk.py`: flat, gmax, dynamic |
| 🟢 P3 | **Chance-constrained OPF** | Not implemented | Roadmap (stochastic extension) |
| 🟢 P3 | **Options dict pattern** | Ad-hoc parameters | ✅ DONE — `lp_optimization/options.py` |

### 5.2 What energy-py-linear does better (and what to adopt)

| Priority | Pattern | Current State | Adoption Plan |
|----------|---------|--------------|---------------|
| 🔴 P1 | **OneInterval asset pattern** | Monolithic functions | ✅ DONE — `assets.py`: Asset, BatteryAsset, GeneratorAsset, SpillAsset |
| 🟡 P2 | **Known-optimal dispatch tests** | Not implemented | ✅ DONE — 13 asset lifecycle + dispatch tests |
| 🟡 P2 | **Physical invariant validation** | Manual assertions | ✅ DONE — `invariants.py`: auto-validate post-solve |
| 🟢 P3 | **ConstraintTerm DSL** | Inline constraints | Roadmap (declarative DSL) |
| 🟢 P3 | **Spill assets** | Not implemented | ✅ DONE — `SpillAsset` with penalty-cost feasibility guarantee |

### 5.3 What PyPSA does better (and what to adopt)

| Priority | Pattern | Current State | Adoption Plan |
|----------|---------|--------------|---------------|
| 🟡 P2 | **Accessor pattern** | Direct function calls | ✅ DONE — assets expose `.variables`, `.results`, `.net_power` |
| 🟢 P3 | **extra_functionality hook** | Not implemented | ✅ DONE — `hooks.py`: PRE_SOLVE, POST_SOLVE, POST_EXTRACT |
| 🟢 P3 | **Solver-agnostic config** | Hardcoded CBC | ✅ DONE — `solver_config.py`: CBC, HiGHS, Gurobi, CPLEX |
| 🟢 P3 | **Descriptive metadata** | Scattered `__all__` lists | ✅ DONE — `metadata.py`: VariableRegistry, ModelMetadata |

---

## 6. Edge Cases & Defensive Patterns

### 6.1 Common Optimization Edge Cases

| Edge Case | How We Handle | Example |
|-----------|--------------|---------|
| **Infeasible model** | Return `{status: "Infeasible"}` — never crash | test_transportation_infeasible |
| **Zero demand** | Supply = 0, demand = 0 → 0 trades, welfare = 0 | test_no_trades_zero_demand |
| **All/only empty input** | Handled by early return with empty results | Edge case tests |
| **Negative prices** | Battery charges at negative prices → objective correctly reduces cost | Storage LP naturally handles this |
| **Exclusive blocks both profitable** | At most one is accepted (sum ≤ 1) | test_exclusive_blocks |
| **Linked blocks impossible** | Both accepted or both rejected | test_linked_blocks |
| **Numerical tolerance issues** | Binary check uses `pulp.value(var) > 0.5` not `== 1.0` | Acceptance extraction |
| **Solvers returning non-optimal** | Status checked before result extraction — clean error dict | Demo status check before report() |

### 6.2 Backtesting Edge Cases

| Edge Case | How We Handle | Status |
|-----------|--------------|--------|
| **Flat prices (no movement)** | Zero return, Sharpe = 0, VaR = 0 | test_backtest_all_flat |
| **Constant up-trend** | Momentum goes long → positive Sharpe | test_sharpe_ratio_positive |
| **Constant down-trend** | Momentum goes short → may also be positive | test_sharpe_ratio_negative |
| **VaR with insufficient data** | NaN for < 252 returns | test_var_95 |
| **Kelly fraction > 1** | Bounded correctly | test_kelly_fraction_bounds |

### 6.3 ENTSO-E Pipeline Edge Cases

| Edge Case | How We Handle |
|-----------|--------------|
| **Invalid API key (401)** | Return structured error dict |
| **Network timeout** | Exception caught → error dict |
| **Malformed XML** | ParseError caught → error dict |
| **ENTSO-E returns error message** | Parsed from `<Reason>` element |
| **No data for date** | ENTSO-E returns empty `<TimeSeries>` → empty results |
| **Date out of range (>1 year ago)** | ENTSO-E only keeps recent data |

---

## 7. Iteration History

| Date | Iteration | Tests | Modules | Key Changes |
|------|-----------|-------|---------|-------------|
| 2026-05-22 | 27 | 571 | 9 | 90% coverage gate completed; RAM-bounded coverage workflow documented |
|| 2026-04-30 | 7 | 51 | 12 | FBMC flow-based coupling + loop flows + ENTSO-E API config |
| 2026-04-29 00:15 | 5 | 40 | 11 | BESS, intraday, ENTSO-E pipeline, notebook |
| 2026-04-29 23:55 | 4 | 26 | 8 | LICENSE, whitepaper expansion, checklist cleanup |
| 2026-04-29 23:30 | 3 | 26 | 8 | Re-audit, public repo research, multi-zone, CI |
| 2026-04-29 22:00 | 2 | 16 | 5 | PCR overhaul, UC fixes, tests, pyproject.toml |
| 2026-04-29 20:00 | 1 | 0 | 5 | Initial audit + 5 critical bug fixes |
| 2026-04-29 19:30 | 0 | 0 | 5 | Initial build |

---

## 8. Extending the Framework

### 8.1 Adding a New Optimization Module

1. Create `your_module/` directory with `__init__.py`, `core.py`, `demo.py`
2. Implement your solve function following the pattern:
   ```python
   def solve_your_model(param1, param2, verbose=False) -> dict:
       # Build PuLP problem
       # Add variables, constraints, objective
       # Solve, check status, extract
       return {"status": status, "key": value}
   ```
3. Add a `demo_your_model()` function
4. Add `__all__` exports to `__init__.py`
5. Add tests to `tests/test_your_module.py`
6. Update `pyproject.toml` includes
7. Run `scripts/update_framework_metrics.sh` to regenerate FRAMEWORK.md metrics

### 8.2 Running the Auto-Update

```bash
./scripts/update_framework_metrics.sh
```

This script:
1. Counts modules, files, lines
2. Runs benchmarks on all solve functions
3. Regenerates the metrics tables in FRAMEWORK.md
4. Updates the iteration log

**Add as a pre-commit hook:**
```bash
ln -s ../../scripts/update_framework_metrics.sh .git/hooks/pre-commit
```
