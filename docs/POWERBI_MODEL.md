# PowerBI Data Model — Energy Algorithms Adequacy

This document describes the star-schema warehouse produced by `scripts/build_warehouse.py` and the
DAX measures used to build the resource-adequacy dashboards in PowerBI Desktop.

> **Reproducibility note:** the repo ships the CSV/Parquet warehouse tables (`data/warehouse/`),
> this documented model, and the DAX measures below. Producing the binary `.pbix` file and capturing
> screenshots is a **manual PowerBI-Desktop step** driven by this document. No binary is committed to
> keep the repo fresh-clone reproducible and free of large binary assets.

---

## 1. Schema overview

```
                        ┌─────────────┐
                        │  dim_date   │
                        │ (365 rows)  │
                        └──────┬──────┘
                               │ date
                               │
┌──────────────┐   zone  ┌─────┴──────────────┐   hour  ┌─────────────┐
│   dim_zone   ├─────────┤   fact_hourly       ├─────────┤  dim_hour   │
│  (1+ rows)   │         │  (8,760 rows/zone)  │         │  (24 rows)  │
└──────────────┘         └────────────────────┘         └─────────────┘
        │
        │ zone
        │
┌───────┴──────────┐
│  fact_adequacy   │
│   (1 row: base/BE)│
└──────────────────┘

dim_technology  (standalone lookup — no FK in current schema)
```

---

## 2. Table definitions

### fact_hourly

Grain: one row per hour per zone (8,760 rows per zone for a full year).

| Column | Type | Description |
|---|---|---|
| `datetime` | datetime | UTC timestamp (hourly) |
| `zone` | string | Bidding zone code (e.g. `BE`) |
| `load_mw` | float | Gross load (MW) |
| `vre_mw` | float | Variable renewable energy output (MW) |
| `available_mw` | float | Derated thermal + VRE available capacity (MW) |
| `margin_mw` | float | `available_mw − load_mw`; negative = shortfall |
| `lolp` | float | Loss-of-Load Probability for this hour (0–1) |
| `ens_mwh` | float | Energy Not Served this hour (MWh); 0 when margin ≥ 0 |
| `date` | date | FK → `dim_date[date]` |
| `hour` | int | Hour of day 0–23; FK → `dim_hour[hour]` |

### fact_adequacy

Grain: one row per scenario/zone/simulation run.

| Column | Type | Description |
|---|---|---|
| `scenario` | string | Scenario label (e.g. `base`) |
| `zone` | string | Bidding zone; FK → `dim_zone[zone]` |
| `n_years` | int | Monte-Carlo simulation length (years) |
| `lole_h` | float | Loss-of-Load Expectation (h/yr) |
| `eens_mwh` | float | Expected Energy Not Served (MWh/yr) |
| `peak_load_mw` | float | Peak load across simulation (MW) |
| `total_capacity_mw` | float | Installed fleet capacity (MW) |
| `reserve_margin` | float | `(total_capacity_mw − peak_load_mw) / peak_load_mw` (fraction) |

### dim_date

Grain: one row per calendar date (365 rows for a non-leap year).

| Column | Type | Description |
|---|---|---|
| `date` | date | Calendar date (PK) |
| `month` | int | Month number 1–12 |
| `week` | int | ISO week number |
| `season` | string | `winter`, `spring`, `summer`, `autumn` (lowercase — match exactly in DAX filters) |

### dim_hour

Grain: one row per hour of the day (24 rows).

| Column | Type | Description |
|---|---|---|
| `hour` | int | Hour 0–23 (PK) |
| `is_peak` | bool | True for hours 17–20 (evening peak window) |

### dim_zone

| Column | Type | Description |
|---|---|---|
| `zone` | string | Bidding zone code (PK, e.g. `BE`) |
| `country` | string | Country name |
| `tso` | string | Transmission system operator |

### dim_technology

| Column | Type | Description |
|---|---|---|
| `technology` | string | Technology label (e.g. `Nuclear`, `CCGT`, `OCGT`, `Biomass`) |

---

## 3. Relationships (star schema)

| From | To | Cardinality |
|---|---|---|
| `fact_hourly[date]` | `dim_date[date]` | Many → One |
| `fact_hourly[hour]` | `dim_hour[hour]` | Many → One |
| `fact_hourly[zone]` | `dim_zone[zone]` | Many → One |
| `fact_adequacy[zone]` | `dim_zone[zone]` | Many → One |

`dim_technology` is a standalone lookup table with no FK relationship in the current schema.

---

## 4. Data quality

Running `scripts/build_warehouse.py` also writes `data/warehouse/data_quality_report.csv` via
`check_consistency()`. The report has three columns: `check`, `n_failures`, `ok`. All five checks
pass (`ok = True`) on the committed synthetic sample.

---

## 5. Ingest / refresh

```bash
# Rebuild all warehouse tables from the committed synthetic sample data:
python scripts/build_warehouse.py
# Output: data/warehouse/*.csv  (and *.parquet if pyarrow is installed)
# Stage for commit:
git add -f data/warehouse/
```

The script reads `data/sample_adequacy_units.csv`, `data/sample_load_8760.csv`,
`data/sample_vre_8760.csv`, and the Monte-Carlo result computed by
`src/energy_algorithms/domain/adequacy/monte_carlo.py` (seed 42, n_years=50).

To refresh in PowerBI: **Home → Transform data → Refresh** (or schedule via PowerBI Service gateway
pointing at the CSV/Parquet files).

---

## 6. DAX measures

Create these measures in a dedicated `_Measures` table in PowerBI Desktop.

```dax
-- Core adequacy KPIs
LOLE (h/yr)         = SUM(fact_adequacy[lole_h])
EENS (MWh/yr)       = SUM(fact_adequacy[eens_mwh])

-- Capacity figures
Peak Load (MW)      = MAX(fact_hourly[load_mw])
Total Capacity (MW) = MAX(fact_adequacy[total_capacity_mw])
Min Margin (MW)     = MIN(fact_hourly[margin_mw])

-- Shortfall events
Hours in Shortfall  = CALCULATE(COUNTROWS(fact_hourly), fact_hourly[ens_mwh] > 0)

-- Reserve margin
-- Option A: read the pre-computed column (recommended — avoids division on filtered contexts)
Reserve Margin %    = MAX(fact_adequacy[reserve_margin])

-- Option B: compute from capacity measures (use when filtering by scenario)
Reserve Margin % (calc) =
    DIVIDE(
        [Total Capacity (MW)] - [Peak Load (MW)],
        [Peak Load (MW)]
    )
```

> **Which form to use:** Option A (`MAX(fact_adequacy[reserve_margin])`) reads the column computed
> by the Python script and is correct in any slicer context. Option B (`DIVIDE(...)`) recomputes
> dynamically and is useful when the peak-load measure is sliced by a dimension that `fact_adequacy`
> does not share. Both are provided; use Option A unless you need dynamic recomputation.

---

## 7. Sample results (synthetic, seed 42, n_years=50)

All figures below are from the **synthetic** sample dataset. They are not real Belgian market data.

| Metric | Value |
|---|---|
| LOLE | 5.2 h/yr |
| EENS | 1,432 MWh/yr |
| Min mean capacity margin | 930 MW |
| Reserve margin | 20.8% |
| Fleet | 14 units, 5,950 MW installed (≈ 5,646 MW derated) |
| Peak load | 4,927 MW |

Fleet composition: 2 × Nuclear 1,000 MW (FOR 0.06), 7 × CCGT 450 MW (FOR 0.04),
4 × OCGT 150 MW (FOR 0.08), 1 × Biomass 200 MW (FOR 0.05).

The base-case LOLE of ≈ 5 h/yr breaches a **3 h/yr** LOLE reliability standard (a common European
adequacy target). The "need for
capacity" scenario analysis (n_years=30) shows that adding ≈ 200 MW of firm capacity restores
compliance:

| Added capacity (MW) | LOLE (h/yr) |
|---|---|
| +0 | 5.0 |
| +200 | 2.4 |
| +400 | 1.2 |
| +600 | 0.6 |
| +800 | 0.3 |

> All data is synthetic. Scenario sizing is illustrative only.
