# Block Orders: Linked, Exclusive & Non-Convex Pricing

## What Are Block Orders?

A **block order** is a bid to buy or sell a fixed quantity of electricity across multiple consecutive hours at a single price. Unlike simple hourly orders, blocks are **all-or-nothing** — they're either fully accepted in all hours or fully rejected.

```
Simple hourly order: "I'll sell 50 MW at hour 12 for €80/MWh"
Block order: "I'll sell 200 MW for hours 8-20 inclusive at €55/MWh — take it all or nothing"
```

### Why Blocks Exist

Nuclear, coal, and combined-cycle gas plants have:
- **High startup costs** (€10K–€500K to start)
- **Minimum run times** (hours to days)
- **Ramp rate limits** (MW/minute constraints)

A nuclear plant can't economically start up for just one peak hour. Block orders let it bid for a continuous run, amortizing startup costs.

### Block Order Types

| Type | Constraint | Example |
|------|-----------|---------|
| **Regular block** | All-or-nothing across specified hours | Nuclear baseload: 24h, 800 MW, €45/MWh |
| **Linked block** | Two blocks accepted/rejected together | Parent (cheap) + child (must-run minimum) |
| **Exclusive block** | At most one from a group is accepted | Build option A vs option B (mutually exclusive) |
| **Curtailable block** | Can be partially reduced (not in our simple model) | Flexible demand response |
| **Profile block** | Varying quantities across hours (not in our model) | Run-of-river hydro |

---

## Mathematical Formulation

### Without Blocks (Pure LP)

```
max Σ(consumer_bids) - Σ(producer_bids)
s.t.
 Energy balance (supply = demand)
 0 ≤ x ≤ 1 (continuous acceptance)
```

This is a **Linear Program** — polynomial time, globally optimal.

### With Block Orders (MIP)

```
max Σ(consumer_bids) - Σ(producer_bids) - Σ(block_bids · y)
s.t.
 Energy balance (supply + blocks = demand)
 0 ≤ x ≤ 1 (continuous hourly acceptance)
 y ∈ {0, 1} (binary block acceptance)
```

This is a **Mixed Integer Program** — NP-hard in general. Euphemia solves this for 25+ countries with 1M+ orders.

### Linked Blocks in Our Code

From `energy_markets/block_orders.py`:

```python
# Linked blocks share a group identifier
model.add_block("Nuclear_Parent", price=45, qty=800, group="nuclear")
model.add_block("MustRun_Min", price=50, qty=200, group="nuclear")

# Constraint: y_parent == y_child
# Both accepted or both rejected
prob += (y_parent == y_child, "link_nuclear")
```

### Exclusive Blocks in Our Code

```python
# Exclusive group: at most one accepted
model.add_block("Build_Coal", price=60, qty=500, group="excl_plant")
model.add_block("Build_Gas", price=55, qty=400, group="excl_plant")

# Constraint: sum(y_i for i in "excl_plant") <= 1
prob += (y_coal + y_gas <= 1, "excl_plant")
```

---

## Non-Convexity: Why This Matters

### What Makes It Non-Convex?

The feasible region of an LP is convex. With binary variables, it becomes a disjunctive union of convex regions — **not convex**.

**Consequence:** The welfare-maximizing solution with binary block decisions may NOT have uniform clearing prices that leave every market participant non-negative in surplus.

### The Welfare Gap

```
Simple hourly clearing: MCP = €50/MWh, everyone happy
With blocks accepted: Block accepted at €45/MWh, but uniform MCP = €55/MWh
 → Block holder loses €10/MWh × 800 MW per hour
 → Paradoxically accepted block (accepted but loses money)
```

This is why Euphemia has a separate **IP pricing** pass.

---

## MCP vs IP Pricing

### Market Clearing Price (MCP)

The simple approach:
```
MCP = max(price of last accepted supply unit)
```

Used in our `pcr_model.py` for simplicity.

### Integer Programming (IP) Pricing

After finding the welfare-maximizing dispatch (which blocks are accepted), solve a separate LP:
```
min Σ(make-whole payments)
s.t.
 Same dispatch as MIP solution
 Prices minimize deviations from uniform pricing
 Block holders get non-negative surplus
```

This is what real Euphemia does. Our `pcr_model.py` documents this as a known limitation.

### Make-Whole Payments

When a block is "paradoxically accepted" (accepted in the MIP but would lose money at uniform MCP), the market operator pays the difference:

```
make_whole = max(0, block_cost - block_revenue_at_MCP)
```

---

## Block Order Clearing Algorithm

```
1. Collect all orders (hourly + blocks) for the day
2. Order matching: group linked blocks, identify exclusive groups
3. Solve MIP: max welfare with binary block variables
4. Fix block decisions (y values now known)
5. Solve LP: compute prices that minimize make-whole payments
6. Publish results: accepted blocks, hourly prices, flows
```

Euphemia repeats steps 3-5 multiple times with different block order iterations because:
- Some blocks may be submitted conditionally ("accept only if price > X")
- Block decisions change prices, which may change which blocks are profitable
- The process iterates until convergence

---

## Edge Cases

### 1. Block at Exactly the Marginal Price
```
Supply: [10 @ €50, 20 @ €60]
Block: 15 @ €60
Demand: 25 @ €100
```
The block's price equals the marginal unit. Should it be accepted? Floating-point tolerances can flip this decision. Euphemia has explicit tie-breaking rules.

### 2. Empty Linked Group
A single block with a group ID but no partner — should this be a warning or an error? Our code handles this gracefully (the constraint is trivially satisfied).

### 3. Exclusive Group with All Rejected
```
Exclusive group: Block_A (€100), Block_B (€95)
MCP with neither: €50
Wait — should both be rejected even though they'd make money?
```
If both are above MCP, the solver must pick at most one. It picks the one that maximizes welfare (lower price wins). The other is rejected despite being "profitable" individually.

### 4. Block Size vs Market Size
A 1000 MW block in a 200 MW market — accepted or rejected? It must displace all smaller orders, potentially reducing welfare. The MIP handles this automatically.

### 5. Numerical Tolerance Issues
```python
# Binary check in our code uses 0.5 threshold, not == 1.0
accepted = pulp.value(y_var) > 0.5 # Safe for CBC's numerical noise
```

---

## Quick Quiz

**Q1:** Why do block orders make market coupling an MIP instead of LP?

**Q2:** What's the difference between linked and exclusive blocks? Give a real-world example of each.

**Q3:** What is a "paradoxically accepted block"?

**Q4:** Why does Euphemia solve a separate LP for pricing after the MIP solve?

**Q5:** In the code, why do we check `pulp.value(y_var) > 0.5` instead of `== 1.0`?

---

## Answers

**A1:** Block orders introduce binary variables (0 or 1 for acceptance). Binary variables make the problem non-convex — the feasible region becomes a disjunctive union. Solving requires branch-and-bound (MIP), not pure simplex (LP).

**A2:** Linked blocks: both accepted or both rejected (parent+child nuclear). Exclusive: at most one accepted (comparing two investment options). Linked uses equality constraint; exclusive uses `sum <= 1`.

**A3:** A block accepted in the welfare-maximizing MIP but whose holder would have negative surplus at the uniform MCP. Requires make-whole payments to compensate.

**A4:** The MIP finds the optimal dispatch (which blocks to accept). Then a separate LP finds prices that minimize make-whole payments while preserving the dispatch. This two-stage process is the Euphemia approach.

**A5:** CBC (and most MIP solvers) have numerical tolerances — a binary variable might be 0.999999 or 0.000001 instead of exactly 1.0 or 0.0. Using `> 0.5` is a robust threshold against this floating-point noise.

---

**Code references:** `energy_markets/block_orders.py`, `energy_markets/pcr_model.py`, `tests/test_pcr_model.py`
