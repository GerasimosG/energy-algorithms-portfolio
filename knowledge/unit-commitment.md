# Unit Commitment: MIP Formulation & Edge Cases

## What Is Unit Commitment?

**Unit Commitment (UC)** decides which generators to turn ON/OFF and how much power each should produce, for every hour of the planning horizon (typically 24-168 hours), to meet demand at minimum cost.

It's the fundamental problem in power system operations — solved daily by every grid operator worldwide.

---

## Why UC Is Hard

| Challenge | Why It Matters |
|-----------|---------------|
| **Binary decisions** | Generator is on (1) or off (0) — MIP, not LP |
| **Temporal coupling** | Today's decision affects tomorrow (ramp rates, min up/down) |
| **Startup costs** | Turning on a cold generator costs money (fuel to heat up) |
| **Non-convex costs** | Heat rate curves are nonlinear (we linearize for LP) |
| **Combinatorial explosion** | 10 generators × 24 hours = 2^240 possible on/off patterns |

---

## Mathematical Formulation

### Decision Variables

```
u[g,t] ∈ {0,1} : ON/OFF status of generator g at time t
p[g,t] ∈ ℝ : Power output of generator g at time t (MW)
su[g,t] ∈ {0,1} : Startup indicator (= 1 if g starts at time t)
sd[g,t] ∈ {0,1} : Shutdown indicator (= 1 if g shuts down at time t)
```

### Objective

```
min Σ(cost[g] · p[g,t] + startup_cost[g] · su[g,t])
```

Minimize: fuel costs + startup costs.

### Constraints

**1. Energy Balance (exact!)**
```
Σ(p[g,t]) = demand[t] for all t
```
Supply must exactly equal demand in every period. No ">= " — that would allow over-generation without storage.

**2. Reserve Margin**
```
Σ(max_output[g] · u[g,t]) ≥ demand[t] · (1 + margin)
```
The sum of MAX capacities of online generators must exceed demand by a reserve margin (typically 5-15%). This handles generator trips, forecast errors.

**3. Generator Limits**
```
min_output[g] · u[g,t] ≤ p[g,t] ≤ max_output[g] · u[g,t]
```
When ON: produce between min and max. When OFF: produce 0.

**4. Ramp Rate Limits**
```
|p[g,t] - p[g,t-1]| ≤ ramp_rate[g] · max_output[g]
```
How fast can a generator change output? Gas turbines: fast (10% per minute). Nuclear: slow (1-5% per hour).

**5. Startup/Shutdown Logic**
```
su[g,t] - sd[g,t] = u[g,t] - u[g,t-1]
```
If ON now but OFF before → startup. If OFF now but ON before → shutdown.

**6. Minimum Uptime**
```
Σ_{τ=t}^{t+min_up-1} u[g,τ] ≥ min_up · su[g,t]
```
If started at t, must stay ON for at least `min_up` periods. Prevents rapid cycling that damages equipment.

**7. Minimum Downtime**
```
Σ_{τ=t}^{t+min_down-1} (1 - u[g,τ]) ≥ min_down · sd[g,t]
```
If shut down at t, must stay OFF for at least `min_down` periods. Allows equipment to cool before restart.

**8. Initial Conditions (critical!)**
```
u[g,0] = init_status[g]
```
If the generator was already ON at hour 0, the min uptime clock has already been running. Without this, the model might shut it down prematurely.

---

## Edge Cases (From Our Test Suite)

### 1. Initial Conditions (Issue #6 in our audit)
```python
# WRONG: ignores that generator has been ON for 5 hours already
# Model might shut it down at hour 1 (violating min uptime of 6h)

# RIGHT: pass init_status, init_uptime, init_downtime
solve_unit_commitment(
 demands=[100, 120, 110],
 generators=[...],
 init_status=[1, 0, 1], # gen 0 ON, gen 1 OFF, gen 2 ON
 init_uptime=[5, 0, 3], # gen 0 has been ON for 5h already
 init_downtime=[0, 8, 0], # gen 1 has been OFF for 8h
)
```

### 2. Horizon-End Constraints
What happens at t=23 (last hour)?

**Naive:** No constraint beyond T → generator might start at t=22, run for 1 hour, and stop.
**Correct:** Min up/down constraints extend through the horizon — if started at t=22 with min_up=3, it can't start. If already ON, it must stay ON.

### 3. Must-Run Generators
Some generators must always run (nuclear, combined heat and power):
```python
min_output[g] = max_output[g] # Fixed output
u[g,t] = 1 # Always ON
```

### 4. The 0-1-0 Problem
```
min_output: 50 MW
max_output: 200 MW
min_up: 3 hours
min_down: 2 hours

Time: 0 1 2 3 4 5
u: 1 0 1 0 1 0
```
The generator cycles ON for 1 hour, OFF for 1 hour — violating both min up and min down. The MIP must prevent this.

### 5. Ramp vs Capacity Coupling
```
ramp_rate = 0.2 (20% of capacity per hour)
p[g,0] = 0 (generator OFF)
p[g,1] ≤ 200 (can go from 0 to 200 in one period? NO!)
p[g,1] ≤ 0 + 0.2·200 = 40 (ramp limited to 40 MW)
```
But the generator must also satisfy min_output when ON. If min_output=50 and max ramp = 40, the generator can't even turn on in one period!

---

## Euphemia's UC Approach

Euphemia doesn't solve a full UC — it solves market coupling with block orders. But the same MIP techniques apply:

1. **Binary variables** for block acceptance (analogous to u[g,t])
2. **Linked constraints** for must-run conditions (analogous to min up)
3. **Exclusive constraints** for mutually exclusive options (analogous to min down)
4. **Ramp-like constraints** for paradoxical block prevention

The key difference: Euphemia optimizes WELFARE (social surplus), not COST. The math is the same, just the sign flips.

---

## Quick Quiz

**Q1:** Why is unit commitment an MIP, not an LP?

**Q2:** What's the purpose of the reserve margin constraint?

**Q3:** What are "initial conditions" and why do they matter?

**Q4:** Why do min up/down constraints extend through the end of the horizon?

**Q5:** A generator has max_output=200, ramp_rate=0.1, and min_output=50. It's OFF at t=0. Can it be ON at t=1? At t=2?

---

## Answers

**A1:** Generator ON/OFF decisions are binary (u ∈ {0,1}), making it a Mixed Integer Program. The binary variables create a non-convex feasible region that requires branch-and-bound to solve.

**A2:** To ensure the system can handle unexpected generator outages or demand spikes. The sum of MAX capacities of online units must exceed demand by a safety margin (typically 5-15%), separate from the energy balance constraint.

**A3:** The status of generators BEFORE the optimization horizon starts. If a generator has been ON for 5 hours when the optimization begins, its min uptime clock has already been partially satisfied. Ignoring this could cause the model to shut it down prematurely, violating min uptime.

**A4:** The horizon is an artificial boundary — the real world continues past T. If a generator starts at t=T-1, it commits to running for min_up hours, some of which extend beyond the model horizon. The model must respect this or the dispatch would be infeasible in real operation.

**A5:** At t=1: NO. Max ramp from 0 to p[1] is 0.1·200 = 20 MW. But min_output = 50 > 20, so it can't reach minimum output in one period. At t=2: YES. From 0 to p[1]=20 MW (sub-minimum, but this is the ramp path), then 20 to 50 MW (ramp of 30 ≤ 20? No, still can't). Actually: first step to 20, second step to 40, third step to 60 → can reach min at t=3. Need 3 periods to go from OFF to min_output.
