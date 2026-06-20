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

## Provenance & reproduction

Snapshot of the local ENTSO-E disk cache (Belgian bidding zone, ~26-day window, 2026). Loaded via
`scripts/_viz_data.py`, which prefers these `sample_*.csv` files and falls back to a full local
`entsoe_30day_*.csv` / `bt_hourly.csv` cache when present.

## Note on version control

`data/` is gitignored. These sample files are committed deliberately — stage them with
`git add -f data/sample_*.csv data/README.md`. Keep the sample small; do not commit the full cache.
