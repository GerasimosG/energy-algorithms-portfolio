.PHONY: install install-pip test test-fast lint lint-fix typecheck clean docker-build

# ── Primary: Conda ──────────────────────────────────────────────────────────

install:
	conda env create -f environment.yml || conda env update -f environment.yml
	conda activate energy-algorithms
	pip install -e ".[live]"  # for ENTSO-E live pipeline
	pre-commit install 2>/dev/null || true

update:
	conda env update -f environment.yml

activate:
	@echo "conda activate energy-algorithms"

# ── Fallback: pip ───────────────────────────────────────────────────────────

install-pip:
	pip install -e ".[dev]"

install-pip-all:
	pip install -e ".[dev,live,docs]"

# ── Common tasks ────────────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

test-fast:
	pytest tests/ -v -m "not slow and not pc"

lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

typecheck:
	mypy src/energy_algorithms/

clean:
	rm -rf .pytest_cache .mypy_cache __pycache__ */__pycache__

docker-build:
	docker build -t energy-algorithms .
