# Interview Preparation — Euphemia   & Industry Belgium

> Detailed interview prep material: company context, JD mapping, edge-case questions, and "exceptional" answers for the two target roles. **Companion to the main [README](../README.md).** This file is reference material — the README is the entry point.

---

This portfolio is laser-targeted at two specific roles. Below is a detailed breakdown of what each role requires, how this repo addresses it, and — crucially — the **edge cases** interviewers use to separate prepared candidates from exceptional ones.

---

### Euphemia   — Junior Optimization Engineer

**Company context:** Euphemia   develops **Euphemia**, the algorithm that clears Pan-European electricity markets (25+ countries, 1M+ orders per session). You'd be joining the team that builds and maintains this algorithm — it's mission-critical infrastructure processing billions in daily trades.

#### Core Requirements — How This Repo Answers

| Requirement | What Interviewers Look For | This Repo's Answer |
|---|---|---|
| **LP/MIP formulation** | Can you translate a business problem into mathematical constraints? | `pcr_model.py` — social welfare LP with binary block orders. `scheduling.py` — unit commitment MIP with min up/down, ramp rates, reserve. `storage.py` — BESS revenue-maximizing LP. `ancillary.py` — joint BESS + FCR + aFRR LP |
| **Energy market domain** | Do you understand PCR, Euphemia, market coupling, block orders, merit order? | `EUPHEMIA_INTERVIEW.md` — full question bank. `multi_zone.py` — ATC-constrained coupling. `fbmc.py` — FBMC with PTDF/RAM (the real Euphemia algorithm). `block_orders.py` — linked + exclusive group mechanisms |
| **Solver experience** | Have you used optimization solvers? Understand their limitations? | PuLP/CBC used throughout. README documents PuLP's quadratic limitation (why scipy handles portfolio risk). Honest about CBC vs commercial solvers |
| **Python + software engineering** | Can you write production code, not just notebooks? | 578 collected pytest tests with a 90% coverage gate (92.55% measured), CI/CD (GitHub Actions, 3 Python versions), `pyproject.toml`, `__all__` exports, NumPy docstrings, clean git history |
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
| **Production Python** | Can you deploy reliable code that runs unattended? | Full package, CI/CD (3 Python versions), 578 tests, **92.55% measured coverage** (90% gate), structured error handling, `pyproject.toml` |
| **BESS modeling** | Do you understand round-trip efficiency, SoC dynamics, arbitrage? | `storage.py` — BESS revenue-maximizing LP with η=90%, 30-day arbitrage demo, +€143/MWh hour-of-day spread |
| **Backtesting** | Look-ahead, survivorship, transaction costs, walk-forward? | 7 risk metrics (Sharpe, Sortino, VaR95/99, Kelly, Calmar, Max DD, CVaR), signal-shift anti-look-ahead, commission + slippage |
| **ENTSO-E data pipelines** | Can you build reliable market data infrastructure? | REST client with structured error matrix (401, 503, XML parse, timeout), SQLite persistence, JSON disk cache with TTL, live-data-graceful-degradation pattern |
| **Intraday trading** | Do you understand continuous order books, cross-border spreads? | `intraday.py` — order book matching with price-time priority, cross-border BE↔FR↔DE↔NL demo (max spread €13/MWh May 3) |
| **Day-Ahead markets** | Do you understand PCR/Euphemia, MCP, social welfare? | `pcr_model.py` — 5-stage Euphemia walkthrough, social welfare LP with binary block orders, known limitations documented |
| **Ancillary services (FCR, aFRR)** | Joint energy + reserve bidding, revenue stacking? | `ancillary.py` — joint BESS + FCR (symmetric) + aFRR (capacity) LP, revenue decomposition, SoC headroom constraints. mFRR remains the only fully missing product |
| **ML / data analytics** | Time-series, signal extraction, forecasting? | 3 strategy types, 26-day real Belgian data on hour-of-day, solar duck, calendar spread, CO₂-adjusted PCR pricing. `experiment_tracker.py` for research workflow |
| **Risk management** | VaR, drawdown, position sizing? | All 7 metrics implemented. Risk-aware portfolio optimization with cardinality constraints |
| **Framework development** | Can you design and maintain a large codebase? | Hexagonal architecture (domain/ports/adapters), hooks system, solver-config factory, solver-agnostic design. 11 domain files route through one `solve_model()` |

#### Coverage Gaps — Honest Assessment

| Requirement | Status | What To Say In Interview |
|---|---|---|
| **FCR (symmetric) + aFRR (capacity-only)** | ✅ Implemented in `ancillary.py` | "Joint LP with SoC headroom constraints. FCR commits symmetric capacity, aFRR commits directional capacity. Revenue decomposition by stream. mFRR is the only fully missing product — TSO-specific activation rules differ per country and would need separate handling." |
| **mFRR (manual reserve)** | ❌ Not modeled | "Manual activation (15-min response), TSO-specific rules. Same LP pattern as aFRR but with a different probability model. Trivial extension of `ancillary.py` once I had real Elia mFRR clearing data." |
| **Wind generation modeling** | ❌ Not modeled | "I'd approach it via stochastic optimization — scenarios from ECMWF forecasts with quantile regression, then a two-stage SP where day-ahead commitment is here-and-now and intraday re-dispatch is wait-and-see. My `stochastic.py` shows VSS/EVPI calculation; the pattern extends." |
| **Proprietary trading signals** | ⚠️ Basic strategies | "The 3 strategies (momentum, mean-reversion, SMA) demonstrate the framework. In production I'd build a signal library — order flow imbalance, cross-border spread, wind forecast error, solar ramp-rate predictions." |
| **Monitoring / observability** | ❌ Not deployed | "My pipeline design includes structured error handling and SQLite state persistence. For production I'd add Prometheus metrics (P&L, fills, API latency) and Grafana dashboards." |
| **Low-latency** | ❌ Not addressed | "My strategies are hourly resolution — not HFT. For sub-minute execution I'd use C++ or Rust kernels with memory-mapped IPC, but the business logic lives in Python with the runtime engine optimized separately." |

#### Edge Cases — What Separates Good from Exceptional

**🔴 "Your hour-of-day spread shows +€143/MWh on Belgian data. Walk me through what happens when Doel 4 trips."**
- **Exceptional answer:** "The hour-of-day strategy buys the overnight trough (€10-30/MWh) and sells the morning peak. If Doel 4 (1 GW nuclear) trips at 06:00 during the ramp, Belgian prices spike instantly — the morning sell order executes at a windfall profit. But the real risk: if the trip happens at 02:00 when I'm accumulating the long position, I'm buying into a price spike from a supply crash, not the normal trough. Real-time outage monitoring from ENTSO-E is essential to pause or reverse a position when a large generator trips. My pipeline structure supports this — the cached data pattern degrades gracefully, but live outage feeds would need WebSocket connections or sub-minute REST polling."

**🔴 "How would you optimize a BESS bidding for both day-ahead energy AND aFRR reserve simultaneously?"**
- **Exceptional answer:** "Joint optimization with two decision stages. Stage 1 (day-ahead): reserve commitment — bid aFRR capacity. Stage 2 (real-time): energy trading with reduced SoC range. The tradeoff: holding reserve capacity reduces arbitrage revenue (you can't charge/discharge fully if you might need to deliver reserve). Optimal split is a function of reserve price vs energy spread. Mathematically: max[ arbitrage_rev + reserve_price × capacity_reserved ] subject to SoC dynamics, with the aFRR delivery reducing η. My `ancillary.py` now implements exactly this — FCR symmetric, aFRR directional, with SoC headroom for upward and downward reserve commitment."

**🔴 "Solar duck curve — your strategy returned -0.94% in spring. Why does it underperform, and how would you fix it?"**
- **Exceptional answer:** "The solar duck curve captures the mid-day price depression from solar generation. In spring (Apr-May), solar is ramping up but demand is low, so the duck belly is deep and wide. My simple strategy buys the belly and sells shoulders — but the profit margin shrinks as solar penetration increases (more solar → lower mid-day prices, but also lower shoulder prices as the solar ramp widens). To fix: add a wind-solar balance indicator — on high-wind days the shoulder ramps are steeper. Also add a CCGT startup cost proxy: if clean spark spreads are negative, the evening ramp is steeper because fewer gas plants are online to cover it."

**🔴 "A trader says the aFRR activation signal arrived but your BESS didn't respond. How do you debug?"**
- **Exceptional answer:** "Three layers: (1) Telemetry — did the BESS controller receive the signal? Check MQTT/API logs. (2) SoC state — was the battery at a state where it could deliver? If SoC was 0% and the signal demanded up-regulation, it physically can't deliver — that's a scheduling error in the day-ahead reserve bid, not a real-time bug. (3) Latency — how long from signal to power output? If it's >30s for aFRR (requires 5-min response), the algorithm itself may be slow. I'd add a watchdog: if no aFRR response within 10s, revert to a default pre-approved ramp schedule. This recovery logic is not in my repo (fair for a portfolio), but I'd implement it as a state machine with fallback states."

**🔴 "Walk me through how you'd build a signal from wind forecast errors."**
- **Exceptional answer:** "I'd start with ECMWF ensemble forecasts for Belgian wind zones and compare against actual SCADA wind output (ENTSO-E Actual Generation). The forecast error `e(t) = forecast(t) - actual(t)` is mean-reverting — if the forecast says 2 GW but actual is 1.5 GW, prices should rise as the market re-prices the shortage. The signal: `e(t) - MA(e, 6h)` — large positive errors (over-forecasting) mean wind is below prediction, buy. Large negative errors, sell. Key refinement: separate offshore vs onshore — offshore errors are larger but faster-reverting. My pipeline's `energy_data/` structure is designed to ingest this; adding ECMWF feed is a new adapter."

**🔴 "Your repo has 578 tests at 92.55% coverage. An algo trading system goes live and loses €10K on day one. What failed that your tests didn't catch?"**
- **Exceptional answer:** "Three things tests miss: (1) **Data quality** — a bad tick from ENTSO-E (negative price that's actually a missing value encoded as -1) passes all type checks but corrupts the P&L. My tests use clean golden data. (2) **Latency** — tests assume instantaneous execution; real markets have slippage, queue position, partial fills. My slippage model is a flat 0.1% — unrealistic. (3) **Regime change** — the strategy was fit on April data but May had a different wind/solar pattern. Tests validate correctness, not profitability. For a trading system, I'd add: historical replay testing (walk-forward), synthetic data stress tests, and a shadow-mode period where the algo runs alongside the trader without executing."

**🔴 "How would you design the monitoring dashboard for your live algo?"**
- **Exceptional answer:** "Five panels: (1) **Position & P&L** — current positions per market/asset, daily and cumulative P&L. (2) **Execution quality** — slippage vs limit price, fill rate, order latency. (3) **Market context** — current Day-Ahead/Intraday prices, BE↔FR↔DE spreads, wind/solar generation. (4) **Risk metrics** — live VaR, current drawdown, position limits utilization. (5) **Health** — API connectivity status, data freshness, strategy running/stopped. I'd add a separate alert panel: 'Position exceeds risk limit', 'Data feed stale >5min', 'Strategy unresponsive >1min'. This is infrastructure work, not algo work — but it's essential for the INDUSTRY role, which explicitly mentions collaboration with manual traders who need these dashboards."

**🔴 "What is the marginal cost of a 1 MW aFRR capacity bid, and how does it interact with your day-ahead schedule?"**
- **Exceptional answer:** "The marginal cost is the *opportunity cost* of the foregone energy arbitrage, not the direct energy cost. Holding 1 MW of upward aFRR means the BESS can only use `P_max - 1` MW for day-ahead discharge across all hours, plus it must keep SoC headroom of `1 MW × activation_prob × (1/η_out)` MWh. The optimizer in `ancillary.py` resolves this: it allocates capacity to whichever stream pays more per MW, accounting for the reduced arbitrage opportunity. In practice with €15/MW/h aFRR and €100/MWh energy spreads, the optimizer typically bids upward aFRR only in hours with low price spreads and full power in high-spread hours. The revenue decomposition in the result makes this trade-off explicit."

---

### Cross-Cutting Interview Preparation

**The Portfolio Walkthrough** — When an interviewer says "walk me through this repo":
1. Open with: "This is my optimization portfolio — built for energy algorithmic trading roles. The standout is `domain/markets/` (PCR/Euphemia) and `domain/optimization/ancillary.py` (joint BESS + reserve bidding). 578 tests, 92.55% coverage, hexagonal architecture with ports/adapters."
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
- "Describe a time you had to prioritize between features." → "I chose to push coverage to 90% before adding new features. 578 tests mean I can refactor without fear."
- "What's something in this repo you're not proud of?" → The hardcoded 0.001 tolerance, and that mFRR is the only missing ancillary product. Shows awareness and honesty.

---

### Quick Reference: Module → INDUSTRY Belgium Role Mapping

| Module (new hex path / old flat path) | Primary INDUSTRY Relevance |
|---|---|
| `domain/optimization/storage.py` / `lp_optimization/storage.py` | ⭐⭐⭐ **BESS** — battery storage LP for energy arbitrage |
| `domain/optimization/ancillary.py` | ⭐⭐⭐ **Ancillary services** — joint BESS + FCR + aFRR LP |
| `domain/markets/intraday.py` / `energy_markets/intraday.py` | ⭐⭐⭐ **Intraday** — continuous order book matching, cross-border spreads |
| `domain/markets/pcr_model.py` / `energy_markets/pcr_model.py` | ⭐⭐ **Day-Ahead** — market coupling understanding, MCP, social welfare |
| `domain/markets/multi_zone.py` / `energy_markets/multi_zone.py` | ⭐⭐ **Cross-border** — BE↔FR↔DE↔NL spread trading |
| `domain/markets/fbmc.py` / `energy_markets/fbmc.py` | ⭐⭐ **Flow-based** — PTDF/RAM, loop flows, CBCO screening |
| `domain/trading/` / `backtester/` | ⭐⭐⭐ **Backtesting** — 7 risk metrics, walk-forward, signal-shift |
| `domain/trading/strategies/` / `strategies/` | ⭐⭐⭐ **Signals** — hour-of-day, calendar spread, solar duck |
| `adapters/entsoe_client.py` / `energy_data/` | ⭐⭐⭐ **Data** — ENTSO-E REST, SQLite, JSON cache, graceful degradation |
| `domain/optimization/scheduling.py` / `lp_optimization/scheduling.py` | ⭐⭐ **UC** — MIP for thermal assets, ramp rates, min up/down |
| `domain/optimization/assets.py` / `lp_optimization/assets.py` | ⭐⭐⭐ **Asset modeling** — Battery, Generator, SpillAsset patterns |
| `domain/emissions.py` | ⭐⭐ **CO₂** — EUA pass-through pricing, clean spark/dark spread |
| `infrastructure/experiment_tracker.py` | ⭐⭐ **ML tracking** — SQLite-backed research runs, CLI comparison |

**Coverage note (2026-06):** FCR (symmetric) + aFRR (capacity-only) are now implemented in `domain/optimization/ancillary.py` with joint BESS + reserve LP. mFRR remains the only fully missing product (TSO-specific activation rules differ per country).
