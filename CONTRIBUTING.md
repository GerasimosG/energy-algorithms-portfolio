# Contributing to Energy Algorithms

Thank you for your interest in contributing! This project is a public portfolio demonstrating optimization modeling, energy market domain knowledge (PCR/Euphemia), and algorithmic trading in a hexagonal architecture.

## Table of Contents

- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Pull Request Template](#pull-request-template)

## How to Contribute

1. **Issues first** — Open an issue describing the bug, feature, or improvement before writing code. This avoids duplicated effort and allows discussion.

2. **Fork the repository** — Create your own fork, then clone locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Energy_Algorithms.git
   cd Energy_Algorithms
   ```

3. **Create a branch** — Use a descriptive branch name:
   ```bash
   git checkout -b feat/my-feature     # new feature
   git checkout -b fix/my-bug-fix      # bug fix
   git checkout -b docs/my-doc-update  # documentation
   ```

4. **Make your changes** — Follow the code style and testing guidelines below.

5. **Run tests** — Ensure all tests pass (`pytest`).

6. **Submit a pull request** — Target the `main` branch. Reference the issue number in your PR description.

## Development Setup

### Prerequisites

- [Miniforge](https://github.com/conda-forge/miniforge) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (recommended)
- Git

### Install (Conda — Primary)

```bash
# Clone the repository
git clone https://github.com/GerasimosG/Energy_Algorithms.git
cd Energy_Algorithms

# Create the conda environment (all deps included)
conda env create -f environment.yml

# Activate it
conda activate energy-algorithms

# Install the package in editable mode (for entry-point scripts)
pip install -e ".[live]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Install (Pip — Fallback)

```bash
# Clone the repository
git clone https://github.com/GerasimosG/Energy_Algorithms.git
cd Energy_Algorithms

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### What Gets Installed
- Runtime dependencies: `numpy`, `scipy`, `pandas`, `matplotlib`, `pulp`, `yfinance`
- Dev dependencies: `pytest`, `pytest-cov`, `hypothesis`, `ruff`
- The package itself in editable mode so your changes take effect immediately

### Optional Extras

```bash
pip install -e ".[live]"   # ENTSO-E live data (requests)
pip install -e ".[docs]"   # Sphinx documentation
```

### Verify

```bash
python -c "import energy_algorithms; print('OK')"
pytest -q
```

## Code Style

This project uses **ruff** for linting and formatting. The configuration is in `pyproject.toml`.

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format
ruff format .
```

### Rules

- **`src` layout only** — All package code lives under `src/energy_algorithms/`. No `sys.path` hacks.
- **`from __future__ import annotations`** — First line of every `.py` file.
- **Type hints on all functions** — Parameters and return values. Use `X | None` not `Optional[X]`. Use standard library generics (`list[X]` not `List[X]`).
- **Absolute imports only** — `from energy_algorithms.domain.markets import ...` — no relative imports.
- **NumPy-style docstrings** — `Parameters` / `Returns` / `Raises` sections on every public function.
- **`__all__`** — Exported in every `__init__.py` (names only, no docstrings).
- **No magic numbers** — Named constants: `ACCEPTANCE_TOLERANCE = 0.001`.
- **No bare `except:`** — Always catch specific exceptions. Use `except Exception` if you must.
- **Line length** — 100 characters maximum (enforced by ruff).
- **Import order** — stdlib → third-party → first-party (enforced by ruff isort).

### Architecture Rules

This project follows a **hexagonal (ports/adapters) architecture**:

| Layer | Location | Rules |
|-------|----------|-------|
| Domain | `src/energy_algorithms/domain/` | Pure business logic. No I/O, no solver imports. stdlib + numpy + scipy + pulp only. |
| Ports | `src/energy_algorithms/ports/` | Abstract interfaces (ABCs, Protocols). Zero dependencies beyond stdlib + typing. |
| Adapters | `src/energy_algorithms/adapters/` | Concrete implementations of ports. May do I/O. |
| Application | `src/energy_algorithms/application/` | Use-case orchestrators. Wires domain + adapters. |
| Infrastructure | `src/energy_algorithms/infrastructure/` | Backward-compat re-exports. New code imports from `domain/` directly. |

**Domain code never imports adapters or application layers.**

## Testing

All tests use **pytest**.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=energy_algorithms

# Run specific test file
pytest tests/test_pcr_model.py

# Run tests matching a keyword
pytest -k "storage"

# Run slow tests (may take >5s each)
pytest -m slow

# Run test file with verbose output
pytest -v tests/test_integration.py
```

### Test conventions

- One test file per module, mirroring `src/` layout
- Tests are independent — no shared state, no ordering dependencies
- Seeds for reproducibility in stochastic tests
- Known-optimal tests with expected output values (not just "solves without error")
- Edge cases documented in `AGENTS.md` must have corresponding tests

### Writing tests

```python
"""Tests for my_feature module."""
from __future__ import annotations

import pytest


def test_basic_functionality():
    """Describe what this test verifies."""
    result = my_function(input_data)
    assert result == expected_output


@pytest.mark.slow
def test_expensive_operation():
    """Mark slow tests with @pytest.mark.slow."""
    ...
```

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

[optional body with details]
```

### Types

| Type     | Usage                                      |
|----------|--------------------------------------------|
| `feat:`  | New feature                                |
| `fix:`   | Bug fix                                    |
| `refactor:` | Code change without feature/bug change |
| `docs:`  | Documentation only                        |
| `test:`  | Adding or improving tests                  |
| `chore:` | Build, CI, dependencies, tooling           |
| `style:` | Formatting, imports, lint fixes            |

### Examples

```
feat: add multi-day coupling with storage carry-over
fix: correct MCP calculation for exclusive block orders
refactor: extract solve chain into reusable pipeline
docs: add architecture diagram to README
test: add known-optimal tests for battery lifecycle
chore: update ruff config to py311 target
style: apply ruff auto-fixes across all files
```

## Pull Request Process

1. **Before submitting:** Run `ruff check --fix .` and `pytest -q` to verify clean state.
2. **Target branch:** Always target `main`.
3. **Description:** Reference the related issue and describe what changed and why.
4. **Size:** Keep PRs focused. One feature/fix per PR. Large changes should be split.
5. **Review:** At least one approval required before merging.
6. **Squash merge:** PRs are squash-merged to keep history clean.

## Pull Request Template

```markdown
## Description
Brief description of the change and why it's needed.

Closes #ISSUE_NUMBER

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactor
- [ ] Test improvement
- [ ] Build/CI

## How Has This Been Tested?
- [ ] `pytest -q` passes
- [ ] `ruff check .` passes
- [ ] Manual testing (describe)

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass
- [ ] Type hints and docstrings are complete
- [ ] `__all__` is updated in `__init__.py` if needed
- [ ] Architecture layering rules are respected
```
