# Competitor Analysis: pomato, PyPSA, energy-py-linear

## Why Study Competitors?

Understanding what other frameworks do better (and worse) shows you've done your homework. In an interview at , mentioning that you studied pomato's FBMC implementation demonstrates genuine domain engagement.

---

## 1. pomato

**Repo:** github.com/FRESNA/pomato
**Stars:** 96
**Language:** Python + Julia (optimization core)
**Focus:** European electricity market simulation with full network models

### What pomato does better

**FBMC with full network topology:**
- pomato uses actual IEEE network models (118-bus, DE case with 450 nodes)
- Our FBMC uses simplified zonal PTDF (educational, not production)
- pomato's PTDF is computed from line impedances; ours is hand-crafted

**N-1 Security (Clarkson Algorithm):**
- pomato implements redundancy removal: 26,000 CBCOs → 540 active constraints (98% reduction)
- Our LODF screening provides the same concept but at smaller scale
- The Clarkson algorithm requires Julia (JuMP.jl) — we'd need a Julia bridge

**SCOPF (Security-Constrained Optimal Power Flow):**
- Preventive N-1: dispatch is feasible under ANY single contingency
- Corrective N-1: dispatch can be adjusted after a contingency
- Both are supported; we only have screening

**Chance-constrained OPF:**
- Accounts for wind/solar forecast uncertainty
- Ensures constraints hold with specified probability (e.g., 95%)
- Our models are deterministic

### What we do better

**Block orders:** pomato has no block order support (nodal market, not zonal with Euphemia-style blocks). Our linked/exclusive block mechanisms are directly relevant to .

**ENTSO-E integration:** pomato has no real data pipeline. Our `energy_data/` module connects to live ENTSO-E data.

**Educational clarity:** pomato is complex and poorly documented. Our code has docstrings, architectural diagrams, and this knowledge base.

**Intraday simulation:** Our order book matching (`intraday.py`) fills a gap pomato doesn't address.

---

## 2. PyPSA

**Repo:** github.com/PyPSA/PyPSA
**Stars:** 1,965
**Language:** Python (with linopy for optimization)
**Focus:** Power system analysis for research and planning

### What PyPSA does better

**Full energy system modeling:**
- Generators, storage, transmission, loads — all networked
- Multi-period with investment optimization (build new capacity)
- Our models are single-period or short-horizon

**Network topology:**
- Real grid models with line impedances, transformers, buses
- Our models abstract the grid to zones

**Solved by linopy:**
- Uses the linopy library (xarray-labeled variables)
- Cleaner API than raw PuLP for network problems
- Supports multiple solvers seamlessly

**Professional CI/CD:**
- 60+ tests with GitHub Actions
- Documentation on ReadTheDocs
- Badges, releases, contribution guidelines

**N-1 SCLOPF:**
- Security-constrained linear optimal power flow
- Linear in number of contingencies (after CBCO screening)
- Our approach is zonal, not nodal

### What we do better

**Market focus:** PyPSA is a planning tool, not a market tool. No block orders, no PCR/Euphemia, no intraday trading.

**Energy market domain:** Our `energy_markets/` module is directly relevant to  roles. PyPSA is better for system planning roles.

**Portfolio scope:** We cover optimization (LP/MIP), backtesting, and data pipelines. PyPSA is only optimization.

---

## 3. energy-py-linear

**Repo:** github.com/ADGEfficiency/energy-py-linear
**Stars:** ~50
**Language:** Python
**Focus:** Battery and renewable energy asset optimization

### What energy-py-linear does better

**OneInterval Asset Pattern:**
- Clean separation: each asset implements constraints, objective, post-processing
- Our `assets.py` now implements this pattern (P1 gap resolved)

**Known-optimal tests:**
- Uses Hypothesis property-based testing
- 250 random examples per test run
- Compares solver results against analytically known solutions
- Our tests are fixed-scenario, not property-based

### Where we match

**OneInterval pattern:** Now implemented in `assets.py`
**Spill assets:** Now implemented (SpillAsset with penalty cost)
**Physical invariants:** Now implemented in `invariants.py`

### Where we go beyond

**Market coupling:** energy-py-linear is a single-site optimizer. Our FBMC handles multi-zone market coupling.

**ENTSO-E data:** energy-py-linear has no data pipeline. We have live API access.

---

## Gap Resolution Status

| Framework | P1 | P2 | P3 | Deferred |
|-----------|----|----|-----|----------|
| pomato | ✅ FBMC ✅ LODF | ✅ GSK | ✅ Options | Clarkson (Julia), Chance-OPF |
| energy-py-linear | ✅ OneInterval | ✅ Tests ✅ Invariants | ✅ Spill | ConstraintTerm DSL |
| PyPSA | — | ✅ Accessor | ✅ Hooks ✅ Solver ✅ Metadata | — |

### Why Some Gaps Stay Open

**Clarkson redundancy removal:** Requires Julia/JuMP.jl integration. Portfolio overkill.

**Chance-constrained OPF:** Requires stochastic programming. PhD-level complexity.

**ConstraintTerm DSL:** Declarative constraint definitions add complexity without demonstrative value.

**N-1 SCLOPF (full):** Requires full network model with line impedances. Nodal, not zonal.

---

## What This Means for Your Interview

When asked "have you looked at how the pros do this?", you can say:

> "Yes — I studied pomato for FBMC implementation, PyPSA for system architecture, and energy-py-linear for the OneInterval asset pattern. I adopted their best ideas where they fit (FBMC with PTDF, LODF screening, lifecycle hooks, invariant validation) and documented what I couldn't adopt and why (Clarkson needs Julia, chance-constrained OPF is PhD-level). My FRAMEWORK.md has a detailed gap analysis with priority levels."

This answer demonstrates:
1. You don't just code — you study the field
2. You know what's production-grade vs portfolio-scale
3. You're honest about limitations
4. You can evaluate tradeoffs
