# Market Coupling: PCR, Euphemia, ATC vs FBMC

> **Target audience:** Engineering/optimization generalist seeking deep energy domain
> knowledge for roles in energy market roles, EPEX SPOT, ENTSO‑E, or similar.
> **Repo references:** `energy_markets/pcr_model.py`, `energy_markets/multi_zone.py`,
> `energy_markets/fbmc.py`, `energy_markets/block_orders.py`,
> `energy_markets/market_clearing.py`, `energy_markets/lodf_utils.py`,
> `energy_markets/gsk.py`.

---

## 1. What Is Market Coupling and Why Does It Exist?

Market coupling is the mechanism that **simultaneously clears multiple power exchanges
across different geographic zones (or countries)** so that electricity flows from
low-price areas to high-price areas — up to the physical limits of the transmission
network. Without it, each country would run its own auction and cross-border capacity
would be allocated in a separate, sequential "explicit auction" that traders then use to
arbitrage price differences.

### The problem with explicit auctions

```
Before coupling (explicit auction):
 Zone A: MCP = €30/MWh (cheap wind)
 Zone B: MCP = €70/MWh (expensive gas)
 Interconnector capacity: 100 MW

 Trader buys 100 MW of capacity at €X/MW in explicit auction,
 buys power in A at €30, sells in B at €70.
 Profit = 100 × (70 - 30 - X).

 If X < 40, trader profits.
 If X > 40, capacity unused even though physical wire is there.
 Worst case: capacity allocated to the wrong trader, or
 Germany↔France gets congested but Netherlands↔Belgium is fine
 because no one bid.
```

Market coupling **embeds cross-border capacity into the same auction as energy**, so the
optimization jointly decides who generates, who consumes, and how much flows — all to
maximize total **social welfare**. This is the core innovation behind PCR (Price
Coupling of Regions) and the Euphemia algorithm.

### DID YOU KNOW?

> The first multi-region market coupling went live in 2006 between France, Belgium, and
> the Netherlands ("Trilateral Market Coupling"). By 2025, the Single Day-Ahead Coupling
> (SDAC) covers **27 European countries** with ~3,500 TWh of yearly demand and **3.1
> million price-zone-hour combinations solved daily**.

---

## 2. Social Welfare Maximization — The Fundamental Objective

### Intuition

The "right" thing for a market to do is **maximize the sum of consumer surplus plus
producer surplus**. In a competitive equilibrium, this is equivalent to maximizing:

```
Welfare = Σ (value consumers get) — Σ (cost producers incur)
```

On a step-wise bid curve, we write it as:

```
max Σ Σ (demand_price[di] × demand_qty[di] × d_frac[di])
 - Σ Σ (supply_price[si] × supply_qty[si] × s_frac[si])
 - Σ (block_price[bi] × block_qty[bi] × b_bin[bi]) ... if block orders present
```

where `d_frac`, `s_frac` ∈ [0, 1] are continuous acceptance fractions, and `b_bin` ∈ {0, 1}
are binary (all-or-nothing for block orders).

### Derivation from consumer/producer surplus

Consider a single zone with supply curve S(q) and demand curve D(q). At equilibrium
quantity q*, the price p* clears the market. The shaded areas:

```
Price
 ^
 | D(q)
 | \
 | \ consumer surplus = area between D(q) and p*
 | \
 |--------\------- p* ← clearing price
 | /\
 | / \
 | / \ producer surplus = area between p* and S(q)
 | / S(q) \
 | / \
 +---+----------+--------> Quantity
 0 q*
```

In the optimization, we don't set p* directly. Instead, we **provisionally accept all
demand bids at their bid price and all supply bids at their offer price**, then let the
solver pick acceptance fractions. The total surplus is:

```
Σ (demand_bid_price × accepted_qty) — Σ (supply_offer_price × accepted_qty)
```

This is exactly the linear objective in `PCRModel.solve()` (`pcr_model.py` line 59-67).
If we subtract this from the total demand value if all demand were served, we get the
standard "minimize cost" formulation — but maximization of surplus is more natural
because it handles both sides symmetrically.

### Concrete numerical example

```
Supply offers:
 Wind: 200 MW @ €5/MWh
 Hydro: 100 MW @ €30/MWh
 Gas: 200 MW @ €80/MWh

Demand bids:
 Industry: 250 MW @ €180/MWh
 Residential: 150 MW @ €120/MWh
```

The intersection is at ~300 MWh (all Wind + 100 MW of Hydro), with a clearing price of
€30/MWh (the marginal accepted supply). Consumer surplus = (180-30)×250 + (120-30)×50 =
€42,000. Producer surplus = (30-5)×200 + (30-30)×100 = €5,000. **Total social welfare
= €47,000.**

In the LP, the objective would be:
```
W = (180×250×d1 + 120×150×d2) — (5×200×s1 + 30×100×s2 + 80×200×s3)
```
The solver sets d1=1.0, d2=0.333..., s1=1.0, s2=1.0, s3=0 → W = 63,000 — 15,000 = 48,000
(small difference due to partial acceptance — the LP allows fractional acceptance of the
marginal demand bid, yielding the exact equilibrium).

---

## 3. PCR (Price Coupling of Regions) — Step by Step

PCR is the **algorithmic framework** that couples day-ahead electricity markets across
Europe. Euphemia is the **implementation** — a large-scale Mixed Integer Programming
(MIP) solver for European market coupling.

### The PCR process in 7 steps

```
1. Order Collection (by 12:00 CET)
 └─ Market participants submit hourly supply/demand bids
 and complex (block) orders to their local power exchange.

2. Order Sharing
 └─ All orders are anonymized and sent to the central PCR system.
 Each PX is a "party" with its own order book zone(s).

3. Network Data Ingestion
 └─ TSOs provide Available Transfer Capacity (ATC) or
 Flow-Based (FBMC) parameters per interconnector/direction.

4. Welfare Maximization LP/MIP
 └─ Euphemia solves one giant optimization problem:
 max Σ(welfare across all zones)
 s.t. per-zone energy balance, ATC/FB constraints,
 block order integrality, ramping, etc.

5. Price Determination (MCP or IP Pricing)
 └─ For zones without block orders: MCP = dual of energy balance.
 For zones with block orders: IP pricing to handle paradoxically
 accepted/rejected blocks (see §10).

6. Result Dissemination (by 13:00 CET)
 └─ Each PX receives clearing prices, accepted volumes,
 and cross-border flows for every hour of the next day.

7. Fallback Procedure
 └─ If coupling fails (e.g., IT outage), each zone decouples and
 runs local auctions independently.
```

### In the repo

`PCRModel` (`pcr_model.py`) implements a **single-zone MIP** with continuous
supply/demand and binary block orders, plus linked/exclusive group constraints.
It demonstrates steps 1, 4, 5 in miniature. The `solve()` method constructs a
`pulp.LpProblem`, adds acceptance variables and energy balance, and solves with CBC.

---

## 4. The Euphemia Algorithm — the industry's Implementation

Euphemia (the commercial implementation of PCR) is **not** just "a big MIP solver." It
is a highly specialized algorithm with several innovations that make the full European
problem tractable (hundreds of millions of variables in raw form):

### Key algorithmic innovations

1. **Spatial decomposition (ATC regions):** For ATC-based coupling, zones that are not
 congested with each other can be merged into "net positions." Euphemia exploits this
 network sparsity aggressively.

2. **Block order pre-processing:** Many block orders are **dominated** by continuous
 orders at the same price and can be removed before the MIP starts. Others are
 eliminated by comparing their prices to feasible bounds derived from supply/demand
 curves ("economic pre-processing").

3. **Branch-and-cut with custom cuts:** The core MIP solver (XPRESS) uses problem-specific
 cutting planes — e.g., "minimum income condition" cuts that enforce: if a block is
 accepted, the market price must be at least its offer price plus a small uplift
 (otherwise another feasible dispatch would have higher welfare).

4. **Heuristic primal search:** A fast constructive heuristic finds a good feasible
 solution quickly, giving the MIP a warm start and an upper bound for early pruning.

5. **Benders-like decomposition for FBMC:** In flow-based mode, the physical network
 constraints (PTDF × net_positions ≤ RAM) are separated from the market clearing
 problem. Flow constraints are generated lazily — only violated ones are added to the
 master problem.

6. **Paradoxical block resolution:** After the welfare-maximizing MIP dispatch, Euphemia
 runs a second pricing optimization that finds the uniform clearing price minimizing
 "make-whole" payments to blocks whose acceptance status appears contradictory at that
 price (see §10).

### DID YOU KNOW?

> Euphemia solves the full European day-ahead market in under **17 minutes** — with
> roughly 500,000 binary variables. The raw problem (before preprocessing/decomposition)
> would have hundreds of millions of binaries, making it one of the largest MIPs solved
> daily in the world.

---

## 5. ATC (Available Transfer Capacity) — The Simplified Approach

ATC is the **older, simpler** way to represent cross-border transmission constraints:

- Each interconnector between two zones has a single MW capacity limit.
- The flow from zone A to zone B cannot exceed `ATC[A→B]` MW.
- The flow from B to A cannot exceed `ATC[B→A]` MW (may differ).

### ATC formulation in the LP

```
Variables:
 flow[A→B] ∈ [0, ATC_AB] for each directional pair

Constraints (per zone):
 supply_z + Σ(imports into z) = demand_z + Σ(exports from z)
```

In `multi_zone.py` (line 59), flow variables are created only for pairs with ATC entries,
and each flow variable has an upper bound equal to the ATC.

### Concrete ATC example (3 zones)

```
Zones:
 North: supply {Wind: 300MW@€5, Hydro: 200MW@€30}, demand {200MW@€100}
 Center: supply {Gas: 150MW@€40, Coal: 200MW@€70}, demand {400MW@€150}
 South: supply {Gas: 100MW@€60, Diesel: 200MW@€90}, demand {250MW@€120}

ATC limits:
 North→Center: 200 MW
 Center→South: 100 MW

Optimal dispatch:
 North generates 350 MW, consumes 200 MW, exports 150 MW to Center
 Center generates 150 MW (gas), imports 150 MW from North,
 consumes 250 MW, exports 50 MW to South
 South generates 50 MW (gas), imports 50 MW from Center,
 consumes 100 MW
 Remaining demand in Center (50 MW) and South (150 MW) unmet
 (insufficient transfer capacity)

MCPs: North €5, Center €40-70, South €60-90 (varies by binding)
```

### Limitations of ATC

ATC assumes that the only thing constraining trade between A and B is the wire between
them. In a meshed network, this is fundamentally wrong — power flows according to
Kirchhoff's laws, distributing across all parallel paths, not just the direct connection.

---

## 6. FBMC (Flow-Based Market Coupling) — The Real Thing

FBMC replaces ATC limits with **physical network constraints** derived from the Power
Transfer Distribution Factor (PTDF) matrix and Reliability Assessment Margins (RAM).

### Core concept

Instead of saying "flow A→B ≤ 100 MW," FBMC says:

```
For every critical branch (transmission line) l:
 -RAM_reverse[l] ≤ Σ_z (PTDF[l, z] × net_position[z]) ≤ RAM_forward[l]
```

where:
- **PTDF[l, z]** = change in flow on branch *l* for a 1 MW increase in net injection at
 zone *z* (with 1 MW withdrawal at a reference/slack bus).
- **net_position[z]** = total generation — total consumption in zone *z* (positive =
 exporter, negative = importer).
- **RAM[l]** = Reliability Assessment Margin — how much headroom is left on branch *l*
 after subtracting the base-case ("reference") flow and a security margin for N-1
 contingencies.

### Why PTDF rows must sum to zero

Kirchhoff's current law: total generation = total consumption across the system. If you
increase all zones' net positions by exactly the same amount, the physical flows on every
line stay the same. This is enforced by:

```
Σ_z PTDF[l, z] = 0 for every branch l
```

In `fbmc.py` (line 84-88), this constraint is validated at input.

### In the repo

`solve_fbmc()` (`fbmc.py`) implements the full FBMC LP:
- Decision variables: supply/demand acceptance fractions per zone, net_position per zone.
- Constraints: per-zone energy balance, system energy balance (Σ net_positions = 0),
 PTDF flow constraints on each branch.
- Extracts branch flow utilization after solving.

### GSK (Generation Shift Key) — mapping zones to nodes

The PTDF matrix relates zonal net positions to branch flows, but physical generation
injections happen at **nodes** (individual busbars). The GSK matrix `GSK[i, z]` tells
us what fraction of zone z's net position is injected at node i.

The repo's `gsk.py` implements three strategies:
1. **Flat GSK:** equal share per node in a zone.
2. **Gmax GSK:** share proportional to installed generation capacity.
3. **Dynamic GSK:** share proportional to actual dispatch (reflecting real-time
 conditions, with capacity fallback).

---

## 7. Loop Flows — The Killer Example That Breaks ATC

Loop flows are the primary reason FBMC exists. Consider three zones A, B, C in a
triangle:

```
 A ─────────── B
 │ \ / │
 │ \ / │
 │ Line_AC │ │
 │ \ / │
 │ \ / │
 └────── C ──────┘
```

Zones A and B are connected directly (Line_AB) and also indirectly through C
(A→C→B) and through two parallel paths (A→C→B and A→B). When A exports 100 MW to B:

**ATC assumes:** 100 MW goes on Line_AB. If ATC_AB = 80 MW, flow is capped at 80 MW.

**Physical reality (Kirchhoff):** The 100 MW divides among all parallel paths according
to impedances:
- 60 MW on Line_AB (direct path)
- 25 MW on Line_AC (A→C) and then 25 MW on Line_BC (C→B)
- 15 MW circulating via some other path (loop flow)

The 25 MW on Line_AC flows **from A toward C**, even though the trade is A→B. This is a
loop flow — it can overload Line_AC even when ATC_A→C is not directly used.

### Concrete loop-flow example that breaks ATC

```
PTDF matrix (rows sum to 0):

 A B C
 Line_AB: [ 0.60, -0.40, -0.20 ]
 Line_BC: [ 0.30, 0.30, -0.60 ]
 Line_AC: [ 0.10, -0.10, 0.00 ]

RAM (all lines): ±100 MW

ATC-only approach:
 ATC_AB = 100 MW, ATC_BC = 100 MW, ATC_AC = 100 MW
 No individual ATC is violated → ATC says "OK"

Actual net positions:
 A exports 80 MW, B imports 60 MW (net), C imports 20 MW

Flows under PTDF:
 Line_AB: 0.60×80 + (-0.40)×(-60) + (-0.20)×(-20) = 48 + 24 + 4 = 76 MW ✓
 Line_BC: 0.30×80 + 0.30×(-60) + (-0.60)×(-20) = 24 - 18 + 12 = 18 MW ✓
 Line_AC: 0.10×80 + (-0.10)×(-60) + 0.00×(-20) = 8 + 6 + 0 = 14 MW ✓

Now suppose A wants to export 150 MW to B:
 Line_AB: 0.60×150 + 0.40×60 + 0.20×20 = 90 + 24 + 4 = 118 MW → VIOLATES 100 MW RAM!

ATC would never catch this because no individual A→B flow is set to 150 MW — the
interaction of flows on the meshed network creates a violation that ATC is blind to.
```

Only FBMC, which models the complete PTDF × net_position for every branch, can detect and
prevent such violations.

### N‑1 contingency screening (LODF)

FBMC must also check N-1 security: what happens if a branch *k* trips? The **Line Outage
Distribution Factor (LODF)** matrix tells us how flow redistributes:

```
LODF[l, k] = fractional change in flow on branch l when branch k is outaged
```

The CBCO screening in `lodf_utils.py` filters out branches that won't bind even under
contingency, reducing the constraint count. The screening condition is:

```
|base_flow[l]| + |LODF[l,k] × base_flow[k]| ≥ threshold × RAM[l]
```

---

## 8. Merit Order Stack — Supply Curves, Demand Curves, Clearing

### The merit order principle

Supply offers are sorted by **ascending price** (merit order — cheapest first). Demand
bids are sorted by **descending price** (highest willingness-to-pay first). The
intersection determines the market clearing price (MCP) and volume.

```
Price (€/MWh)
 ^
200│ ┌──────────────────── Demand
 │ │
180│ │╲
 │ │ ╲
150│ │ ╲
 │ │ ╲
120│ │ ╲___
 │ │ ╲___
100│ │ ╲___
 │ │ ╲___
 80│ ┌───┤ ╲
 │ ____│ │ ╲
 60│ ___│ │ │ ╲
 │ │ │ │ │ ╲
 40│ │ │___│ │ ╲
 │ │ │ │ │ ╲
 20│ │__│___│___│______________________╲___
 │__│__│___│___│______________________╲_
 +--+--+---+---+---+---+---+---+---+---+--→ Quantity (MWh)
 0 100 200 300 400 500 600 700 800 900 1000
 Wind Hydro Gas Coal
```

### In the repo

`market_clearing.py` (`find_equilibrium()`) computes the exact intersection by
interpolating both curves on a shared quantity grid and finding the sign-change point.
The plot function (`plot_supply_demand_stack`) produces the diagram above.

The LP-based approach (`PCRModel`, `fbmc.py`) is mathematically equivalent but directly
yields the dual price at the energy balance constraint (the MCP).

### DID YOU KNOW?

> In the real European market, the "merit order" isn't just generation cost — it also
> includes must-run blocks (nuclear minimum load), CHP (combined heat and power) plants
> that must run for heat, and renewable priority dispatch rules. All of these become
> constraints in Euphemia's MIP.

---

## 9. Non‑Convexities — Why Block Orders Break Everything

### What is a block order?

A block order is an **all-or-nothing** bid: the generator offers to supply exactly X MW
at price P for a set of consecutive hours, and the market must either accept the entire
block or reject it. Examples:

- **Nuclear must-run:** minimum stable load, can't modulate below 80 MW.
- **CHP plant:** produces electricity + heat — either runs at rated output or shuts down.
- **Cascaded hydro:** three plants on a river system must operate together.

### Why non-convex?

A block order introduces a binary variable `b ∈ {0, 1}` into what would otherwise be a
Linear Program (convex). The constraint "accept exactly 0 or Q MW" is:

```
q = Q × b where b ∈ {0, 1}
```

This makes the problem a **Mixed Integer Program (MIP)** — NP-hard in general. The
feasible region is no longer convex, which means:

1. **No dual prices:** LP duality theory doesn't hold. The marginal value of relaxing
 the energy balance constraint is not a well-defined "market price."

2. **Welfare gap:** The optimal integer dispatch may leave some cheap supply unused (or
 expensive demand served) because fractional acceptance would be better but isn't
 allowed.

3. **Paradoxical blocks:** A block with offer price €50/MWh might be rejected while a
 continuous supply at €70/MWh is accepted, because accepting the 80 MW block would
 force the rejection of even more valuable demand or cheaper supply elsewhere.

### Linked and exclusive blocks

Block orders can be grouped:
- **Linked (`group="cascade"`):** all blocks in the group must share the same binary
 value — either all accepted or all rejected (`pcr_model.py` line 88-92).
- **Exclusive (`group="excl_*"`):** at most one block in the group can be accepted —
 used for mutually exclusive plant configurations (`pcr_model.py` line 86-87).

### In the repo

`block_orders.py` demonstrates three scenarios:
1. Simple block (nuclear baseload — €40/MWh, 80 MW must-run)
2. Linked block (two hydro plants on a cascade)
3. Exclusive block (coal plant vs gas plant — mutually exclusive)

---

## 10. IP Pricing vs MCP — When and Why They Differ

### MCP (Marginal Clearing Price)

In a purely convex LP (no block orders), the MCP is the dual variable of the energy
balance constraint — the price at which an additional 1 MW of demand would be served.
Every accepted supply offer is at or below MCP; every accepted demand bid is at or above
MCP. **No one is "paradoxical."**

### The paradox

With block orders (MIP), the welfare-maximizing dispatch may include:

- **Paradoxically Accepted (PA):** a block with offer price €70/MWh accepted, even though
 the uniform price is €60/MWh. At €60, the block "shouldn't" want to run — it loses
 €10/MWh. But accepting it enables acceptance of a very high-value demand block that
 more than compensates.

- **Paradoxically Rejected (PR):** a block with offer price €40/MWh rejected, even though
 the uniform price is €60/MWh. At €60, it "should" want to run and earn €20/MWh. But
 accepting it would force rejection of even better blocks (or violate a constraint).

### IP (Integer Programming) pricing

IP pricing finds the **uniform clearing price** that minimizes "make-whole" payments to
these paradoxical blocks:

```
make_whole_payment =
 Σ_{PA} (offer_price - IP_price) × qty ... compensate accepted blocks above IP
+ Σ_{PR} (IP_price - offer_price) × qty ... compensate rejected blocks below IP
```

The IP price is found by:
1. Solve the welfare-maximizing MIP to get the optimal dispatch.
2. Identify the feasible IP price range (must cover all accepted continuous supply and be
 ≤ all accepted demand prices).
3. Enumerate candidate IP prices from all relevant price breakpoints.
4. Pick the one that minimizes total make-whole payments.

The repo's `PCRModel.solve_with_ip_pricing()` (`pcr_model.py` lines 147-251) implements
this simplified IP pricing with exhaustive enumeration over candidate prices.

### DID YOU KNOW?

> In Euphemia, IP pricing runs separately for **every hour** of the next day — 24 pricing
> problems per day. With 27+ zones, that's 648+ IP pricing solutions every day. The
> algorithm uses sophisticated dominance checks and price-range narrowing to keep it
> tractable, not brute-force enumeration.

---

## EDGE CASES

### 1. RAM = 0 (zero transfer capacity)

When all interconnector RAM is zero, zones are completely isolated. Each zone must
balance internally. The FBMC LP is still feasible (each zone's net_position = 0), but
social welfare is lower because cheap generation can't reach distant demand. Tested in
`test_fbmc_zero_ram_constrains_flow()` (`tests/test_fbmc.py` line 166).

### 2. Zero demand

When a zone has no demand, it can still export (net_position > 0) if another zone wants
its supply. But if no zone has demand, the optimal solution is zero supply accepted
everywhere — welfare = 0. Handled gracefully in `test_fbmc_zero_demand()`.

### 3. PTDF degeneracy (row doesn't sum to zero)

Violates Kirchhoff's law. The solver would produce physically impossible flows.
`fbmc.py` raises `ValueError` at input validation (line 84-88).

### 4. Block order at exactly MCP

A block with offer price equal to the MCP may be accepted or rejected depending on solver
tie-breaking. Euphemia uses explicit tie-breaking rules (accept if profitable or
zero-profit). The repo's 0.001 tolerance threshold (`> 0.5` for binaries, `> 0.001` for
continuous) handles floating-point noise but doesn't implement formal tie-breaking.

### 5. Linked block with empty group

If one block in a linked group has zero quantity (0 MW), the linkage constraint forces
the other block's binary to also be 0 — effectively rejecting the group. More
interestingly, if one block's price is negative (willing to pay to generate), the solver
must still either accept both or reject both.

### 6. Exclusive group with identical welfare

When two mutually exclusive blocks produce identical economic outcomes, the solver picks
arbitrarily. In practice, Euphemia would apply a secondary criterion (e.g., minimize
uplift, or prefer blocks submitted earlier).

### 7. Integer infeasibility from tight ATC + big blocks

A block of 200 MW can't flow if ATC is 100 MW in all directions — infeasibility.
Euphemia uses "Prezzo Unico Nazionale" (PUN)-like fallback and minimum acceptance ratio
constraints to handle such cases. The repo's simplified models return "Infeasible"
status in this case.

### 8. Zone order invariance

The PTDF matrix columns correspond to zone order. If you swap zones, you must also swap
the PTDF columns (and vice versa). `test_fbmc_zone_order_invariant()` verifies that
welfare and dispatch quantities are preserved under correct reordering.

### 9. All supply at zero price

If all supply is offered at €0/MWh (e.g., mandatory renewables with subsidy), the LP
accepts exactly enough to meet demand, MCP = €0/MWh, and social welfare = total demand
value. Perfectly valid — represents "free energy" scenarios (rare in practice but
theoretically interesting).

### 10. Negative block prices ("pay to run")

A generator may offer a negative price (bid to pay up to -€X/MWh to stay online). In
block order context, the binary `b_i` multiplies a negative price × quantity, which adds
to welfare (subtracting a negative = adding). The LP handles this correctly — the block
is accepted if it enables enough consumer surplus to compensate.

---

## QUICK QUIZ

1. **What is the fundamental objective function of market coupling, and what two
 components does it represent?**

2. **Why do ATC-based constraints fail to capture loop flows? Give a concrete 3-zone
 example where ATC declares "no constraint violated" but physical flows would overload a
 line.**

3. **What is a "paradoxically accepted" block order, and why can't MCP pricing handle it?**

4. **In FBMC, what does the PTDF matrix represent, and why must every row sum to zero?**

5. **Name three algorithmic innovations that make the full Euphemia MIP solvable within
 operational time limits.**

### Answers

1. **Social welfare maximization:** `Σ(demand_value × accepted_qty) — Σ(supply_cost ×
 accepted_qty)`. This represents consumer surplus (value consumers receive minus what
 they pay at the market price) plus producer surplus (revenue minus generation cost).
 Equivalent to minimizing total generation cost for fixed demand, or maximizing net
 surplus for elastic demand.

2. **ATC measures only direct flows between named zones.** In a 3-zone triangle (A-B, B-C,
 A-C), a trade from A to B creates physical flows on A→C and C→B (loop flows) even
 though neither zone C is directly involved in the trade. If A→B trade is 150 MW and
 line A→C has PTDF=0.10 for zone A's net position, the A→C line sees 15 MW from a trade
 it's not supposed to be involved in. ATC only checks A→B ≤ ATC_AB — it never checks
 A→C, so it misses the overload. See the PTDF calculation in §7 above.

3. **A paradoxically accepted (PA) block** has an offer price above the uniform clearing
 price but is accepted because its acceptance enables a more valuable demand bid (or
 displaces an even more expensive block). At MCP, the PA block would lose money per MWh
 — but the social welfare gain from the enabled demand outweighs this loss. MCP can't
 price this correctly because the MCP is derived from continuous supply/demand only,
 ignoring the non-convex binary decision. IP pricing computes a uniform price that
 minimizes "make-whole" payments to both PA and PR blocks.

4. **PTDF[l, z]** is the sensitivity of branch *l*'s flow to a 1 MW change in zone *z*'s
 net position. Each row must sum to zero because of Kirchhoff's current law: if all
 zones increase their net positions by 1 MW simultaneously (balanced system with no net
 change), branch flows remain unchanged. Σ_z PTDF[l, z] × 1 = 0 must hold for all rows.
 Validated in `fbmc.py` line 84-88.

5. **Three Euphemia innovations:**
 - Block order pre-processing (removing dominated/trivially-rejected blocks before the
 MIP starts)
 - Custom branch-and-cut cuts (minimum income condition, symmetry-breaking)
 - Lazy constraint generation for FBMC (Benders-like decomposition — only violated flow
 constraints are added to the master problem)
 *(Also acceptable: spatial decomposition by ATC regions, heuristic warm-start for
 primal search, IP pricing with dominance-based price-range narrowing.)*

---

## References

- **EUPHEMIA Public Description** — PCR Market Coupling Algorithm:
 [https://www.epexspot.com/en/euphemia](https://www.epexspot.com/en/euphemia)
- **ENTSO‑E Flow-Based Market Coupling**:
 [https://www.entsoe.eu/network_codes/cacm/](https://www.entsoe.eu/network_codes/cacm/)
- **pomato framework** (FRESNA): [https://github.com/FRESNA/pomato](https://github.com/FRESNA/pomato)
- **the industry**: [https://www.n-side.com/](https://www.n-side.com/)
- **Repo files referenced:**
 - `energy_markets/pcr_model.py` — single-zone PCR model with block orders and IP pricing
 - `energy_markets/multi_zone.py` — multi-zone ATC coupling
 - `energy_markets/fbmc.py` — flow-based coupling with PTDF constraints
 - `energy_markets/block_orders.py` — linked and exclusive block order examples
 - `energy_markets/market_clearing.py` — merit order stack and equilibrium finding
 - `energy_markets/lodf_utils.py` — LODF computation and CBCO screening for N-1
 - `energy_markets/gsk.py` — Generation Shift Key strategies
