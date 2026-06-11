#!/usr/bin/env python3
"""
Portfolio Benchmark -- runnable Energy Algorithms benchmark.

Demonstrates solve times, solution quality, and solver capabilities
across all major modules. Runs on any hardware (Pi or PC).

Usage:
    python scripts/run_benchmark.py          # quick run
    python scripts/run_benchmark.py --full   # more benchmarks
"""

import argparse
import time
from dataclasses import dataclass, field

import numpy as np

from energy_algorithms.infrastructure.solver_config import list_available_solvers


@dataclass
class BenchmarkResult:
    name: str
    elapsed_ms: float
    status: str = "OK"
    details: str = ""
    tags: list[str] = field(default_factory=list)


def report(results: list[BenchmarkResult]):
    available = list_available_solvers()
    total = sum(r.elapsed_ms for r in results)
    passed = sum(1 for r in results if r.status == "OK")
    width = 60

    print(f"\n{'='*width}")
    print("  Energy Algorithms -- Benchmark Report")
    print(f"{'='*width}")
    print(f"  Solvers: {', '.join(available)}")
    print(f"{'='*width}")
    print(f"  {'Benchmark':<35} {'Time (ms)':<12} {'Status':<8}")
    print(f"  {'-'*35} {'-'*12} {'-'*8}")
    for r in results:
        tag_str = f" [{','.join(r.tags)}]" if r.tags else ""
        print(f"  {r.name:<35} {r.elapsed_ms:<12.1f} {r.status:<8}{tag_str}")
        if r.details:
            for line in r.details.split("\n"):
                print(f"    -> {line}")
    print(f"  {'-'*35} {'-'*12} {'-'*8}")
    print(f"  {'TOTAL':<35} {total:<12.1f}")
    print(f"  {'PASSED':<35} {passed}/{len(results)}")
    print(f"{'='*width}")
    print(f"  HiGHS: {'yes' if 'highs' in available else 'no'}")
    print(f"{'='*width}\n")


def bench(name: str, tags: list[str], fn, *args, **kwargs) -> BenchmarkResult:
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        t1 = time.perf_counter()
        status = "OK"
        details = str(result)[:200] if isinstance(result, str) else ""
        return BenchmarkResult(name, (t1 - t0) * 1000, status, details, tags)
    except Exception as e:
        t1 = time.perf_counter()
        return BenchmarkResult(name, (t1 - t0) * 1000, f"FAIL: {e}", "", tags)


def run_quick_benchmarks() -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    np.random.seed(42)

    # 1. Solver detection
    t0 = time.perf_counter()
    solvers = list_available_solvers()
    t1 = time.perf_counter()
    results.append(BenchmarkResult(
        "solver_detection", (t1 - t0) * 1000,
        details=f"Found: {', '.join(solvers)}",
        tags=["infrastructure"],
    ))

    # 2. PCR market clearing
    from energy_algorithms.domain.markets.pcr_model import PCRModel
    t0 = time.perf_counter()
    m = PCRModel(area="BE")
    m.add_supply("wind", 5, 500)
    m.add_supply("gas", 60, 400)
    m.add_supply("coal", 40, 300)
    m.add_demand("industry", 90, 600)
    m.add_demand("residential", 120, 400)
    r = m.solve()
    t1 = time.perf_counter()
    price = r.get("mcp", "?")
    welfare = r.get("welfare", 0)
    results.append(BenchmarkResult(
        "pcr_clearing_1zone", (t1 - t0) * 1000,
        details=f"Price: {price} | Welfare: {welfare:,.0f}" if isinstance(welfare, (int, float)) else f"Price: {price}",
        tags=["markets", "lp"],
    ))

    # 3. FBMC 3-zone
    from energy_algorithms.domain.markets.fbmc import solve_fbmc
    zones = [
        {"name": "BE", "supply": [{"price": 10, "qty": 300}, {"price": 50, "qty": 200}], "demand": [{"price": 80, "qty": 400}]},
        {"name": "FR", "supply": [{"price": 15, "qty": 400}, {"price": 55, "qty": 150}], "demand": [{"price": 70, "qty": 350}]},
        {"name": "DE", "supply": [{"price": 20, "qty": 500}, {"price": 45, "qty": 250}], "demand": [{"price": 75, "qty": 500}]},
    ]
    ptdf = np.array([[0.3, -0.2, -0.1], [0.1, 0.4, -0.5], [-0.2, 0.3, -0.1]])
    ram = [{"name": f"L{i}", "ram_forward": 200, "ram_reverse": 200} for i in range(3)]
    t0 = time.perf_counter()
    r = solve_fbmc(zones, ptdf, ram, ["BE", "FR", "DE"])
    t1 = time.perf_counter()
    welfare = r.get("welfare") or r.get("total_welfare", 0)
    results.append(BenchmarkResult(
        "fbmc_3zone", (t1 - t0) * 1000,
        details=f"Welfare: {welfare:,.0f} | Status: {r.get('status', '?')}",
        tags=["markets", "fbmc"],
    ))

    # 4. Block orders (linked + exclusive)
    t0 = time.perf_counter()
    m = PCRModel(area="IT")
    m.add_supply("hydro", 10, 400)
    m.add_supply("gas", 70, 300)
    m.add_demand("base", 100, 500)
    m.add_block("hydro_1", 15, 200, group="linked")
    m.add_block("hydro_2", 15, 150, group="linked")
    m.add_block("gas_peak", 65, 100, group="excl_config")
    m.add_block("oil_peak", 80, 120, group="excl_config")
    r = m.solve()
    t1 = time.perf_counter()
    results.append(BenchmarkResult(
        "block_orders_linked_exclusive", (t1 - t0) * 1000,
        details=f"Status: {r.get('status', '?')} | Price: {r.get('mcp', '?')}",
        tags=["markets", "mip"],
    ))

    # 5. Demo unit commitment
    from energy_algorithms.domain.optimization.scheduling import demo_uc
    t0 = time.perf_counter()
    r = demo_uc()
    t1 = time.perf_counter()
    cost = r.get("total_cost", 0) or r.get("objective", 0)
    results.append(BenchmarkResult(
        "unit_commitment_demo", (t1 - t0) * 1000,
        details=f"Cost: {cost:,.0f} | Status: {r.get('status', '?')}",
        tags=["optimization", "mip"],
    ))

    # 6. Demo site (BESS + generators)
    from energy_algorithms.domain.optimization.assets import demo_site
    t0 = time.perf_counter()
    r = demo_site()
    t1 = time.perf_counter()
    revenue = r.get("revenue", r.get("total_revenue", 0))
    results.append(BenchmarkResult(
        "storage_site_demo", (t1 - t0) * 1000,
        details=f"Revenue: {revenue:,.2f}" if isinstance(revenue, (int, float)) else f"Status: {r.get('status', '?')}",
        tags=["optimization", "lp"],
    ))

    # 7. Multi-zone ATC
    from energy_algorithms.domain.markets.multi_zone import solve_multi_zone
    zone_data = [
        {"name": "BE", "supply": [{"price": 10, "qty": 500}, {"price": 60, "qty": 200}], "demand": [{"price": 90, "qty": 400}]},
        {"name": "NL", "supply": [{"price": 25, "qty": 300}, {"price": 70, "qty": 150}], "demand": [{"price": 85, "qty": 300}]},
    ]
    t0 = time.perf_counter()
    r = solve_multi_zone(zone_data, {("BE", "NL"): 200})
    t1 = time.perf_counter()
    welfare = r.get("welfare", 0)
    results.append(BenchmarkResult(
        "multi_zone_atc_2zone", (t1 - t0) * 1000,
        details=f"Welfare: {welfare:,.0f}" if isinstance(welfare, (int, float)) else f"Status: {r.get('status', '?')}",
        tags=["markets", "lp"],
    ))

    return results


def main():
    parser = argparse.ArgumentParser(description="Run Energy Algorithms benchmarks")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    results = run_quick_benchmarks()

    if args.full:
        from energy_algorithms.domain.optimization.stochastic import solve_scenario_uc
        t0 = time.perf_counter()
        r = solve_scenario_uc(n_gen=5, n_hours=12, n_scenarios=3)
        t1 = time.perf_counter()
        cost = r.get("total_cost", 0)
        results.append(BenchmarkResult(
            "stochastic_uc_5x12x3", (t1 - t0) * 1000,
            details=f"Cost: {cost:,.0f} Status: {r.get('status', '?')}",
            tags=["optimization", "stochastic"],
        ))

    report(results)


if __name__ == "__main__":
    main()
