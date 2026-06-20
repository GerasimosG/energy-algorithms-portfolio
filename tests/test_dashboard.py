"""Smoke tests for the interactive Plotly dashboard generator (scripts/generate_dashboard.py).

These keep the dashboard reproducible: if the sample data schema or solve_storage return shape
changes, the panel builders break here rather than silently producing an empty page.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

plotly_go = pytest.importorskip("plotly.graph_objects")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH_PATH = os.path.join(ROOT, "scripts", "generate_dashboard.py")

# The dashboard script imports its sibling _viz_* helpers from scripts/. When run directly that
# dir is auto-added to sys.path; under pytest we add it explicitly so the importlib load resolves.
sys.path.insert(0, os.path.join(ROOT, "scripts"))


@pytest.fixture(scope="module")
def dash():
    """Import scripts/generate_dashboard.py as a module."""
    spec = importlib.util.spec_from_file_location("generate_dashboard", DASH_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PANELS = [
    "panel_heatmap", "panel_duration_curve", "panel_model_vs_actual",
    "panel_welfare", "panel_bess", "panel_hod_pnl",
]


@pytest.mark.parametrize("name", PANELS)
def test_panel_returns_nonempty_figure(dash, name):
    fig = getattr(dash, name)()
    assert isinstance(fig, plotly_go.Figure)
    assert len(fig.data) > 0, f"{name} produced no traces"


def test_bess_panel_runs_real_solver(dash):
    # panel_bess calls solve_storage; a non-Optimal solve would yield no schedule traces.
    fig = dash.panel_bess()
    names = {t.name for t in fig.data}
    assert {"Discharge (MW)", "Charge (MW)", "State of charge (MWh)"} <= names


def test_build_dashboard_writes_file(dash, tmp_path):
    out = tmp_path / "dashboard.html"
    path = dash.build_dashboard(str(out))
    assert os.path.exists(path)
    content = out.read_text(encoding="utf-8")
    assert len(content) > 10_000
    assert "Energy Algorithms" in content
    assert "Plotly" in content or "plotly" in content  # CDN script embedded
