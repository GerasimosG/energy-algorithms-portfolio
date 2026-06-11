# Energy Markets Module — Code Review Findings

**Reviewed by:** code review agent 
**Date:** 2026-04-29 
**Files reviewed:** pcr_model.py, block_orders.py, market_clearing.py, demo.py, README.md 
**Scope:** LP correctness, block order logic, market clearing, bugs, code quality, documentation

---

## Executive Summary

The module demonstrates solid understanding of European power market coupling concepts (PCR/Euphemia) and the social welfare LP formulation is conceptually correct. However, there are **critical bugs** in the block order semantics (linked blocks) and the market clearing equilibrium finder that would be caught in a technical interview. Several **high-severity** issues in the demo scenarios undermine their pedagogical value.

**Severity breakdown:** 3 critical, 2 high, 3 medium, 5 low

---

## Critical Issues

### C1. Linked blocks are NOT enforced as linked [block_orders.py:32-49]

**Location:** `scenario_linked_block()` in `block_orders.py` 
**File:** `block_orders.py`, lines 46-47

**Problem:** The "linked block" scenario calls `model.add_block("Hydro_Upper", 25, 50)` and `model.add_block("Hydro_Lower", 25, 60)`. Each call creates an **independent binary variable** in the PCR model (`b_vars[i]`). The blocks can be independently accepted or rejected, which violates the linked block contract (all must be accepted or all rejected).

The code comment on line 37 says *"We model this with a shared binary variable via the PCR model"* — but the PCR model has no mechanism for shared binary variables. The comment is aspirational, not implemented.

**Proof:** When `Hydro_Upper` is priced at 90 (expensive) and `Hydro_Lower` at 25 (cheap), the optimizer accepts Hydro_Lower alone and rejects Hydro_Upper — a correct independent-block decision but a violation of linked-block semantics.

**Fix needed:** Add a `link_group` parameter to `add_block()` and the LP formulation that forces `b_i == b_j` for all blocks in the same group.

---

### C2. Market clearing `find_equilibrium` returns wrong MCP [market_clearing.py:32-63]

**Location:** `find_equilibrium()` in `market_clearing.py`, lines 48-51 (the `np.all(sup_at_q <= dem_at_q)` branch)

**Problem:** When the supply curve is entirely below the demand curve (no crossing in the interpolated range), the fallback on line 50 is:
```python
clearing_price = float(sup_prices[-1])
```
This returns the **highest supply offer price** (€120 for "Diesel") instead of the price of the **marginal unit that clears the market**.

**Demo data:** Supply = Solar(5,200) + Wind(15,150) + Hydro(35,100) + Gas(80,200) + Diesel(120,100). Demand = Ind_Base(200,300) + Ind_Peak(150,200) + Residential(100,150). Total demand = 650 MWh. The marginal unit that serves the 650th MWh is **Gas at €80/MWh** (cumulative range [450, 650]). The code returns 120.

**Impact:** The demo output shows "Clearing Price: €120.00/MWh" — a 50% error that would be immediately spotted by an interviewer familiar with electricity markets.

**Fix needed:** Replace `sup_prices[-1]` with interpolation at `q_max`:
```python
clearing_price = float(np.interp(q_max, sup_cum_qty, sup_prices, left=0, right=sup_prices[-1]))
```

---

### C3. PCR model has no support for linked blocks at all [pcr_model.py:41-42]

**Location:** `PCRModel.add_block()` in `pcr_model.py`

**Problem:** The `add_block()` method only stores `id`, `price`, `qty`. There is no mechanism to group blocks into linked sets or exclusive sets. This means:
- The "linked block" demo scenario is misleading (see C1)
- The "exclusive block" demo must resort to brute-force scenario comparison (see H2)
- Any complex order handling requires external logic, not the model itself

**Fix needed:** Add a `group` parameter to `add_block()`, and in `solve()`, add constraints:
- For linked groups: `b_i == b_j` for all blocks in the group
- For exclusive groups: `Σ(b_i) ≤ 1` for all blocks in the group

---

## High Severity Issues

### H1. MCP calculation ignores block orders [pcr_model.py:83-85]

**Location:** `PCRModel.solve()`, lines 83-85

**Problem:** The MCP is computed as:
```python
accepted_supply = [self.supply_orders[i]
 for i in range(Ns) if pulp.value(s_vars[i]) > 0.001]
mcp = max(o["price"] for o in accepted_supply) if accepted_supply else 0.0
```

This only considers continuous supply orders, **not block orders**. If the marginal unit is a block order (e.g., all flexible supply is exhausted and a block provides the remaining MW), the MCP would be computed from the last accepted flexible supply rather than the block's cost.

**Example:** Supply(Solar=10€,50MW), Block(Nuclear=80€,100MW), Demand(150€,120MW). Block accepted, MCP computed as max(10) = 10€, but the true marginal cost is 80€. This is also the well-known non-convexity pricing problem in Euphemia (handled via IP/PD pricing rules), which is worth discussing in an interview — but as presented, it's an undetected approximation.

**Severity:** High for a job-interview demo (would signal shallow understanding of marginal pricing).

---

### H2. Exclusive block comparison uses unequal supply curves [block_orders.py:60-85]

**Location:** `scenario_exclusive_block()` in `block_orders.py`

**Problem:** The two scenarios being compared have **different continuous supply curves**:

| Scenario | Supply | Block |
|----------|--------|-------|
| A (Coal) | Gas(70,200) + Solar(10,100) | CoalPlant_A(35,80) |
| B (Gas) | Solar(10,100) *only* | GasPlant_B(45,80) |

Scenario B is **missing** the Gas(70,200) flexible supply. This means Scenario B's supply capacity is only 180 MW (vs Demand of 250 MW), making it impossible to fully serve demand. The welfare comparison is confounded — it's not about Coal vs Gas plant choice, but about Gas(70) supply availability.

**Fix needed:** Both scenarios should share the same base supply curve. Only the block offer should differ.

---

### H3. Consumer/Producer surplus shading is incorrect [market_clearing.py:100-103]

**Location:** `plot_supply_demand_stack()` in `market_clearing.py`

**Problem:** The shading for producer and consumer surplus uses filled rectangles:
```python
ax.fill_betweenx([0, cp], 0, cv, ...) # Producer surplus (WRONG)
ax.fill_betweenx([cp, max(demand_prices)*1.1], 0, cv, ...) # Consumer surplus (WRONG)
```

Correct surplus shading should fill:
- **Producer surplus:** Area **between the supply curve** and the price line (from 0 to cv)
- **Consumer surplus:** Area **between the demand curve** and the price line (from 0 to cv)

The current implementation fills simple rectangles, which don't correspond to actual economic surplus. This would be noticed by an interviewer reviewing the plot.

**Fix needed:** Use `fill_between` with the actual supply/demand step curves.

---

## Medium Severity Issues

### M1. Energy balance uses `>=` instead of `==` [pcr_model.py:75]

**Location:** `PCRModel.solve()`, line 75

```python
prob += total_supply + total_block >= total_demand
```

For a single-zone market with no exports/imports, physical energy balance requires **exact equality**. The `>=` constraint means excess supply is allowed (though penalized by the objective). In practice, the optimizer avoids excess supply because it reduces welfare, so results are usually correct. However:
- It's conceptually wrong (physical power systems must balance exactly)
- Could produce subtly wrong results in edge cases with negative-priced blocks or zero-cost supply

**Fix:** Use `==` (single-zone with no interconnection).

---

### M2. Demo ignores non-optimal solve status [demo.py:31-46]

**Location:** `demo.py`, lines 31, 45

**Problem:** The demo calls `model.solve()` then `model.report()` without checking if the solution was optimal. If `solve()` returns non-optimal (e.g., Infeasible, Unbounded), line 81 of `pcr_model.py` returns early **without setting `self._result`**, so `report()` prints "No result. Run solve() first." — a confusing message since solve was indeed called.

**Fix:** Check the solve status before calling `report()`, or set `self._result` in all code paths.

---

### M3. `__init__.py` is empty — no public API [energy_markets/__init__.py]

**File:** `__init__.py` — completely empty.

This means users must know the full module path for every import (e.g., `from energy_markets.pcr_model import PCRModel`). A populated `__init__.py` would export key classes and provide cleaner imports.

**Also:** The module can't be imported as `from energy_markets import *` (no `__all__` defined).

---

## Low Severity Issues

### L1. No unit tests

Zero test coverage. The module has no `tests/` directory, no `pytest` tests, and no `conftest.py`. For an "interview-ready" portfolio module claiming *"Clean Python: Modular design, tests, type hints, git discipline"* (from root README), the absence of tests is a gap.

---

### L2. Hardcoded tolerance for acceptance check [pcr_model.py:84]

```python
if pulp.value(s_vars[i]) > 0.001
```

The threshold 0.001 is hardcoded. For markets with very small quantities or prices, this could misclassify small fills as "not accepted." Should be a class parameter or use `pulp.value()` with `eps` awareness.

---

### L3. Type hints incomplete

- `PCRModel.__init__` parameter `area: str` is hinted, but return types are missing throughout (`solve()` returns `dict` but no return annotation).
- `add_supply`, `add_demand`, `add_block` have no return type hints (should be `-> None`).
- `find_equilibrium()` parameter types use `list[dict]` but no `TypedDict` for order structure.

---

### L4. README doesn't document limitations

The README (and the module docstrings) do not mention:
- That linked blocks are not actually linked (C1)
- That MCP pricing ignores blocks (H1)
- That the market clearing uses interpolation approximation (C2)
- That energy balance uses `>=` not `==` (M1)

For an interview module, documenting **known limitations** demonstrates self-awareness and depth.

---

### L5. No requirements.txt or setup.py packaging

The module has no `pyproject.toml`, `setup.py`, or `setup.cfg`. While the parent repo has `requirements.txt` with `pulp`, the energy_markets module itself isn't installable as a package. Consider adding a minimal `pyproject.toml`.

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| C1 | **Critical** | block_orders.py:46-47 | Linked blocks not linked (independent binary vars) |
| C2 | **Critical** | market_clearing.py:50 | MCP = highest supply price, not marginal unit price |
| C3 | **Critical** | pcr_model.py:41-42 | No link/exclusive group mechanism in LP model |
| H1 | **High** | pcr_model.py:83-85 | MCP ignores block orders entirely |
| H2 | **High** | block_orders.py:60-85 | Exclusive comparison has unequal supply curves |
| H3 | **High** | market_clearing.py:100-103 | Surplus shading uses rectangles, not area-between-curves |
| M1 | **Medium** | pcr_model.py:75 | Energy balance uses `>=` not `==` |
| M2 | **Medium** | demo.py:31-46 | No status check before report() on non-optimal |
| M3 | **Medium** | __init__.py | Empty `__init__.py` — no package API |
| L1 | **Low** | — | Zero unit tests |
| L2 | **Low** | pcr_model.py:84 | Hardcoded acceptance tolerance |
| L3 | **Low** | Multiple | Missing type hints and return annotations |
| L4 | **Low** | README.md | Doesn't document known limitations |
| L5 | **Low** | — | No package build configuration |

---

## Recommendations (Priority Order)

1. **Fix C2 (market clearing MCP)** — Replace `sup_prices[-1]` with `np.interp()`. This is a one-line fix that corrects a 50% price error.
2. **Fix C1/C3 (linked blocks)** — Add `group` support to `PCRModel` with equality constraints for linked blocks and sum-≤1 for exclusive blocks.
3. **Fix H2 (exclusive scenario)** — Use identical base supply curves in both scenarios.
4. **Fix H1 (MCP with blocks)** — Document as a known limitation, or include block prices in MCP calculation when blocks are marginal.
5. **Fix H3 (surplus shading)** — Use `fill_between` with actual step curve data.
6. **Add unit tests** — At minimum test: basic LP solution, block acceptance/rejection, MCP calculation, linked block constraint, edge cases (infeasible, zero demand).
7. **Fix M1** — Change `>=` to `==` for single-zone energy balance.
