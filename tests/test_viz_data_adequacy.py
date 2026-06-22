# tests/test_viz_data_adequacy.py
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    "_viz_data", os.path.join(os.path.dirname(__file__), "..", "scripts", "_viz_data.py"))
viz = importlib.util.module_from_spec(spec); spec.loader.exec_module(viz)

def test_units_loader():
    df = viz.load_adequacy_units()
    assert {"unit", "technology", "capacity_mw", "for"} <= set(df.columns)
    assert (df["for"].between(0, 1)).all()

def test_load_and_vre_loaders():
    assert {"datetime", "load_mw"} <= set(viz.load_load_8760().columns)
    assert {"datetime", "wind_mw", "solar_mw"} <= set(viz.load_vre_8760().columns)

def test_antares_loader():
    df = viz.load_antares_sample()
    assert {"area", "hour_index", "load_mw"} <= set(df.columns)
