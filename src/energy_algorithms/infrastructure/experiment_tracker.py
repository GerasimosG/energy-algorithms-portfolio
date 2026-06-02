"""Lightweight ML experiment tracker — SQLite-backed, zero-dependency.

Tracks experiment runs, parameters, metrics, and artifacts for optimization
and backtesting experiments. No servers, no API keys — just a local SQLite DB.

Usage:
    tracker = ExperimentTracker()
    with tracker.run(name="fbmc_sensitivity", description="RAM reduction") as run:
        run.log_param("ram_factor", 0.8)
        run.log_metric("social_welfare", 471234.56)
        run.log_artifact("plots/output.png", "Price curve")
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ExperimentTracker:
    """Persistent experiment tracker backed by SQLite.

    Each ``run()`` context manager creates a new run entry with a UUID,
    timestamps, and the given name/description. Parameters, metrics, and
    artifacts are logged inside the context.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".hermes" / "experiments.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    # ── public API ──────────────────────────────────────────────────

    @contextmanager
    def run(
        self,
        name: str,
        description: str = "",
        tags: str = "",
    ) -> Generator[ExperimentRun, None, None]:
        """Context manager: creates a run, yields it, marks it completed.

        ``name`` is a human-readable experiment name (e.g. "fbmc_sweep").
        ``description`` is optional free text.
        ``tags`` is a comma-separated list for filtering.

        If the context raises, the run is marked ``"failed"`` and the
        exception propagates.
        """
        run_id = uuid.uuid4().hex[:12]
        created = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO runs (run_id, name, description, tags, status, created) "
            "VALUES (?, ?, ?, ?, 'running', ?)",
            (run_id, name, description, tags, created),
        )
        self._conn.commit()
        er = ExperimentRun(run_id, self._conn)
        try:
            yield er
        except BaseException:
            er.set_status("failed")
            raise
        else:
            if er._status_override:
                # set_status() was called manually — respect it
                self._conn.execute(
                    "UPDATE runs SET finished=? WHERE run_id=?",
                    (datetime.now(UTC).isoformat(), run_id),
                )
            else:
                self._conn.execute(
                    "UPDATE runs SET status='completed', finished=? WHERE run_id=?",
                    (datetime.now(UTC).isoformat(), run_id),
                )
            self._conn.commit()

    def list_runs(
        self,
        status: str | None = None,
        name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return recent runs, optionally filtered by status or name."""
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if name:
            clauses.append("name LIKE ?")
            params.append(f"%{name}%")
        where = " AND ".join(clauses) if clauses else "1"
        rows = self._conn.execute(
            f"SELECT run_id, name, description, tags, status, created, finished "
            f"FROM runs WHERE {where} ORDER BY created DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [
            {
                "run_id": r[0],
                "name": r[1],
                "description": r[2],
                "tags": r[3],
                "status": r[4],
                "created": r[5],
                "finished": r[6],
            }
            for r in rows
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Return a single run with its params, metrics, and artifacts."""
        run_row = self._conn.execute(
            "SELECT run_id, name, description, tags, status, created, finished "
            "FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None:
            return None
        params = self._conn.execute(
            "SELECT key, value FROM params WHERE run_id = ?", (run_id,)
        ).fetchall()
        metrics = self._conn.execute(
            "SELECT key, value, step FROM metrics WHERE run_id = ? ORDER BY step",
            (run_id,),
        ).fetchall()
        artifacts = self._conn.execute(
            "SELECT path, description, kind FROM artifacts WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return {
            "run_id": run_row[0],
            "name": run_row[1],
            "description": run_row[2],
            "tags": run_row[3],
            "status": run_row[4],
            "created": run_row[5],
            "finished": run_row[6],
            "params": {p[0]: json.loads(p[1]) for p in params},
            "metrics": [
                {"key": m[0], "value": json.loads(m[1]), "step": m[2]}
                for m in metrics
            ],
            "artifacts": [
                {"path": a[0], "description": a[1], "kind": a[2]} for a in artifacts
            ],
        }

    def compare_runs(
        self, run_ids: list[str]
    ) -> dict[str, Any]:
        """Side-by-side comparison of multiple runs.

        Returns dict with ``"params"``, ``"metrics"``, and ``"metadata"``
        keys, each a list of per-run dicts.
        """
        runs = [self.get_run(rid) for rid in run_ids]
        return {
            "metadata": [
                {"run_id": r["run_id"], "name": r["name"], "status": r["status"]}
                for r in runs
                if r
            ],
            "params": [r["params"] if r else {} for r in runs],
            "metrics": [r["metrics"] if r else [] for r in runs],
        }

    def export_json(self, limit: int = 50) -> str:
        """Export runs as a JSON string for external analysis."""
        runs = self.list_runs(limit=limit)
        full = [self.get_run(r["run_id"]) for r in runs]
        return json.dumps([f for f in full if f], indent=2, default=str)

    # ── internals ───────────────────────────────────────────────────

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id    TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags      TEXT DEFAULT '',
                status    TEXT NOT NULL DEFAULT 'running',
                created   TEXT NOT NULL,
                finished  TEXT
            );
            CREATE TABLE IF NOT EXISTS params (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                key    TEXT NOT NULL,
                value  TEXT NOT NULL,
                PRIMARY KEY (run_id, key)
            );
            CREATE TABLE IF NOT EXISTS metrics (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                key    TEXT NOT NULL,
                value  TEXT NOT NULL,
                step   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (run_id, key, step)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                run_id      TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                path        TEXT NOT NULL,
                description TEXT DEFAULT '',
                kind        TEXT DEFAULT 'file'
            );
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_runs_name ON runs(name);
        """)
        self._conn.commit()


class ExperimentRun:
    """Proxy object for a single run, yielded by ``ExperimentTracker.run()``."""

    def __init__(self, run_id: str, conn: sqlite3.Connection) -> None:
        self._run_id = run_id
        self._conn = conn
        self._status_override = False

    @property
    def run_id(self) -> str:
        return self._run_id

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter (e.g. solver name, ram_factor, zone count)."""
        self._conn.execute(
            "INSERT OR REPLACE INTO params (run_id, key, value) VALUES (?, ?, ?)",
            (self._run_id, key, json.dumps(value)),
        )
        self._conn.commit()

    def log_metric(self, key: str, value: float, step: int = 0) -> None:
        """Log a scalar metric (e.g. social welfare, solve time, Sharpe)."""
        self._conn.execute(
            "INSERT INTO metrics (run_id, key, value, step) VALUES (?, ?, ?, ?)",
            (self._run_id, key, json.dumps(value), step),
        )
        self._conn.commit()

    def log_artifact(
        self, path: str, description: str = "", kind: str = "file"
    ) -> None:
        """Log an artifact file path (plot, model, CSV export, etc.)."""
        self._conn.execute(
            "INSERT INTO artifacts (run_id, path, description, kind) "
            "VALUES (?, ?, ?, ?)",
            (self._run_id, path, description, kind),
        )
        self._conn.commit()

    def set_status(self, status: str) -> None:
        """Manually override run status (e.g. 'failed', 'interrupted')."""
        self._status_override = True
        self._conn.execute(
            "UPDATE runs SET status=?, finished=? WHERE run_id=?",
            (status, datetime.now(UTC).isoformat(), self._run_id),
        )
        self._conn.commit()


# ── convenience: single-instance ───────────────────────────────────

_DEFAULT_TRACKER: ExperimentTracker | None = None


def get_tracker(db_path: str | Path | None = None) -> ExperimentTracker:
    """Return the module-level default tracker (lazy init)."""
    global _DEFAULT_TRACKER
    if _DEFAULT_TRACKER is None:
        _DEFAULT_TRACKER = ExperimentTracker(db_path)
    return _DEFAULT_TRACKER
