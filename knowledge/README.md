# 📚 Energy Algorithms — Knowledge Base

**Your complete reference for energy market optimization mastery.**

This folder is a structured curriculum covering all theory, edge cases, interview preparation, and self-assessment needed to be genuinely expert-level in the domains this repo demonstrates.

---

## How to Use This Knowledge Base

1. **Read in order** — Each file builds on the previous
2. **Take the quiz** after each section — immediate feedback
3. **Use the interview Q&A** to prepare for actual Euphemia   / Industry questions
4. **Edge Case sections** are what separates good from exceptional

---

## Table of Contents

| # | File | What You'll Learn |
|---|------|-------------------|
| 1 | [Market Coupling](market-coupling.md) | PCR, Euphemia, ATC vs FBMC, social welfare |
| 2 | [Block Orders](block-orders.md) | Linked, exclusive, MCP vs IP pricing, make-whole payments |
| 3 | [FBMC & PTDF Theory](fbmc-ptdf.md) | PTDF matrices, loop flows, N-1 security, LODF |
| 4 | [LP/MIP Optimization](optimization-theory.md) | Simplex, duality, branch & bound, solver internals |
| 5 | [Unit Commitment](unit-commitment.md) | MIP formulation, min up/down, ramp rates, edge cases |
| 6 | [Storage Optimization](storage-optimization.md) | BESS models, SoC dynamics, efficiency, arbitrage |
| 7 | [Backtesting & Metrics](backtesting.md) | Look-ahead bias, Sharpe, Sortino, VaR, Kelly |
| 8 | [ENTSO-E & Energy Data](entsoe.md) | Transparency Platform, bidding zones, PSR types |
| 9 | [Competitor Analysis](competitor-analysis.md) | pomato, PyPSA, energy-py-linear — what they do better |
| 10 | [Interview Q&A](interview-qa.md) | 30+ questions with exceptional answers, edge cases |
| 11 | [Self-Assessment Quiz](quiz.md) | 50 questions across all domains with answer key |

---

## The Expert's Mindset

This knowledge base isn't just facts — it's **why** things work the way they do:

- Why does Euphemia use MIP instead of LP?
- Why can't you just sum ATC limits for market coupling?
- Why does a battery's round-trip efficiency kill arbitrage profits?
- Why does look-ahead bias inflate Sharpe ratios by 2-3x?

If you can explain these to an interviewer without notes, you're ready.

---

## Quick Reference

**Euphemia Pipeline:**
```
Orders → Welfare Maximization (MIP) → IP Pricing → Market Results
   ↑_______________ Block iterations _______________|
```

**FBMC Constraint:**
```
-RAM_l ≤ Σ(PTDF[l,n] · net_position[n]) ≤ RAM_l  ∀ critical branches l
```

**Key Numbers to Know:**
- Euphemia clears 25+ countries, 1M+ orders per session
- CBC struggles beyond ~100K variables; Gurobi handles millions
- A full day's day-ahead market costs billions in cleared volume
- Belgian nuclear baseload is ~4.8 GW
- ENTSO-E API token required for live data (stored in `energy_data/config.py`)

---

**Version:** 1.0 | **Last Updated:** 2026-04-30
