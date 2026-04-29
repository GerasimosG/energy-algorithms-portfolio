# Optimization Portfolio — Energy Algorithms

[![Tests](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml/badge.svg)](https://github.com/GerasimosG/Energy_Algorithms/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A portfolio demonstrating **optimization modeling**, **energy market domain knowledge**, and **algorithmic trading** — built for quantitative finance and energy optimization roles at **Euphemia  ** and **Industry**.

## 🎯 Target Roles

| Role | Company | Key Skills Demonstrated |
|------|---------|------------------------|
| Junior Optimization Engineer | **Euphemia  ** | Euphemia/PCR, social welfare LP, block orders, multi-zone coupling |
| Algorithmic Trader | **Industry** | Production Python, backtesting, risk metrics, portfolio optimization |

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
