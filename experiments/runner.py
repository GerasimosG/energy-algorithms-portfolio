"""
Run all experiments in sequence.

Usage
-----
 python experiments/runner.py exp1
 python experiments/runner.py exp2
 python experiments/runner.py all
 python experiments/runner.py all --out experiments/output --db /tmp/my_experiments.db

The runner exists so a single command reproduces all tracked experiments.
The outputs land in the SQLite tracker (default ``~/.hermes/experiments.db``)
plus optional CSV/JSON dumps to ``--out``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def run_exp1(out_dir: Path | None, db: Path | None) -> int:
 from experiments.joint_reserve_revenue_stack import run_experiment
 results = run_experiment(out_dir=out_dir, tracker_db=db)
 return 0 if results else 1


def run_exp2(out_dir: Path | None, db: Path | None) -> int:
 from experiments.strategy_head_to_head import run_experiment
 results = run_experiment(out_dir=out_dir, tracker_db=db)
 return 0 if results else 1


def main() -> int:
 parser = argparse.ArgumentParser(
 description="Run all (or one) portfolio experiments."
 )
 parser.add_argument(
 "which",
 choices=["exp1", "exp2", "all"],
 help="Which experiment(s) to run.",
 )
 parser.add_argument(
 "--out",
 type=Path,
 default=None,
 help="Optional output directory for CSV/JSON dumps.",
 )
 parser.add_argument(
 "--db",
 type=Path,
 default=None,
 help="Optional path to experiment tracker SQLite DB.",
 )
 args = parser.parse_args()

 print(f"Running: {args.which}")
 if args.which in ("exp1", "all"):
 rc = run_exp1(args.out, args.db)
 if rc != 0:
 return rc
 if args.which in ("exp2", "all"):
 rc = run_exp2(args.out, args.db)
 if rc != 0:
 return rc
 print()
 print("Done. Inspect with:")
 print(" ea-experiments list --name exp1")
 print(" ea-experiments list --name exp2")
 print(" ea-experiments compare <id1> <id2> ...")
 return 0


if __name__ == "__main__":
 sys.exit(main())
