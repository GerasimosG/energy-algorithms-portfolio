# Sample data for figures & dashboard

This directory holds a **small canonical sample** of cached ENTSO-E Belgian day-ahead market data,
committed so a fresh clone can reproduce every figure (`scripts/generate_figures.py`) and the
interactive dashboard (`scripts/generate_dashboard.py`) without network access or API credentials.

> The full live pipeline lives in `src/energy_algorithms/adapters/entsoe_client.py`. These CSVs are a
> trimmed canonical snapshot — not the live source of truth.

## Files

| File | Rows | Schema |
|---|---|---|
| `sample_entsoe_prices.csv` | ~5.3k | `date, hour, price_eur_mwh` — 15-min slots (`hour` 1–96) over 28 days |
| `sample_entsoe_summary.csv` | 28 | `date, entsoe_avg_price, entsoe_min, entsoe_max, model_mcp, price_diff, price_diff_pct, total_gen_mw, traded_mw, social_welfare, energy_balance_ok, supply_constraint_ok, demand_constraint_ok, all_ok` |
| `sample_bt_hourly.csv` | ~2.5k | `datetime, open, high, low, close, volume` — hourly OHLCV used by backtest signals |

`model_mcp` is this repo's PCR market-clearing model output; `entsoe_avg_price` is the published
ENTSO-E day-ahead price — the dashboard compares the two.

## Resource-adequacy sample (synthetic)

A fully **synthetic** sample for the resource-adequacy pipeline (`domain/adequacy/`,
`scripts/build_warehouse.py`, `scripts/generate_adequacy_figures.py`). Generated deterministically by
`scripts/_gen_sample_adequacy.py` (fixed seed — re-runs are byte-stable). Not real market data.

| File | Rows | Schema |
|---|---|---|
| `sample_adequacy_units.csv` | 14 | `unit, technology, capacity_mw, for` — thermal fleet with forced-outage rates |
| `sample_load_8760.csv` | 8,760 | `datetime, load_mw` — one synthetic year of hourly demand |
| `sample_vre_8760.csv` | 8,760 | `datetime, wind_mw, solar_mw` — one synthetic year of hourly VRE availability |
| `antares_sample/economy/mc-all/areas/be/values-hourly.txt` | 168 | ANTARES economy `values-hourly` format (1 week), read by `adapters/antares_io.py` |
| `warehouse/*.csv` (+ `.parquet` if `pyarrow` present) | — | PowerBI star schema (`fact_hourly`, `fact_adequacy`, `dim_date/hour/zone/technology`) + `data_quality_report.csv`, built by `scripts/build_warehouse.py` |

Rebuild: `python scripts/_gen_sample_adequacy.py && python scripts/build_warehouse.py`.

## Provenance & reproduction

Snapshot of the local ENTSO-E disk cache (Belgian bidding zone, ~26-day window, 2026). Loaded via
`scripts/_viz_data.py`, which prefers these `sample_*.csv` files and falls back to a full local
`entsoe_30day_*.csv` / `bt_hourly.csv` cache when present.

## Note on version control

`data/` is gitignored. These sample files are committed deliberately — stage them with
`git add -f data/sample_*.csv data/README.md`. Keep the sample small; do not commit the full cache.
