#!/usr/bin/env python3
"""Generate a standalone interactive Plotly dashboard for the Energy Algorithms portfolio.

Emits ``docs/dashboard.html`` — a single self-contained file (Plotly via CDN, no server)
with a branded header, KPI cards, and six interactive panels:

  1. Day × hour price heatmap (negative prices visible via a diverging scale)
  2. Price-duration curve (annotated: % negative hours, median)
  3. PCR model MCP vs ENTSO-E day-ahead price (with daily min–max band)
  4. Social welfare cleared per day
  5. BESS dispatch schedule on the most volatile day (charge/discharge + SoC + price)
  6. Hour-of-day strategy P&L and win rate

Data comes through ``_viz_data`` (committed sample dataset); the BESS panel runs the real
domain solver ``solve_storage``.
"""

from __future__ import annotations

import os

# Sibling helpers in this scripts/ dir (auto-added to sys.path when run directly).
import _viz_data as data  # noqa: E402
import _viz_theme as theme  # noqa: E402
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Domain solver (read-only) — runs the real BESS optimisation in the dashboard. Resolved via
# the editable install (``pip install -e .``); no sys.path manipulation in package-adjacent code.
from energy_algorithms.domain.optimization.storage import solve_storage
from energy_algorithms.domain.adequacy import AdequacyInputs, run_monte_carlo, duration_curve  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
OUTPUT = os.path.join(DOCS_DIR, "dashboard.html")

C = theme.PALETTE
COLORWAY = theme.PLOTLY_COLORWAY
TEMPLATE = theme.PLOTLY_TEMPLATE


def _style(fig: go.Figure, title: str, subtitle: str = "",
           hovermode: str | None = None) -> go.Figure:
    """Apply the shared template + title convention to a figure.

    Parameters
    ----------
    hovermode : str | None
        Plotly hovermode.  ``None`` defaults to ``"x unified"``; pass a
        different string (e.g. ``"closest"``) for specialised panels such
        as the 2-D heatmap.
    """
    head = f"<b>{title}</b>"
    if subtitle:
        head += f"<br><span style='font-size:13px;color:{C['neutral']}'>{subtitle}</span>"
    fig.update_layout(
        template=TEMPLATE,
        colorway=COLORWAY,
        title=dict(text=head, x=0.01, xanchor="left", font=dict(color=C["ink"], size=20)),
        margin=dict(l=70, r=40, t=78, b=72),
        hovermode=hovermode or "x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="center", x=0.5),
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", color=C["ink"]),
        height=450,
    )
    return fig


# ── Panel builders (each returns a go.Figure) ────────────────────────────────

def panel_heatmap() -> go.Figure:
    mat = data.prices_hourly_matrix()
    dates = [d for d in mat.index]
    fig = go.Figure(go.Heatmap(
        z=mat.values, x=[f"{h:02d}" for h in mat.columns], y=dates,
        colorscale="RdBu_r", zmid=0,
        colorbar=dict(title="€/MWh", thickness=14),
        hovertemplate="Date %{y}<br>Hour %{x}<br>%{z:.1f} €/MWh<extra></extra>",
    ))
    fig.update_xaxes(title_text="Hour of day")
    return _style(fig, "Price Heatmap — Day × Hour",
                  "Diverging scale centred at €0: deep blue = negative prices (renewable gluts)",
                  hovermode="closest")


def panel_duration_curve() -> go.Figure:
    prices = np.sort(data.prices_hourly_matrix().values.flatten())[::-1]
    prices = prices[~np.isnan(prices)]
    pct = np.linspace(0, 100, len(prices))
    median = float(np.median(prices))
    neg_share = float((prices < 0).mean() * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pct, y=prices, mode="lines", line=dict(color=C["primary"], width=2.5),
        fill="tozeroy", fillcolor="rgba(31,119,180,0.12)", name="Price",
        hovertemplate="%{x:.0f}% of hours ≥ %{y:.1f} €/MWh<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=C["neutral"], dash="dot"))
    fig.add_hline(y=median, line=dict(color=C["accent"], dash="dash"),
                  annotation_text=f"median €{median:.0f}", annotation_position="top right")
    fig.add_annotation(x=92, y=prices.min() * 0.6 if prices.min() < 0 else 10,
                       text=f"{neg_share:.1f}% of hours < €0", showarrow=False,
                       font=dict(color=C["loss"], size=13))
    fig.update_xaxes(title_text="% of hours (sorted, highest → lowest)")
    fig.update_yaxes(title_text="Price (€/MWh)")
    return _style(fig, "Price-Duration Curve",
                  "How often prices are high vs negative — the shape that sizes flexible assets")


def panel_model_vs_actual() -> go.Figure:
    df = data.load_summary().sort_values("date")
    mae = float((df["model_mcp"] - df["entsoe_avg_price"]).abs().mean())
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["entsoe_max"], mode="lines",
                             line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["entsoe_min"], mode="lines",
                             line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(31,119,180,0.10)", name="Daily min–max",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["entsoe_avg_price"], mode="lines+markers",
                             line=dict(color=C["primary"], width=2.4), name="ENTSO-E avg",
                             hovertemplate="%{y:.1f} €/MWh<extra>ENTSO-E</extra>"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["model_mcp"], mode="lines+markers",
                             line=dict(color=C["accent"], width=2.2, dash="dash"),
                             name="PCR model MCP",
                             hovertemplate="%{y:.1f} €/MWh<extra>Model</extra>"))
    fig.update_yaxes(title_text="Price (€/MWh)")
    return _style(fig, "PCR Model vs Market",
                  f"Daily clearing price: model vs ENTSO-E · MAE €{mae:.1f}/MWh over {len(df)} days")


def panel_welfare() -> go.Figure:
    df = data.load_summary().sort_values("date")
    welfare_m = df["social_welfare"] / 1e6
    fig = go.Figure(go.Bar(
        x=df["date"], y=welfare_m, marker_color=C["primary"],
        hovertemplate="%{x|%d %b}<br>€%{y:.2f} M<extra>Social welfare</extra>"))
    fig.add_hline(y=float(welfare_m.mean()), line=dict(color=C["accent"], dash="dash"),
                  annotation_text=f"mean €{welfare_m.mean():.2f} M", annotation_position="top left")
    fig.update_yaxes(title_text="Social welfare (€ millions)")
    return _style(fig, "Social Welfare Cleared per Day",
                  "Objective the PCR auction maximises — total surplus from each daily clearing")


def _most_volatile_day() -> tuple[str, list[float]]:
    mat = data.prices_hourly_matrix()
    spread = (mat.max(axis=1) - mat.min(axis=1))
    day = spread.idxmax()
    return str(day), [float(v) for v in mat.loc[day].to_numpy()]


def panel_bess() -> go.Figure:
    day, prices = _most_volatile_day()
    res = solve_storage(prices=prices, capacity=100.0, max_power=25.0,
                        eff_in=0.95, eff_out=0.95, initial_soc=0.0)
    sched = res.get("schedule", [])
    hours = list(range(len(sched)))
    charge = [-s["charge"] for s in sched]      # draw charging below zero
    discharge = [s["discharge"] for s in sched]
    soc = [s["soc"] for s in sched]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=hours, y=discharge, name="Discharge (MW)", marker_color=C["gain"],
                         hovertemplate="H%{x}: +%{y:.1f} MW<extra>discharge</extra>"),
                  secondary_y=False)
    fig.add_trace(go.Bar(x=hours, y=charge, name="Charge (MW)", marker_color=C["loss"],
                         hovertemplate="H%{x}: %{y:.1f} MW<extra>charge</extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=hours, y=soc, name="State of charge (MWh)", mode="lines+markers",
                             line=dict(color=C["ink"], width=2),
                             hovertemplate="H%{x}: SoC %{y:.1f} MWh<extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=hours, y=prices, name="Price (€/MWh)", mode="lines",
                             line=dict(color=C["accent"], width=2, dash="dot"),
                             hovertemplate="H%{x}: €%{y:.1f}/MWh<extra>price</extra>"),
                  secondary_y=True)
    fig.update_layout(barmode="relative", hovermode="x unified")
    fig.update_xaxes(title_text="Hour of day", tickmode="linear", dtick=2)
    fig.update_yaxes(title_text="Power (MW) / SoC (MWh)", secondary_y=False)
    fig.update_yaxes(title_text="Price (€/MWh)", secondary_y=True, showgrid=False)
    return _style(fig, "BESS Dispatch — Optimised on the Most Volatile Day",
                  f"{day} · 100 MWh / 25 MW battery · revenue €{res.get('revenue', 0):,.0f} · "
                  f"{res.get('total_cycles', 0):.2f} cycles — charges into cheap hours, discharges into peaks")


def _hod_pnl_table() -> pd.DataFrame:
    df = data.load_hourly()
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date
    df = df.groupby(["date", "hour"], as_index=False)["close"].mean()
    hourly_avg = df.groupby("hour")["close"].mean()
    long_h = set(hourly_avg.nsmallest(6).index)
    short_h = set(hourly_avg.nlargest(6).index)
    bucket: dict[int, list[float]] = {h: [] for h in range(24)}
    for _, d in df.groupby("date"):
        s = d.set_index("hour")["close"]
        cheap = np.nanmean([float(s.get(h, np.nan)) for h in long_h])
        dear = np.nanmean([float(s.get(h, np.nan)) for h in short_h])
        for h in range(24):
            if h not in s.index:
                continue
            p = float(s[h])
            if h in long_h:
                bucket[h].append(dear - p)
            elif h in short_h:
                bucket[h].append(p - cheap)
    rows = [{"hour": h, "mean": float(np.mean(v)), "win": sum(x > 0 for x in v) / len(v) * 100}
            for h, v in bucket.items() if v]
    return pd.DataFrame(rows).sort_values("hour")


def panel_hod_pnl() -> go.Figure:
    t = _hod_pnl_table()
    colors = [C["gain"] if v > 0 else C["loss"] for v in t["mean"]]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=t["hour"], y=t["mean"], marker_color=colors, name="Mean P&L",
                         hovertemplate="H%{x}: €%{y:.1f}/MWh<extra>mean P&L</extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=t["hour"], y=t["win"], mode="lines+markers", name="Win rate",
                             line=dict(color=C["ink"], width=2),
                             hovertemplate="H%{x}: %{y:.0f}%<extra>win rate</extra>"),
                  secondary_y=True)
    fig.add_hline(y=50, line=dict(color=C["neutral"], dash="dash"), secondary_y=True)
    fig.update_xaxes(title_text="Hour of day", tickmode="linear", dtick=2)
    fig.update_yaxes(title_text="Mean daily P&L (€/MWh)", secondary_y=False)
    fig.update_yaxes(title_text="Win rate (%)", secondary_y=True, range=[0, 105], showgrid=False)
    return _style(fig, "Hour-of-Day Strategy",
                  "Long cheapest hours, short most expensive — mean P&L and win rate by hour "
                  "(in-sample; see backtest caveats)")


def panel_adequacy() -> go.Figure:
    """Build the Adequacy panel: ENS duration curve from Monte-Carlo simulation."""
    units = data.load_adequacy_units()
    load = data.load_load_8760()
    vre = data.load_vre_8760()
    res = run_monte_carlo(
        AdequacyInputs(
            units["capacity_mw"].to_numpy(float),
            units["for"].to_numpy(float),
            load["load_mw"].to_numpy(float),
            (vre["wind_mw"] + vre["solar_mw"]).to_numpy(float),
        ),
        n_years=30,
        seed=42,
    )
    ens_dc = duration_curve(res.ens_by_hour_mean)
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=ens_dc, fill="tozeroy", name="expected ENS (MWh)"))
    fig = _style(
        fig,
        "Adequacy — Security of Supply",
        f"LOLE {res.lole_h:.1f} h/yr · EENS {res.eens_mwh:.0f} MWh/yr · Monte-Carlo (synthetic)",
    )
    fig.update_layout(xaxis_title="hours (sorted)", yaxis_title="expected ENS (MWh)")
    return fig


def adequacy_panel_html() -> str:
    """Return a self-contained HTML fragment for the Adequacy dashboard section."""
    fig = panel_adequacy()
    frag = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": True, "responsive": True},
    )
    return f"<div class='card'><section id=\"adequacy\"><h2>Adequacy</h2>{frag}</section></div>"


# ── KPIs + assembly ──────────────────────────────────────────────────────────

def _kpis() -> list[tuple[str, str]]:
    summary = data.load_summary()
    mat = data.prices_hourly_matrix()
    flat = mat.values.flatten()
    neg = float((flat < 0).mean() * 100)
    mae = float((summary["model_mcp"] - summary["entsoe_avg_price"]).abs().mean())
    _, prices = _most_volatile_day()
    rev = solve_storage(prices, 100.0, 25.0, 0.95, 0.95, 0.0).get("revenue", 0.0)
    return [
        (f"{len(summary)}", "days of market data"),
        (f"€{summary['entsoe_avg_price'].mean():.1f}", "avg day-ahead €/MWh"),
        (f"{neg:.1f}%", "hours priced &lt; €0"),
        (f"€{mae:.1f}", "model MAE €/MWh"),
        (f"€{summary['social_welfare'].sum() / 1e6:.0f}M", "total social welfare"),
        (f"€{rev:,.0f}", "BESS day revenue"),
    ]


_HTML_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Energy Algorithms — Market Dashboard</title>
<style>
  :root {{ --ink:{ink}; --accent:{accent}; --neutral:{neutral}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:Inter,"Segoe UI",system-ui,sans-serif; color:var(--ink);
         background:#f4f6fa; }}
  header {{ background:linear-gradient(120deg,{ink} 0%,#2c4a7a 100%); color:#fff;
           padding:34px 28px 26px; }}
  header h1 {{ margin:0 0 6px; font-size:26px; letter-spacing:-0.3px; }}
  header p {{ margin:0; opacity:.85; font-size:15px; max-width:880px; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:22px 16px 60px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
          gap:14px; margin:-44px 16px 26px; }}
  .kpi {{ background:#fff; border-radius:12px; padding:16px 18px;
         box-shadow:0 4px 16px rgba(20,40,80,.08); }}
  .kpi .v {{ font-size:26px; font-weight:700; color:var(--ink); }}
  .kpi .l {{ font-size:12.5px; color:var(--neutral); margin-top:3px; }}
  .card {{ background:#fff; border-radius:14px; padding:8px 10px 4px; margin:18px 0;
          box-shadow:0 4px 18px rgba(20,40,80,.07); }}
  footer {{ text-align:center; color:var(--neutral); font-size:12.5px; padding:18px; }}
  a {{ color:var(--accent); }}
</style></head><body>
<header>
  <h1>Energy Algorithms — Market Dashboard</h1>
  <p>Interactive view of Belgian day-ahead market data, PCR market-clearing model output, and an
     optimised battery dispatch. Hover any chart for detail. Reproducible from the committed sample
     dataset via <code>scripts/generate_dashboard.py</code>.</p>
</header>
<div class="kpis">{kpi_cards}</div>
<div class="wrap">
"""

_HTML_FOOT = """</div>
<footer>Generated by scripts/generate_dashboard.py · data: ENTSO-E Belgian day-ahead cache (sample)
· part of the energy-algorithms portfolio</footer>
</body></html>
"""


def build_dashboard(output_path: str = OUTPUT) -> str:
    """Build all panels and write a single standalone HTML file. Returns the path."""
    panels = [
        panel_heatmap(), panel_duration_curve(),
        panel_model_vs_actual(), panel_welfare(),
        panel_bess(), panel_hod_pnl(),
    ]
    kpi_cards = "".join(
        f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{lbl}</div></div>"
        for v, lbl in _kpis()
    )
    parts = [_HTML_HEAD.format(ink=C["ink"], accent=C["accent"], neutral=C["neutral"],
                               kpi_cards=kpi_cards)]
    for i, fig in enumerate(panels):
        parts.append("<div class='card'>")
        parts.append(fig.to_html(full_html=False,
                                 include_plotlyjs="cdn" if i == 0 else False,
                                 config={"displayModeBar": True, "responsive": True}))
        parts.append("</div>")
    parts.append(adequacy_panel_html())
    parts.append(_HTML_FOOT)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return output_path


if __name__ == "__main__":
    path = build_dashboard()
    print(f"✅ dashboard written to {path} ({os.path.getsize(path):,} bytes)")
