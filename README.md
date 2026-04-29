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
| **Energy market domain** | Do you understand PCR, Euphemia, market coupling, block orders, merit order? | `EUPHEMIA_INTERVIEW.md` — full question bank. `multi_zone.py` — ATC-constrained coupling. `block_orders.py` — linked + exclusive group mechanisms |
| **Solver experience** | Have you used optimization solvers? Understand their limitations? | PuLP/CBC used throughout. README documents PuLP's quadratic limitation (why scipy handles portfolio risk). Honest about CBC vs commercial solvers |
| **Python + software engineering** | Can you write production code, not just notebooks? | 40 pytest tests, CI/CD (GitHub Actions, 3 Python versions), `pyproject.toml`, `__all__` exports, NumPy docstrings, clean git history |
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

### Industry — Energy Algorithmic Trader / Quantitative Analyst

**Company context:** Industry is a global energy company operating across the entire value chain — generation (nuclear, gas, hydro, wind, solar), trading, retail supply, and energy services. Trading roles span day-ahead, intraday, futures, and options markets across European power, gas, and carbon.

#### Core Requirements — How This Repo Answers

| Requirement | What Interviewers Look For | This Repo's Answer |
|---|---|---|
| **Production Python** | Can you write code that runs reliably in production, not just a Jupyter notebook? | Full package structure, CI/CD, 40 tests, error handling throughout, `pyproject.toml` |
| **Backtesting** | Do you understand look-ahead bias, survivorship bias, transaction costs? | `engine.py` — vectorized, signal-shifted to avoid look-ahead. Commission and slippage modeled per trade. 7 risk metrics |
| **Quantitative modeling** | Can you build and validate statistical models? | 3 strategy types (momentum, mean-reversion, SMA crossover) with parameterized thresholds. Portfolio optimization with cardinality constraints |
| **Risk management** | Do you understand VaR, drawdown, Sharpe, Sortino, Kelly? | `metrics.py` — 7 metrics. Kelly fraction properly bounded. Sortino uses downside deviation only |
| **Market data pipelines** | Can you build reliable data infrastructure? | `market_data/` — Yahoo Finance → SQLite. `energy_data/` — ENTSO-E Transparency Platform API client with proper error handling |
| **Domain knowledge** | Do you understand electricity markets specifically? | Intraday simulation with order book matching, ENTSO-E pipeline, PCR/Euphemia understanding |

#### Edge Cases — What Separates Good from Exceptional

**🔴 "Your backtest shows a Sharpe of 3.2. What's wrong?"**
- **Exceptional answer:** "A Sharpe above 2 in real markets is almost certainly an error. I'd check: (1) Is there look-ahead bias? My engine shifts signals by 1 bar, but if the signal generation uses future data, the Sharpe is inflated. (2) Are transaction costs realistic? 0.1% commission per trade seems small but compounds dramatically. (3) Survivorship bias — am I backtesting on stocks that still exist? (4) Overfitting — 3 parameters on 2 years of data is easy to curve-fit. I'd do walk-forward validation and out-of-sample testing."
- **Repo evidence:** `engine.py` documents the signal-shift anti-look-ahead mechanism. `backtest()` includes commission and slippage parameters.

**🔴 "Your mean-reversion strategy triggers on Bollinger Bands. What market regime kills it?"**
- **Exceptional answer:** "Strong trending markets. Bollinger Bands assume mean-reversion, so a sustained trend (like a gas supply shock during an energy crisis) would generate repeated false reversal signals. The strategy would go long at the lower band, price keeps falling through it, then the strategy doubles down. This killed many natural gas traders in 2022. A real system would need a trend filter — perhaps an ADX threshold or a regime-switching model."
- **Repo evidence:** `mean_reversion.py` is deliberately simple and honest about its assumptions.

**🔴 "You're trading intraday power. A nuclear plant trips offline. What do you do?"**
- **Exceptional answer:** "Prices spike immediately — this is a supply shock. If I'm flat, buying the spike is dangerous because prices can overshoot and revert within hours as cross-border flows ramp up. If I'm short, I need to cover immediately — the loss is already incurred, the question is whether to cut losses or wait for reversion. This is where having real-time ENTSO-E data and outage monitoring is critical — my `energy_data` pipeline structure is designed for exactly this."
- **Repo evidence:** `intraday.py` with order book matching + ENTSO-E pipeline shows integrated thinking about market data and trading.

**🔴 "Explain VaR to a non-technical stakeholder. What's its biggest weakness?"**
- **Exceptional answer:** "VaR answers 'What's the worst loss I'll see on 95% of days?' — so if VaR95 = €10K, you lose more than €10K roughly once a month. The biggest weakness: VaR tells you nothing about HOW BAD the bad days are. It's like saying 'the flood barrier holds 95% of the time' without mentioning that the 5% is a tsunami. That's why I also compute Expected Shortfall (CVaR) and max drawdown — VaR alone is insufficient."
- **Repo evidence:** `metrics.py` computes both VaR95 and VaR99, plus max drawdown and Calmar ratio.

**🔴 "Walk me through your ENTSO-E data pipeline. How do you handle API failures?"**
- **Exceptional answer:** "The `EntsoeClient` wraps the ENTSO-E REST API with proper error handling: HTTP errors (401 unauthorized, 503 unavailable), XML parse errors, and network timeouts all return structured error dicts instead of crashing. For production, I'd add: exponential backoff with jitter, a local cache with TTLs so the pipeline degrades gracefully during outages, and alerting when data freshness exceeds a threshold. The demo data fallback shows the pattern."
- **Repo evidence:** `energy_data/fetcher.py` has explicit error handling for HTTPError, URLError, ParseError, and generic exceptions — each returning a structured dict with `status: "error"`.

**🔴 "Design a P&L attribution system for an energy trading desk."**
- **Exceptional answer:** "I'd decompose daily P&L into: (1) Delta — P&L from directional exposure to spot/futures prices. (2) Gamma — P&L from options convexity. (3) Vega — P&L from volatility changes (critical for power options). (4) Theta — time decay. (5) Residual — everything unexplained, which I'd investigate for model error or unmodeled risk factors like cross-border flow changes. For power specifically, I'd add a 'spark spread' component separating fuel cost changes from power price changes."
- **This is a stretch question** — it tests whether you think like a trading desk quant, not just a developer. If you can't answer this, pivot to: "I understand the concept but haven't implemented it. Here's how I'd approach it..."

---

### Cross-Cutting Interview Preparation

**The Portfolio Walkthrough** — When an interviewer says "walk me through this repo":
1. Open with: "This is my optimization portfolio, built for energy market and quantitative trading roles. The hero module is `energy_markets/` — it implements a PCR market coupling LP that maps directly to Euphemia concepts."
2. Show the README's "Implementation → Real Euphemia Mapping" table — it demonstrates you know exactly where your model simplifies reality.
3. Run `pytest tests/ -v` live if possible — 40 green tests in 2 seconds is compelling.
4. Open `notebooks/walkthrough.ipynb` and run a few cells — the multi-zone coupling or BESS storage demos are visually impressive.

**Technical Questions They Will Ask Both Roles:**
- "What's the time complexity of your solution?" — Our PCR LP is O(n³) in theory (simplex worst case) but O(n²) in practice for these sizes.
- "How would you parallelize this?" — Independent zones can solve in parallel. Benders decomposition separates the master problem from subproblems.
- "What would you do differently with unlimited time?" — Add FBMC (flow-based coupling), IP pricing, stochastic programming for renewable uncertainty, and property-based testing with Hypothesis.

**Behavioral Questions — Be Ready For:**
- "Tell me about a bug you found and fixed." → Any of the 13 issues in AGENTS.md. Pick the linked blocks fix — it's a great story about debugging constraint interactions.
- "Describe a time you disagreed with a technical decision." → The `risk_target` parameter in `optimize_portfolio()` is accepted but not enforced by PuLP. Documenting this honestly and providing the scipy alternative shows you'd raise concerns constructively.
- "What's something in this repo you're not proud of?" → The acceptance tolerance of 0.001 is hardcoded (should be configurable). The type hints on some internal helper functions are missing (though all public APIs are typed). This shows self-awareness.

---

### Quick Reference: Module → Job Mapping

| Module | Euphemia   Relevance | Industry Relevance |
|--------|-----------------|-----------------|
| `energy_markets/pcr_model.py` | ⭐⭐⭐ Core — PCR/Euphemia | ⭐⭐ Market understanding |
| `energy_markets/multi_zone.py` | ⭐⭐⭐ Core — Zonal coupling | ⭐⭐ Cross-border trading |
| `energy_markets/intraday.py` | ⭐ Market design | ⭐⭐⭐ Core — Intraday trading |
| `energy_markets/block_orders.py` | ⭐⭐⭐ Core — Non-convex orders | ⭐ Market structure |
| `lp_optimization/scheduling.py` | ⭐⭐⭐ Core — MIP modeling | ⭐⭐ Asset optimization |
| `lp_optimization/storage.py` | ⭐⭐ Emerging market design | ⭐⭐⭐ Core — Battery trading |
| `lp_optimization/portfolio.py` | ⭐ Optimization fundamentals | ⭐⭐⭐ Core — Risk/return |
| `backtester/engine.py` | ⭐ Software engineering | ⭐⭐⭐ Core — Strategy validation |
| `energy_data/fetcher.py` | ⭐ Market data | ⭐⭐⭐ Core — Data infrastructure |
| `strategies/*` | — | ⭐⭐⭐ Core — Trading signals |

## 📦 Architecture

```
Energy_Algorithms/
├── energy_markets/        ★ HERO — PCR coupling, block orders, multi-zone, intraday, Euphemia context
│   ├── pcr_model.py       LP: social welfare maximization with binary block orders
│   ├── multi_zone.py      Multi-zone coupling with ATC constraints
│   ├── block_orders.py    Linked, exclusive, and simple block order scenarios
│   ├── intraday.py        Continuous intraday trading simulation with order matching ★ new
│   ├── market_clearing.py Supply/demand stack equilibrium + visualization
│   └── EUPHEMIA_INTERVIEW.md  Interview prep: Euphemia concepts, question bank
├── lp_optimization/        Core LP/MIP skills
│   ├── transportation.py  Classic transportation LP
│   ├── portfolio.py       Mean-variance (scipy SLSQP) + linear (PuLP)
│   ├── scheduling.py      Unit commitment MIP with min up/down, ramp rates, reserve
│   └── storage.py         BESS battery storage optimization LP ★ new
├── energy_data/            European electricity market data ★ new
│   ├── fetcher.py         ENTSO-E Transparency Platform API client
│   └── demo.py            Demo with realistic Belgian market data
├── backtester/             Vectorized backtesting engine + 7 risk metrics
├── strategies/             3 signal-based strategies (momentum, mean-reversion, SMA)
├── market_data/            Yahoo Finance → SQLite pipeline
├── tests/                  40 pytest tests across 4 modules ★ 26→40
├── notebooks/              Walkthrough notebook for Euphemia   demo ★ new
└── .github/workflows/      CI: Python 3.11–3.13, tests + demo verification
```

## 🚀 Quick Start

```bash
git clone git@github.com:GerasimosG/Energy_Algorithms.git
cd Energy_Algorithms
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"

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

### Known Limitations (Documented for Interview Transparency)

- ⚠ **MCP pricing**: Uses simple `max(accepted_prices)` — real Euphemia uses IP pricing
  for non-convex block orders (discussed in `EUPHEMIA_INTERVIEW.md`)
- ⚠ **Single-period**: No inter-temporal constraints (storage, hydro reservoirs)
- ⚠ **No flow-based coupling**: ATC is simpler than FBMC; FBMC is discussed in docs
- ⚠ **No PUN pricing**: Italy's single national price not modeled

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Python modules | 11 |
| Total source files | 24 |
| Test files | 4 |
| Test cases | 40 (all passing) |
| Risk metrics | 7 (Sharpe, Sortino, maxDD, Calmar, VaR95, VaR99, Kelly) |
| Optimization solvers | 2 (PuLP/CBC, scipy SLSQP) |
| New in this iteration | BESS storage, intraday trading, ENTSO-E pipeline, notebook walkthrough |

## 🧪 Testing

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

## 📚 References

- [EUPHEMIA Public Description](https://www.epexspot.com/en/euphemia) — PCR market coupling algorithm
- [PyPSA](https://github.com/PyPSA/PyPSA) — Python for Power System Analysis (reference architecture)
- [POMATO](https://github.com/richard-weinhold/pomato) — Power Market Tool (FBMC reference)

## 🔒 Status

**Currently private** — not yet ready for public portfolio. Targeted for public release
when the remaining limitations are addressed and CI is green.

## Author

Built for quantitative optimization and energy market role applications at Euphemia   and Industry.
