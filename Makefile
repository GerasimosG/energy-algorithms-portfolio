.PHONY: install test test-fast lint lint-fix typecheck clean docker-build

install:
	pip install -e ".[dev]"

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
