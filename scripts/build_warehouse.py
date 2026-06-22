"""Build a PowerBI-ready star-schema warehouse from the synthetic adequacy sample.

Facts: fact_hourly, fact_adequacy. Dimensions: dim_date, dim_hour, dim_zone,
dim_technology. Also writes data_quality_report.csv (input/output consistency
checks). CSV always; Parquet additionally when pyarrow is available.
See docs/POWERBI_MODEL.md for the data model + DAX measures.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from energy_algorithms.domain.adequacy import AdequacyInputs, run_monte_carlo  # noqa: E402

ZONE = "BE"


def check_consistency(fact_hourly: pd.DataFrame) -> pd.DataFrame:
    """Input/output consistency checks valid for Monte-Carlo MEAN data."""
    checks = {
        "load_non_negative": (fact_hourly["load_mw"] < 0).sum(),
        "vre_non_negative": (fact_hourly["vre_mw"] < 0).sum(),
        "ens_non_negative": (fact_hourly["ens_mwh"] < 0).sum(),
        "lolp_in_unit_interval": ((fact_hourly["lolp"] < 0) | (fact_hourly["lolp"] > 1)).sum(),
        "ens_implies_shortfall_risk": ((fact_hourly["ens_mwh"] > 0) & (fact_hourly["lolp"] <= 0)).sum(),
    }
    rows = [{"check": k, "n_failures": int(v), "ok": int(v) == 0} for k, v in checks.items()]
    return pd.DataFrame(rows)


def build_warehouse(out_dir: str, n_years: int = 50, seed: int = 42) -> dict[str, pd.DataFrame]:
    os.makedirs(out_dir, exist_ok=True)
    _spec = importlib.util.spec_from_file_location("_viz_data", os.path.join(ROOT, "scripts", "_viz_data.py"))
    _viz = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_viz)
    units = _viz.load_adequacy_units()
    load = _viz.load_load_8760()
    vre = _viz.load_vre_8760()
    vre_total = (vre["wind_mw"] + vre["solar_mw"]).to_numpy()

    result = run_monte_carlo(AdequacyInputs(
        unit_capacity_mw=units["capacity_mw"].to_numpy(float),
        unit_for=units["for"].to_numpy(float),
        demand_mw=load["load_mw"].to_numpy(float),
        vre_mw=vre_total,
    ), n_years=n_years, seed=seed)

    available = load["load_mw"].to_numpy() + result.margin_by_hour_mean  # expected available
    fact_hourly = pd.DataFrame({
        "datetime": load["datetime"], "zone": ZONE,
        "load_mw": load["load_mw"].round(1),
        "vre_mw": np.round(vre_total, 1),
        "available_mw": np.round(available, 1),
        "margin_mw": np.round(result.margin_by_hour_mean, 1),
        "lolp": np.round(result.lolp_by_hour, 4),
        "ens_mwh": np.round(result.ens_by_hour_mean, 2),
    })

    fact_adequacy = pd.DataFrame([{
        "scenario": "base", "zone": ZONE, "n_years": n_years,
        "lole_h": round(result.lole_h, 2), "eens_mwh": round(result.eens_mwh, 1),
        "peak_load_mw": round(float(load["load_mw"].max()), 1),
        "total_capacity_mw": float(units["capacity_mw"].sum()),
        "reserve_margin": round(
            (float(units["capacity_mw"].sum()) - float(load["load_mw"].max()))
            / float(load["load_mw"].max()), 3),
    }])

    fact_hourly["date"] = pd.to_datetime(fact_hourly["datetime"]).dt.date
    fact_hourly["hour"] = pd.to_datetime(fact_hourly["datetime"]).dt.hour

    _dd = pd.to_datetime(pd.Series(sorted(set(pd.to_datetime(fact_hourly["datetime"]).dt.normalize()))))
    dim_date = pd.DataFrame({
        "date": _dd.dt.date, "month": _dd.dt.month,
        "week": _dd.dt.isocalendar().week.astype(int),
        "season": (_dd.dt.month % 12 // 3).map({0: "winter", 1: "spring", 2: "summer", 3: "autumn"}),
    }).reset_index(drop=True)
    dim_hour = pd.DataFrame({"hour": range(24),
                             "is_peak": [h in range(17, 21) for h in range(24)]})
    dim_zone = pd.DataFrame([{"zone": ZONE, "country": "Belgium", "tso": "national TSO"}])
    dim_technology = units[["technology"]].drop_duplicates().reset_index(drop=True)

    quality = check_consistency(fact_hourly)

    tables = {
        "fact_hourly": fact_hourly, "fact_adequacy": fact_adequacy,
        "dim_date": dim_date, "dim_hour": dim_hour, "dim_zone": dim_zone,
        "dim_technology": dim_technology, "data_quality_report": quality,
    }
    have_parquet = importlib.util.find_spec("pyarrow") is not None
    for name, df in tables.items():
        df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
        if have_parquet:
            df.to_parquet(os.path.join(out_dir, f"{name}.parquet"), index=False)
    return tables


if __name__ == "__main__":
    out = os.path.join(ROOT, "data", "warehouse")
    t = build_warehouse(out)
    print(f"warehouse → {out}")
    print(t["data_quality_report"].to_string(index=False))
