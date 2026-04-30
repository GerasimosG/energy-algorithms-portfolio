# LP Optimization Module

Demonstrates core LP/MIP modeling skills using PuLP — directly relevant to optimization engineer take-home tests and interviews.

## Problems Solved

### 1. Transportation Problem
Minimize shipping cost across a network of supply nodes (warehouses) and demand nodes (retailers). Classic LP with:
- Supply capacity constraints
- Demand satisfaction constraints
- Flow conservation

**Why it matters:** Foundation of supply chain optimization, network flow problems, and spatial arbitrage in energy markets.

### 2. Portfolio Optimization
Mean-variance optimization with linear constraints using PuLP:
- Maximize expected return for a given risk target
- Constraint: sector exposure limits
- Constraint: min/max individual asset weights
- Constraint: cardinality (at most N assets selected) — introduces binary variables (MIP)

**Why it matters:** Core optimization skill for any quantitative role. Extends Markowitz to real-world linear constraints.

### 3. Unit Commitment (Simplified)
MIP model for generator scheduling with:
- Minimum uptime constraints (once on, must stay on for N hours)
- Minimum downtime constraints (once off, must stay off for N hours)
- Ramp rate limits
- Demand balance
- Reserve margin

**Why it matters:** Directly relevant to Euphemia   — Euphemia handles unit commitment constraints in power markets. This simplified model shows understanding of the MIP structure.

## Key Libraries

- **pulp** — LP/MIP modeling framework
- **numpy** — data structures

## Running

```bash
python -m lp-optimization.demo
```
