"""Portfolio experiments — joint BESS/reserve stacking + strategy head-to-head.

Each experiment is a standalone CLI plus a trackable run in the
SQLite-backed experiment tracker.

Quick start
-----------
    python experiments/runner.py exp1           # revenue stack
    python experiments/runner.py exp2           # strategy head-to-head
    python experiments/runner.py all            # both

Or run each directly:
    python experiments/joint_reserve_revenue_stack.py --out experiments/output
    python experiments/strategy_head_to_head.py    --out experiments/output

Inspect the results:
    ea-experiments list --name exp1
    ea-experiments list --name exp2
    ea-experiments compare <run_id_1> <run_id_2> ...
"""
