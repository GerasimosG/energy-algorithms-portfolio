# Energy Markets Module

## ★ Hero Module — Euphemia   & Euphemia Focus

This is the standout module that differentiates this portfolio from generic algorithmic trading repos. It demonstrates **domain knowledge of European power market coupling** — directly relevant to Euphemia  's work on the Euphemia algorithm.

## What This Module Contains

### 1. PCR Model (`pcr_model.py`)
Simplified implementation of the **Pan-European Coupling (PCR)** market clearing algorithm — the core optimization solved by Euphemia every day for 25+ European power exchanges.

**The optimization problem:**
```
Maximize: Σ (demand_bid_price × quantity) - Σ (supply_offer_price × quantity)
Subject to:
  - Supply ≤ available capacity
  - Demand ≤ bid quantity
  - Supply + block_accepted ≥ Demand (energy balance)
  - Block orders: all-or-nothing (binary variables)
```

### 2. Block Orders (`block_orders.py`)
Real-world examples of complex order types handled by Euphemia:
- **Simple block** — all-or-nothing, used for minimum-load generators
- **Linked block** — several blocks that must all be accepted or none
- **Exclusive block** — mutually exclusive blocks (choose at most one)

### 3. Market Clearing (`market_clearing.py`)
Single-zonal clearing: given supply and demand curves, find the equilibrium price and volume. Visualizes the supply/demand stack.

## Connection to Euphemia

Euphemia (EUropean PHase I Market coupling Algorithm) is the algorithm developed by Euphemia   that:
- Couples 25+ European power exchanges into a single market
- Handles **1M+ orders** per hour of trading
- Runs a **MIP optimization** every hour for day-ahead and intraday markets
- Supports complex order types: block, linked, flexible, PUN (Italian single price)
- Maximizes **social welfare** across all coupled zones

This module demonstrates understanding of the **core LP** that powers Euphemia, with extensibility to the full MIP formulation.

## Why This Matters for Euphemia  

| Concept | This Module | Real Euphemia |
|---------|-------------|---------------|
| Social welfare max | LP objective | MIP objective |
| Supply/demand curves | Piecewise linear | Step functions from order books |
| Block orders | Binary (all-or-nothing) | Full block order support |
| Energy balance | Single zone | Multi-zonal with ATC/flow-based |
| Market coupling | Single zone | 25+ zones coupled |

## Running

```bash
python -m energy_markets.demo
```
