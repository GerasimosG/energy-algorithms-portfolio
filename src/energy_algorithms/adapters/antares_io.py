"""ANTARES values-hourly reader/writer for economy adequacy hourly outputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ANTARES_VARIABLE_MAP: dict[str, str] = {
    "OV. COST": "ov_cost_eur",
    "OP. COST": "op_cost_eur",
    "MRG. PRICE": "marginal_price_eur_mwh",
    "LOAD": "load_mw",
    "BALANCE": "balance_mw",
    "LOLD": "lold_h",
    "UNSP. ENRG": "ens_mwh",
}
_INVERSE_MAP = {v: k for k, v in ANTARES_VARIABLE_MAP.items()}
_UNITS = {
    "ov_cost_eur": "Euro", "op_cost_eur": "Euro", "marginal_price_eur_mwh": "Euro/MWh",
    "load_mw": "MWh", "balance_mw": "MWh", "lold_h": "Hours", "ens_mwh": "MWh",
}


def read_values_hourly(path, area: str | None = None) -> pd.DataFrame:
    """Parse ANTARES-style ``values-hourly.txt`` tidy DataFrame."""
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    hdr = next((i for i, ln in enumerate(lines) if any(tok in ln for tok in ANTARES_VARIABLE_MAP)), None)
    if hdr is None:
        raise ValueError(f"{p}: no data rows parsed")

    # Parse variable names from header and compute offset
    var_line = lines[hdr]
    names = [c.strip() for c in var_line.split("\t")]
    offset = next(j for j, c in enumerate(names) if c in ANTARES_VARIABLE_MAP)
    var_names = names[offset:]

    # Parse data rows
    records = []
    for ln in lines[hdr + 1:]:
        cells = ln.split("\t")
        if len(cells) <= offset:
            continue
        head = [c.strip() for c in cells[:offset]]
        ints = [c for c in head if c.isdigit()]
        if not ints:  # skip the units/stat rows
            continue
        rec = {"hour_index": int(ints[0])}
        for name, val in zip(var_names, cells[offset:]):
            col = ANTARES_VARIABLE_MAP.get(name.strip())
            if col:
                v = val.strip()
                rec[col] = float(v) if v else float("nan")
        records.append(rec)

    if not records:
        raise ValueError(f"{p}: no data rows parsed")

    df = pd.DataFrame.from_records(records).sort_values("hour_index").reset_index(drop=True)
    df.insert(0, "area", area or p.parent.name.upper())
    return df


def write_values_hourly(df: pd.DataFrame, path, area: str, variables: list[str] | None = None) -> None:
    """Write tidy frame simplified ANTARES-style hourly layout."""
    cols = variables or [c for c in ANTARES_VARIABLE_MAP.values() if c in df.columns]
    antares_names = [_INVERSE_MAP[c] for c in cols]
    n = len(df)
    out = [
        f"{area}\tarea\tva\t\thourly",
        "\tVARIABLES\tBEGIN\tEND",
        f"\t{len(cols)}\t1\t{n}",
        "",
        "\t".join([area, "hourly", "", ""] + antares_names),
        "\t".join(["", "", "index", "hour"] + [_UNITS[c] for c in cols]),
    ]
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        out.append("\t".join(
            [area, "", str(i), f"{(i - 1) % 24:02d}:00"] + [f"{float(row[c]):.2f}" for c in cols]
        ))

    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")
