# Optimization Portfolio — Energy Algorithms

[![Tests](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml/badge.svg)](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A portfolio demonstrating **optimization modeling**, **energy market domain knowledge**, and **algorithmic trading** — built for quantitative finance and energy optimization roles at **Euphemia  ** and **Industry**.

## 🎯 Job Requirements & Interview Preparation

This portfolio is laser-targeted at two specific roles. Below is a detailed breakdown of what each role requires, how this repo addresses it, and — crucially — the **edge cases** interviewers use to separate prepared candidates from exceptional ones.

---

### Euphemia   — Junior Optimization Engineer

**Company context:** Euphemia   develops **Euphemia**, the algorithm that clears Pan-European electricity markets (25+ countries, 1M+ orders per session). You'd be joining the team that builds and maintains this algorithm — it's mission-critical infrastructure processing billions in daily trades.

#### Core Requirements — How This Repo Answers

| Requirement | What Interviewers Look For | This Repo's Answer |
|---|---|---|
| **LP/MIP formulation** | Can you translate a business problem into mathematical constraints? | `pcr_model.py` — social welfare LP with binary block orders. `scheduling.py` — unit commitment MIP with min up/down, ramp rates, reserve. `storage.py` — BESS revenue-maximizing LP |
| **Energy market domain** | Do you understand PCR, Euphemia, market coupling, block orders, merit order? | `EUPHEMIA_INTERVIEW.md` — full question bank. `multi_zone.py` — ATC-constrained coupling. `fbmc.py` — FBMC with PTDF/RAM (the real Euphemia algorithm). `block_orders.py` — linked + exclusive group mechanisms |
| **Solver experience** | Have you used optimization solvers? Understand their limitations? | PuLP/CBC used throughout. README documents PuLP's quadratic limitation (why scipy handles portfolio risk). Honest about CBC vs commercial solvers |
| **Python + software engineering** | Can you write production code, not just notebooks? | 571 collected pytest tests with a 90% coverage gate (94% measured), CI/CD (GitHub Actions, 3 Python versions), `pyproject.toml`, `__all__` exports, NumPy docstrings, clean git history |
| **Non-convexity awareness** | Do you know that block orders make the problem non-convex? | Explicitly documented: MCP vs IP pricing gap, make-whole payments, PUN pricing. The README's "Implementation → Real Euphemia Mapping" table shows exactly where we simplify |

#### Edge Cases — What Separates Good from Exceptional

These are the curveball questions Euphemia   interviewers use. Prepare for every one.

**🔴 "Why did you use PuLP instead of Gurobi/CPLEX?"**
- **Good answer:** "PuLP is open-source, great for prototyping and demonstrating understanding."
- **Exceptional answer:** "PuLP is the right choice for a portfolio because it installs with zero friction. But I know that in production Euphemia   uses commercial solvers — and I can discuss the tradeoffs: Gurobi's presolve is far superior for large MIPs, CBC struggles beyond ~100K variables, and the barrier method in CPLEX handles degenerate problems better. I'd be excited to work with production-grade solvers."
- **Repo evidence:** `pyproject.toml` lists `pulp>=3.0`. The `optimize_portfolio_scipy()` docstring explicitly says "For proper Markowitz optimization, use scipy — PuLP can't handle quadratic constraints." This shows you understand solver limitations.

**🔴 "Walk me through how Euphemia clears the market, step by step."**
- **Good answer:** Recite the 5-step algorithm walkthrough from this README.
- **Exceptional answer:** Add: "And here's where it gets interesting — after the welfare-maximizing dispatch is found, Euphemia runs a separate IP pricing pass because block orders create non-convexities. The simple MCP from `max(accepted_prices)` would leave some block order holders with negative surplus, so Euphemia computes prices that minimize make-whole payments while preserving the dispatch. This is why Euphemia uses a MIP rather than a pure LP — and why my `pcr_model.py` documents this as a known limitation."
- **Repo evidence:** The "Known Limitations" section and `EUPHEMIA_INTERVIEW.md` cover IP pricing in depth.

**🔴 "What happens when two zones have the same MCP but the ATC is binding?"**
- **Good answer:** "No flow occurs — prices are equal, no arbitrage incentive."
- **Exceptional answer:** "Correct — no flow. But this is where FBMC differs from ATC. In flow-based market coupling, even with equal zonal prices, the network topology can force counter-intuitive flows due to loop flows and PTDF constraints. My `multi_zone.py` uses simple ATC, but I'm aware that real Euphemia uses FBMC with a full network model — and I'd be eager to work with those constraint matrices."
- **Repo evidence:** `multi_zone.py` docs mention FBMC vs ATC tradeoff.

**🔴 "How would you test a market clearing algorithm?"**
- **Good answer:** "Unit tests with known inputs and expected outputs."
- **Exceptional answer:** "I'd use multiple testing layers: (1) Property-based tests — energy balance must hold exactly, welfare must be ≥ any manual dispatch, MCP must be within supply/demand price range. (2) Edge cases — zero demand, all blocks rejected, at-capacity ATC, negative prices from must-run renewables. (3) Regression tests — golden output files for standard scenarios to catch any changes. (4) Stress tests — scale to thousands of orders and verify solve time stays reasonable. My test suite has 40 tests covering many of these, but I'd add property-based testing with Hypothesis for production."
- **Repo evidence:** `test_pcr_model.py` has edge cases: `test_no_trades_zero_demand`, `test_block_rejected`, `test_exclusive_blocks`, `test_linked_blocks`, `test_energy_balance_exact`.

**🔴 "A trader reports that a block order was accepted when it shouldn't have been. How do you debug?"**
- **Exceptional answer:** "First, I'd reproduce with the exact input data. Then binary search on constraints — remove block groups one by one to isolate which constraint is misbehaving. Check the MIP gap — if the solver terminated early with a non-zero gap, the solution might not be truly optimal. Check for numerical issues — PuLP's default tolerance is 1e-6, and block orders near the marginal price can flip due to floating-point. If it's a linked block issue, verify the group constraint is `==` not `>=`. I'd also check if the order was submitted with the correct group identifier — these bugs are often data issues, not algorithm bugs."
- **Repo evidence:** The 13 issues fixed and documented in `AGENTS.md` show exactly this debugging methodology.

**🔴 "Explain the difference between social welfare, consumer surplus, and producer surplus. Why do we maximize welfare, not minimize price?"**
- **Exceptional answer:** "Consumer surplus = area between demand curve and price. Producer surplus = area between price and supply curve. Social welfare = both summed. We maximize welfare — not minimize price — because minimizing price would dispatch only the cheapest generators regardless of demand value, causing shortages. Welfare maximization balances willingness-to-pay against production cost. This is literally the Euphemia objective function."
- **Repo evidence:** `market_clearing.py` computes all three surpluses and visualizes them in the supply/demand stack plot.

**🔴 "What's your experience with large-scale data? Euphemia processes millions of orders."**
- **Exceptional answer:** "My portfolio works with small datasets for demonstration, but I understand the scaling challenges: sparse matrix representations for the constraint matrix, warm-starting from previous day's solution, decomposition methods (Benders for multi-period, Lagrangian relaxation for zonal coupling). I'd be excited to learn Euphemia  's production architecture."
- **Honesty matters here:** Don't claim experience you don't have. Euphemia   respects intellectual honesty.

---

### INDUSTRY Belgium — Algorithmic Trader (Short-Term Power, Uccle)

**Company context:** INDUSTRY Belgium's short-term trading desk in Uccle, Brussels runs automated strategies for **Battery Energy Storage Systems (BESS)**, renewables (wind/solar), and proprietary trading across **Day-Ahead**, **Intraday**, **Ancillary Services**, and **Balancing** markets. The mandate is to transition the trading floor to a fully automated, data-driven operation.

**Role:** Full lifecycle — signal research → strategy coding → backtesting → production deployment → framework development. You own the algorithm from idea to P&L.

#### Core Requirements — How This Repo Answers

| Requirement | What They Look For | This Repo's Answer |
|---|---|---|
| **Production Python** | Can you deploy reliable code that runs unattended? | Full package, CI/CD (3 Python versions), 571 tests, **94% measured coverage** (90% gate), structured error handling, `pyproject.toml` |
| **BESS modeling** | Do you understand round-trip efficiency, SoC dynamics, arbitrage? | `storage.py` — BESS revenue-maximizing LP with η=90%, 30-day arbitrage demo, +€143/MWh hour-of-day spread |
| **Backtesting** | Look-ahead, survivorship, transaction costs, walk-forward? | 7 risk metrics (Sharpe, Sortino, VaR95/99, Kelly, Calmar, Max DD, CVaR), signal-shift anti-look-ahead, commission + slippage |
| **ENTSO-E data pipelines** | Can you build reliable market data infrastructure? | REST client with structured error matrix (401, 503, XML parse, timeout), SQLite persistence, live-data-graceful-degradation pattern |
| **Intraday trading** | Do you understand continuous order books, cross-border spreads? | `intraday.py` — order book matching with price-time priority, cross-border BE↔FR↔DE↔NL demo (max spread €13/MWh May 3) |
| **Day-Ahead markets** | Do you understand PCR/Euphemia, MCP, social welfare? | `pcr_model.py` — 5-stage Euphemia walkthrough, social welfare LP with binary block orders, known limitations documented |
| **ML / data analytics** | Time-series, signal extraction, forecasting? | 3 strategy types, 26-day real Belgian data on hour-of-day, solar duck, calendar spread, CO₂-adjusted PCR pricing |
| **Risk management** | VaR, drawdown, position sizing? | All 7 metrics implemented. Risk-aware portfolio optimization with cardinality constraints |
| **Framework development** | Can you design and maintain a large codebase? | Hexagonal architecture (domain/ports/adapters), hooks system, solver-config factory, solver-agnostic design |

#### Coverage Gaps — Honest Assessment

| Requirement | Status | What To Say In Interview |
|---|---|---|
| **Ancillary Services** (FCR, aFRR, mFRR) | ❌ Not modeled | "I understand the products — FCR is symmetric power, aFRR is 5-min activated reserve, mFRR is manual. I haven't coded a bidding strategy because the market rules differ per TSO, but the optimization framework (LP with reserve constraints) maps directly. I'd model it as a joint energy+reserve UC, with binary commitment for each reserve product and a deterministic activation cost in the objective." |
| **Wind generation modeling** | ❌ Not modeled | "I'd approach it via stochastic optimization — scenarios from ECMWF forecasts with quantile regression, then a two-stage SP where day-ahead commitment is here-and-now and intraday re-dispatch is wait-and-see. My `stochastic.py` shows VSS/EVPI calculation; the pattern extends." |
| **Proprietary trading signals** | ⚠️ Basic strategies | "The 3 strategies (momentum, mean-reversion, SMA) demonstrate the framework. In production I'd build a signal library — order flow imbalance, cross-border spread, wind forecast error, solar ramp-rate predictions." |
| **Monitoring / observability** | ❌ Not deployed | "My pipeline design includes structured error handling and SQLite state persistence. For production I'd add Prometheus metrics (P&L, fills, API latency) and Grafana dashboards." |
| **Low-latency** | ❌ Not addressed | "My strategies are hourly resolution — not HFT. For sub-minute execution I'd use C++ or Rust kernels with memory-mapped IPC, but the business logic lives in Python with the runtime engine optimized separately." |

#### Edge Cases — What Separates Good from Exceptional

**🔴 "Your hour-of-day spread shows +€143/MWh on Belgian data. Walk me through what happens when Doel 4 trips."**
- **Exceptional answer:** "The hour-of-day strategy buys the overnight trough (€10-30/MWh) and sells the morning peak. If Doel 4 (1 GW nuclear) trips at 06:00 during the ramp, Belgian prices spike instantly — the morning sell order executes at a windfall profit. But the real risk: if the trip happens at 02:00 when I'm accumulating the long position, I'm buying into a price spike from a supply crash, not the normal trough. Real-time outage monitoring from ENTSO-E is essential to pause or reverse a position when a large generator trips. My pipeline structure supports this — the cached data pattern degrades gracefully, but live outage feeds would need WebSocket connections or sub-minute REST polling."

**🔴 "How would you optimize a BESS bidding for both day-ahead energy AND aFRR reserve simultaneously?"**
- **Exceptional answer:** "Joint optimization with two decision stages. Stage 1 (day-ahead): reserve commitment — bid aFRR capacity. Stage 2 (real-time): energy trading with reduced SoC range. The tradeoff: holding reserve capacity reduces arbitrage revenue (you can't charge/discharge fully if you might need to deliver reserve). Optimal split is a function of reserve price vs energy spread. Mathematically: max[ arbitrage_rev + reserve_price × capacity_reserved ] subject to SoC dynamics, with the aFRR delivery reducing η. My `storage.py` is pure-arbitrage, but adding reserve as a separate market with capacity constraint on SoC is a natural extension."

**🔴 "Solar duck curve — your strategy returned -0.94% in spring. Why does it underperform, and how would you fix it?"**
- **Exceptional answer:** "The solar duck curve captures the mid-day price depression from solar generation. In spring (Apr-May), solar is ramping up but demand is low, so the duck belly is deep and wide. My simple strategy buys the belly and sells shoulders — but the profit margin shrinks as solar penetration increases (more solar → lower mid-day prices, but also lower shoulder prices as the solar ramp widens). To fix: add a wind-solar balance indicator — on high-wind days the shoulder ramps are steeper. Also add a CCGT startup cost proxy: if clean spark spreads are negative, the evening ramp is steeper because fewer gas plants are online to cover it."

**🔴 "A trader says the aFRR activation signal arrived but your BESS didn't respond. How do you debug?"**
- **Exceptional answer:** "Three layers: (1) Telemetry — did the BESS controller receive the signal? Check MQTT/API logs. (2) SoC state — was the battery at a state where it could deliver? If SoC was 0% and the signal demanded up-regulation, it physically can't deliver — that's a scheduling error in the day-ahead reserve bid, not a real-time bug. (3) Latency — how long from signal to power output? If it's >30s for aFRR (requires 5-min response), the algorithm itself may be slow. I'd add a watchdog: if no aFRR response within 10s, revert to a default pre-approved ramp schedule. This recovery logic is not in my repo (fair for a portfolio), but I'd implement it as a state machine with fallback states."

**🔴 "Walk me through how you'd build a signal from wind forecast errors."**
- **Exceptional answer:** "I'd start with ECMWF ensemble forecasts for Belgian wind zones and compare against actual SCADA wind output (ENTSO-E Actual Generation). The forecast error `e(t) = forecast(t) - actual(t)` is mean-reverting — if the forecast says 2 GW but actual is 1.5 GW, prices should rise as the market re-prices the shortage. The signal: `e(t) - MA(e, 6h)` — large positive errors (over-forecasting) mean wind is below prediction, buy. Large negative errors, sell. Key refinement: separate offshore vs onshore — offshore errors are larger but faster-reverting. My pipeline's `energy_data/` structure is designed to ingest this; adding ECMWF feed is a new adapter."

**🔴 "Your repo has 571 tests at 94% coverage. An algo trading system goes live and loses €10K on day one. What failed that your tests didn't catch?"**
- **Exceptional answer:** "Three things tests miss: (1) **Data quality** — a bad tick from ENTSO-E (negative price that's actually a missing value encoded as -1) passes all type checks but corrupts the P&L. My tests use clean golden data. (2) **Latency** — tests assume instantaneous execution; real markets have slippage, queue position, partial fills. My slippage model is a flat 0.1% — unrealistic. (3) **Regime change** — the strategy was fit on April data but May had a different wind/solar pattern. Tests validate correctness, not profitability. For a trading system, I'd add: historical replay testing (walk-forward), synthetic data stress tests, and a shadow-mode period where the algo runs alongside the trader without executing."

**🔴 "How would you design the monitoring dashboard for your live algo?"**
- **Exceptional answer:** "Five panels: (1) **Position & P&L** — current positions per market/asset, daily and cumulative P&L. (2) **Execution quality** — slippage vs limit price, fill rate, order latency. (3) **Market context** — current Day-Ahead/Intraday prices, BE↔FR↔DE spreads, wind/solar generation. (4) **Risk metrics** — live VaR, current drawdown, position limits utilization. (5) **Health** — API connectivity status, data freshness, strategy running/stopped. I'd add a separate alert panel: 'Position exceeds risk limit', 'Data feed stale >5min', 'Strategy unresponsive >1min'. This is infrastructure work, not algo work — but it's essential for the INDUSTRY role, which explicitly mentions collaboration with manual traders who need these dashboards."

---

### Cross-Cutting Interview Preparation

**The Portfolio Walkthrough** — When an interviewer says "walk me through this repo":
1. Open with: "This is my optimization portfolio — built for energy algorithmic trading roles. The standout is `domain/markets/` (PCR/Euphemia) and `domain/optimization/storage.py` (BESS). 571 tests, 94% coverage, hexagonal architecture with ports/adapters."
2. Show the **Industry demo results** — the hour-of-day spread (+€143), cross-border spreads, BESS arbitrage. "These run on real Belgian ENTSO-E data."
3. Mention the **honest coverage gaps** table above — "I know what I haven't built yet, and I can discuss exactly how I'd extend."
4. If they ask about production: "The solver_config.py supports Gurobi/CPLEX/HiGHS with one config change. Switching from CBC to commercial for large-scale is trivial."

**Technical Questions They Will Ask — Prep For:**
- "How would you handle a data gap in the ENTSO-E feed?" → Cache-with-TTL fallback to previous day's profile, with an alert flag.
- "What happens if the CBC solver doesn't converge in time for the market deadline?" → Time-limited solve with MIP gap target, then use the best feasible solution.
- "How do you ensure the backtest reflects real trading?" → Slippage model, commission, signal-shift. The real gap is market impact — my model assumes the algo doesn't move prices.
- "Your BESS model has no binary for simultaneous charge/discharge. Why?" → The objective penalizes it naturally (η² efficiency loss). At zero prices, could be optimal — acknowledged limitation.

**Behavioral Questions — Be Ready For:**
- "Tell me about a bug you found and fixed." → The linked blocks constraint bug. Block orders that should have been linked weren't — the equality constraint was missing. It's a great story about constraint debugging methodology.
- "Describe a time you had to prioritize between features." → "I chose to push coverage to 90% before adding new features. 571 tests mean I can refactor without fear."
- "What's something in this repo you're not proud of?" → The hardcoded 0.001 tolerance, and that ancillary services aren't modeled. Shows awareness and honesty.

---

### Quick Reference: Module → INDUSTRY Belgium Role Mapping

| Module (new hex path / old flat path) | Primary INDUSTRY Relevance |
|---|---|
| `domain/optimization/storage.py` / `lp_optimization/storage.py` | ⭐⭐⭐ **BESS** — battery storage LP for energy arbitrage |
| `domain/markets/intraday.py` / `energy_markets/intraday.py` | ⭐⭐⭐ **Intraday** — continuous order book matching, cross-border spreads |
| `domain/markets/pcr_model.py` / `energy_markets/pcr_model.py` | ⭐⭐ **Day-Ahead** — market coupling understanding, MCP, social welfare |
| `domain/markets/multi_zone.py` / `energy_markets/multi_zone.py` | ⭐⭐ **Cross-border** — BE↔FR↔DE↔NL spread trading |
| `domain/markets/fbmc.py` / `energy_markets/fbmc.py` | ⭐⭐ **Flow-based** — PTDF/RAM, loop flows, CBCO screening |
| `domain/trading/` / `backtester/` | ⭐⭐⭐ **Backtesting** — 7 risk metrics, walk-forward, signal-shift |
| `domain/trading/strategies/` / `strategies/` | ⭐⭐⭐ **Signals** — hour-of-day, calendar spread, solar duck |
| `adapters/entsoe_client.py` / `energy_data/` | ⭐⭐⭐ **Data** — ENTSO-E REST, SQLite, graceful degradation |
| `domain/optimization/scheduling.py` / `lp_optimization/scheduling.py` | ⭐⭐ **UC** — MIP for thermal assets, ramp rates, min up/down |
| `domain/optimization/assets.py` / `lp_optimization/assets.py` | ⭐⭐⭐ **Asset modeling** — Battery, Generator, SpillAsset patterns |
| `domain/emissions.py` | ⭐⭐ **CO₂** — EUA pass-through pricing, clean spark/dark spread |

**Coverage gap:** Ancillary Services (FCR, aFRR, mFRR) — not yet implemented. See interview response in gaps table above.

## 📖 Framework Documentation & Knowledge Base

**FRAMEWORK.md** explains the full architecture, data flow, competitor comparisons, benchmark methodology, and iteration history. Auto-updated with each iteration.

**`knowledge/`** is a comprehensive curriculum (12 files, 3,610 lines) covering theory, edge cases, interview Q&A, and self-assessment:
- Market coupling (PCR, Euphemia, FBMC), block orders, PTDF deep dive, LP/MIP theory
- Unit commitment, storage optimization, backtesting methodology, ENTSO-E platform
- Competitor analysis (pomato, PyPSA, energy-py-linear) with gap resolution status
- Interview Q&A with 20 questions and exceptional answers, 50-question self-assessment quiz

## 📦 Architecture

```
Energy_Algorithms/
├── energy_markets/        ★ HERO — PCR, FBMC, block orders, intraday, LODF screening
│   ├── pcr_model.py       Social welfare LP with binary block orders
│   ├── fbmc.py            FBMC flow-based coupling (PTDF + RAM, loop flows) ★
│   ├── multi_zone.py      Multi-zone coupling with ATC constraints
│   ├── lodf_utils.py      LODF computation + N-1 CBCO screening ★
│   ├── gsk.py             GSK strategies (flat, gmax, dynamic) ★
│   ├── block_orders.py    Linked, exclusive, and simple block orders
│   ├── intraday.py        Continuous intraday trading order book matching
│   └── market_clearing.py Supply/demand stack equilibrium + visualization
├── lp_optimization/        Core LP/MIP + infrastructure
│   ├── scheduling.py      Unit commitment MIP (min up/down, ramp, reserve)
│   ├── storage.py         BESS battery storage LP
│   ├── portfolio.py       Mean-variance (scipy SLSQP) + linear (PuLP)
│   ├── transportation.py  Classic transportation LP
│   ├── assets.py          OneInterval pattern: Battery, Generator, SpillAsset ★
│   ├── invariants.py      Post-solve physical invariant validation ★
│   ├── hooks.py           PRE_SOLVE/POST_SOLVE event hooks ★
│   ├── solver_config.py   CBC, HiGHS, Gurobi, CPLEX with fallback ★
│   ├── options.py         Centralized get/set/reset config ★
│   └── metadata.py        VariableRegistry, ModelMetadata introspection ★
├── energy_data/            ENTSO-E Transparency Platform API client
│   ├── fetcher.py         REST client with structured error handling
│   ├── config.py          Environment-driven live API config ★
│   └── demo.py            Demo with realistic Belgian market data
├── backtester/             Vectorized backtesting engine + 7 risk metrics
├── strategies/             3 signal-based strategies
├── market_data/            Yahoo Finance → SQLite pipeline
├── knowledge/              12-file theory + Q&A curriculum ★
├── tests/                  571 collected pytest tests (90% gate, 94% measured cov) ★
├── notebooks/              Walkthrough notebook for Euphemia   demo
└── .github/workflows/      CI: Python 3.11–3.13
```

### ✨ New: Industry Trading Demo

A dedicated **energy algorithmic trading demo** (`src/energy_algorithms/application/industry_demo.py`) runs all trading strategies on 26 days of **real Belgian ENTSO-E data**:

| Strategy | Period | Key Result | Literature |
|----------|--------|------------|------------|
| **Hour-of-day spread** | 26 days | +€143.84/MWh avg daily, 67% win rate | Kiesel & Paraschiv (2021) |
| **Solar duck curve** | Apr-May 2026 | +€0.28/MWh avg peak premium | EEX market patterns |
| **Calendar spread** (3d/7d MA) | 26 days | +265%, Sharpe 8.4, 4 trades | Commodity momentum |
| **CO₂-adjusted PCR** (€70/t EUA) | Gas-marginal day | MCP €60→€78, CO₂ pass-through | Clean spark/dark spread |
| **BESS storage** (historical_analysis.py) | 30 days | 2 battery sizes, cross-border spreads | Energy arbitrage |
| **Cross-border spreads** | BE↔FR↔DE↔NL | Max spread €13/MWh (May 3) | Market coupling theory |

Run: `python3 -m energy_algorithms.application.industry_demo`

### ✨ New: 90% Coverage Gate Without Laptop RAM Spikes

Coverage is now enforced at **90%** in `pyproject.toml`; the latest bounded verification measured **94% total coverage**. Because the full suite imports plotting, backtrader, pandas, solvers, and application demos, the recommended local workflow is file-by-file coverage append:

```bash
python -m coverage erase
for f in tests/test_*.py; do
  PYTHONPATH="$(pwd)/src" python -m pytest "$f" -m "not slow and not pc" \
    --cov=energy_algorithms --cov-append --cov-report= --cov-fail-under=0 -q
done
PYTHONPATH="$(pwd)/src" python -m coverage report --fail-under=90
```

This keeps each test module in a fresh Python process so memory is released between files. The `PYTHONPATH` prefix pins imports to the current checkout when an editable install points at another worktree.

### ✨ New: TradePro — backtrader + OpenSpace Integration

> **Full benchmark comparison vs PyPSA, POMATO, backtrader, LEAN, freqtrade:**
> See [`docs/BENCHMARK_REPORT.md`](docs/BENCHMARK_REPORT.md) with 4 professional plots.

Our repo now **combines the best of multiple frameworks** instead of depending on any single one:

| Framework | What We Use From It | What We Add |
|-----------|--------------------|-------------|
| **backtrader** (5.5K★) | Event-driven engine, order types, commission models, walk-forward analyzers | ENTSO-E data feeds, energy strategies (hour-of-day, solar duck) |
| **OpenSpace** (academic) | Agent-based market simulation concept | PCR/Euphemia clearing with CO₂ costs, agent learning |
| **bt (fja)** (2K★) | Strategy comparison via algo-chaining | Energy-specific strategy composition |

**backtrader results on 26 days real ENTSO-E data:**

| Strategy | Engine | Trades | Win Rate | Return | 
|----------|--------|--------|----------|--------|
| Hour-of-Day Spread | backtrader | 32 | 68.75% | +75.09% |
| Solar Duck Curve | backtrader | 218 | 40.7% | -0.94% (spring) |

**OpenSpace market simulation (6-agent PCR):** Avg MCP €16.17/MWh, €9.6M welfare, generators learn optimal bidding.

Run: `python3 -m energy_algorithms.application.tradepro_demo`

## 🚀 Quick Start

```bash
git clone git@github.com:GerasimosG/Energy_Algorithms.git
cd Energy_Algorithms

# Conda (primary — recommended)
conda env create -f environment.yml
conda activate energy-algorithms
pip install -e ".[live]"

# Or pip (fallback)
# pip install -e ".[dev]"

# Run the showcase modules
python -m energy_markets.demo      # ★ PCR, block orders, market stack
python -m lp_optimization.demo     # Transportation, portfolio, unit commitment
python -m backtester.demo          # Backtesting + risk metrics
python -m strategies.demo          # Trading strategies
python -m market_data.demo         # Data pipeline

# Run tests
pytest tests/ -v
```

## ★ Energy Markets Module — Euphemia Connection

The `energy_markets/` module demonstrates deep understanding of the **PCR (Pan-European Coupling)** market clearing algorithm that powers **Euphemia** — the algorithm Euphemia   develops for 25+ European power exchanges. This section presents it as a mini-whitepaper: problem formulation, algorithm walkthrough, and honest limitations.

### Problem Formulation

The market coupling problem is a **social welfare optimization**:

**Given:**
- Supply step orders from generators: `(p_i^s, q_i^s)` — price and quantity offered
- Demand step orders from consumers: `(p_j^d, q_j^d)` — price and quantity bid
- Binary block orders: `(p_k^b, q_k^b, y_k ∈ {0,1})` — all-or-nothing
- Inter-zonal ATC: `ATC_{z1,z2}` — max flow between zones

**Find** acceptance variables `x_i^s ∈ [0,1]`, `x_j^d ∈ [0,1]`, `y_k ∈ {0,1}` that:

```
max Σ_j(p_j^d · q_j^d · x_j^d) − Σ_i(p_i^s · q_i^s · x_i^s) − Σ_k(p_k^b · q_k^b · y_k)
```

**Subject to:**
- **Energy balance:** `Σ_i(q_i^s · x_i^s) + Σ_k(q_k^b · y_k) = Σ_j(q_j^d · x_j^d)` (supply = demand, exact match)
- **Linked blocks:** `y_a = y_b` for blocks a,b in same `group` (cascading hydro cannot partially accept)
- **Exclusive blocks:** `Σ_{k ∈ group} y_k ≤ 1` (at most one configuration selected)
- **Zonal flow:** `|flow_{z1→z2}| ≤ ATC_{z1,z2}`
- **Domain:** `x_i^s, x_j^d ∈ [0,1]`, `y_k ∈ {0,1}`

**Market Clearing Price:** `MCP = max({p | x > 0})` — highest accepted price sets the uniform clearing price.

### Algorithm Walkthrough

```
1. BUILD ORDER STACKS
   Supply orders sorted ascending by price (cheapest first)
   Demand orders sorted descending (highest willingness-to-pay first)
   → Forms the classic "merit order" supply curve

2. FORMULATE LP
   Objective: maximize social welfare
   Constraints: energy balance, block group constraints, ATC limits

3. SOLVE (PuLP → CBC solver)
   Returns: continuous acceptance fractions + binary block decisions

4. EXTRACT MCP
   Scan all accepted supply orders
   MCP = highest accepted supply price
   (Real Euphemia: IP pricing for non-convex block orders)

5. COMPUTE SURPLUS
   Consumer surplus = area between demand curve and MCP
   Producer surplus = area between MCP and supply curve
   Social welfare = consumer + producer surplus
```

### Implementation → Real Euphemia Mapping

| Concept | This Implementation | Real Euphemia | Gap |
|---------|-------------------|---------------|-----|
| Social welfare max | LP with continuous vars | MIP with integer vars | Model complexity |
| Supply/demand curves | Piecewise linear from step orders | Full order book step functions | Fidelity |
| Block orders | Binary (all-or-nothing) | Full: simple, linked, exclusive, flexible | No flexible blocks |
| Linked blocks | Equality constraints (`group=`) | Complex dependency graphs | Our model is simpler |
| Exclusive blocks | Sum-≤1 constraints (`excl_*`) | Mutually exclusive configurations | Equivalent approach |
| Multi-zone coupling | ATC-constrained flows | FBMC (flow-based) | ATC simpler than FBMC |
| MCP pricing | `max(accepted_prices)` | IP pricing (non-convexity aware) | No make-whole payments |
| Unit commitment | Separate MIP (`scheduling.py`) | Integrated into welfare max | Modular vs monolithic |

### Why This Matters for Euphemia  

- **Domain fluency:** You can discuss PCR, Euphemia, social welfare, block orders, IP pricing, FBMC vs ATC, and PUN pricing from first principles — not just from reading papers, but from implementing them.
- **MIP competence:** Unit commitment with binary variables, ramp rates, min up/down, and initial conditions in `scheduling.py` mirrors the Euphemia   workload of building optimization models.
- **Honest about gaps:** Interviewers respect candidates who know what they don't know. The known limitations below are documented for interview transparency.

> See `energy_markets/EUPHEMIA_INTERVIEW.md` for the full interview question bank and talking points.

### 🎯 Euphemia Gap Analysis — My Implementation vs Euphemia   Production

This table goes deeper than the mapping above. It's the honest technical assessment you'd discuss in an interview:

| Feature | My Implementation | Production (Euphemia) | Gap | Bridge |
|---|---|---|---|---|
| **Social welfare LP** | Continuous vars, linear objective | MIP with integer vars | Model complexity | Understand MIP formulation, can extend |
| **IP pricing** | `max(accepted_prices)` = simple MCP | IP pricing pass for make-whole payments | ⚠️ No make-whole | Theory covered in `EUPHEMIA_INTERVIEW.md`. First thing I'd learn |
| **Flow-Based MC** | `fbmc.py`: PTDF × net position ≤ RAM, LODF, GSK | Full FBMC + remedial actions, CBCO management | LODF ✓ GSK ✓ Need: remedial actions | Implementation exists; needs production hardening |
| **Block orders** | Simple, linked (`group=`), exclusive (`excl_*`) | Full: simple, linked, exclusive, flexible, min-acceptance | No flexible blocks | Flexible = continuous ∈ [min%, 100%] — trivial extension |
| **Multi-period** | 24h UC (`scheduling.py`), 7d multi-day | Full inter-temporal + hydro cascades, must-run | Storage ✓ Hydro cascades missing | Linear extension of storage pattern |
| **Scalability** | 10-zone, 50-gen — <5s on Pi | Millions of orders, 25+ zones, sub-minute | 3-4 orders of magnitude | Understand theory (sparse matrices, decomposition). Production experience is the gap |
| **Solvers** | CBC + HiGHS (via `highspy 1.14`) | Gurobi/CPLEX with tuned parameters | Licensing | Know tradeoffs: presolve, barrier, crossover, MIP gap tuning |
| **Data pipeline** | Demo data + ENTSO-E API client | Real-time feeds from multiple PXs + SCADA + weather | Live integration | ENTSO-E structure correct; needs caching, alerting, failover |

**Interview-ready response when asked about gaps:**
> *"I've implemented the core concepts — social welfare LP, block orders, FBMC with PTDF/LODF, multi-zone coupling — in clean hexagonal architecture with 571 collected tests, a 90% coverage gate, and 5 solvers available including HiGHS. I understand where my implementation simplifies reality: IP pricing, production scalability, and commercial solvers. I'd rather be honest about the gaps than pretend otherwise. The fundamentals are solid; the production experience is what I'm applying to gain."*

### Known Limitations (Documented for Interview Transparency)

- ⚠ **MCP pricing**: Uses simple `max(accepted_prices)` — real Euphemia uses IP pricing
  for non-convex block orders (discussed in `EUPHEMIA_INTERVIEW.md`)
- ⚠ **Single-period**: No inter-temporal constraints (storage, hydro reservoirs)
- ⚠ **No flow-based coupling**: ATC is simpler than FBMC; FBMC is discussed in docs
- ⚠ **No PUN pricing**: Italy's single national price not modeled

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Python modules | 18 |
| Total source files | 35+ |
| Test files | 10 |
| Test cases | 571 collected (RAM-bounded fast coverage gate: 94%, fail-under 90) |
| Knowledge base | 12 files, 3,610 lines |
| Risk metrics | 7 (Sharpe, Sortino, maxDD, Calmar, VaR95, VaR99, Kelly) |
| Optimization solvers | 2+ (PuLP/CBC, scipy SLSQP, HiGHS/Gurobi/CPLEX configs) |
| Competitor gaps resolved | 12/14 (Clarkson/Chance-OPF: roadmap) |

## 🧪 Testing

```bash
pytest tests/ -v --cov=energy_algorithms --cov-report=term-missing
```

## 📚 References

- [EUPHEMIA Public Description](https://www.epexspot.com/en/euphemia) — PCR market coupling algorithm
- [PyPSA](https://github.com/PyPSA/PyPSA) — Python for Power System Analysis (reference architecture)
- [POMATO](https://github.com/richard-weinhold/pomato) — Power Market Tool (FBMC reference)

## 🔒 Status

**Production-ready** — 571 tests, 94% coverage, hexagonal architecture. Ready for portfolio submission.

## Author

Built for quantitative optimization and energy market role applications at Euphemia   and Industry.
