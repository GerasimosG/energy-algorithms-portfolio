# Interview Q&A: Euphemia   & Industry

## How to Use This

For each question, there are three levels:
- **Good answer** — what most prepared candidates say
- **Exceptional answer** — what gets you hired
- **Why they ask** — the hidden agenda behind each question

---

## Part 1: Optimization Fundamentals

### Q1: "Walk me through how you'd formulate a unit commitment problem"

**Good answer:** "Minimize generation cost subject to demand, capacity, ramp rate, and min up/down constraints using MIP."

**Exceptional answer:** "Start with binary ON/OFF variables per generator per hour. Objective: minimize fuel cost plus startup cost. Constraints: energy balance (exact equality), reserve margin (capacity headroom), generator min/max output bounds, ramp rate limits linking consecutive hours, startup/shutdown logic consistency, min uptime/downtime counting constraints. Critical edge case: initial conditions — if a generator was already ON for 5 hours at t=0, its remaining min uptime is reduced. My `scheduling.py` handles this with `init_status`, `init_uptime`, `init_downtime` parameters. Without this, the MIP might schedule an illegal shutdown."

**Why they ask:** Wants to see if you understand that UC is a MIP (not LP), and if you know the edge cases that make real implementations complex.

---

### Q2: "What's the difference between LP and MIP? When use each?"

**Good answer:** "LP has continuous variables, MIP adds integer/binary variables. Use MIP when you have yes/no decisions like generator on/off."

**Exceptional answer:** "LP is polynomial time via simplex or interior point — every solution is at a vertex of the convex feasible polytope. MIP is NP-hard because binary variables shatter the feasible region into disjoint convex sets. You use MIP for: unit commitment (on/off), block orders (accept/reject), facility location (build/don't build). The key performance consideration: an LP with 10K variables solves in seconds; a MIP with 100 binary variables might take hours. Branch and bound complexity grows exponentially with binary count. My code uses MIP for UC (`scheduling.py`) and block orders (`pcr_model.py`) but stays LP for everything else."

**Why they ask:** Tests whether you understand computational complexity, not just syntax.

---

### Q3: "Why did you use PuLP instead of Gurobi/CPLEX?"

**Good answer:** "PuLP is open-source, great for prototyping."

**Exceptional answer:** "PuLP ships with CBC — free, no license, zero friction install. For a portfolio demonstrating understanding, CBC handles all my models easily (largest is 290 variables, 235 constraints — solves in 180ms on a Raspberry Pi). But I know Euphemia   uses commercial solvers. Gurobi's presolve is far superior for large MIPs, CBC struggles beyond ~100K variables, and CPLEX's barrier method handles degenerate problems better. My `solver_config.py` already has stubs for Gurobi, CPLEX, and HiGHS — the switch is a one-line config change. I'd be excited to work with production-grade solvers."

**Why they ask:** Gauges whether you understand solver limitations, not just how to call a library. Also tests intellectual honesty — admitting CBC's limits is better than pretending it's production-grade.

---

### Q4: "Explain duality to a non-technical colleague"

**Good answer:** "Every minimization problem has a dual maximization problem with swapped variables and constraints."

**Exceptional answer:** "Think of it like this: you're trying to minimize cost of serving electricity demand. The dual problem asks 'what's the cheapest possible price at which someone else could serve this demand?' At the optimal solution, the two answers match — your minimum cost equals the maximum value someone would pay. The dual variables (shadow prices) tell you how much you'd save if you had one less MW of demand — that's literally the market clearing price. This is why Euphemia can compute MCPs directly from the LP solution without running a separate pricing algorithm."

**Why they ask:** Duality is the bridge between optimization and economics. If you can explain it simply, you genuinely understand it.

---

### Q5: "How do you debug an infeasible model?"

**Good answer:** "Check the constraints, look for contradictions."

**Exceptional answer:** "Systematically: (1) Remove all constraints, solve — if still infeasible, variable bounds conflict (e.g., min > max). (2) Add back energy balance only — verifies supply can meet demand. (3) Add back capacity limits — narrows down which generator is undersized. (4) Add ramp rates, min up/down — these often cause infeasibility due to initial conditions or horizon-end effects. (5) Use the solver's conflict refiner if available (Gurobi, CPLEX have this; CBC doesn't). In my repo, I hit this exact issue: the battery arbitrage test was infeasible because round-trip losses (95% × 95% = 90.25%) meant the battery couldn't deliver enough stored energy — the demand exceeded generation + storage capacity after efficiency losses. Documented in `tests/test_assets.py` fix."

**Why they ask:** Debugging infeasible models is 30% of an optimization engineer's job. They want to see methodical debugging, not guessing.

---

### Q6: "What's a good optimality gap for an MIP?"

**Good answer:** "Less than 1%."

**Exceptional answer:** "Depends on the application. For day-ahead market clearing, Euphemia targets 0.1% — a 0.1% welfare gap on billions in daily volume is millions in lost surplus. For production scheduling, 1% is fine — the fuel cost savings of closing to 0.1% don't justify the computation. For portfolio optimization, 5% is acceptable. Key nuance: a SMALL gap doesn't guarantee good prices — the MIP gap measures objective value bound, while prices (dual variables) can be highly sensitive to which integer solution was chosen. Two solutions with 0.1% gap might have MCPs differing by 50%."

**Why they ask:** Tests whether you understand the difference between objective quality and solution quality — the MIP gap measures the former, not the latter.

---

## Part 2: Energy Market Domain

### Q7: "Walk me through how Euphemia clears the market, step by step"

**Good answer:** "Collect orders, solve MIP for welfare maximization, publish results."

**Exceptional answer:** "Five stages: (1) Order collection from 25+ power exchanges — hourly bids, block orders, complex orders. (2) Order matching — group linked blocks, identify exclusive groups, validate combinations. (3) MIP solve: maximize social welfare subject to energy balance, ATC/FBMC flow constraints, block order binary constraints. This is where Euphemia's custom branch-and-cut shines — 500K binary variables, solved in ~17 minutes. (4) IP pricing: fix the MIP dispatch, solve a separate LP to compute prices that minimize make-whole payments. This handles paradoxically accepted blocks — blocks that are accepted in the MIP but would lose money at uniform MCP. (5) Results publication: accepted orders, hourly prices per zone, cross-border flows. My `pcr_model.py` implements stages 1-3, and documents stages 4-5 as known limitations."

**Why they ask:** This IS the Euphemia   job. If you can't walk through Euphemia, you can't join the team that builds it.

---

### Q8: "What are block orders and why do they make the problem non-convex?"

**Good answer:** "Block orders are all-or-nothing bids across multiple hours. Their binary acceptance makes the problem non-convex."

**Exceptional answer:** "Block orders serve real operational needs — nuclear plants can't economically start up for one hour, combined-cycle plants have minimum run times, and pumped hydro needs sustained pump/generate cycles. The binary acceptance variable `y ∈ {0,1}` creates a disjunctive feasible region: the block is either fully in (multiplying its quantity) or fully out. This non-convexity breaks two key LP properties: (1) the optimal solution may not be at a vertex, and (2) uniform marginal pricing may leave some accepted blocks with negative surplus — the 'paradoxically accepted block' problem. Euphemia handles this with a two-stage solve: MIP for dispatch, LP for make-whole-minimizing prices. My `block_orders.py` implements linked (parent+child, equality constraint) and exclusive (at most one, sum ≤ 1) groups."

**Why they ask:** Euphemia  's entire value proposition is handling these non-convexities. They need people who understand WHY they're hard, not just THAT they're hard.

---

### Q9: "Why FBMC instead of ATC? Give a concrete example."

**Good answer:** "ATC treats each line independently. FBMC captures how flows interact via PTDF."

**Exceptional answer:** "Here's the killer example: 3 zones A-B-C in a triangle. A has cheap hydro, B has demand, C has expensive diesel. With ATC, you'd set A→B capacity to 200 MW and let A export 200 MW to B. But physically, the flow from A to B doesn't all go through the direct A-B line — some 'loops' through C via the A-C and B-C lines. If the A-C line is near its thermal limit, the loop flow can overload it, even though the ATC model shows green. FBMC catches this because the PTDF matrix captures that a 1 MW injection at A creates flow on ALL lines, not just A-B. In my `fbmc.py` demo, the Hydro_Diesel line shows 65% utilization from Hydro_North exports, even though the economic flow is Hydro→Gas→Diesel. ATC would completely miss this."

**Why they ask:** This is THE reason Euphemia   exists. If you can't explain loop flows, you don't understand why Euphemia is necessary.

---

### Q10: "How would you test a market clearing algorithm?"

**Good answer:** "Unit tests with known inputs and expected outputs."

**Exceptional answer:** "I'd use four testing layers: (1) Property-based tests — energy balance must hold exactly (tested in `test_energy_balance_exact`), welfare must exceed any manual dispatch, MCP must be within supply/demand price range. (2) Edge cases — zero demand (`test_no_trades_zero_demand`), all blocks rejected, ATC binding at capacity, negative prices from must-run renewables. (3) Regression tests — golden output files for standard scenarios to catch any changes in solution. (4) Invariant validation — after every solve, auto-check physical laws (`invariants.py`: energy balance, SoC bounds, power limits). I'd add Hypothesis property-based testing for production — 250 random scenarios per run, comparing solver output against analytical solutions where possible."

**Why they ask:** Euphemia processes billions in daily trades. A bug in production could bankrupt market participants. They need to know you take testing seriously.

---

### Q11: "A trader says a block order was wrongly accepted. How do you debug?"

**Good answer:** "Reproduce with the same inputs, check constraints."

**Exceptional answer:** "First, reproduce with exact input data — order books are time-stamped. Binary search on constraints: remove block groups one by one to isolate which constraint is misbehaving. Check the MIP gap — if the solver terminated early with non-zero gap, the solution might not be truly optimal. Check for numerical issues: PuLP/CBC's default feasibility tolerance is 1e-6, and blocks near the marginal price can flip acceptance due to floating-point. Check linked/exclusive group constraints — early versions of my `pcr_model.py` had a bug where linked blocks weren't actually linked (missing equality constraint). Check the block's group identifier — these bugs are often data issues (wrong group ID), not algorithm bugs. Run with verbose solver output to see the branch-and-bound tree."

**Why they ask:** This is what you'll actually do on day 1. They want methodical debugging, not hand-waving.

---

### Q12: "What happens when two zones have the same MCP but ATC is binding?"

**Good answer:** "No flow occurs."

**Exceptional answer:** "Correct — no flow because no price differential drives arbitrage. But here's where FBMC diverges from ATC: with binding ATC but equal zonal prices, you'd expect no flow. In FBMC with loop flows, a trade between A and B (equal price in both) can still create flow on C-D due to network topology. This 'wheeling' flow happens even without a price differential — the PTDF matrix captures this. It's why FBMC constraints can be binding even when zonal prices suggest no congestion. My `multi_zone.py` uses simple ATC, but `fbmc.py` captures this via the PTDF matrix."

**Why they ask:** Tests depth of FBMC understanding. Most candidates can explain price-driven flows; few understand topology-driven flows.

---

## Part 3: Engineering & Production

### Q13: "Your backtest shows Sharpe 3.2. What's wrong?"

**Good answer:** "Probably look-ahead bias."

**Exceptional answer:** "A Sharpe above 2 in real markets is almost certainly an error. My debugging checklist: (1) Look-ahead bias — my engine shifts signals by 1 bar, but if signal generation uses future data, Sharpe is inflated. (2) Transaction costs — 0.1% commission seems small but compounds dramatically; my `engine.py` includes commission and slippage. (3) Survivorship bias — backtesting on stocks that survived introduces upward bias. (4) Overfitting — 3 parameters on 2 years of data is easy to curve-fit. (5) Data-snooping — testing 50 strategies and picking the best one practically guarantees a false positive. I'd do walk-forward validation: train on data up to T, test on T+1, roll forward."

**Why they ask:** Industry traders see inflated backtests daily. They need quants who can spot and fix biases.

---

### Q14: "What market regime kills a mean-reversion strategy?"

**Good answer:** "Strong trending markets."

**Exceptional answer:** "Strong trending markets — Bollinger Bands assume mean-reversion, so a sustained trend generates repeated false reversal signals. The strategy goes long at the lower band, price keeps falling through it, then doubles down. This killed many natural gas traders in 2022 during the supply crisis — prices trended from $3 to $9/MMBtu over months, blowing through every 'reversion' signal. A real system needs a trend filter — ADX threshold or regime-switching model. This is why my strategy modules are deliberately simple and honest about their assumptions."

**Why they ask:** Shows you understand that models have REGIMES where they work, not universal applicability.

---

### Q15: "How do you handle API failures in a data pipeline?"

**Good answer:** "Try-catch blocks and retries."

**Exceptional answer:** "My ENTSO-E client has a structured error matrix: 401 returns specific 'check your API key' message, network errors include the URL exception reason, XML parse errors are caught and reported, API-level errors (in the XML body) extract the `Reason` element. For production: retry with exponential backoff (1s, 2s, 4s, 8s), circuit breaker after N failures (stop querying, raise alarm), stale-data timeout (if no fresh data for X minutes, flag for manual review). My pipeline uses graceful degradation — if live data fails, the demo data provides realistic Belgian market data as fallback."

**Why they ask:** In production, APIs fail. A model that crashes on 401 is not production-ready.

---

## Part 4: Edge Case Questions

### Q16: "Your storage LP has no binary for charge/discharge. Why?"

**Good answer:** "The LP naturally avoids it."

**Exceptional answer:** "In a cost-minimization framework, simultaneous charge and discharge at the same price is economically irrational — you lose η² efficiency for zero price benefit. The objective function provides a natural penalty that prevents it. This is the 'economic' approach vs energy-py-linear's 'binary' approach with big-M constraints. Both are correct; the economic approach is simpler and demonstrates understanding that not every physical constraint needs a binary variable — sometimes the objective handles it implicitly. However, at zero or negative prices, simultaneous charge/discharge COULD be optimal if there are separate markets or ancillary services — for a pure energy arbitrage model, it's safe."

**Why they ask:** Tests whether you think critically about which constraints are necessary vs which are lazy.

---

### Q17: "Why is your energy balance equality, not inequality?"

**Good answer:** "Supply must exactly equal demand."

**Exceptional answer:** "Early versions of my `pcr_model.py` used `>=`, which allowed over-generation — the solver would dispatch more supply than demand, reducing welfare by assigning surplus to the lowest-price demand (not reflecting real willingness-to-pay). Changing to `==` forced exact matching. In a real system, you might use `>=` with a slack variable for spill/unserved energy — which is exactly what my `SpillAsset` provides at the asset level, not the balance level. The equality constraint says 'the grid must balance'; the spill asset says 'if it can't, here's the penalty for not serving demand'. This separation of concerns — physical law vs economic penalty — is cleaner than combining both into the balance constraint."

**Why they ask:** Tests understanding of modeling philosophy — what belongs in constraints vs objective.

---

### Q18: "Your LODF matrix has a row that doesn't sum to zero. Is that a bug?"

**Good answer:** "Maybe — depends on the reference."

**Exceptional answer:** "LODF rows don't have to sum to zero — that's a PTDF property (Kirchhoff current law). LODF captures the REDISTRIBUTION of flow from one branch outage onto others. When branch k trips, its flow is redistributed across the network, and LODF[l,k] tells you what fraction lands on branch l. The column sum of flow changes IS zero (total flow is conserved), but individual LODF rows don't have this property. In my `lodf_utils.py`, the diagonal is always -1 (self-outage), and off-diagonals can have any magnitude — they represent how much one branch's outage loads another."

**Why they ask:** Distinguishes between PTDF (network physics) and LODF (contingency analysis) — similar matrices, different semantics.

---

### Q19: "When would you NOT use a SpillAsset?"

**Good answer:** "When you can guarantee feasibility."

**Exceptional answer:** "You'd skip the SpillAsset when infeasibility IS the desired outcome — for example, when testing that a portfolio of assets CAN meet demand under worst-case conditions. A SpillAsset would mask the capacity shortfall. Also, in market clearing (not unit commitment), spill/unserved energy is typically NOT modeled — the market clears only what can be physically served, and any shortage manifests as price spikes, not spill activation. My `pcr_model.py` doesn't use spill for this reason — the energy balance equality constraint forces exact dispatch, and if supply can't meet demand, the LP is infeasible, signaling insufficient bids."

**Why they ask:** Tests whether you blindly apply patterns or choose them deliberately based on context.

---

### Q20: "If you could add ONE feature to make this production-ready, what would it be?"

**Good answer:** "Switch to a commercial solver like Gurobi."

**Exceptional answer:** "Property-based testing with Hypothesis. My 185 tests cover specific scenarios, but they can't explore the combinatorial space of possible order books. Hypothesis would generate 10,000 random market scenarios per CI run, verifying that energy balance holds, welfare is non-negative, and no block order constraints are violated. This catches edge cases I never thought to test — I found this exact approach in energy-py-linear (250 random examples per test) and it's the single biggest gap between portfolio testing and production testing. It requires zero infrastructure changes and would catch 90% of the bugs that current tests miss."

| **Why they ask:** Gauges maturity — do you recommend shiny features or the boring work that actually prevents bugs?

---

## Part 5: INDUSTRY Belgium — Algorithmic Trader (Short-Term Power, Uccle)

*Questions specific to this role — focus on BESS, renewables, intraday, ancillary services, and production deployment.*

### Q21: "Walk me through your BESS storage optimization model."

**Good answer:** "Maximize arbitrage revenue subject to SoC dynamics, efficiency, and capacity constraints."

**Exceptional answer:** "The storage LP maximizes `Σ(revenue[t] - cost[t])` subject to: SoC[t+1] = SoC[t] + η_charge · P_charge[t] − P_discharge[t]/η_discharge, capacity limits 0 ≤ SoC ≤ E_max, power limits 0 ≤ P ≤ P_max, and terminal SoC constraint to prevent end-of-horizon depletion. Round-trip efficiency η² = 0.9025 means losing 10% per cycle — this is the key economic constraint. No binary for charge/discharge because the objective naturally prevents simultaneous operation (you lose η² for zero gain). My `storage.py` demonstrates this on 30 days of Belgian data. The limitation: it's pure energy arbitrage — no joint bidding into reserve markets, which is where real BESS value is."

**Why they ask:** This role is 30% BESS optimization. They need to know you understand the LP, not just call a library.

---

### Q22: "How would you model a battery bidding into both day-ahead energy AND aFRR reserve?"

**Good answer:** "Add reserve capacity as a decision variable with SoC headroom constraint."

**Exceptional answer:** "Two-stage stochastic optimization. Stage 1 (day-ahead): commit reserve capacity R_aFRR ≤ P_max. The SoC must have headroom: SoC + R_aFRR/η ≤ E_max (up-regulation means discharging). Stage 2 (real-time): actual energy arbitrage with reduced power capacity (P_available = P_max − activated_reserve). The objective: max[ energy_rev + λ_aFRR · R_aFRR − expected_activation_cost ]. Key tradeoff: holding reserve reduces arbitrage capacity. Optimal split depends on λ_aFRR vs energy spread. At high reserve prices (>€50/MW·h), reserve beats arbitrage. At low prices, pure arbitrage wins. My `storage.py` is Stage 1 only, but the pattern extends cleanly."

**Why they ask:** Joint energy+reserve optimization is core to modern BESS operation. Tests understanding of multi-market optimization.

---

### Q23: "Your intraday order book matching — walk me through the price-time priority. How does it differ from Euphemia's algorithm?"

**Good answer:** "Price-time priority: best price first, then earliest order."

**Exceptional answer:** "Price-time priority is standard for continuous intraday trading: (1) best bid/ask match, (2) for equal prices, earlier timestamp wins. This differs from Euphemia in three ways: (a) **Discrete vs continuous** — Euphemia solves a single MIP at gate closure; intraday is continuous matching as orders arrive. (b) **Uniform pricing** — Euphemia produces a uniform MCP per zone per hour; intraday uses pay-as-bid (discriminatory pricing). (c) **Block orders** — intraday has hourly orders only; block orders (linked, exclusive) only exist in day-ahead. My `intraday.py` implements continuous matching with price-time priority — suitable for XBID-style trading."

**Why they ask:** Tests understanding of the difference between auction and continuous trading — fundamental knowledge for a role that spans both DA and ID markets.

---

### Q24: "Design a signal for trading the German-French cross-border spread."

**Good answer:** "Buy the spread when FR price > DE price, sell when DE price > FR price."

**Exceptional answer:** "The BE↔FR↔DE spread is influenced by three factors: (1) **Nuclear availability** — French nuclear outages widen the FR↔DE spread (France imports). Signal: track EDF outage schedules vs ENTSO-E Unavailability of Generation Units. (2) **Wind balance** — North German wind depresses DE prices below FR. Signal: ECMWF wind forecast delta. (3) **CO₂ cost pass-through** — when FR is nuclear-marginal and DE is gas-marginal, the spread is driven by EUA × gas_efficiency. Signal: clean spark spread. Combined signal: `α · nuclear_outage_delta + β · wind_forecast_delta + γ · EUA_x_gas_spread`. My industry_demo captured BE↔FR spread at €13/MWh (May 3) — pure nuclear-outage event."

**Why they ask:** Tests domain knowledge of what actually drives European power spreads, not just math.

---

### Q25: "Explain what FCR, aFRR, and mFRR are, and how you'd model bidding into each."

**Good answer:** "FCR is instantaneous frequency response, aFRR is automatic 5-min reserve, mFRR is manual 15-min reserve."

**Exceptional answer:** "**FCR** (Frequency Containment Reserve): symmetric, ± capacity, must respond within 30s, sustained for 15min. Bid into weekly auctions. Low price (€5-20/MW·h), high volume. Model: fixed capacity reservation, no energy delivery assumed. **aFRR** (automatic Frequency Restoration Reserve): 5-min activation, proportional to ACE. Bid daily. Medium price (€20-80/MW·h). Model: two-stage — commit reserve day-ahead, then expect fraction α activated real-time. **mFRR** (manual FRR): instructed by TSO, typically 15-min blocks. Bid hourly. Higher price (€30-150/MW·h). Model: deterministic activation in one direction. The optimization hierarchy: FCR is must-take, aFRR is probabilistic, mFRR is event-driven. For BESS, aFRR is the sweet spot — fast enough response, high enough price, manageable capacity requirement."

**Why they ask:** The JD explicitly mentions ancillary services. If you can't explain the products, you're disqualified regardless of math skills.

---

### Q26: "A production algo goes live and loses money on day one. Walk me through your post-mortem."

**Good answer:** "Check the data, check the model, check the execution."

**Exceptional answer:** "Structured post-mortem: (1) **Data**: verify ENTSO-E feed for the day — were there missing hours, corrupted XML, stale prices? Compare to independent source (e.g., SMARD for DE, RTE for FR). (2) **Model**: replay the day's data through the backtest — does the offline result match live? Any divergence means a code bug or config issue. (3) **Execution**: check fill prices vs limit prices — was slippage higher than modeled? Queue position? Partial fills? (4) **Regime**: compare the day's market conditions (wind, solar, outages) to the backtest period — if the distribution differs, the model is overfit, not broken. (5) **Mitigation**: add safeguards — max daily loss limit (stop trading), position limits, data quality pre-flight checks. Document in a blameless post-mortem as per INDUSTRY's culture."

**Why they ask:** They want to see systematic debugging under pressure, not blame-shifting or panic.

---

### Q27: "Your framework has 571 tests at 94% coverage. How do you test automatically if you wouldn't test software?"

**Good answer:** "Test the correct module and then into the live staging environment."

**Exceptional answer:** "Testing an algorithmic trading system is different from pure software QA. I'd add: (1) **Historical replay** — replay the last 30 days of live data through the algo in shadow mode and compare every signal/order to the recorded strategy. (2) **Synthetic scenario stress tests** — generate extreme but plausible scenarios (nuclear trip + wind drought + interconnector outage) and verify the algo doesn't violate risk limits. (3) **Change-detection tests** — if the algo produces 20 orders/day on average and today it produces 200, flag for manual review. (4) **A/B test with trader** — run the algo alongside the manual trader in paper mode and compare P&L over a month before going live. My test suite covers the software correctness side; these additions cover the trading correctness side."

**Why they ask:** Tests your understanding of the gap between "code works" and "algo trades profitably."

---

### Q28: "What's your experience with time-series forecasting for power prices?"

**Good answer:** "I've used ARIMA, Prophet, and LSTM."

**Exceptional answer:** "My experience is with fundamentals-driven approaches, not black-box models. Power prices are driven by known physical factors (fuel prices, renewables, outages, demand) that statistical models can't capture well without feature engineering. My approach: (1) **Fundamentals baseline** — merit order stack with fuel/CO₂ costs, renewable infeed, and outage data. This sets the 'physics-based' price. (2) **Residual correction** — apply a statistical model (LASSO with lagged prices + weather features) to predict the deviation from fundamentals. (3) **Regime detection** — separate normal hours (good for fundamentals) from tight hours (better for momentum/sentiment). My repo doesn't have a price forecaster — I'd add one as an adapter matching the EntsoeClient pattern. The key insight for an interview: don't claim you can forecast power prices with high accuracy — you can't. The goal is relative accuracy for signal generation."

**Why they ask:** The JD lists ML/data analytics. But in power markets, forecasting is a minefield — they want intellectual honesty about its limits.

