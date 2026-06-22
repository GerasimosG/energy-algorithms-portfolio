# Adequacy Visualization Patterns

The adequacy figures and the dashboard's **Adequacy** section follow the visual conventions used across
European resource-adequacy assessments and ten-year network-development scenario reports. Those studies
have converged on a small set of chart types that communicate security-of-supply results clearly to a
non-specialist audience. This repository reproduces those patterns from a committed synthetic sample
(no third-party data or branding) so the techniques can be inspected and reused.

All figures are produced by `scripts/generate_adequacy_figures.py` and share the one visual identity in
`scripts/_viz_theme.py`. The interactive counterpart lives in the dashboard's `#adequacy` section
(`scripts/generate_dashboard.py`).

## The patterns and why they work

| Pattern | What it shows | Why it is effective | This repo |
|---|---|---|---|
| **LOLE sensitivity bars** | Loss-of-load expectation (h/yr) under different system states, against a reference line | A single bar-vs-threshold read tells a decision-maker whether the system meets a reliability target and which lever moves it most | `fig_adequacy_lole.png` |
| **ENS duration curve** | Expected energy-not-served (MWh) for every hour, sorted high→low | The area under the curve is total unserved energy; the shape separates "a few severe hours" from "many shallow hours" at a glance | `fig_adequacy_ens_duration.png` |
| **Capacity-margin heatmap** | Mean available margin (MW) over day-of-year × hour-of-day | Surfaces *when* the system is tight — winter evenings vs summer nights — in one calendar view | `fig_adequacy_margin_heatmap.png` |
| **Scenario / "need for capacity" curve** | LOLE as firm capacity is added, against the reliability standard | Directly answers "how much new capacity restores compliance?" — the core question of an adequacy study | `fig_adequacy_scenarios.png` |
| **Interactive adequacy panel** | Live ENS duration curve with LOLE/EENS headline | Lets a reviewer hover hour-by-hour and re-read the headline metrics without re-running code | dashboard `#adequacy` |

## Design conventions reused

- **Reference lines over raw bars** — a reliability standard (e.g. a 3 h/yr LOLE target) is drawn as a
  threshold so the eye lands on compliance, not absolute height.
- **Duration curves, not time series** — adequacy cares about the worst tail of hours; sorting removes
  calendar noise and makes the tail legible.
- **Diverging colour for margin** — surplus vs deficit reads instantly; the shared theme's diverging
  colormap centres on zero margin.
- **Headline metrics in the title** — LOLE (h/yr) and EENS (MWh/yr) travel with the chart so a figure
  is self-describing when lifted into a slide or report.

## Reproducing

```bash
pip install -e ".[dev]"
python scripts/generate_adequacy_figures.py      # the four PNGs above
python scripts/generate_dashboard.py             # rebuilds docs/dashboard.html incl. #adequacy
```

All inputs are the committed synthetic sample (`data/sample_adequacy_units.csv`,
`data/sample_load_8760.csv`, `data/sample_vre_8760.csv`); see `data/README.md`. Results are deterministic
(Monte-Carlo seed 42).
