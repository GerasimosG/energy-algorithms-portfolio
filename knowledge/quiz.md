# Self-Assessment Quiz

**50 questions across all domains. Answer key at the bottom.**

---

## Domain 1: Market Coupling (10 questions)

1. What is the objective function of market coupling?
2. Why does Euphemia use MIP instead of LP?
3. What is a block order and why do they exist?
4. What's the difference between linked and exclusive blocks?
5. What is ATC and what is its main limitation?
6. What does PTDF stand for and what does it capture?
7. What are loop flows and why can't ATC model them?
8. What is RAM in the FBMC context?
9. What is a paradoxically accepted block?
10. What are make-whole payments?

## Domain 2: Optimization Theory (10 questions)

11. Why is the optimal LP solution always at a vertex?
12. What is the dual problem and what do dual variables represent?
13. What is branch and bound?
14. When do you prune a branch in branch and bound?
15. What is presolve and why does it matter?
16. Why use CBC over Gurobi for a portfolio?
17. What is an optimality gap and when is 5% acceptable?
18. What causes degeneracy in LP?
19. What's the difference between feasibility and optimality tolerance?
20. Why check `pulp.value(binary_var) > 0.5` instead of `== 1.0`?

## Domain 3: Unit Commitment (5 questions)

21. What are the 8 main constraints in UC?
22. Why are initial conditions critical?
23. What is the reserve margin constraint?
24. Can a generator go from OFF to min_output in one period?
25. What is the 0-1-0 problem?

## Domain 4: Storage Optimization (5 questions)

26. Why doesn't our storage LP need binary charge/discharge variables?
27. What is round-trip efficiency and how does it affect arbitrage?
28. At negative prices, what should a battery do?
29. What is the OneInterval asset pattern?
30. What does SpillAsset do?

## Domain 5: FBMC & PTDF (5 questions)

31. What is the FBMC flow constraint equation?
32. Why do PTDF rows sum to zero?
33. What is LODF and how does it differ from PTDF?
34. What does CBCO screening do?
35. Name the three GSK strategies.

## Domain 6: Backtesting (5 questions)

36. What is look-ahead bias and how does it inflate Sharpe?
37. Why is Sortino better than Sharpe for asymmetric returns?
38. What is VaR's biggest weakness?
39. What is the Kelly criterion?
40. Why vectorize a backtester?

## Domain 7: ENTSO-E & Data (5 questions)

41. What is the EIC code for Belgium?
42. What document type code fetches day-ahead prices?
43. What PSR code represents nuclear generation?
44. How does EntsoeClient handle a 401 response?
45. Why might day-ahead price data be unavailable for today?

## Domain 8: Edge Cases & Critical Thinking (5 questions)

46. A backtest shows Sharpe 3.2. What are the 3 most likely problems?
47. Your battery arbitrage test is infeasible. What's the likely cause?
48. Two zones have the same MCP but ATC is binding. Is that possible?
49. When would you deliberately NOT use a SpillAsset?
50. If the solver returns Optimal with 0.5% gap, is the solution trustworthy?

---

# Answer Key

## Domain 1: Market Coupling

1. **Maximize social welfare** = consumer surplus + producer surplus. Mathematically: `max Σ(demand_bids) - Σ(supply_bids)`

2. **Block orders introduce binary variables.** The all-or-nothing acceptance creates a non-convex feasible region, requiring branch-and-bound (MIP) instead of simplex (LP).

3. **An all-or-nothing bid across multiple hours.** Exists because nuclear/coal plants have high startup costs and minimum run times — can't economically start up for one hour.

4. **Linked:** Both accepted or both rejected (equality constraint). **Exclusive:** At most one accepted (sum ≤ 1). Linked serves parent+child blocks; exclusive serves mutually exclusive options.

5. **Available Transfer Capacity** — a simple MW limit on each interconnection. **Limitation:** can't model loop flows where a trade between A and B overloads line C-D.

6. **Power Transfer Distribution Factor** — captures how a 1 MW injection at a node affects flow on each transmission line. Rows sum to 0 (Kirchhoff).

7. **Flows that take paths other than the direct economic route.** A trade from A (cheap) to B (demand) creates flow on the A-C-B path, potentially overloading C-B even though no trade involves C.

8. **Remaining Available Margin** — the thermal capacity of a line minus already-scheduled flows. What's left for the market coupling to use.

9. **A block order accepted in the welfare-maximizing MIP** that would have negative surplus at the uniform MCP. Requires make-whole payments to compensate.

10. **Payments to block order holders** whose blocks were accepted in the MIP solution but would lose money at the uniform clearing price. Minimized in Euphemia's IP pricing stage.

## Domain 2: Optimization Theory

11. **Linear objective on a convex polytope** achieves optimum at an extreme point. Moving to the interior always degrades the objective.

12. The dual problem swaps variables and constraints. **Dual variables are shadow prices** — the marginal value of relaxing each constraint. For energy balance: the shadow price IS the MCP.

13. **MIP algorithm:** Solve LP relaxation. If fractional: branch on a fractional variable (≤0 or ≥1). Bound: prune branches that can't beat the best known integer solution. Repeat.

14. **When the LP relaxation's best possible objective** is WORSE than the best known integer solution. You can't possibly beat the champion, so stop exploring that branch.

15. **Preprocessing that simplifies the model:** removes fixed variables, tightens bounds, deletes redundant constraints. Can reduce solve time by 10-100x.

16. CBC is free, ships with PuLP, handles portfolio-scale models easily. Gurobi needs a license and adds complexity — unnecessary for demonstration.

17. Gap = (best_bound - best_feasible) / best_feasible. **5% acceptable** for production scheduling where closing to 0.1% doesn't justify computation. Not acceptable for market clearing (needs 0.1%).

18. **Multiple constraints active at the same vertex.** More constraints than dimensions means the basis isn't unique — solver may cycle or stall.

19. **Feasibility:** how close constraints must be to satisfied (default 1e-6). **Optimality:** how close the objective must be to the theoretical optimum.

20. **Numerical noise.** CBC returns 0.999999 or 0.000001 instead of exactly 1.0 or 0.0 due to floating-point tolerances. Using `> 0.5` is robust.

## Domain 3: Unit Commitment

21. Energy balance, reserve margin, generator limits, ramp rates, startup/shutdown logic, min uptime, min downtime, initial conditions.

22. **The generator's status BEFORE the optimization horizon.** If a generator has been ON for 5h already, its remaining min uptime is reduced. Without this, the model might schedule an illegal shutdown.

23. **Ensures total online capacity exceeds demand by a safety margin** (5-15%). This provides headroom for unexpected generator trips or demand spikes.

24. **Not necessarily.** If ramp_rate × max_output < min_output, the generator can't reach minimum in one period. Needs multiple periods to ramp from 0 to min_output.

25. **Rapid ON-OFF-ON cycling** that violates min uptime and min downtime simultaneously. The MIP constraints must prevent the pattern u = [1, 0, 1, 0, 1, 0].

## Domain 4: Storage Optimization

26. **The objective function naturally prevents it.** Charging and discharging simultaneously at the same price loses η² efficiency for no economic benefit.

27. **η_rt = η_in × η_out** (typically ~90%). Each MWh stored returns 0.9 MWh. The price spread must exceed `buy_price × (1/η_rt - 1)` to be profitable.

28. **Charge as much as possible.** At negative prices, you're PAID to take electricity. Discharge later when prices are positive.

29. **Asset lifecycle pattern:** each asset implements `_constraints()` (build model), `_objective()` (economic terms), `_post_solve()` (extract results). `build_site()` orchestrates all assets.

30. **Penalty-cost slack supply guaranteeing LP feasibility.** If generators + storage can't meet demand, spill provides unlimited supply at a very high penalty price.

## Domain 5: FBMC & PTDF

31. `-RAM_rev[l] ≤ Σ(PTDF[l,n] · net_position[n]) ≤ RAM_fwd[l]` for each critical branch l.

32. **Kirchhoff current law.** Net injection at all nodes sums to zero. The reference node absorbs the negative sum.

33. **LODF captures post-contingency flow redistribution.** PTDF captures how injection affects flow. LODF[l,k] = flow change on branch l when branch k trips. Diagonal = -1. LODF rows don't sum to zero.

34. **Filters out Critical Branch Contingency Outages** that won't bind under N-1. Constraint: `|base_flow[l]| + |LODF[l,k] · base_flow[k]| < threshold · RAM[l]`. Reduces constraints by up to 95%.

35. **Flat** (uniform distribution), **Gmax** (proportional to generation capacity), **Dynamic** (weighted by actual dispatch).

## Domain 6: Backtesting

36. **Using information at time t that wasn't available at time t.** Computing a signal from price[t] and trading at price[t] assumes you can see the future. Inflates Sharpe by 2-3x.

37. **Sortino only penalizes downside volatility.** Sharpe penalizes ALL volatility, including large positive returns which are good. A strategy with volatile gains and small losses has lower Sharpe but high Sortino.

38. **VaR tells you the loss threshold for 95% of days but NOTHING about the worst 5%.** Expected Shortfall (CVaR) fixes this by averaging the worst-case losses.

39. **Optimal bet size for maximizing long-term growth.** Formula: f* = (p·b - q) / b. Full Kelly is VERY aggressive; half-Kelly is common in practice.

40. **100-1000x faster than loops.** NumPy operations are C-level, vectorized across all timesteps simultaneously. Cleaner, less error-prone, easier to audit for look-ahead bias.

## Domain 7: ENTSO-E & Data

41. `10YBE----------2`

42. **A44** — Day-ahead prices [12.1.D]

43. **B14** — Nuclear

44. Returns structured error dict: `{"status": "error", "error": "Unauthorized — check your API key"}.` Never crashes.

45. Day-ahead prices for TODAY were published YESTERDAY. Tomorrow's prices haven't been published yet (~13:00 CET).

## Domain 8: Edge Cases

46. **Look-ahead bias** (using future information), **survivorship bias** (backtesting on stocks that survived), **data snooping** (testing 50 strategies, picking the best). Also: transaction cost neglect, overfitting.

47. **Round-trip efficiency losses.** If `capacity × η_in × η_out < total_discharge_needed`, the battery can't deliver enough energy. The energy balance constraint becomes infeasible.

48. **Yes, with FBMC.** Loop flows can create binding constraints on lines that don't directly connect the zones with price differentials. A trade between A and B overloads C-D, even though C's price equals A's price.

49. **In market clearing** (not unit commitment) where unserved energy should NOT be modeled. The market should clear only what can be physically served; infeasibility signals insufficient bids, and should trigger price spikes, not spill activation.

50. **For market clearing: NO.** A 0.5% gap on billions in daily volume means millions in unaccounted welfare. Dual variables (prices) can be highly sensitive to which integer solution was chosen. **For production scheduling: YES.** The fuel savings of closing to 0.0% don't justify the computation time.
