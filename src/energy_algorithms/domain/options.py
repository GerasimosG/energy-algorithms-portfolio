"""
Centralised options dictionary for LP/MIP optimisation settings.

Provides a global key-value store with sensible defaults for solver
configuration, tolerances, verbosity, and time limits so that all
optimisation modules share the same tuning parameters without each
module needing its own argument handling.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sensible defaults
# ---------------------------------------------------------------------------

_DEFAULT_OPTIONS: dict[str, Any] = {
    # --- Solver ---
    "solver": "cbc",
    "solver_msg": False,
    "time_limit": None,        # seconds; None = no limit
    "threads": None,           # None = solver default
    "mip_gap": 0.0001,          # relative MIP optimality gap
    # --- Tolerances ---
    "feasibility_tol": 1e-6,
    "optimality_tol": 1e-6,
    "integrality_tol": 1e-5,
    # --- Verbosity ---
    "verbose": False,
    # --- Hooks ---
    "run_hooks": True,          # whether to invoke registered hooks
    "hook_events": ["pre_solve", "post_solve", "post_extract"],
    # --- Reporting ---
    "report_format": "dict",
    # --- Solver-specific kwargs (forwarded opaquely) ---
    "solver_kwargs": {},
}

# The *active* options — deep-copied from defaults so callers can't
# accidentally mutate the template.
_OPTIONS: dict[str, Any] = copy.deepcopy(_DEFAULT_OPTIONS)


def _check_key(key: str, allow_unknown: bool = False) -> None:
    """Raise KeyError with a helpful message if *key* is unknown."""
    if key not in _DEFAULT_OPTIONS:
        if allow_unknown:
            return
        known = ", ".join(sorted(_DEFAULT_OPTIONS.keys()))
        raise KeyError(
            f"Unknown option '{key}'. Known options: {known}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_option(key: str, default: Any = None) -> Any:
    """
    Retrieve the current value of an option.

    Parameters
    ----------
    key : str
        Option name (e.g. ``"solver"``, ``"verbose"``, ``"time_limit"``).
    default : any, optional
        Value to return if *key* has never been set.  Defaults to
        ``None``, which may differ from the built-in default.

    Returns
    -------
    any
        Current value of the option, or *default* if not found.

    Raises
    ------
    KeyError
        If *key* is not a recognised option and *default* is not
        explicitly provided.
    """
    _check_key(key, allow_unknown=default is not None)
    return _OPTIONS.get(key, default)


def set_option(key: str, value: Any) -> None:
    """
    Set an option to *value*.

    Parameters
    ----------
    key : str
        Option name.
    value : any
        New value.  No type-checking is performed — it is the
        caller's responsibility to supply a sensible value.

    Raises
    ------
    KeyError
        If *key* is not a recognised option.
    """
    _check_key(key)
    _OPTIONS[key] = value
    logger.debug("Option '%s' set to %r", key, value)


def reset_options() -> None:
    """
    Reset every option back to its factory default.

    The active dictionary is replaced with a fresh deep-copy of the
    default values.  All prior changes are discarded.
    """
    global _OPTIONS  # noqa: PLW0603
    _OPTIONS = copy.deepcopy(_DEFAULT_OPTIONS)
    logger.debug("Options reset to defaults.")


def get_options_dict() -> dict[str, Any]:
    """
    Return a shallow copy of the entire active options dictionary.

    Returns
    -------
    dict
        The current options.  Mutating the returned dict will **not**
        affect the internal store.
    """
    return dict(_OPTIONS)
