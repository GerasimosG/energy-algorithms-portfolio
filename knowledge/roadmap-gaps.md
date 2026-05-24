# Gap-Closing Roadmap — INDUSTRY Algorithmic Trader (Uccle)

**Goal:** Address the 3 major gaps identified in the July 2025 INDUSTRY Belgium Algorithmic Trader JD.

## Priority Ranking

| Priority | Gap | Interview Impact | Effort |
|----------|-----|-----------------|--------|
| P0 | Ancillary Services (FCR, aFRR, mFRR) | 🚨 JD explicitly lists it | Medium |
| P1 | Wind generation / stochastic renewables | ⚠️ JD lists renewables | Medium |
| P2 | Proprietary trading signals | ⚠️ Expected for "algo trader" | Small |
| P3 | Monitoring / observability | Low — portfolio-safe skip | Small |

---

## P0: Ancillary Services

### What To Build

A `domain/markets/ancillary.py` module modeling aFRR bidding for a BESS, plus FCR/mFRR products.

**Core deliverable:** BESS bidding jointly into day-ahead energy + aFRR reserve.

### Files
- `src/energy_algorithms/domain/markets/ancillary.py` — Model
- `src/energy_algorithms/application/ancillary_demo.py` — Demo runner
- `tests/test_ancillary.py` — Tests
- `docs/ANCILLARY_SERVICES.md` — Theory doc

### Model Design
```
Two-stage stochastic:
  Stage 1 (DA): commit R_aFRR capacity, schedule energy
  Stage 2 (RT): residual arbitrage with reduced power headroom
  
  max Σ[ revenue_energy + λ_aFRR · R_aFRR - E[activation_cost] ]
  s.t. SoC dynamics, capacity, R_aFRR ≤ P_max
       SoC + R_aFRR/η ≤ E_max  (up-regulation headroom)
       SoC - R_aFRR·η ≥ 0      (down-regulation headroom)
```

### Tasks

- [ ] Create `knowledge/ancillary-services.md` — theory doc covering FCR/aFRR/mFRR products, Belgian market rules (Ella TSO), product specs, pricing
- [ ] Create `domain/markets/ancillary.py` — the joint energy+reserve optimization model
- [ ] Create `application/ancillary_demo.py` — demo on synthetic + real Belgian data
- [ ] Create `tests/test_ancillary.py` — edge cases: zero reserve price, full reserve commitment, SoC headroom binding, joint vs separate optimization comparison
- [ ] Verify: `pytest tests/test_ancillary.py -v --cov=energy_algorithms` passes with 90%+ on the new module
- [ ] Update knowledge/interview-qa.md with ancillary-specific questions (Q29-Q30)
- [ ] Document in README coverage gaps table: "Ancillary Services → ✅ Implemented"

---

## P1: Wind Generation / Stochastic Renewables

### What To Build

A wind generation model with forecast uncertainty, integrated into the storage LP as co-located BESS+wind.

### Model Design
```
Wind power: P_wind(t) = P_rated · CF(t) where CF is from ERA5/weather data
Forecast scenarios: CF(t) + ε(t) where ε ~ N(0, σ² * CF(t))

Two-stage SP:
  Here-and-now: DA battery schedule + reserve
  Wait-and-see: wind realization, residual battery dispatch
```

### Tasks

- [ ] Create `domain/optimization/renewables.py` — wind power curve model + scenario generator
- [ ] Integrate with `storage.py`: co-located BESS+wind farm optimization
- [ ] Create `application/renewables_demo.py` — profit comparison: standalone BESS vs BESS+wind vs standalone wind
- [ ] Create `tests/test_renewables.py` — edge cases: zero wind, curtailment, negative prices from over-generation
- [ ] Update knowledge/interview-qa.md with wind-specific questions
- [ ] Verify: 90%+ coverage on new module

---

## P2: Proprietary Trading Signals

### What To Build

2 additional signal strategies relevant to the INDUSTRY role, plus a signal evaluation framework.

### Ideas (pick 2)
- **Cross-border spread strategy** — long BE↔FR spread when French nuclear unavailability is high
- **Wind forecast error strategy** — long when ECMWF over-forecasts Belgian wind
- **Solar ramp rate strategy** — intraday positions based on cloud-cover satellite imagery proxy
- **Intraday imbalance price strategy** — predict 15-min balancing price from the TSO's activated reserve volume

### Tasks

- [ ] Design and implement strategy A (e.g., cross-border spread) in `domain/trading/strategies/`
- [ ] Design and implement strategy B (e.g., wind forecast error) in `domain/trading/strategies/`
- [ ] Add to industry_demo.py so all 5 strategies run in a single demo
- [ ] Create `tests/test_custom_strategies.py`
- [ ] Verify integration: `python -m energy_algorithms.application.industry_demo` produces valid output for all 5 strategies

---

## P3: Monitoring / Observability (Optional)

### What To Build

A dashboard notebook showing live-like metrics: position, P&L, risk, data freshness.

### Tasks

- [ ] Create `notebooks/algo_dashboard.ipynb` — 5-panel layout: P&L, positions, risk metrics, market context, API health
- [ ] Uses synthetic/replayed data (no live connection needed)
- [ ] Look professional for interview walkthrough (dark theme, clear panes)

---

## Phase Order

```
Phase 1: Ancillary Services (P0)    — highest interview impact
Phase 2: Trading Signals (P2)       — quick wins, visible in industry_demo
Phase 3: Wind / Renewables (P1)     — deep modeling value
Phase 4: Monitoring Dashboard (P3)  — polish for interview demo
```

**Verification gate:** After each phase, `pytest -q` must not regress and coverage gate must hold at 90%+.
