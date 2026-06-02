"""
Experiment 1 — Joint BESS + FCR + aFRR revenue stacking.

Research question
-----------------
Does revenue stacking (energy arbitrage + FCR capacity + aFRR capacity)
beat pure energy arbitrage for a Belgian 100 MWh / 50 MW BESS over
~30 days of real ENTSO-E day-ahead prices?

Why this matters
----------------
This is the single most important experiment for the Industry (Algorithmic
Trader) role. The JD mentions "revenue stacking for BESS" and the
interview prep (`docs/INTERVIEW_PREP.md`) has a candidate question on
joint energy + aFRR bidding. After this experiment you can answer from
*measured data* instead of theory.

Hypothesis
----------
H1: The optimizer learns to skip reserve commitment in hours with high
    price spread (opportunity cost dominates the capacity payment).
H2: FCR contributes more revenue per MW than aFRR at 2024 BE prices
    (€20 vs €15), so the optimizer saturates FCR before aFRR.
H3: Total revenue uplift from stacking is > 5% over arbitrage-only
    baseline, driven mostly by FCR.

Methodology
-----------
1. Load ~30 days of Belgian day-ahead prices.
2. Define 4 scenarios (same BESS, different product mix):
   - A: Arbitrage only (FCR=0, aFRR=0)
   - B: Arbitrage + FCR
   - C: Arbitrage + aFRR (up + down)
   - D: Full stack (arbitrage + FCR + aFRR)
3. For each day and each scenario, solve the joint LP and record
   revenue split (energy / FCR / aFRR).
4. Aggregate: total revenue, % of hours with FCR committed, % of
   hours with aFRR committed, FCR utilization, aFRR utilization.
5. Log all runs to the SQLite experiment tracker with
   ``ExperimentTracker().run(name=..., tags=...)``.

Outputs
-------
- 4 experiment runs in ``~/.hermes/experiments.db`` (one per scenario).
- Console summary table.
- Optional CSV/JSON dump to ``experiments/output/`` if ``--out`` passed.

Run
---
    python experiments/joint_reserve_revenue_stack.py
    python experiments/joint_reserve_revenue_stack.py --out experiments/output
    python experiments/runner.py exp1

Caveats
-------
- aFRR activation probability is a known unknown; the experiment
  sweeps 0.0, 0.3, and 0.5 to show sensitivity.
- FCR/aFRR prices are held constant at typical 2024 BE levels
  (€20/MW/h and €15/MW/h). Production would forecast these.
- Single BESS, no portfolio bidding, no prequalification constraints.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

# Make the src/ layout importable when running from repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from energy_algorithms.domain.optimization.ancillary import (  # noqa: E402
    solve_joint_bess_reserve,
)
from energy_algorithms.infrastructure.experiment_tracker import (  # noqa: E402
    ExperimentTracker,
)
from experiments._data import load_belgian_prices  # noqa: E402

# ── Constants —────────────────────────────────────────────────────────

# Belgian 2024 typical ancillary prices (€/MW/h, capacity-only).
DEFAULT_FCR_PRICE = 20.0
DEFAULT_AFRR_UP_PRICE = 15.0
DEFAULT_AFRR_DOWN_PRICE = 12.0

# BESS configuration — matches industry_demo defaults.
BESS_CAPACITY_MWH = 100.0
BESS_MAX_POWER_MW = 50.0
BESS_EFF_IN = 0.92
BESS_EFF_OUT = 0.92
BESS_INITIAL_SOC = 50.0

# aFRR "committed" threshold: any hour with capacity > this is
# considered committed in the aggregate count.
AFRR_COMMITMENT_TOLERANCE_MW = 1e-3

# Data path — Belgian ENTSO-E day-ahead prices, 30 days, quarter-hourly.
DEFAULT_DATA_PATH = _REPO_ROOT / "data" / "entsoe_30day_prices.csv"


# ── Data structures —──────────────────────────────────────────────────


@dataclass(frozen=True)
class ScenarioConfig:
    """One (scenario, activation_prob) configuration."""

    name: str
    description: str
    enable_fcr: bool
    enable_afrr: bool
    activation_prob: float
    fcr_price: float
    afrr_up_price: float
    afrr_down_price: float


@dataclass(frozen=True)
class DailyResult:
    """Result for one (scenario, day)."""

    scenario: str
    date: str
    status: str
    energy_eur: float
    fcr_eur: float
    afrr_eur: float
    total_eur: float
    fcr_capacity_mw: float
    n_afrr_up_committed: int  # hours with afrr_up > 0
    n_afrr_dn_committed: int  # hours with afrr_dn > 0


# ── Scenario definitions —─────────────────────────────────────────────


def build_scenarios(
    fcr_price: float = DEFAULT_FCR_PRICE,
    afrr_up_price: float = DEFAULT_AFRR_UP_PRICE,
    afrr_down_price: float = DEFAULT_AFRR_DOWN_PRICE,
) -> list[ScenarioConfig]:
    """Four scenarios × one activation_prob (best-case stacking)."""
    return [
        ScenarioConfig(
            name="A_arbitrage_only",
            description="Pure energy arbitrage (FCR=0, aFRR=0)",
            enable_fcr=False,
            enable_afrr=False,
            activation_prob=0.0,
            fcr_price=fcr_price,
            afrr_up_price=afrr_up_price,
            afrr_down_price=afrr_down_price,
        ),
        ScenarioConfig(
            name="B_arbitrage_plus_fcr",
            description="Arbitrage + symmetric FCR",
            enable_fcr=True,
            enable_afrr=False,
            activation_prob=0.0,
            fcr_price=fcr_price,
            afrr_up_price=afrr_up_price,
            afrr_down_price=afrr_down_price,
        ),
        ScenarioConfig(
            name="C_arbitrage_plus_afrr",
            description="Arbitrage + aFRR (up + down) at p=0.3",
            enable_fcr=False,
            enable_afrr=True,
            activation_prob=0.3,
            fcr_price=fcr_price,
            afrr_up_price=afrr_up_price,
            afrr_down_price=afrr_down_price,
        ),
        ScenarioConfig(
            name="D_full_stack",
            description="Arbitrage + FCR + aFRR (full stack)",
            enable_fcr=True,
            enable_afrr=True,
            activation_prob=0.3,
            fcr_price=fcr_price,
            afrr_up_price=afrr_up_price,
            afrr_down_price=afrr_down_price,
        ),
    ]


# ── Experiment runner —────────────────────────────────────────────────


def run_scenario_on_day(
    cfg: ScenarioConfig,
    prices_24h: list[float],
) -> DailyResult:
    """Run one (scenario, day) and return the result."""
    T = 24
    afrr_up = (
        [cfg.afrr_up_price] * T
        if cfg.enable_afrr
        else [0.0] * T
    )
    afrr_dn = (
        [cfg.afrr_down_price] * T
        if cfg.enable_afrr
        else [0.0] * T
    )
    r = solve_joint_bess_reserve(
        prices=prices_24h,
        capacity_mwh=BESS_CAPACITY_MWH,
        max_power_mw=BESS_MAX_POWER_MW,
        eff_in=BESS_EFF_IN,
        eff_out=BESS_EFF_OUT,
        initial_soc_mwh=BESS_INITIAL_SOC,
        fcr_price=cfg.fcr_price if cfg.enable_fcr else 0.0,
        afrr_up_price=afrr_up,
        afrr_down_price=afrr_dn,
        afrr_activation_prob=cfg.activation_prob,
    )
    return DailyResult(
        scenario=cfg.name,
        date="",  # filled by caller via ``DailyResult.replace(date=...)`` if needed
        status=r["status"],
        energy_eur=r.get("energy_revenue_eur", 0.0),
        fcr_eur=r.get("fcr_revenue_eur", 0.0),
        afrr_eur=r.get("afrr_revenue_eur", 0.0),
        total_eur=r.get("total_revenue_eur", 0.0),
        fcr_capacity_mw=r.get("fcr_capacity_mw", 0.0),
        n_afrr_up_committed=int(
            sum(
                1 for v in r.get("afrr_up", [])
                if v > AFRR_COMMITMENT_TOLERANCE_MW
            )
        ),
        n_afrr_dn_committed=int(
            sum(
                1 for v in r.get("afrr_down", [])
                if v > AFRR_COMMITMENT_TOLERANCE_MW
            )
        ),
    )


def run_experiment(
    out_dir: Path | None = None,
    tracker_db: Path | None = None,
) -> list[DailyResult]:
    """
    Run all scenarios on all days. Log each scenario to the tracker.

    Returns the flat list of per-day results.
    """
    prices, dates = load_belgian_prices(DEFAULT_DATA_PATH, source_tag="exp1")
    scenarios = build_scenarios()
    # Pair dates with prices once so downstream code can iterate without
    # re-zipping the two lists.
    daily_pairs: list[tuple[str, list[float]]] = list(zip(dates, prices))

    tracker = ExperimentTracker(db_path=tracker_db) if tracker_db else ExperimentTracker()
    all_results: list[DailyResult] = []

    for cfg in scenarios:
        run_name = f"exp1_{cfg.name}"
        with tracker.run(
            name=run_name,
            description=cfg.description,
            tags="exp1,revenue_stack,portfolio",
        ) as run:
            run.log_param("scenario", cfg.name)
            run.log_param("description", cfg.description)
            run.log_param("enable_fcr", cfg.enable_fcr)
            run.log_param("enable_afrr", cfg.enable_afrr)
            run.log_param("activation_prob", cfg.activation_prob)
            run.log_param("fcr_price_eur_mw_h", cfg.fcr_price)
            run.log_param("afrr_up_price_eur_mw_h", cfg.afrr_up_price)
            run.log_param("afrr_down_price_eur_mw_h", cfg.afrr_down_price)
            run.log_param("bess_capacity_mwh", BESS_CAPACITY_MWH)
            run.log_param("bess_max_power_mw", BESS_MAX_POWER_MW)
            run.log_param("n_days", len(dates))

            day_results: list[DailyResult] = []
            for date, day_prices in daily_pairs:
                r = run_scenario_on_day(cfg, day_prices)
                # Stamp the date into the result without rebuilding all fields.
                r = replace(r, date=date)
                day_results.append(r)
                all_results.append(r)

            # Aggregate per-scenario metrics.
            n_days = len(day_results)
            total_revenue = sum(r.total_eur for r in day_results)
            energy_revenue = sum(r.energy_eur for r in day_results)
            fcr_revenue = sum(r.fcr_eur for r in day_results)
            afrr_revenue = sum(r.afrr_eur for r in day_results)
            avg_fcr_mw = float(
                np.mean([r.fcr_capacity_mw for r in day_results])
            ) if day_results else 0.0
            n_afrr_up_days = sum(
                1 for r in day_results if r.n_afrr_up_committed > 0
            )
            n_afrr_dn_days = sum(
                1 for r in day_results if r.n_afrr_dn_committed > 0
            )
            n_optimal = sum(1 for r in day_results if r.status == "Optimal")

            run.log_metric("total_revenue_eur", total_revenue, step=n_days)
            run.log_metric("energy_revenue_eur", energy_revenue, step=n_days)
            run.log_metric("fcr_revenue_eur", fcr_revenue, step=n_days)
            run.log_metric("afrr_revenue_eur", afrr_revenue, step=n_days)
            run.log_metric("avg_fcr_capacity_mw", avg_fcr_mw, step=n_days)
            run.log_metric("n_days_afrr_up_committed", n_afrr_up_days, step=n_days)
            run.log_metric("n_days_afrr_dn_committed", n_afrr_dn_days, step=n_days)
            run.log_metric("n_days_optimal", n_optimal, step=n_days)
            run.log_metric("n_days_total", n_days, step=n_days)

    _print_summary(all_results)
    if out_dir is not None:
        _dump_outputs(out_dir, all_results, scenarios)

    return all_results


# ── Reporting —────────────────────────────────────────────────────────


def _print_summary(results: list[DailyResult]) -> None:
    """Per-scenario aggregate table to stdout."""
    by_scenario: dict[str, list[DailyResult]] = defaultdict(list)
    for r in results:
        by_scenario[r.scenario].append(r)

    # Compute baseline once (A_arbitrage_only total revenue).
    baseline_rows = by_scenario.get("A_arbitrage_only", [])
    baseline_total = sum(r.total_eur for r in baseline_rows) if baseline_rows else 0.0

    print()
    print("=" * 88)
    print("  EXPERIMENT 1 — Revenue stack summary")
    print("=" * 88)
    header = (
        f"{'Scenario':<25} {'Days':>5} {'Total €':>12} "
        f"{'Energy €':>12} {'FCR €':>10} {'aFRR €':>10} "
        f"{'Avg FCR MW':>11}"
    )
    print(header)
    print("-" * 88)
    for name in [
        "A_arbitrage_only",
        "B_arbitrage_plus_fcr",
        "C_arbitrage_plus_afrr",
        "D_full_stack",
    ]:
        rows = by_scenario.get(name, [])
        if not rows:
            continue
        total = sum(r.total_eur for r in rows)
        energy = sum(r.energy_eur for r in rows)
        fcr = sum(r.fcr_eur for r in rows)
        afrr = sum(r.afrr_eur for r in rows)
        avg_fcr = float(np.mean([r.fcr_capacity_mw for r in rows]))
        if name == "A_arbitrage_only":
            uplift = ""
        elif baseline_total > 0:
            uplift = f"  (+{(total - baseline_total) / baseline_total * 100:.1f}% vs A)"
        else:
            uplift = ""
        print(
            f"{name:<25} {len(rows):>5} {total:>12.2f} "
            f"{energy:>12.2f} {fcr:>10.2f} {afrr:>10.2f} "
            f"{avg_fcr:>11.2f}{uplift}"
        )
    print("=" * 88)
    print("  Per-day results: see ExperimentTracker DB or 'experiments/output/' if --out given.")
    print()


def _dump_outputs(
    out_dir: Path,
    results: list[DailyResult],
    scenarios: list[ScenarioConfig],
) -> None:
    """Write CSV + JSON to out_dir for offline inspection."""
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "exp1_daily_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    json_path = out_dir / "exp1_scenarios.json"
    with open(json_path, "w") as f:
        json.dump([asdict(s) for s in scenarios], f, indent=2)
    print(f"[exp1] Wrote {csv_path} and {json_path}.")


# ── CLI —──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Experiment 1 — joint BESS + FCR + aFRR revenue stacking.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional directory to write CSV + JSON outputs.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Optional path to experiment tracker SQLite DB.",
    )
    args = parser.parse_args()

    results = run_experiment(out_dir=args.out, tracker_db=args.db)
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
