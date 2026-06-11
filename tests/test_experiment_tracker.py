"""Tests for the experiment tracker module."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from energy_algorithms.infrastructure.experiment_tracker import (
 ExperimentTracker,
 get_tracker,
)


@pytest.fixture
def tracker() -> ExperimentTracker:
 """Return a tracker backed by a temp file."""
 _, path = tempfile.mkstemp(suffix=".db")
 yield ExperimentTracker(path)
 try:
 os.unlink(path)
 except OSError:
 pass


# ── Basic run lifecycle ────────────────────────────────────────────


def test_run_created_and_completed(tracker: ExperimentTracker) -> None:
 with tracker.run(name="test_run") as run:
 assert run.run_id is not None
 assert len(run.run_id) == 12

 runs = tracker.list_runs()
 assert len(runs) == 1
 assert runs[0]["name"] == "test_run"
 assert runs[0]["status"] == "completed"


def test_run_status_failed_on_exception(tracker: ExperimentTracker) -> None:
 with pytest.raises(ValueError, match="boom"):
 with tracker.run(name="fail_run"):
 raise ValueError("boom")

 runs = tracker.list_runs()
 assert runs[0]["status"] == "failed"


# ── Parameters ──────────────────────────────────────────────────────


def test_log_param(tracker: ExperimentTracker) -> None:
 with tracker.run(name="param_test") as run:
 run.log_param("solver", "CBC")
 run.log_param("ram_factor", 0.85)
 run.log_param("zone_count", 3)

 details = tracker.get_run(run.run_id)
 assert details is not None
 assert details["params"]["solver"] == "CBC"
 assert details["params"]["ram_factor"] == 0.85
 assert details["params"]["zone_count"] == 3


# ── Metrics ─────────────────────────────────────────────────────────


def test_log_metric(tracker: ExperimentTracker) -> None:
 with tracker.run(name="metric_test") as run:
 run.log_metric("social_welfare", 471234.56)
 run.log_metric("solve_time", 1.23, step=1)

 details = tracker.get_run(run.run_id)
 assert details is not None
 assert any(m["key"] == "social_welfare" and m["value"] == 471234.56 for m in details["metrics"])
 assert any(m["key"] == "solve_time" and m["value"] == 1.23 for m in details["metrics"])


# ── Artifacts ───────────────────────────────────────────────────────


def test_log_artifact(tracker: ExperimentTracker) -> None:
 with tracker.run(name="artifact_test") as run:
 run.log_artifact("plots/output.png", "Price curve", kind="plot")

 details = tracker.get_run(run.run_id)
 assert details is not None
 assert any(a["path"] == "plots/output.png" and a["description"] == "Price curve" for a in details["artifacts"])


# ── List / Filter ───────────────────────────────────────────────────


def test_list_runs_filtered(tracker: ExperimentTracker) -> None:
 with tracker.run(name="alpha"):
 pass
 with tracker.run(name="beta"):
 pass
 with tracker.run(name="gamma"):
 pass

 all_runs = tracker.list_runs(limit=10)
 assert len(all_runs) == 3

 alpha_runs = tracker.list_runs(name="alpha")
 assert len(alpha_runs) == 1
 assert alpha_runs[0]["name"] == "alpha"


# ── Compare ─────────────────────────────────────────────────────────


def test_compare_runs(tracker: ExperimentTracker) -> None:
 with tracker.run(name="run_a") as run_a:
 run_a.log_param("x", 1)
 run_a.log_metric("y", 10.0)

 with tracker.run(name="run_b") as run_b:
 run_b.log_param("x", 2)
 run_b.log_metric("y", 20.0)

 comparison = tracker.compare_runs([run_a.run_id, run_b.run_id])
 assert len(comparison["metadata"]) == 2
 assert comparison["params"][0]["x"] == 1
 assert comparison["params"][1]["x"] == 2


# ── Export ──────────────────────────────────────────────────────────


def test_export_json(tracker: ExperimentTracker) -> None:
 with tracker.run(name="export_me") as run:
 run.log_param("p", 42)
 run.log_metric("m", 3.14)

 exported = tracker.export_json(limit=10)
 data = json.loads(exported)
 assert len(data) >= 1
 assert data[0]["name"] == "export_me"
 assert data[0]["params"]["p"] == 42


# ── set_status ──────────────────────────────────────────────────────


def test_set_status_override(tracker: ExperimentTracker) -> None:
 with tracker.run(name="status_test") as run:
 run.set_status("interrupted")

 details = tracker.get_run(run.run_id)
 assert details is not None
 assert details["status"] == "interrupted"


# ── get_tracker singleton ───────────────────────────────────────────


def test_get_tracker_singleton() -> None:
 t1 = get_tracker()
 t2 = get_tracker()
 assert t1 is t2
