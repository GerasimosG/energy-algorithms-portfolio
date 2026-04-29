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
├── energy_markets/        ★ HERO — PCR coupling, block orders, multi-zone, Euphemia context
│   ├── pcr_model.py       LP: social welfare maximization with binary block orders
│   ├── multi_zone.py      Multi-zone coupling with ATC constraints
│   ├── block_orders.py    Linked, exclusive, and simple block order scenarios
│   ├── market_clearing.py Supply/demand stack equilibrium + visualization
│   └── EUPHEMIA_INTERVIEW.md  Interview prep: Euphemia concepts, question bank
├── lp_optimization/        Core LP/MIP skills
│   ├── transportation.py  Classic transportation LP
│   ├── portfolio.py       Mean-variance (scipy SLSQP) + linear (PuLP)
│   └── scheduling.py      Unit commitment MIP with min up/down, ramp rates, reserve
├── backtester/             Vectorized backtesting engine + 7 risk metrics
├── strategies/             3 signal-based strategies (momentum, mean-reversion, SMA)
├── market_data/            Yahoo Finance → SQLite pipeline
├── tests/                  28 pytest tests across all modules
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

The `energy_markets/` module demonstrates understanding of the **PCR (Pan-European Coupling)** market clearing algorithm that powers Euphemia — the algorithm Euphemia   develops for 25+ European power exchanges.

### What's Implemented

| Concept | Implementation | Real Euphemia |
|---------|---------------|---------------|
| Social welfare max | LP objective (PuLP) | MIP objective |
| Supply/demand curves | Piecewise linear | Step functions from order books |
| Block orders | Binary (all-or-nothing) | Full block order support |
| Linked blocks | Equality constraints (`group=`) | Cascading hydro, multi-unit plants |
| Exclusive blocks | Sum-≤1 constraints (`excl_*`) | Mutually exclusive configurations |
| Multi-zone coupling | ATC-constrained flows | 25+ zones with FBMC |
| MCP pricing | max(accepted prices) | IP pricing (non-convexity aware) |

### Known Limitations (Documented for Interview Transparency)

- ⚠ **MCP pricing**: Uses simple `max(accepted_prices)` — real Euphemia uses IP pricing
  for non-convex block orders (discussed in `EUPHEMIA_INTERVIEW.md`)
- ⚠ **Single-period**: No inter-temporal constraints (storage, hydro reservoirs)
- ⚠ **No flow-based coupling**: ATC is simpler than FBMC; FBMC is discussed in docs
- ⚠ **No PUN pricing**: Italy's single national price not modeled

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Python modules | 8 |
| Total source files | 18 |
| Test files | 3 |
| Test cases | 28 (all passing) |
| Risk metrics | 7 (Sharpe, Sortino, maxDD, Calmar, VaR95, VaR99, Kelly) |
| Optimization solvers | 2 (PuLP/CBC, scipy SLSQP) |

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
