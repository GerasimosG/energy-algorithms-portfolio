"""`ea-adequacy` — read an ANTARES sample, run Monte-Carlo adequacy, report LOLE/EENS.

Demonstrates the resource-adequacy pipeline end-to-end on the committed synthetic sample:
ANTARES output (adapter) -> adequacy metrics + Monte-Carlo (domain).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _viz():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_viz_data", os.path.join(ROOT, "scripts", "_viz_data.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv=None) -> int:
    from energy_algorithms.domain.adequacy import AdequacyInputs, run_monte_carlo
    viz = _viz()
    units = viz.load_adequacy_units()
    load = viz.load_load_8760()
    vre = viz.load_vre_8760()
    res = run_monte_carlo(AdequacyInputs(
        units["capacity_mw"].to_numpy(float), units["for"].to_numpy(float),
        load["load_mw"].to_numpy(float),
        (vre["wind_mw"] + vre["solar_mw"]).to_numpy(float)), n_years=50, seed=42)
    ant = viz.load_antares_sample()
    print("=== Resource-adequacy demo (synthetic sample) ===")
    print(f"thermal units: {len(units)} · total {units['capacity_mw'].sum():.0f} MW · peak load {load['load_mw'].max():.0f} MW")
    print(f"ANTARES sample rows: {len(ant)} (area {ant['area'].iloc[0]})")
    print(f"LOLE = {res.lole_h:.1f} h/yr")
    print(f"EENS = {res.eens_mwh:.0f} MWh/yr")
    print(f"min mean margin = {res.margin_by_hour_mean.min():.0f} MW")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
