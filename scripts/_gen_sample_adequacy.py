"""Generate the committed synthetic adequacy sample (deterministic).

Outputs (all SYNTHETIC — not real market or ANTARES data):
  data/sample_adequacy_units.csv, data/sample_load_8760.csv,
  data/sample_vre_8760.csv, data/antares_sample/.../values-hourly.txt
Run once, then commit with `git add -f`. Re-runs are byte-stable (fixed seed).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from energy_algorithms.adapters.antares_io import write_values_hourly  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
HOURS = 8760
RNG = np.random.default_rng(2026)


def _units() -> pd.DataFrame:
    # Synthetic Belgian-style fleet sized so the base case is realistically tight:
    # derated capacity ~5,650 MW vs ~4,927 MW peak load -> LOLE ~5 h/yr, just above
    # Belgium's 3 h/yr legal standard, so the "need for capacity" scenarios show LOLE
    # dropping below the standard as a few hundred MW of firm capacity is added.
    return pd.DataFrame([
        ("NUC1", "nuclear", 1000, 0.06), ("NUC2", "nuclear", 1000, 0.06),
        ("CCGT1", "gas_ccgt", 450, 0.04), ("CCGT2", "gas_ccgt", 450, 0.04),
        ("CCGT3", "gas_ccgt", 450, 0.04), ("CCGT4", "gas_ccgt", 450, 0.04),
        ("CCGT5", "gas_ccgt", 450, 0.04), ("CCGT6", "gas_ccgt", 450, 0.04),
        ("CCGT7", "gas_ccgt", 450, 0.04), ("OCGT1", "gas_ocgt", 150, 0.08),
        ("OCGT2", "gas_ocgt", 150, 0.08), ("OCGT3", "gas_ocgt", 150, 0.08),
        ("OCGT4", "gas_ocgt", 150, 0.08), ("BIO1", "biomass", 200, 0.05),
    ], columns=["unit", "technology", "capacity_mw", "for"])


def _profiles() -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = pd.date_range("2026-01-01", periods=HOURS, freq="h")
    t = np.arange(HOURS)
    season = np.cos(2 * np.pi * (t / HOURS))            # winter peak
    daily = np.cos(2 * np.pi * ((t % 24) - 18) / 24)    # evening peak
    load = 3200 + 900 * season + 500 * daily + RNG.normal(0, 120, HOURS)
    solar = np.clip(700 * np.sin(np.pi * ((t % 24) - 6) / 12), 0, None) * (0.6 + 0.4 * (season < 0))
    wind = np.clip(RNG.weibull(2.0, HOURS) * 450, 0, 1200)
    load_df = pd.DataFrame({"datetime": idx, "load_mw": load.round(1)})
    vre_df = pd.DataFrame({"datetime": idx, "wind_mw": wind.round(1), "solar_mw": solar.round(1)})
    return load_df, vre_df


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    _units().to_csv(os.path.join(DATA, "sample_adequacy_units.csv"), index=False)
    load_df, vre_df = _profiles()
    load_df.to_csv(os.path.join(DATA, "sample_load_8760.csv"), index=False)
    vre_df.to_csv(os.path.join(DATA, "sample_vre_8760.csv"), index=False)

    # a short (1-week) synthetic ANTARES economy output for the reader demo
    n = 168
    ant = pd.DataFrame({
        "load_mw": load_df["load_mw"].head(n).to_numpy(),
        "marginal_price_eur_mwh": np.clip(40 + 0.02 * (load_df["load_mw"].head(n) - 3000), 5, 4000).round(2),
        "ens_mwh": np.zeros(n),
        "lold_h": np.zeros(n),
    })
    ant_path = os.path.join(DATA, "antares_sample", "economy", "mc-all", "areas", "be", "values-hourly.txt")
    os.makedirs(os.path.dirname(ant_path), exist_ok=True)
    write_values_hourly(ant, ant_path, area="BE")
    print("wrote synthetic adequacy sample to", DATA)


if __name__ == "__main__":
    main()
