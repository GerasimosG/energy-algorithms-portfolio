#!/usr/bin/env bash
# Update FRAMEWORK.md metrics — run before each commit
# Recomputes: module counts, test counts, benchmark solve times
# Usage: ./scripts/update_framework_metrics.sh
# Or as pre-commit hook: ln -s ../../scripts/update_framework_metrics.sh .git/hooks/pre-commit

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
if [ -z "${PYTHON_BIN:-}" ]; then
    PYTHON_BIN=$(command -v python || command -v python3)
fi

echo "=== Energy_Algorithms Framework Metrics Update ==="

# 1. Count modules (directories with __init__.py in the src layout)
MODULES=$(find src/energy_algorithms -name '__init__.py' -not -path '*__pycache__*' | wc -l)
echo "  Modules: $MODULES"

# 2. Count source files (non-test, non-cache .py files)
SRC_FILES=$(find src/energy_algorithms -name '*.py' -not -path '*__pycache__*' | wc -l)
echo "  Source files: $SRC_FILES"

# 3. Count lines of source code
SRC_LINES=$(find src/energy_algorithms -name '*.py' -not -path '*__pycache__*' -exec cat {} + | wc -l)
echo "  Source lines: $SRC_LINES"

# 4. Count collected tests without running them. Disable coverage addopts so this
# stays lightweight on memory-constrained laptops.
TESTS=$("$PYTHON_BIN" -m pytest --collect-only -q tests/ --no-cov 2>&1 | grep -oE '[0-9]+ tests collected' | tail -1 | awk '{print $1}')
TESTS=${TESTS:-?}
echo "  Tests: $TESTS"

# 5. Update FRAMEWORK.md header
sed -i "s/^\*\*Modules:\*\*.*/**Modules:** $MODULES  |  **Tests:** $TESTS  |  **Solvers:** PuLP\\/CBC + scipy SLSQP/" FRAMEWORK.md
sed -i "s/^\*\*Generated:\*\*.*/**Generated:** \`$(date '+%Y-%m-%d %H:%M %Z')\`  /" FRAMEWORK.md

# 6. Run benchmarks (if not in CI or forced)
if [ "${CI:-}" != "true" ] && [ "${1:-}" != "--skip-benchmarks" ]; then
    echo "  Running benchmarks (5 iterations each)..."
    "$PYTHON_BIN" -c "
import time, json
cases = {
    'PCR simple clearing': lambda: __import__('energy_algorithms.domain.markets.market_clearing',
        fromlist=['demo_clearing']).demo_clearing(),
    'BESS 24 periods': lambda: __import__('energy_algorithms.domain.optimization.storage',
        fromlist=['demo_storage']).demo_storage(),
}
results = {}
for name, fn in cases.items():
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    results[name] = {
        'avg': round(sum(times)/len(times), 1),
        'min': round(min(times), 1),
        'max': round(max(times), 1),
    }
    print(f'    {name}: {results[name][\"avg\"]}ms avg')
with open('.framework_benchmarks.json', 'w') as f:
    json.dump(results, f, indent=2)
" 2>&1 || echo "  (benchmarks skipped — run from repo root)"
fi

echo "=== Update complete ==="
echo "  Modules: $MODULES | Source: $SRC_FILES files, $SRC_LINES lines | Tests: $TESTS"
echo "  Commit now: git add -A && git commit -m \"...\""
