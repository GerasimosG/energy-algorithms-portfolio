"""Cohesive visual identity shared by the static figures and the Plotly dashboard.

One palette, one set of conventions, used everywhere so the portfolio's visuals read as a single
designed system rather than ad-hoc charts.
"""

from __future__ import annotations

# ── Palette ────────────────────────────────────────────────────────────────
# A restrained "energy desk" palette: deep navy structure, a warm accent for the
# model/headline series, green/red for gains/losses, slate for neutral context.
PALETTE = {
    "ink": "#1b2a4a",        # near-black navy — titles, primary lines
    "primary": "#1f77b4",    # ENTSO-E / actual series (blue)
    "accent": "#e4572e",     # model / headline series (warm orange-red)
    "gain": "#2ca02c",       # positive P&L
    "loss": "#d1495b",       # negative P&L
    "neutral": "#8d99ae",    # context lines, bands
    "muted": "#adb5bd",      # day-spaghetti lines, gridish accents
    "band": "#1f77b4",       # fill bands (uses primary at low alpha)
}

# Sequential + diverging colormaps (matplotlib names) for heat-style figures.
SEQ_CMAP = "viridis"
DIVERGING_CMAP = "RdBu_r"   # red high / blue low — centered for negative prices

# Plotly colorway (kept consistent with PALETTE order)
PLOTLY_COLORWAY = [
    PALETTE["primary"], PALETTE["accent"], PALETTE["gain"],
    PALETTE["loss"], PALETTE["neutral"], PALETTE["ink"],
]
PLOTLY_TEMPLATE = "plotly_white"

SOURCE = "Source: ENTSO-E Belgian day-ahead cache (sample) · energy-algorithms"


def apply_theme() -> None:
    """Apply the shared matplotlib rcParams. Call once before building figures."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "figure.figsize": (11, 5.5),
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": PALETTE["neutral"],
        "axes.grid": True,
        "axes.grid.axis": "both",
        "grid.color": PALETTE["muted"],
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.titlecolor": PALETTE["ink"],
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "axes.labelcolor": PALETTE["ink"],
        "font.size": 10,
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.edgecolor": PALETTE["muted"],
        "xtick.color": PALETTE["ink"],
        "ytick.color": PALETTE["ink"],
    })


def source_note(fig, text: str = SOURCE) -> None:
    """Add a small right-aligned provenance note to the bottom of a figure."""
    fig.text(0.995, 0.005, text, ha="right", va="bottom",
             fontsize=7.5, color=PALETTE["neutral"], style="italic")


def title_block(ax, title: str, subtitle: str | None = None) -> None:
    """Set a bold title with an optional lighter subtitle line below it.

    The title is padded clear of the axes and the subtitle sits just above the
    top spine, so the two never overlap.
    """
    ax.set_title(title, loc="left", pad=26 if subtitle else 8)
    if subtitle:
        ax.text(0.0, 1.0, subtitle, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9.5, color=PALETTE["neutral"])
