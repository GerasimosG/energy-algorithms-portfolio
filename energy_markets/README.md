# Energy Markets Module

## ★ Hero Module — Euphemia   & Euphemia Focus

This is the standout module that differentiates this portfolio from generic algorithmic trading repos. It demonstrates **domain knowledge of European power market coupling** — directly relevant to Euphemia  's work on the Euphemia algorithm.

## What This Module Contains

### 1. PCR Model (`pcr_model.py`)
Simplified implementation of the **Pan-European Coupling (PCR)** market clearing algorithm — the core optimization solved by Euphemia every day for 25+ European power exchanges.

**Features:**
- Social welfare maximization LP with PuLP
- Continuous supply/demand acceptance variables
- Binary block orders (all-or-nothing)
- Linked blocks: equality constraints via `group=` (cascade hydro)
- Exclusive blocks: sum-≤1 constraints via `excl_*` groups

### 2. Multi-Zone Coupling (`multi_zone.py`)
Extends the single-zone PCR model to multiple coupled zones with ATC (Available Transfer Capacity) constraints. Demonstrates the core of Euphemia: coupling separate markets so that cheap power flows to expensive zones up to transmission limits.

### 3. Block Orders (`block_orders.py`)
Real-world examples of complex order types handled by Euphemia:
- **Simple block** — all-or-nothing, used for minimum-load generators
- **Linked block** — several blocks that must all be accepted or none (cascade hydro)
- **Exclusive block** — mutually exclusive blocks (choose at most one configuration)

### 4. Market Clearing (`market_clearing.py`)
Single-zonal clearing: given supply and demand curves, find the equilibrium price and volume. Visualizes the supply/demand stack with proper consumer/producer surplus shading.

### 5. Euphemia   Interview Prep (`EUPHEMIA_INTERVIEW.md`)
Comprehensive guide mapping this codebase to Euphemia concepts:
- IP pricing for non-convex block orders
- PUN (Italy's single national price)
- FBMC vs ATC
- Interview question bank

## Connection to Euphemia

Euphemia (EUropean PHase I Market coupling Algorithm) is the algorithm developed by Euphemia   that:
- Couples 25+ European power exchanges into a single market
- Handles **1M+ orders** per hour of trading
- Runs a **MIP optimization** every hour for day-ahead and intraday markets
- Supports complex order types: block, linked, flexible, PUN (Italian single price)
- Maximizes **social welfare** across all coupled zones

This module demonstrates understanding of the **core LP** that powers Euphemia, with extensions to the full MIP formulation.

## Why This Matters for Euphemia  

| Concept | This Module | Real Euphemia |
|---------|-------------|---------------|
| Social welfare max | LP objective | MIP objective |
| Supply/demand curves | Piecewise linear | Step functions from order books |
| Block orders | Binary (all-or-nothing) | Full block order support |
| Linked blocks | Equality constraints | Cascading constraints |
| Exclusive blocks | Sum-≤1 constraints | Mutually exclusive families |
| Multi-zone coupling | ATC-constrained LP | 25+ zones with FBMC |
| MCP pricing | max(accepted prices) | IP pricing (non-convex) |

## Known Limitations

- ⚠ **MCP pricing**: Uses simple `max(accepted_prices)` — real Euphemia uses IP pricing for non-convex block orders (well-documented for interview discussion)
- ⚠ **No storage**: No inter-temporal constraints (hydro reservoirs, batteries)
- ⚠ **No FBMC**: ATC is simpler than flow-based market coupling
- ⚠ **No PUN**: Italy's single national price not modeled

## Running

```bash
# Full demo (PCR, blocks, market stack)
python -m energy_markets.demo

# Multi-zone coupling demo
python -c "from energy_markets.multi_zone import demo_multi_zone; print(demo_multi_zone())"
```
