# Storage Optimization: BESS, SoC Dynamics & Arbitrage

## What Is BESS?

**Battery Energy Storage System** — buys electricity when cheap, sells when expensive. The simplest form of energy arbitrage.

---

## Mathematical Formulation

### Decision Variables
```
charge[t] ≥ 0 : MW charged at time t
discharge[t] ≥ 0 : MW discharged at time t
SoC[t] ∈ [0, cap] : State of charge at time t (MWh)
```

### Objective (Revenue Maximization)
```
max Σ(price[t] · (discharge[t] - charge[t]))
```

Buy low (charge), sell high (discharge). Equivalent to minimizing cost in a portfolio context.

### Constraints

**1. Power Limits**
```
0 ≤ charge[t] ≤ max_power
0 ≤ discharge[t] ≤ max_power
```

**2. SoC Dynamics**
```
SoC[t] = SoC[t-1] + charge[t] · η_in - discharge[t] / η_out
```
Where η_in, η_out ∈ (0, 1] are charging/discharging efficiencies. Storing 1 MWh costs 1/η_in MWh of electricity.

**3. SoC Bounds**
```
0 ≤ SoC[t] ≤ capacity
```

**4. Initial/Final SoC** (optional, not in our simple model)
```
SoC[0] = initial_soc
SoC[T] ≥ target_final_soc (don't leave the battery empty)
```

---

## The Efficiency Trap

### Round-Trip Losses

Typical Li-ion battery: η_in = 0.95, η_out = 0.95

**Round-trip efficiency:** η_rt = η_in × η_out = 0.9025 (90.25%)

For every 1 MWh stored, you get back 0.9025 MWh. You lose ~10%.

### When Arbitrage Stops Making Sense

```
Buy at: €50/MWh
Sell at: €55/MWh
Revenue: €55 × 0.9025 - €50 × 1.0 = €49.64 - €50.00 = -€0.36 LOSS
```

The price spread of €5 isn't enough to cover 10% losses. You need:
```
spread_needed = buy_price × (1/η_rt - 1)
 = 50 × (1/0.9025 - 1)
 = 50 × 0.108
 = €5.40/MWh
```

Below €5.40 spread, the battery loses money.

### Why Our Model Avoids Simultaneous Charge/Discharge

```python
# No binary constraint preventing simultaneous charge+discharge
# The LP naturally avoids it because:
# charge[t] + discharge[t] > 0 with price[t] same for both
# → charging costs money, discharging earns money
# → doing both at same price cancels out but loses η² efficiency
# → objective pushes away from simultaneous
```

This is the **economic** prevention of simultaneous charge/discharge, vs the **binary** prevention (energy-py-linear's approach with big-M constraints). Both work; ours is simpler and equally correct for linear prices.

---

## The OneInterval Asset Pattern

Our `lp_optimization/assets.py` implements the energy-py-linear inspired pattern:

```python
class BatteryAsset(Asset):
 def _constraints(self, prob, interval_data, T):
 # Create charge, discharge, SoC variables
 # Add energy balance per interval
 # Set power limits
 
 def _objective(self, prob, interval_data, T):
 # Return price[t] * (charge[t] - discharge[t])
 return pulp.lpSum(price[t] * (charge[t] - discharge[t]))
 
 def _post_solve(self, prob, interval_data, T):
 # Extract schedule: charge, discharge, SoC per interval
```

**Why this pattern?**
1. Each asset is independent — add/remove without touching other code
2. Lifecycle hooks make it clear WHEN each logic runs
3. `build_site()` orchestrates all assets into a single LP

---

## Edge Cases

### 1. Negative Prices
```
price[t] = -€10/MWh
```
The battery should CHARGE at negative prices (you get PAID to take electricity) and never discharge. Our LP handles this correctly because:
```
objective term: -10 × (charge - discharge)
To maximize (or minimize cost): want charge > 0, discharge = 0
```

### 2. Zero Price
At zero price, the battery should do nothing — no arbitrage opportunity. The LP will set charge=discharge=0.

### 3. Initial SoC
If initial_soc > 0, the battery can discharge immediately without charging first. This is free energy (already paid for).

### 4. Capacity Constraint Binding
At SoC = capacity, charge must be 0 (can't overfill). At SoC = 0, discharge must be 0 (can't draw from empty).

### 5. Spill Asset Interaction
Our `SpillAsset` has penalty cost €5000/MWh. The battery will ALWAYS be used before spill because battery cost is price[t]/η_rt (at most ~€200/MWh) << €5000/MWh. Only if the battery is empty AND generators at max does spill activate.

### 6. Round-Trip Losses Create "Infeasibility"
From our test fixes: a 50 MWh battery charging 10 MW for 2 periods at 95% efficiency stores 19 MWh, then discharging 10 MW for 2 periods at 95% needs 21.05 MWh — more than was stored. The model becomes infeasible. Fix: oversize the battery or provide additional generation.

---

## Quick Quiz

**Q1:** Why doesn't our storage LP need binary variables to prevent simultaneous charge/discharge?

**Q2:** What's the minimum price spread needed for a battery with η_in=0.92, η_out=0.92, buying at €40/MWh?

**Q3:** At negative prices (-€20/MWh), what should the battery do?

**Q4:** Why does the OneInterval pattern separate _constraints, _objective, and _post_solve?

**Q5:** A battery has capacity=100 MWh, max_power=25 MW, initial_soc=50. Price pattern: [10, 10, 100, 100]. What's the optimal dispatch?

---

## Answers

**A1:** The objective function naturally prevents it. Doing both charge and discharge in the same period loses η² efficiency without any price benefit, so the LP never chooses it. This is the "economic" approach vs "binary" approach.

**A2:** η_rt = 0.92 × 0.92 = 0.8464. Spread needed = 40 × (1/0.8464 - 1) = 40 × 0.1814 = €7.26/MWh. Below this, the battery loses money.

**A3:** Charge as much as possible. At -€20/MWh, you're paid €20 for every MWh you take. Then discharge when prices are positive. Free money + arbitrage profit.

**A4:** Separation of concerns. _constraints builds the model structure. _objective expresses the economic goal. _post_solve extracts results. A new asset type only needs to implement these three methods. build_site() doesn't care what each asset does internally.

**A5:** t=0: charge 25 MW (SoC=50+23.75=73.75). t=1: charge 25 MW (SoC=73.75+23.75=97.5). t=2: discharge 25 MW (SoC=97.5-26.32=71.18). t=3: discharge 25 MW (SoC=71.18-26.32=44.86). Revenue = 100×(25+25) - 10×(25+25) = 5000 - 500 = €4500 profit.
