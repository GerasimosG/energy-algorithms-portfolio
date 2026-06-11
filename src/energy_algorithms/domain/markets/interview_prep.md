# ✨ Interview Readiness — Euphemia Connection

This document explains how this repo's energy markets module maps to
concepts you'll be asked about in a **Junior Optimization Engineer — energy markets** interview.

## Concepts You Must Know

### 1. Social Welfare Maximization (LP → MIP)

**What we have:** `PCRModel` maximizes `Σ(demand_price × qty) − Σ(supply_price × qty)`
with continuous acceptance variables and binary block orders.

**What Euphemia does:** Same objective, but with:
- 25+ zones coupled simultaneously
- ATC (Available Transfer Capacity) constraints between zones
- Flow-based market coupling (FBMC) instead of simple ATC
- 1M+ orders per session

**Our demo:** `energy_markets/multi_zone.py` shows the multi-zone extension.

### 2. Block Orders and Non-Convexity

**What we have:** Simple binary block orders with `group=` for linked/exclusive.

**What Euphemia does additionally:**
- **IP (Integer Programming) pricing**: When block orders create non-convexities,
 the simple `max(accepted_prices)` MCP is not the economically efficient price.
 Euphemia uses IP pricing rules that minimize make-whole payments.
- **PUN (Prezzo Unico Nazionale)**: Italy's single national price — a weighted
 average of zonal prices when zones have different MCPs.
- **Flexible block orders**: Blocks where quantity can vary within a range,
 not just all-or-nothing.

**Know this for interviews:** "The simple LP formulation uses marginal pricing,
but real Euphemia uses IP pricing to handle non-convexities from block orders.
This is the price that minimizes required make-whole payments to block order
holders while maintaining the welfare-maximizing dispatch."

### 3. Merit Order and Price Formation

**What we have:** `market_clearing.py` builds supply/demand stacks and finds
the equilibrium price.

**Know this for interviews:**
- The **merit order** ranks supply by ascending price → cheapest plants dispatched first
- The **marginal plant** sets the price — all accepted suppliers receive the MCP
- **Price spikes** occur when the marginal plant is expensive (gas peaker at €200+/MWh)
- **Negative prices** occur when must-run generation exceeds demand (nuclear/wind at night)

### 4. Unit Commitment (MIP)

**What we have:** `scheduling.py` with binary on/off, min up/down, ramp rates,
startup costs, initial conditions, reserve margin.

**What Euphemia integrates:**
- Generator must-run constraints
- Ramping and startup trajectories
- The unit commitment is part of the welfare maximization (not separate)

### 5. Interview Question Bank

| Question | Answer Points |
|----------|--------------|
| "Explain PCR/Euphemia" | Pan-European Coupling. Algorithm for Pan-European Coupling. Couples 25+ exchanges. Maximizes social welfare via MIP. Supports complex orders. |
| "What is social welfare?" | Sum of consumer surplus + producer surplus. Maximized when marginal cost = marginal benefit. |
| "How do block orders work?" | All-or-nothing binary variables. Can be linked (accept all or none) or exclusive (at most one). Create non-convexities requiring IP pricing. |
| "What is FBMC vs ATC?" | ATC = fixed capacity per border. FBMC = dynamic capacity based on network flows, more efficient. |
| "Why PuLP vs Gurobi?" | PuLP is open-source, great for prototyping and learning. Gurobi/CPLEX for production-scale MIPs. |
| "Explain the merit order" | Supply stacked by ascending price. Intersection with demand sets MCP and volume. |
