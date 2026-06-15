#!/usr/bin/env python3
"""Generate the 4 benchmark figures for the Energy Algorithms portfolio README.

Figures:
  Fig 1 — Hourly price profiles across the Belgian dataset
  Fig 2 — Daily price trends with volatility bands
  Fig 3 — Hour-of-day strategy profit & loss breakdown
  Fig 4 — Carbon impact analysis across trading strategies

Saves PNGs to docs/ relative to the project root.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

os.makedirs(DOCS_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "figure.figsize": (10, 5.5),
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
})


# ── Fig 1: Hourly price profiles ──────────────────────────────────────

def fig1_price_profiles():
    """Plot hourly price profiles: each day as a thin line, mean as thick."""
    df = pd.read_csv(os.path.join(DATA_DIR, "entsoe_30day_prices.csv"))
    # Map 15-min slots (hours 1-96) to hourly periods 0-23
    df["plot_hour"] = (df["hour"] - 1) // 4
    # Average 4 x 15-min slots per hour
    df_avg = df.groupby(["date", "plot_hour"], as_index=False)["price_eur_mwh"].mean()

    fig, ax = plt.subplots()
    # One line per day
    dates = sorted(df_avg["date"].unique())
    for d in dates:
        day = df_avg[df_avg["date"] == d]
        ax.plot(day["plot_hour"], day["price_eur_mwh"], color="steelblue", alpha=0.25, lw=0.7)

    # Mean profile
    mean_profile = df_avg.groupby("plot_hour")["price_eur_mwh"].mean()
    ax.plot(mean_profile.index, mean_profile.values, color="#d62728", lw=2.5, label="Mean")

    # ±1σ band
    std_profile = df_avg.groupby("plot_hour")["price_eur_mwh"].std()
    ax.fill_between(
        mean_profile.index,
        mean_profile - std_profile,
        mean_profile + std_profile,
        color="#d62728", alpha=0.10, label="±1σ"
    )

    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Price (€/MWh)")
    ax.set_title("Hourly Price Profiles — 26-Day Belgian Dataset")
    ax.set_xticks(range(0, 25, 3))
    ax.legend(loc="upper left", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS_DIR, "fig1_price_profiles.png"), bbox_inches="tight")
    plt.close(fig)
    print("✅ fig1_price_profiles.png")


# ── Fig 2: Daily price trends with volatility bands ───────────────────

def fig2_daily_prices():
    """Daily averages with min/max bands and model MCP comparison."""
    df = pd.read_csv(os.path.join(DATA_DIR, "entsoe_30day_summary.csv"))
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(12, 5.5))

    # Min-max band
    ax.fill_between(
        df["date"], df["entsoe_min"], df["entsoe_max"],
        color="steelblue", alpha=0.15, label="Daily range (min–max)"
    )

    # Average price line
    ax.plot(df["date"], df["entsoe_avg_price"], "o-", color="#1f77b4", lw=1.8,
            markersize=4, label="ENTSO-E avg price")

    # Model MCP comparison
    ax.plot(df["date"], df["model_mcp"], "s--", color="#d62728", lw=1.5,
            markersize=4, label="PCR model MCP")

    ax.axhline(df["entsoe_avg_price"].mean(), color="gray", ls=":", lw=1,
               alpha=0.6, label=f'Overall mean: €{df["entsoe_avg_price"].mean():.1f}/MWh')

    ax.set_xlabel("Date")
    ax.set_ylabel("Price (€/MWh)")
    ax.set_title("Daily Price Trends with Volatility Bands")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.legend(loc="upper left", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS_DIR, "fig2_daily_prices.png"), bbox_inches="tight")
    plt.close(fig)
    print("✅ fig2_daily_prices.png")


# ── Fig 3: Hour-of-day strategy P&L breakdown ─────────────────────────

def fig3_hod_pnl():
    """Data-driven hour-of-day P&L: long cheapest hours, short most expensive hours."""
    df = pd.read_csv(os.path.join(DATA_DIR, "bt_hourly.csv"))
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date

    # Average duplicate timestamps by (date, hour)
    df = df.groupby(["date", "hour"], as_index=False)["close"].mean()

    # Find cheapest and most expensive hours from the full dataset
    hourly_avg = df.groupby("hour")["close"].mean()
    hod_long_hours = sorted(hourly_avg.nsmallest(6).index.tolist())
    hod_short_hours = sorted(hourly_avg.nlargest(6).index.tolist())

    # P&L: long at cheap hours → sell at expensive-hr avg; short at expensive hours → cover at cheap-hr avg
    hourly_pnl: dict[int, list[float]] = {h: [] for h in range(24)}

    for date_val, day_df in df.groupby("date"):
        day_prices = day_df.set_index("hour")["close"]
        cheap_avg = np.mean([float(day_prices.get(h, np.nan)) for h in hod_long_hours])
        dear_avg = np.mean([float(day_prices.get(h, np.nan)) for h in hod_short_hours])

        for hour in range(24):
            if hour not in day_prices.index:
                continue
            price = float(day_prices[hour])

            if hour in hod_long_hours:
                pnl = dear_avg - price       # bought cheap, valued at expensive avg
            elif hour in hod_short_hours:
                pnl = price - cheap_avg       # sold expensive, would cover at cheap avg
            else:
                continue
            hourly_pnl[hour].append(pnl)

    rows = []
    for hour, pnls in hourly_pnl.items():
        if pnls:
            rows.append({
                "hour": hour,
                "mean_pnl": np.mean(pnls),
                "std_pnl": np.std(pnls),
                "total_pnl": np.sum(pnls),
                "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
            })
    pnl_df = pd.DataFrame(rows).sort_values("hour")

    long_label = f"Long H{hod_long_hours[0]}–{hod_long_hours[-1]}"
    short_label = f"Short H{hod_short_hours[0]}–{hod_short_hours[-1]}"

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    colors = ["#2ca02c" if v > 0 else "#d62728" for v in pnl_df["mean_pnl"]]
    ax1.bar(pnl_df["hour"], pnl_df["mean_pnl"], color=colors, alpha=0.75, width=0.7,
            edgecolor="white", linewidth=0.5)
    ax1.errorbar(pnl_df["hour"], pnl_df["mean_pnl"], yerr=pnl_df["std_pnl"],
                 fmt="none", ecolor="gray", capsize=3, alpha=0.5)
    ax1.axhline(0, color="black", lw=0.5)
    ax1.set_ylabel("Mean daily P&L (€/MWh)")
    ax1.set_title(f"Hour-of-Day Strategy: P&L by Hour ({long_label}, {short_label})")

    colors_wr = ["#2ca02c" if v >= 50 else "#d62728" for v in pnl_df["win_rate"]]
    ax2.bar(pnl_df["hour"], pnl_df["win_rate"], color=colors_wr, alpha=0.75, width=0.7,
            edgecolor="white", linewidth=0.5)
    ax2.axhline(50, color="black", ls="--", lw=0.7, alpha=0.5)
    ax2.set_xlabel("Hour of day")
    ax2.set_ylabel("Win rate (%)")
    ax2.set_xticks(range(0, 24))
    ax2.set_ylim(0, 105)

    total_pnl = pnl_df["total_pnl"].sum()
    avg_win_rate = pnl_df["win_rate"].mean()
    ax1.text(0.02, 0.95,
             f"Total Σ P&L: €{total_pnl:+.1f}/MWh  |  Avg win rate: {avg_win_rate:.0f}%  |  "
             f"Long H{hod_long_hours[0]}–{hod_long_hours[-1]}  Short H{hod_short_hours[0]}–{hod_short_hours[-1]}",
             transform=ax1.transAxes, fontsize=9, verticalalignment="top",
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    fig.tight_layout()
    fig.savefig(os.path.join(DOCS_DIR, "fig3_hod_pnl.png"), bbox_inches="tight")
    plt.close(fig)
    print("✅ fig3_hod_pnl.png")


# ── Fig 4: CO₂ impact analysis ────────────────────────────────────────

def fig4_co2_impact():
    """CO₂ cost pass-through: impact on marginal costs at different ETS prices."""
    # ETS price range
    ets_prices = np.arange(0, 141, 10)  # €0–140/ton CO₂

    # Emission factors (ton CO₂/MWh)
    em_factor = {
        "Gas": 0.40,     # OCGT: ~0.40 t/MWh
        "Coal": 0.82,    # Hard coal: ~0.82 t/MWh
        "Oil": 0.76,     # Oil: ~0.76 t/MWh
        "Lignite": 1.01, # Brown coal: ~1.01 t/MWh
    }

    # Base marginal costs without CO₂ (€/MWh)
    base_cost = {
        "Gas": 50.0,
        "Coal": 55.0,
        "Oil": 120.0,
        "Lignite": 10.0,
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left subplot: marginal cost vs ETS price
    colors_fuel = {"Gas": "#e67e22", "Coal": "#555555", "Oil": "#8e44ad", "Lignite": "#8B4513"}
    markers = {"Gas": "o", "Coal": "s", "Oil": "^", "Lignite": "d"}

    for fuel in ["Gas", "Coal", "Oil", "Lignite"]:
        cost = base_cost[fuel] + ets_prices * em_factor[fuel]
        ax1.plot(ets_prices, cost, color=colors_fuel[fuel], marker=markers[fuel],
                 markevery=4, lw=2, label=f"{fuel} ({em_factor[fuel]:.2f} t/MWh)")

    # Current ETS price reference
    current_ets = 70
    ax1.axvline(current_ets, color="green", ls="--", lw=1, alpha=0.7,
                label=f"Current ETS: €{current_ets}/t")

    # Annotations at current ETS
    for fuel in ["Gas", "Coal"]:
        cost_at_current = base_cost[fuel] + current_ets * em_factor[fuel]
        ax1.annotate(f"€{cost_at_current:.0f}", xy=(current_ets, cost_at_current),
                     xytext=(current_ets + 12, cost_at_current + 3),
                     fontsize=9, color=colors_fuel[fuel],
                     arrowprops=dict(arrowstyle="->", color=colors_fuel[fuel], lw=0.8))

    ax1.set_xlabel("CO₂ price (€/ton)")
    ax1.set_ylabel("Marginal cost (€/MWh)")
    ax1.set_title("Fuel Marginal Cost vs CO₂ Price")
    ax1.legend(loc="upper left", framealpha=0.9, fontsize=9)

    # Right subplot: CO₂ cost adders as % of base
    x = np.arange(len(em_factor))
    fuels_list = list(em_factor.keys())
    ets_levels = [30, 70, 100]  # Low, current, high

    bar_width = 0.25
    for i, ets in enumerate(ets_levels):
        adders = [(ets * em_factor[f] / base_cost[f]) * 100 for f in fuels_list]
        offset = (i - 1) * bar_width
        bars = ax2.bar(x + offset, adders, bar_width, alpha=0.75,
                       label=f"€{ets}/t CO₂", edgecolor="white", linewidth=0.5)
        # Value labels on bars
        for bar, val in zip(bars, adders):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     f"{val:.0f}%", ha="center", va="bottom", fontsize=8)

    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{f}\n({em_factor[f]} t/MWh)" for f in fuels_list])
    ax2.set_ylabel("CO₂ cost adder (% of base fuel cost)")
    ax2.set_title("CO₂ Cost Pass-Through by Fuel")
    ax2.legend(loc="upper left", framealpha=0.9, fontsize=9)

    fig.suptitle("Carbon Impact Analysis: CO₂ Cost Pass-Through in Energy Markets",
                 fontsize=13, y=1.01)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS_DIR, "fig4_co2_impact.png"), bbox_inches="tight")
    plt.close(fig)
    print("✅ fig4_co2_impact.png")


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating benchmark figures...\n")
    fig1_price_profiles()
    fig2_daily_prices()
    fig3_hod_pnl()
    fig4_co2_impact()
    print(f"\nAll 4 figures saved to {DOCS_DIR}/")
