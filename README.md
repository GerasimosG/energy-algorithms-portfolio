# Optimization Portfolio

A public portfolio repo demonstrating **optimization modeling**, **energy market domain knowledge**, and **algorithmic trading** — built for quantitative finance and energy optimization roles.

## 🎯 Why This Repo

Targeted at the **Euphemia   Junior Optimization Engineer** role and similar positions in energy markets, optimization, and quantitative trading:

| Skill | Demonstrated In |
|-------|-----------------|
| **PuLP LP/MIP modeling** | Transportation problem, portfolio optimization, unit commitment |
| **Energy market domain** | PCR (Pan-European Coupling), Euphemia, social welfare maximization |
| **Block order handling** | All-or-nothing, linked, and exclusive orders in market coupling |
| **scipy optimization** | Efficient frontier, convex portfolio optimization |
| **Backtesting & risk** | Vectorized engine, Sharpe, Sortino, VaR, Kelly criterion |
| **Clean Python** | Modular design, tests, type hints, git discipline |

## Architecture

```
optimization-portfolio/
├── energy_markets/        ★ HERO MODULE — PCR coupling, block orders, Euphemia context
├── lp_optimization/        Core LP/MIP skills — transportation, portfolio, scheduling
├── backtester/             Vectorized backtesting engine + risk metrics
├── strategies/             Signal-based trading strategies
├── market_data/            Free API → SQLite data pipeline
└── notebooks/              Jupyter exploration
```

## Quick Start

```bash
pip install -r requirements.txt
python -m energy_markets.demo      # ★ Start here — the showcase module
python -m lp_optimization.demo     # Core LP/MIP skills
python -m market_data.demo         # Data pipeline
python -m backtester.demo          # Backtesting + risk
python -m strategies.demo          # Trading strategies
```

## Modules

### energy-markets (★ Hero Module)
Simplified PCR (Pan-European Coupling) market clearing model using PuLP. Implements the core Euphemia algorithm logic: social welfare maximization with supply/demand curves, block orders (all-or-nothing), and single-zonal market clearing. This is what makes this repo stand out for energy market roles.

**Why this matters for Euphemia  :** Euphemia   develops the Euphemia algorithm that couples 25+ European power exchanges. This module demonstrates understanding of:
- Social welfare optimization in electricity markets
- Block order constraints (minimum load, must-run generation)
- LP formulation of market clearing
- The connection between theoretical optimization and real-world power trading

### lp-optimization
Three classic optimization problems solved with PuLP:
- **Transportation problem** — minimize shipping cost across supply/demand nodes
- **Portfolio optimization** — mean-variance with linear constraints
- **Unit commitment (simplified)** — MIP with minimum up/down time constraints

### backtester
Vectorized backtesting engine: price series → signals → equity curve → trades log. Risk metrics: Sharpe, Sortino, max drawdown, Calmar, VaR (historical), Kelly fraction. Pure numpy.

### strategies
Three signal-based strategies:
1. SMA crossover (trend following)
2. Bollinger Bands mean reversion
3. Momentum factor

### market-data
Fetches OHLCV from Yahoo Finance (yfinance), stores in SQLite with daily schema. Handles rate limits.

## Requirements

- Python 3.11+
- See `requirements.txt`

## Author

Built for quantitative optimization and energy market role applications.
