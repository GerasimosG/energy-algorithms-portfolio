import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "build_warehouse", os.path.join(os.path.dirname(__file__), "..", "scripts", "build_warehouse.py"))
bw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bw)

def test_build_warehouse_emits_star_schema(tmp_path):
    tables = bw.build_warehouse(str(tmp_path), n_years=5, seed=1)
    for name in ["fact_hourly", "fact_adequacy", "dim_date", "dim_hour",
                 "dim_zone", "dim_technology", "data_quality_report"]:
        assert name in tables
        assert (tmp_path / f"{name}.csv").exists()
    assert {"datetime", "zone", "load_mw", "margin_mw", "ens_mwh"} <= set(tables["fact_hourly"].columns)
    assert {"lole_h", "eens_mwh"} <= set(tables["fact_adequacy"].columns)

def test_consistency_check_flags_negative_load(tmp_path):
    import pandas as pd
    fh = pd.DataFrame({"datetime": pd.date_range("2026-01-01", periods=2, freq="h"),
                       "zone": ["BE", "BE"], "load_mw": [100.0, -5.0],
                       "available_mw": [200.0, 200.0], "margin_mw": [100.0, 205.0],
                       "ens_mwh": [0.0, 0.0], "vre_mw": [0.0, 0.0], "lolp": [0.0, 0.0]})
    rep = bw.check_consistency(fh)
    assert not bool(rep.loc[rep["check"] == "load_non_negative", "ok"].iloc[0])


def test_built_warehouse_quality_all_ok(tmp_path):
    tables = bw.build_warehouse(str(tmp_path), n_years=5, seed=1)
    assert tables["data_quality_report"]["ok"].all()


def test_dim_date_is_daily_grain(tmp_path):
    tables = bw.build_warehouse(str(tmp_path), n_years=5, seed=1)
    assert len(tables["dim_date"]) <= 366
    assert {"date", "month", "season"} <= set(tables["dim_date"].columns)
