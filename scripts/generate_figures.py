#!/usr/bin/env python3
"""Generate the 4 static benchmark figures for the Energy Algorithms README.

Figures (cohesive theme via ``_viz_theme``, reproducible data via ``_viz_data``):
  Fig 1 — Hourly price profiles (mean, ±1σ, p10–p90) across the Belgian dataset
  Fig 2 — Daily price trends: ENTSO-E avg vs PCR model MCP, with volatility band
  Fig 3 — Hour-of-day strategy P&L (mean ± std, cumulative) and win rate
  Fig 4 — Carbon impact: fuel marginal cost vs CO₂ price + coal→gas switching point

Saves PNGs to docs/ relative to the project root.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
# Sibling helpers in this scripts/ dir (auto-added to sys.path when run directly).
import _viz_data as data  # noqa: E402
import _viz_theme as theme  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

theme.apply_theme()
P = theme.PALETTE


def _save(fig, name: str) -> None:
    theme.source_note(fig)
    fig.savefig(os.path.join(DOCS_DIR, name), bbox_inches="tight")
    plt.close(fig)
    print(f"✅ {name}")


# ── Fig 1: Hourly price profiles ─────────────────────────────────────────────

def fig1_price_profiles() -> None:
    """Each day as a faint line; mean profile with ±1σ and p10–p90 bands."""
    mat = data.prices_hourly_matrix()           # rows = date, cols = hour 0..23
    hours = mat.columns.to_numpy()

    fig, ax = plt.subplots()
    for _, row in mat.iterrows():
        ax.plot(hours, row.to_numpy(), color=P["muted"], alpha=0.18, lw=0.7)

    mean = mat.mean(axis=0).to_numpy()
    std = mat.std(axis=0).to_numpy()
    p10 = mat.quantile(0.10, axis=0).to_numpy()
    p90 = mat.quantile(0.90, axis=0).to_numpy()

    ax.fill_between(hours, p10, p90, color=P["primary"], alpha=0.12, label="p10–p90")
    ax.fill_between(hours, mean - std, mean + std, color=P["accent"], alpha=0.16, label="±1σ")
    ax.plot(hours, mean, color=P["accent"], lw=2.6, label="Mean profile")

    peak_h = int(np.argmax(mean))
    trough_h = int(np.argmin(mean))
    for h, label, dy in [(peak_h, "evening peak", 12), (trough_h, "midday trough", -16)]:
        ax.annotate(f"{label}\nH{h} · €{mean[h]:.0f}", xy=(h, mean[h]),
                    xytext=(h, mean[h] + dy), ha="center", fontsize=8.5, color=P["ink"],
                    arrowprops=dict(arrowstyle="->", color=P["neutral"], lw=0.8))

    ax.axhline(0, color=P["neutral"], lw=0.8, ls=":")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Price (€/MWh)")
    ax.set_xticks(range(0, 24, 3))
    theme.title_block(ax, "Hourly Price Profiles — Belgian Day-Ahead",
                      f"{mat.shape[0]} days · spread €{mean[peak_h] - mean[trough_h]:.0f}/MWh "
                      "peak-to-trough · faint lines = individual days")
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "fig1_price_profiles.png")


# ── Fig 2: Daily price trends vs model MCP ───────────────────────────────────

def fig2_daily_prices() -> None:
    """Daily ENTSO-E avg vs PCR model MCP, with daily min–max band."""
    df = data.load_summary().sort_values("date")

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.fill_between(df["date"], df["entsoe_min"], df["entsoe_max"],
                    color=P["primary"], alpha=0.12, label="Daily range (min–max)")
    ax.plot(df["date"], df["entsoe_avg_price"], "o-", color=P["primary"], lw=1.9,
            markersize=4, label="ENTSO-E avg price")
    ax.plot(df["date"], df["model_mcp"], "s--", color=P["accent"], lw=1.6,
            markersize=4, label="PCR model MCP")

    overall = df["entsoe_avg_price"].mean()
    ax.axhline(overall, color=P["neutral"], ls=":", lw=1,
               label=f"Overall mean €{overall:.1f}/MWh")

    # Annotate the day of maximum |model − actual| divergence.
    diff = (df["model_mcp"] - df["entsoe_avg_price"]).abs()
    i = diff.idxmax()
    ax.annotate("max model–actual\ndivergence",
                xy=(df.loc[i, "date"], df.loc[i, "model_mcp"]),
                xytext=(df.loc[i, "date"], df.loc[i, "model_mcp"] - 35),
                ha="center", fontsize=8.5, color=P["ink"],
                arrowprops=dict(arrowstyle="->", color=P["neutral"], lw=0.8))

    mae = (df["model_mcp"] - df["entsoe_avg_price"]).abs().mean()
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (€/MWh)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    theme.title_block(ax, "Daily Price Trends — Model vs Market",
                      f"PCR model MCP vs ENTSO-E day-ahead · MAE €{mae:.1f}/MWh over {len(df)} days")
    ax.legend(loc="upper left", ncol=2)
    fig.tight_layout()
    _save(fig, "fig2_daily_prices.png")


# ── Fig 3: Hour-of-day strategy P&L ──────────────────────────────────────────

def fig3_hod_pnl() -> None:
    """Long the cheapest hours, short the most expensive; P&L + win rate by hour."""
    df = data.load_hourly()
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date
    df = df.groupby(["date", "hour"], as_index=False)["close"].mean()

    hourly_avg = df.groupby("hour")["close"].mean()
    long_hours = sorted(hourly_avg.nsmallest(6).index.tolist())
    short_hours = sorted(hourly_avg.nlargest(6).index.tolist())

    hourly_pnl: dict[int, list[float]] = {h: [] for h in range(24)}
    for _, day_df in df.groupby("date"):
        day = day_df.set_index("hour")["close"]
        cheap_avg = np.nanmean([float(day.get(h, np.nan)) for h in long_hours])
        dear_avg = np.nanmean([float(day.get(h, np.nan)) for h in short_hours])
        for hour in range(24):
            if hour not in day.index:
                continue
            price = float(day[hour])
            if hour in long_hours:
                hourly_pnl[hour].append(dear_avg - price)
            elif hour in short_hours:
                hourly_pnl[hour].append(price - cheap_avg)

    rows = []
    for hour, pnls in hourly_pnl.items():
        if pnls:
            rows.append({
                "hour": hour, "mean": float(np.mean(pnls)), "std": float(np.std(pnls)),
                "win": sum(p > 0 for p in pnls) / len(pnls) * 100,
            })
    rows.sort(key=lambda r: r["hour"])
    hrs = [r["hour"] for r in rows]
    mean = np.array([r["mean"] for r in rows])
    std = np.array([r["std"] for r in rows])
    win = np.array([r["win"] for r in rows])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    colors = [P["gain"] if v > 0 else P["loss"] for v in mean]
    ax1.bar(hrs, mean, color=colors, alpha=0.8, width=0.7, edgecolor="white", linewidth=0.5)
    ax1.errorbar(hrs, mean, yerr=std, fmt="none", ecolor=P["neutral"], capsize=3, alpha=0.6)
    ax1.axhline(0, color=P["ink"], lw=0.6)

    ax1c = ax1.twinx()
    ax1c.plot(hrs, np.cumsum(mean), color=P["ink"], lw=1.6, marker=".", label="Cumulative Σ")
    ax1c.set_ylabel("Cumulative Σ P&L (€/MWh)", color=P["ink"])
    ax1c.grid(False)
    ax1.set_ylabel("Mean daily P&L (€/MWh)")
    theme.title_block(
        ax1, "Hour-of-Day Strategy — P&L by Hour",
        f"Long H{long_hours[0]}–{long_hours[-1]} · Short H{short_hours[0]}–{short_hours[-1]} · "
        f"Σ €{mean.sum():+.1f}/MWh · avg win {win.mean():.0f}%")

    wr_colors = [P["gain"] if v >= 50 else P["loss"] for v in win]
    ax2.bar(hrs, win, color=wr_colors, alpha=0.8, width=0.7, edgecolor="white", linewidth=0.5)
    ax2.axhline(50, color=P["ink"], ls="--", lw=0.7, alpha=0.6)
    ax2.set_xlabel("Hour of day")
    ax2.set_ylabel("Win rate (%)")
    ax2.set_xticks(range(0, 24))
    ax2.set_ylim(0, 105)
    fig.tight_layout()
    _save(fig, "fig3_hod_pnl.png")


# ── Fig 4: CO₂ impact ────────────────────────────────────────────────────────

def fig4_co2_impact() -> None:
    """Fuel marginal cost vs CO₂ price, with the coal→gas switching point."""
    ets = np.arange(0, 141, 10)

    # Illustrative typical values (EU thermal fleet).
    em_factor = {"Gas": 0.40, "Coal": 0.95, "Oil": 0.76, "Lignite": 1.10}
    # Coal/lignite have cheaper *fuel* than gas but emit more — so CO₂ flips merit order.
    base_cost = {"Gas": 50.0, "Coal": 30.0, "Oil": 120.0, "Lignite": 18.0}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.6))
    colors_fuel = {"Gas": P["accent"], "Coal": "#444444", "Oil": "#8e44ad", "Lignite": "#8B4513"}
    markers = {"Gas": "o", "Coal": "s", "Oil": "^", "Lignite": "d"}

    for fuel in ["Gas", "Coal", "Oil", "Lignite"]:
        cost = base_cost[fuel] + ets * em_factor[fuel]
        ax1.plot(ets, cost, color=colors_fuel[fuel], marker=markers[fuel], markevery=3,
                 lw=2, label=f"{fuel} ({em_factor[fuel]:.2f} t/MWh)")

    # Coal→gas switching CO₂ price: base_g + e·ef_g = base_c + e·ef_c.
    e_switch = (base_cost["Coal"] - base_cost["Gas"]) / (em_factor["Gas"] - em_factor["Coal"])
    if 0 <= e_switch <= ets.max():
        c_switch = base_cost["Gas"] + e_switch * em_factor["Gas"]
        ax1.axvline(e_switch, color=P["gain"], ls="--", lw=1.2, alpha=0.8)
        ax1.scatter([e_switch], [c_switch], color=P["gain"], zorder=5, s=45)
        ax1.annotate(f"coal→gas switch\n€{e_switch:.0f}/t CO₂",
                     xy=(e_switch, c_switch), xytext=(e_switch + 14, c_switch + 18),
                     fontsize=9, color=P["gain"],
                     arrowprops=dict(arrowstyle="->", color=P["gain"], lw=0.9))

    current_ets = 70
    ax1.axvline(current_ets, color=P["neutral"], ls=":", lw=1, alpha=0.8,
                label=f"~current ETS €{current_ets}/t")
    ax1.set_xlabel("CO₂ price (€/ton)")
    ax1.set_ylabel("Marginal cost (€/MWh)")
    theme.title_block(ax1, "Fuel Marginal Cost vs CO₂ Price",
                      "Steeper slope = dirtier fuel; lines cross where merit order flips")
    ax1.legend(loc="upper left", fontsize=9)

    x = np.arange(len(em_factor))
    fuels = list(em_factor.keys())
    for i, e in enumerate([30, 70, 100]):
        adders = [(e * em_factor[f] / base_cost[f]) * 100 for f in fuels]
        bars = ax2.bar(x + (i - 1) * 0.25, adders, 0.25, alpha=0.8,
                       label=f"€{e}/t", edgecolor="white", linewidth=0.5,
                       color=[P["primary"], P["accent"], P["loss"]][i])
        for bar, val in zip(bars, adders):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                     f"{val:.0f}%", ha="center", va="bottom", fontsize=7.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{f}\n{em_factor[f]} t/MWh" for f in fuels])
    ax2.set_ylabel("CO₂ adder (% of base fuel cost)")
    theme.title_block(ax2, "CO₂ Cost Pass-Through by Fuel", "Carbon as a share of base cost")
    ax2.legend(loc="upper left", fontsize=9)

    fig.suptitle("Carbon Impact Analysis — CO₂ Cost Pass-Through",
                 fontsize=14, fontweight="bold", color=P["ink"], y=1.02)
    fig.tight_layout()
    _save(fig, "fig4_co2_impact.png")


if __name__ == "__main__":
    print("Generating benchmark figures...\n")
    fig1_price_profiles()
    fig2_daily_prices()
    fig3_hod_pnl()
    fig4_co2_impact()
    print(f"\nAll 4 figures saved to {DOCS_DIR}/")
