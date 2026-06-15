"""CLI for querying experiment tracking data.

Usage:
    ea-experiments list [--name <pattern>] [--status <status>] [--limit N]
    ea-experiments show <run_id>
    ea-experiments compare <run_id1> <run_id2> [<run_id3> ...]
    ea-experiments export [--limit N]
"""

from __future__ import annotations

import argparse
import sys

from energy_algorithms.infrastructure.experiment_tracker import get_tracker


def main() -> None:
    parser = argparse.ArgumentParser(description="ML Experiment Tracker CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = sub.add_parser("list", help="List recent runs")
    list_parser.add_argument("--name", help="Filter by name pattern")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # show
    show_parser = sub.add_parser("show", help="Show run details")
    show_parser.add_argument("run_id", help="Run ID")

    # compare
    compare_parser = sub.add_parser("compare", help="Compare runs side-by-side")
    compare_parser.add_argument("run_ids", nargs="+", help="Run IDs (2+)")

    # export
    export_parser = sub.add_parser("export", help="Export all runs as JSON")
    export_parser.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    tracker = get_tracker()

    if args.command == "list":
        runs = tracker.list_runs(
            status=args.status, name=args.name, limit=args.limit
        )
        if not runs:
            print("No experiments found.")
            return
        print(f"{'Run ID':<16} {'Name':<30} {'Status':<12} {'Created':<28}")
        print("-" * 86)
        for r in runs:
            print(f"{r['run_id']:<16} {r['name']:<30} {r['status']:<12} {r['created']:<28}")

    elif args.command == "show":
        detail = tracker.get_run(args.run_id)
        if detail is None:
            print(f"Run {args.run_id} not found.")
            sys.exit(1)
        print(f"Run:      {detail['run_id']}")
        print(f"Name:     {detail['name']}")
        print(f"Status:   {detail['status']}")
        print(f"Created:  {detail['created']}")
        if detail["finished"]:
            print(f"Finished: {detail['finished']}")
        if detail["params"]:
            print("\nParameters:")
            for k, v in detail["params"].items():
                print(f"  {k}: {v}")
        if detail["metrics"]:
            print("\nMetrics:")
            for m in detail["metrics"]:
                print(f"  {m['key']}: {m['value']} (step {m['step']})")
        if detail["artifacts"]:
            print("\nArtifacts:")
            for a in detail["artifacts"]:
                print(f"  {a['path']} — {a['description']}")

    elif args.command == "compare":
        comparison = tracker.compare_runs(args.run_ids)
        if not comparison["metadata"]:
            print("No matching runs found.")
            return
        print("Comparison:\n")
        for i, meta in enumerate(comparison["metadata"]):
            print(f"  [{i}] {meta['name']} ({meta['run_id']}) — {meta['status']}")
        print("\nParams:")
        for i, p in enumerate(comparison["params"]):
            print(f"  [{i}]: {p}")
        print("\nMetrics:")
        for i, m in enumerate(comparison["metrics"]):
            items = [f"{x['key']}={x['value']}" for x in m]
            print(f"  [{i}]: {items}")

    elif args.command == "export":
        print(tracker.export_json(limit=args.limit))


if __name__ == "__main__":
    main()
