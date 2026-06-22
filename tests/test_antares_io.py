import pandas as pd
import pytest

from energy_algorithms.adapters.antares_io import (
    ANTARES_VARIABLE_MAP,
    read_values_hourly,
    write_values_hourly,
)


def test_round_trip(tmp_path):
    df = pd.DataFrame({
        "load_mw": [100.0, 110.0, 120.0],
        "ens_mwh": [0.0, 0.0, 5.0],
        "marginal_price_eur_mwh": [50.0, 60.0, 3000.0],
        "lold_h": [0.0, 0.0, 1.0],
    })
    path = tmp_path / "areas" / "be" / "values-hourly.txt"
    path.parent.mkdir(parents=True)
    write_values_hourly(df, path, area="BE")
    out = read_values_hourly(path)
    assert out["area"].unique().tolist() == ["BE"]
    assert out["hour_index"].tolist() == [1, 2, 3]
    assert out["load_mw"].tolist() == [100.0, 110.0, 120.0]
    assert out["ens_mwh"].tolist() == [0.0, 0.0, 5.0]
    assert out["marginal_price_eur_mwh"].tolist() == [50.0, 60.0, 3000.0]

def test_area_inferred_from_path(tmp_path):
    df = pd.DataFrame({"load_mw": [100.0]})
    path = tmp_path / "areas" / "fr" / "values-hourly.txt"
    path.parent.mkdir(parents=True)
    write_values_hourly(df, path, area="FR")
    assert read_values_hourly(path)["area"].unique().tolist() == ["FR"]

def test_variable_map_has_core_adequacy_columns():
    assert ANTARES_VARIABLE_MAP["UNSP. ENRG"] == "ens_mwh"
    assert ANTARES_VARIABLE_MAP["LOLD"] == "lold_h"
    assert ANTARES_VARIABLE_MAP["MRG. PRICE"] == "marginal_price_eur_mwh"

def test_missing_header_raises(tmp_path):
    """Test that read_values_hourly raises ValueError when no ANTARES variable header is found."""
    path = tmp_path / "areas" / "be" / "values-hourly.txt"
    path.parent.mkdir(parents=True)
    # Write a file with no ANTARES variable tokens
    path.write_text("Area\tBlank\tIndex\tHour\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows parsed"):
        read_values_hourly(path)

def test_no_data_rows_raises(tmp_path):
    """Test that read_values_hourly raises ValueError when no data rows are present."""
    path = tmp_path / "areas" / "be" / "values-hourly.txt"
    path.parent.mkdir(parents=True)
    # Write a file with valid variable header but no data rows
    content = "Area\thourly\t\t\tLOAD\n\t\tindex\thour\tMWh\n"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows parsed"):
        read_values_hourly(path)
