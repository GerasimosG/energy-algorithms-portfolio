"""Static adequacy figures (industry-standard adequacy chart patterns), reproducible from committed samples.

Mirrors scripts/generate_figures.py: loads via _viz_data, styles via _viz_theme,
writes PNGs to docs/. See docs/VIZ_BENCHMARK.md for the visual references.
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _viz_data as data  # noqa: E402
import _viz_theme as theme  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from energy_algorithms.domain.adequacy import (  # noqa: E402
    AdequacyInputs, run_monte_carlo, duration_curve,
)

theme.apply_theme()
P = theme.PALETTE


def _save(fig, name: str, out_dir: str) -> None:
    theme.source_note(fig)
    fig.savefig(os.path.join(out_dir, name), bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}")


def _result(n_years: int = 50, seed: int = 42):
    units = data.load_adequacy_units()
    load = data.load_load_8760()
    vre = data.load_vre_8760()
    res = run_monte_carlo(AdequacyInputs(
        units["capacity_mw"].to_numpy(float), units["for"].to_numpy(float),
        load["load_mw"].to_numpy(float),
        (vre["wind_mw"] + vre["solar_mw"]).to_numpy(float)), n_years=n_years, seed=seed)
    return units, load, vre, res


def main(out_dir: str = None) -> None:
    out_dir = out_dir or os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    units, load, vre, res = _result()

    # 1) LOLE by technology-removed sensitivity (sensitivity bar)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    techs = units["technology"].unique()
    loles = []
    for tech in techs:
        keep = units[units["technology"] != tech]
        r = run_monte_carlo(AdequacyInputs(
            keep["capacity_mw"].to_numpy(float), keep["for"].to_numpy(float),
            load["load_mw"].to_numpy(float),
            (vre["wind_mw"] + vre["solar_mw"]).to_numpy(float)), n_years=30, seed=42)
        loles.append(r.lole_h)
    ax.bar(techs, loles, color=P["accent"])
    ax.axhline(res.lole_h, ls="--", color=P["ink"], label=f"base LOLE = {res.lole_h:.1f} h/yr")
    ax.set_ylabel("LOLE (h/yr)")
    ax.legend()
    theme.title_block(ax, "Adequacy sensitivity: LOLE if a technology is removed")
    _save(fig, "fig_adequacy_lole.png", out_dir)

    # 2) ENS duration curve
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ens_dc = duration_curve(res.ens_by_hour_mean)
    ax.fill_between(range(len(ens_dc)), ens_dc, color=P["accent"], alpha=0.5)
    ax.set_xlabel("hours (sorted)")
    ax.set_ylabel("expected ENS (MWh)")
    theme.title_block(ax, "Energy-not-served duration curve")
    _save(fig, "fig_adequacy_ens_duration.png", out_dir)

    # 3) Capacity-margin heatmap (day-of-year x hour-of-day)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    margin = res.margin_by_hour_mean[: 365 * 24].reshape(365, 24)
    im = ax.imshow(margin.T, aspect="auto", origin="lower", cmap=theme.DIVERGING_CMAP)
    ax.set_xlabel("day of year")
    ax.set_ylabel("hour of day")
    fig.colorbar(im, ax=ax, label="MW")
    theme.title_block(ax, "Mean capacity margin (MW)")
    _save(fig, "fig_adequacy_margin_heatmap.png", out_dir)

    # 4) Scenario small-multiples: LOLE vs added gas capacity
    fig, ax = plt.subplots(figsize=(8, 4.5))
    adds = [0, 200, 400, 600, 800]
    ys = []
    for mw in adds:
        cap = np.append(units["capacity_mw"].to_numpy(float), mw) if mw else units["capacity_mw"].to_numpy(float)
        fo = np.append(units["for"].to_numpy(float), 0.05) if mw else units["for"].to_numpy(float)
        r = run_monte_carlo(AdequacyInputs(
            cap, fo, load["load_mw"].to_numpy(float),
            (vre["wind_mw"] + vre["solar_mw"]).to_numpy(float)), n_years=30, seed=42)
        ys.append(r.lole_h)
    ax.plot(adds, ys, "o-", color=P["primary"])
    ax.set_xlabel("added CCGT capacity (MW)")
    ax.set_ylabel("LOLE (h/yr)")
    theme.title_block(ax, "Need-for-capacity: LOLE vs new firm capacity")
    _save(fig, "fig_adequacy_scenarios.png", out_dir)


if __name__ == "__main__":
    main()
    print("adequacy figures written to docs/")
