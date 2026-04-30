"""
Solver-agnostic configuration for LP/MIP optimization problems.

Provides a unified interface to discover available solvers, retrieve
configured solver objects, and introspect solver capabilities — all
with graceful fallback when a preferred solver is not installed.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import pulp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known solver identifiers → import / factory helpers
# ---------------------------------------------------------------------------

# Map solver names to (module, class) tuples for PuLP solver classes.
# Some solvers require a separate package; we document that here.
_SOLVER_REGISTRY: dict[str, dict[str, Any]] = {
    "cbc": {
        "cls": pulp.PULP_CBC_CMD,
        "description": "COIN-OR Branch & Cut (default, bundled with PuLP)",
    },
    "highs": {
        "cls": None,  # resolved lazily below
        "description": "HiGHS — open-source MIP/QP/barrier solver",
    },
    "gurobi": {
        "cls": None,
        "description": "Gurobi Optimizer (commercial licence required)",
    },
    "cplex": {
        "cls": None,
        "description": "IBM CPLEX Optimizer (commercial licence required)",
    },
    "glpk": {
        "cls": None,
        "description": "GLPK — GNU Linear Programming Kit",
    },
}

# Lazily-resolved optional solvers


def _try_import_highs():
    """Attempt to import the HiGHS solver class from PuLP."""
    try:
        return pulp.HiGHS_CMD  # type: ignore[attr-defined]
    except AttributeError:
        pass
    try:
        return pulp.HIGHS  # type: ignore[attr-defined]
    except AttributeError:
        pass
    # Fallback: try importing highspy directly and constructing
    try:
        import highspy  # noqa: F401  # type: ignore[import-untyped]

        return pulp.HiGHS_CMD  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        return None


def _try_import_gurobi():
    """Attempt to import the Gurobi solver class from PuLP."""
    try:
        return pulp.GUROBI  # type: ignore[attr-defined]
    except AttributeError:
        try:
            return pulp.GUROBI_CMD  # type: ignore[attr-defined]
        except AttributeError:
            return None


def _try_import_cplex():
    """Attempt to import the CPLEX solver class from PuLP."""
    try:
        return pulp.CPLEX_PY  # type: ignore[attr-defined]
    except AttributeError:
        try:
            return pulp.CPLEX_CMD  # type: ignore[attr-defined]
        except AttributeError:
            return None


def _try_import_glpk():
    """Attempt to import the GLPK solver class from PuLP."""
    try:
        return pulp.GLPK_CMD  # type: ignore[attr-defined]
    except AttributeError:
        return None


# Resolve optional solvers on module load
_RESOLVED: dict[str, Any] = {}
for _name, _resolver in [  # noqa: F811
    ("highs", _try_import_highs),
    ("gurobi", _try_import_gurobi),
    ("cplex", _try_import_cplex),
    ("glpk", _try_import_glpk),
]:
    cls = _resolver()
    if cls is not None:
        _RESOLVED[_name] = cls

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_solver(name: str = "cbc", **kwargs: Any) -> Any:
    """
    Return a PuLP solver object for *name*, with graceful fallback.

    Parameters
    ----------
    name : str
        Solver identifier.  Supported values: ``"cbc"`` (default),
        ``"highs"``, ``"gurobi"``, ``"cplex"``, ``"glpk"``.
    **kwargs
        Keyword arguments forwarded to the solver constructor
        (e.g. ``msg=False``, ``timeLimit=60``, ``threads=4``).

    Returns
    -------
    pulp.apis.LpSolver
        An instantiated PuLP solver object ready to be passed to
        ``prob.solve()``.

    Raises
    ------
    ValueError
        If *name* is not a recognised solver string.
    RuntimeError
        If *name* is recognised but not installed and fallback also fails.

    Notes
    -----
    When the requested solver is not available the function warns and
    falls back to CBC.  If even CBC is unavailable a RuntimeError is raised.
    """
    name = name.lower().strip()

    if name not in _SOLVER_REGISTRY:
        raise ValueError(
            f"Unknown solver '{name}'. "
            f"Available: {list_available_solvers()}"
        )

    # --- Direct CBC path (always available with PuLP) ---
    if name == "cbc":
        return pulp.PULP_CBC_CMD(**kwargs)

    # --- Check if the requested solver is installed ---
    if name in _RESOLVED:
        cls = _RESOLVED[name]
        return cls(**kwargs)

    # --- Warn and fall back to CBC ---
    msg = (
        f"Solver '{name}' is not installed. "
        f"Falling back to CBC (Coin-OR Branch & Cut)."
    )
    warnings.warn(msg, stacklevel=2)
    logger.warning(msg)

    # Default CBC kwargs that make sense regardless of original intent
    fallback_kwargs: dict[str, Any] = {
        k: v for k, v in kwargs.items()
        if k not in ("msg", "timeLimit", "threads", "gapRel")
    }
    return pulp.PULP_CBC_CMD(**fallback_kwargs)


def list_available_solvers() -> list[str]:
    """
    Return the list of solver names that are currently installed
    and usable from PuLP.

    Returns
    -------
    list of str
        Sorted list of installed solver identifiers.  CBC is always
        included because it ships with PuLP.
    """
    installed = ["cbc"]
    installed.extend(sorted(_RESOLVED.keys()))
    return installed


def solver_capabilities(name: str) -> dict[str, bool]:
    """
    Return a dictionary describing the capabilities of solver *name*.

    Parameters
    ----------
    name : str
        Solver identifier (e.g. ``"cbc"``, ``"highs"``).

    Returns
    -------
    dict
        Keys are capability strings (``"mip"``, ``"lp"``, ``"qp"``,
        ``"barrier"``, ``"sos"``, ``"installed"``) mapping to booleans.

    Notes
    -----
    Capability detection is based on known solver features and does
    not dynamically query the solver binary.  For authoritative
    answers consult solver documentation.
    """
    name = name.lower().strip()
    installed = name in list_available_solvers()

    capabilities: dict[str, dict[str, bool]] = {
        "cbc": {
            "lp": True,
            "mip": True,
            "qp": False,
            "barrier": False,
            "sos": True,
        },
        "highs": {
            "lp": True,
            "mip": True,
            "qp": True,
            "barrier": True,
            "sos": True,
        },
        "gurobi": {
            "lp": True,
            "mip": True,
            "qp": True,
            "barrier": True,
            "sos": True,
        },
        "cplex": {
            "lp": True,
            "mip": True,
            "qp": True,
            "barrier": True,
            "sos": True,
        },
        "glpk": {
            "lp": True,
            "mip": True,
            "qp": False,
            "barrier": False,
            "sos": False,
        },
    }

    caps = capabilities.get(name, capabilities["cbc"]).copy()
    caps["installed"] = installed
    return caps
