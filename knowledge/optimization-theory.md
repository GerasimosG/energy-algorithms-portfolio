# LP/MIP Optimization Theory

## What This Covers

The mathematical foundation behind every optimization in this repo. When an interviewer asks "what solver did you use and why?", you need to be able to explain not just which one, but what's happening i.

---

## Linear Programming (LP)

### Standard Form

```
min c^T x
s.t.
  Ax = b
  x ≥ 0
```

Where:
- `c` = cost vector (€/MWh for each generator)
- `x` = decision variables (MW dispatched per generator)
- `A` = constraint matrix (energy balance, capacity limits)
- `b` = right-hand side (demand, limits)

### The Simplex Method

The workhorse algorithm. Key intuition:

1. **Start at a vertex** (a corner of the feasible region)
2. **Check neighboring vertices** — is any better?
3. **Move to the best neighbor** (pivot)
4. **Repeat** until no neighbor is better → optimal

```
         x2
         |
     opt*|  Feasible Region (convex polytope)
       /|\
      / | \
     /  |  \
    /   |   \
   /____|____\_____ x1
```

**Why it works:** The optimal solution to an LP is always at a vertex (extreme point) of the feasible region. You never need to check interior points.

**Runtime:** Exponential worst-case, polynomial in practice. A 100-variable, 200-constraint LP solves in milliseconds.

### Duality

Every LP has a **dual** — another LP with the variables and constraints swapped. The dual of a minimization problem is a maximization problem.

**Weak duality:** Any feasible dual objective ≤ any primal objective (for minimization)
**Strong duality:** At optimality, primal objective = dual objective

**Dual variables (shadow prices):** The dual solution gives the **marginal value** of each constraint:
```
Shadow price of demand constraint = MCP (clearing price)
Shadow price of capacity constraint = value of 1 extra MW of capacity
```

In energy markets: the dual variables of the energy balance constraints ARE the market clearing prices. This is why Euphemia can compute prices from the LP solution.

### Interior Point Methods

Alternative to simplex. Instead of jumping between vertices, walks through the **interior** of the feasible region:
- Uses barrier functions to keep away from boundaries
- Better for very large, sparse problems
- Polynomial time guaranteed
- Used by commercial solvers (Gurobi barrier, CPLEX)

---

## Mixed Integer Programming (MIP)

### What Makes It Hard

Add binary/integer variables:
```
x_i ∈ {0, 1}  (binary: accept/reject a block order)
x_i ∈ ℤ       (integer: number of generators to build)
```

The feasible region is no longer convex — it's a disjoint set of points. No vertex-hopping algorithm works.

**NP-hardness:** MIP is NP-hard. Euphemia solves MIPs with 500K+ binary variables daily. How?

### Branch and Bound

The core algorithm:

```
1. Solve LP relaxation (ignore integer constraints)
2. If all integer variables are integral → DONE (lucky!)
3. Otherwise: pick a fractional variable (x_3 = 0.7)
4. BRANCH: create two subproblems
   - x_3 ≤ 0 (force to 0)
   - x_3 ≥ 1 (force to 1)
5. Solve each subproblem (LP relaxation again)
6. BOUND: if a subproblem's best possible value is worse
   than the best known integer solution → prune it
7. Repeat on remaining subproblems
```

**Visual:**
```
              Root (LP relax)
             /        \
        x3≤0          x3≥1
        /   \         /  \
     x5=0  x5=1    x5=0  x5=1   ← Integer solutions!
```

### Cutting Planes

Add constraints that "cut off" fractional solutions without removing any integer solutions:

```
Fractional LP solution: x = [0.7, 0.3, 0.5]
Cut: x_1 + x_3 ≤ 1  (cuts off the fractional point but not the integer [1, 0, 0] or [0, 0, 1])
```

Modern solvers (CBC, Gurobi) combine branch-and-bound with cutting planes → **Branch and Cut**.

### Optimality Gap

MIP solvers report a gap:
```
gap = |best_bound - best_feasible| / |best_feasible|
```

- **0% gap:** Proven optimal
- **5% gap:** We have a solution within 5% of the theoretical best
- **50% gap:** Might be far from optimal

**When to stop:** For energy markets, Euphemia targets 0.1% gap. For production scheduling, 1% gap is usually fine.

---

## Solver Landscape

| Solver | Type | LP Speed | MIP Speed | License | Our Use |
|--------|------|----------|-----------|---------|---------|
| **CBC** | Open-source | Moderate | Moderate | Free | Primary solver |
| **HiGHS** | Open-source | Fast | Good | Free | Supported (see `solver_config.py`) |
| **Gurobi** | Commercial | Very Fast | Excellent | $$$ | `solver_config.py` stubs |
| **CPLEX** | Commercial | Very Fast | Excellent | $$$ | `solver_config.py` stubs |
| **GLPK** | Open-source | Slow | Basic | Free | Not used |
| **SCIP** | Academic | Moderate | Good | Free (academic) | Not used |

### Why We Use CBC

```
✅ Free and open-source (no license key needed)
✅ Ships with PuLP (pip install pulp → you have CBC)
✅ Handles all our models (<1,000 variables)
✅ Valid for portfolio demonstration
❌ Slower than Gurobi on large MIPs
❌ No native quadratic support (we use scipy for portfolio)
```

In a real job at  or Energy, you'd use Gurobi or CPLEX. But for a portfolio, CBC demonstrates understanding without the licensing hassle.

### What CBC's Presolve Does

Before solving, presolve simplifies the model:
- Remove fixed variables (x_5 = 0? → remove it)
- Tighten bounds (x ≤ 10 and x ≥ 5? → bounds are [5,10])
- Remove redundant constraints (x + y = 10 and 2x + 2y = 20 → keep one)
- Detect infeasibility early

**Why this matters:** A model with presolve might solve in 0.1s where the raw model takes 5s.

---

## Numerical Issues

### Tolerance Hell

CBC uses default tolerances:
- **Feasibility tolerance:** 1e-6
- **Optimality tolerance:** 1e-6
- **Integer tolerance:** 1e-6

What could go wrong?

```
Constraint: x + y = 10
Solution:   x = 4.999999, y = 5.000001
Sum:        10.000000 ✓ (within tolerance)
But:        x could also be 5.000001 → sum = 10.000002 → VIOLATION!
```

This is why our code checks:
```python
accepted = pulp.value(y_var) > 0.5  # NOT > 0.999999
```

### Floating Point in Energy Markets

```
Price:  €50.00 / MWh
Quantity: 100.000000 MW
Block: 100.000001 MW  ← floating point noise!
```

In a market clearing billions in volume, a 1e-6 MW error is negligible. But block order decisions (0 or 1) are binary — there is no "slightly accepted."

### When Things Get Ugly

**Degeneracy:** Multiple constraints active at the same vertex → solver may cycle or stall.
**Ill-conditioning:** Tiny changes in input cause huge changes in output → prices become unstable.
**Symmetry:** Many equivalent solutions → branch and bound explores all of them unnecessarily.

---

## Performance Benchmarks (Raspberry Pi 4)

| Model | Variables | Constraints | Solve Time |
|-------|-----------|-------------|-----------|
| PCR simple | 11 | 4 | 25 ms |
| PCR + blocks | 18 | 8 | 30 ms |
| FBMC 3-zone | 28 | 12 | 35 ms |
| UC 12-period | 290 | 235 | 180 ms |
| BESS 24-period | 72 | 120 | 65 ms |
| Transportation 2×2 | 5 | 2 | 20 ms |

For comparison — pomato on same hardware:
| Model | Variables | Constraints | Solve Time |
|-------|-----------|-------------|-----------|
| IEEE 118 bus | 236 | 470 | 12 s |
| FBMC full | 590 | 1,040 | 45 s |

Our models are didactic scale, not production scale. Production models (Euphemia) have 100K-500K variables and solve in minutes using Gurobi on server hardware.

---

## Quick Quiz

**Q1:** Why is the optimal solution to an LP always at a vertex?

**Q2:** What are dual variables (shadow prices) and why do they matter in energy markets?

**Q3:** Branch and bound: when do you prune a branch?

**Q4:** Why use CBC instead of Gurobi for a portfolio?

**Q5:** What could cause CBC to return "Optimal" with a 0.5% gap?

---

## Answers

**A1:** The LP objective is linear, and the feasible region is convex. A linear function on a convex set achieves its optimum at an extreme point. Moving to the interior always lowers (for min) or raises (for max) the objective.

**A2:** Shadow prices are the marginal value of relaxing a constraint. For the energy balance constraint, the shadow price IS the market clearing price (MCP) — it's what you'd pay for 1 additional MW of demand.

**A3:** Prune when the LP relaxation's best possible objective is WORSE than the best integer solution you've already found. If you can't possibly beat the current champion, stop exploring that branch.

**A4:** CBC is free, ships with PuLP, and handles portfolio-scale models easily. Using Gurobi requires a license ($$$) and adds setup complexity — unnecessary for demonstrating understanding.

**A5:** The solver found an integer-feasible solution and proved it's within 0.5% of the theoretical optimum, but didn't close the gap to 0.0% before hitting the time limit or node limit.
