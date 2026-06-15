"""
Physical invariant validation for LP optimisation results.

Post-solve checks that verify physical laws and operational limits
are respected by the solution.  These are *assertions* — they detect
bugs in problem formulation rather than runtime errors.  Run them
after every solve as part of a test or production guard.

All validators return ``True`` on success, ``False`` on failure.
The ``assert_invariants`` helper raises ``AssertionError`` with a
descriptive message when any check fails.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

# ── Individual validators ────────────────────────────────────────────────────

def validate_energy_balance(
    supply: list[float],
    demand: list[float],
    losses: list[float] | None = None,
    tolerance: float = 0.01,
) -> bool:
    """Check that supply equals demand plus losses in every interval.

    Energy balance:  ``supply[i] ≈ demand[i] + losses[i]``

    Parameters
    ----------
    supply : list[float]
        Total power supplied in each interval (MW).
    demand : list[float]
        Total power consumed in each interval (MW).
    losses : list[float] or None
        Losses (waste heat, efficiency gap) per interval.  If None,
        losses are treated as zero.
    tolerance : float
        Absolute tolerance for floating-point comparison.

    Returns
    -------
    bool
        True if ``|supply[i] - demand[i] - losses[i]| ≤ tolerance``
        for every interval.

    Raises
    ------
    ValueError
        If ``supply``, ``demand``, and ``losses`` have different lengths.
    """
    n = len(supply)
    if len(demand) != n:
        raise ValueError(
            f"supply length {n} != demand length {len(demand)}"
        )
    if losses is None:
        losses = [0.0] * n
    elif len(losses) != n:
        raise ValueError(
            f"supply length {n} != losses length {len(losses)}"
        )

    for i in range(n):
        net = supply[i] - demand[i] - losses[i]
        if abs(net) > tolerance:
            return False
    return True


def validate_soc_bounds(
    soc_values: list[float],
    capacity: float,
    tolerance: float = 0.01,
) -> bool:
    """Check that state-of-charge stays within [0, capacity].

    Parameters
    ----------
    soc_values : list[float]
        State of charge at each interval (MWh).
    capacity : float
        Maximum energy capacity (MWh).
    tolerance : float
        Absolute tolerance for floating-point comparison.

    Returns
    -------
    bool
        True if every SoC satisfies ``-tolerance ≤ soc ≤ capacity + tolerance``.
    """
    for soc in soc_values:
        if soc <= -tolerance or soc >= capacity + tolerance:
            return False
    return True


def validate_power_limits(
    power_values: list[float],
    max_power: float,
    tolerance: float = 0.01,
) -> bool:
    """Check that power stays within [0, max_power].

    Parameters
    ----------
    power_values : list[float]
        Power output at each interval (MW).
    max_power : float
        Maximum rated power (MW).
    tolerance : float
        Absolute tolerance for floating-point comparison.

    Returns
    -------
    bool
        True if every power satisfies ``-tolerance ≤ p ≤ max_power + tolerance``.
    """
    for p in power_values:
        if p <= -tolerance or p >= max_power + tolerance:
            return False
    return True


# ── Invariant assertion helper ───────────────────────────────────────────────

def assert_invariants(
    result: dict,
    checks: Sequence[Callable[[dict], bool] | tuple[Callable[[dict], bool], str]],
) -> None:
    """Run a battery of invariant checks, raising on first failure(s).

    Each check is a callable that receives the ``result`` dict and
    returns ``True`` if the invariant holds.  Optionally, a check may
    be a ``(callable, name)`` tuple for better error messages.

    **All checks are executed** even if some fail, so you see every
    violation at once.

    Parameters
    ----------
    result : dict
        The result dictionary produced by a solution function
        (must include at minimum a ``'status'`` key).
    checks : list of callable or tuple
        Invariants to verify.  Each element is either ``callable`` or
        ``(callable, str)``.

    Raises
    ------
    AssertionError
        If any check returns False.  The message lists each failing
        check by name or string representation.
    """
    failures: list[str] = []

    for i, item in enumerate(checks):
        if isinstance(item, tuple):
            check_fn, name = item
        else:
            check_fn, name = item, f"check_{i}"

        try:
            ok = check_fn(result)
        except Exception as exc:
            failures.append(f"{name} raised {type(exc).__name__}: {exc}")
            continue

        if not ok:
            # Try to show a meaningful representation of the check
            try:
                label = getattr(check_fn, "__name__", None) or str(check_fn)
            except Exception:
                label = "<check>"
            failures.append(f"{name}: {label}")

    if failures:
        raise AssertionError(
            f"Invariant checks failed ({len(failures)}/{len(checks)}):\n  "
            + "\n  ".join(failures)
        )
