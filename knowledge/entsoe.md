# ENTSO-E & Energy Data

## What Is ENTSO-E?

**European Network of Transmission System Operators for Electricity** — the organization representing 39 transmission system operators (TSOs) across 35 European countries.

**Key function:** Coordinates the Pan-European electricity market, including the Euphemia market coupling algorithm.

---

## The Transparency Platform

### What It Provides

The ENTSO-E Transparency Platform is a REST API providing near-real-time electricity market data:

| Data Type | Description | Document Code | Update Frequency |
|-----------|-------------|---------------|-----------------|
| Day-ahead prices | EUR/MWh per bidding zone per hour | A44 | Daily |
| Actual generation | MW per production type per zone | A75 | Hourly |
| Installed capacity | MW of generation capacity | A68 | Annual |
| Load forecast | Day-ahead total load forecast (MW) | A65 | Daily |
| Cross-border flows | Scheduled commercial exchanges | A11 | Hourly |
| Imbalance prices | Real-time balancing energy | A85 | 15-min |

### API Access

**Registration:** https://transparency.entsoe.eu
**API Key Format:** UUID (provided via the `ENTSOE_API_KEY` environment variable)
**Rate Limits:** ~100 requests/minute for personal use
**Format:** XML responses

### Our Implementation (`energy_data/fetcher.py`)

```python
class EntsoeClient:
 def fetch_day_ahead_prices(self, area: str, date: str) -> dict:
 """Fetch day-ahead electricity prices for a bidding zone."""
 
 def fetch_generation_mix(self, area: str, date: str) -> dict:
 """Fetch actual generation per production type."""
 
 def fetch_load_forecast(self, area: str, date: str) -> dict:
 """Fetch day-ahead total load forecast."""
```

**Error handling matrix:**
- 401 Unauthorized → `{"status": "error", "error": "Unauthorized — check your API key"}`
- Network failure → `{"status": "error", "error": "Network error: ..."}`
- Bad XML → `{"status": "error", "error": "XML parse error: ..."}`
- API error → `{"status": "error", "error": "ENTSO-E API: [code] message"}`

---

## Bidding Zones

Europe is divided into **bidding zones** — geographic areas where electricity can be traded without internal congestion:

| Country | Zone Name | EIC Code |
|---------|-----------|----------|
| Belgium | BE | `10YBE----------2` |
| Germany/Luxemburg | DE-LU | `10Y1001A1001A82H` |
| France | FR | `10YFR-RTE------C` |
| Netherlands | NL | `10YNL----------L` |
| UK | GB | `10YGB----------A` |
| Spain | ES | `10YES-REE------0` |
| Italy (North) | IT-NORTH | `10YIT-GRTN-----B` |
| Poland | PL | `10YPL-AREA-----S` |

---

## PSR Types (Generation Classification)

| Code | Type | Relevance |
|------|------|-----------|
| B01 | Biomass | Renewable baseload |
| B04 | Fossil Gas | Flexible, price-setting |
| B05 | Fossil Hard coal | Baseload, declining |
| B11 | Hydro Run-of-river | Non-dispatchable renewable |
| B12 | Hydro Reservoir | Dispatchable, storage |
| B14 | Nuclear | Baseload, zero marginal cost |
| B16 | Solar | Intermittent, duck curve |
| B18 | Wind Offshore | High capacity factor |
| B19 | Wind Onshore | Volatile, zero marginal cost |

---

## Typical Belgian Generation Mix

| Source | MW | Share |
|--------|-----|-------|
| Nuclear | 4,800 | 42% |
| Fossil Gas | 2,100 | 19% |
| Wind Onshore | 1,500 | 13% |
| Wind Offshore | 900 | 8% |
| Solar | 600 | 5% |
| Hydro | 200 | 2% |
| Biomass | 350 | 3% |

**Key insight:** Nuclear dominates Belgian baseload (4.8 GW). When nuclear plants are offline, gas prices spike.

---

## Data Pipeline Architecture

### Our Pipeline
```
Yahoo Finance → yfinance → SQLite (market_data/store.py)
ENTSO-E API → urllib + XML parser → Python dicts
```

### Production Pipeline (What You'd Build in energy trading)
```
ENTSO-E ──┐
Nord Pool ┤
EPEX Spot ┤→ Kafka → TimescaleDB → Redis → Trading system
Reuters ──┤
Weather ──┘
```

---

## Edge Cases

**Missing Data:** ENTSO-E keeps ~1 year of data. Older data requires paid archives.

**DST Transitions:** 23 or 25 hour days on clock change days.

**Zone Splits:** Germany split into DE and LU in 2018. Old codes may fail.

**Publication Delay:** Day-ahead prices published ~13:00 CET for the next day.

---

## Quick Quiz

**Q1:** What's the EIC code for the Belgian bidding zone?

**Q2:** How does EntsoeClient handle a 401 response?

**Q3:** What PSR type is B14?

**Q4:** Why might day-ahead price data be unavailable for today?

**Q5:** What does documentType A75 provide?

---

## Answers

**A1:** `10YBE----------2`

**A2:** Returns `{"status": "error", "error": "Unauthorized — check your API key"}`. Never crashes.

**A3:** Nuclear power. Dominates Belgian generation at ~42% with 7 reactors.

**A4:** Day-ahead prices for today were published yesterday. Tomorrow's not published yet (~13:00 CET).

**A5:** Actual generation output per production type in MW.
