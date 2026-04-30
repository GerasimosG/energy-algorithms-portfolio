"""LODF impact screening utility for FBMC (Flow-Based Market Coupling).

Computes the Line Outage Distribution Factor (LODF) matrix from a zonal
PTDF matrix and screens out non-binding Critical Branch Contingency
Outages (CBCOs) to reduce the number of security constraints in the
market coupling problem.

References
----------
- ENTSO-E Flow-Based Market Coupling documentation
- Euphemia algorithm specification — CBCO filtering
"""
from __future__ import annotations


import numpy as np
from typing import Optional

__all__ = ["compute_lodf", "screen_cbcos"]


# ---------------------------------------------------------------------------
# compute_lodf
# ---------------------------------------------------------------------------

def compute_lodf(
    ptdf: np.ndarray,
    branch_zone_map: Optional[list[tuple[int, int]]] = None,
) -> np.ndarray:
    """Compute the LODF matrix from a zonal PTDF matrix.

    The LODF matrix describes how a branch outage redistributes power flow
    onto the remaining branches. For zonal PTDF, the LODF is approximated
    from the PTDF sensitivity differences between the two zones connected
    by each branch.

    Parameters
    ----------
    ptdf : np.ndarray, shape (n_branches, n_zones)
        Power Transfer Distribution Factor matrix. Each row `l` gives
        the change in flow on branch `l` for a 1 MW net injection at
        each zone (with reference slack). Rows should sum to ~0.

    branch_zone_map : list of tuple (int, int), optional
        Maps each branch index to the zones it connects: ``(from_zone,
        to_zone)``. Must have length ``n_branches``. If not provided,
        a ``ValueError`` is raised.

    Returns
    -------
    lodf : np.ndarray, shape (n_branches, n_branches)
        LODF matrix where ``LODF[l, k]`` is the fractional change in
        flow on branch ``l`` when branch ``k`` is outaged. Diagonal
        entries are -1.0 (self-outage).

    Raises
    ------
    ValueError
        If ``branch_zone_map`` is missing, length mismatches, or zone
        indices are out of range.

    Notes
    -----
    The LODF formula for zonal PTDF:

        LODF[l, k] = (PTDF[l, from_zone_k] - PTDF[l, to_zone_k])
                     -----------------------------------------------
                     1 - (PTDF[k, from_zone_k] - PTDF[k, to_zone_k])

    This is an approximation of the full network LODF. For self-outage
    (``l == k``), the numerator and denominator cancel, giving -1.0.
    If the denominator is zero, the outage is topology-trivial and
    LODF is set to 0.
    """
    if branch_zone_map is None:
        raise ValueError(
            "branch_zone_map is required for zonal LODF computation. "
            "Provide a list of (from_zone, to_zone) tuples for each branch."
        )

    n_branches, n_zones = ptdf.shape

    if len(branch_zone_map) != n_branches:
        raise ValueError(
            f"branch_zone_map length ({len(branch_zone_map)}) must match "
            f"number of PTDF rows ({n_branches})"
        )

    # Validate zone indices
    for bi, (fz, tz) in enumerate(branch_zone_map):
        if fz < 0 or fz >= n_zones:
            raise ValueError(
                f"Branch {bi}: from_zone index {fz} out of range "
                f"[0, {n_zones})"
            )
        if tz < 0 or tz >= n_zones:
            raise ValueError(
                f"Branch {bi}: to_zone index {tz} out of range "
                f"[0, {n_zones})"
            )

    lodf = np.zeros((n_branches, n_branches))

    for k in range(n_branches):
        fz_k, tz_k = branch_zone_map[k]
        denom = 1.0 - (ptdf[k, fz_k] - ptdf[k, tz_k])

        for l in range(n_branches):
            if l == k:
                # Self-outage: flow on outaged branch becomes zero
                lodf[l, k] = -1.0
                continue

            if abs(denom) < 1e-12:
                # Topology-trivial outage (branch has no flow impact)
                lodf[l, k] = 0.0
                continue

            num = ptdf[l, fz_k] - ptdf[l, tz_k]
            lodf[l, k] = num / denom

    return lodf


# ---------------------------------------------------------------------------
# screen_cbcos
# ---------------------------------------------------------------------------

def screen_cbcos(
    ptdf: np.ndarray,
    base_flows: np.ndarray,
    ram_limits: np.ndarray,
    branch_zone_map: Optional[list[tuple[int, int]]] = None,
    threshold: float = 0.10,
    verbose: bool = False,
) -> list[int]:
    """Screen out CBCOs that will not bind under N-1 contingency.

    A branch-flow constraint is considered a Critical Branch Contingency
    Outage (CBCO) if, after the outage of any single branch (N-1), the
    post-contingency flow on a remaining branch could exceed its
    Reliability Assessment Margin (RAM).

    The screening uses the conservative condition:

        |base_flow[l]| + |LODF[l, k] * base_flow[k]| >= threshold * RAM[l]

    If this holds for any outage ``k``, branch ``l`` is flagged as critical
    and must be included in the FBMC optimization constraints.

    Parameters
    ----------
    ptdf : np.ndarray, shape (n_branches, n_zones)
        PTDF matrix. Passed to :func:`compute_lodf`.

    base_flows : np.ndarray, shape (n_branches,)
        Pre-contingency (base-case) power flow on each branch in MW.
        Positive = forward direction; negative = reverse.

    ram_limits : np.ndarray, shape (n_branches,)
        Reliability Assessment Margin for each branch (MW). Must be
        non-negative.

    branch_zone_map : list of tuple (int, int), optional
        Zone connectivity for each branch. Passed to :func:`compute_lodf`.

    threshold : float, default 0.10
        Screening threshold relative to RAM. A constraint is screened
        out (not critical) if the worst-case post-contingency flow
        is below ``threshold * RAM[l]``.
        - ``0.10`` = conservative (10% of RAM -> keep most)
        - ``0.90`` = aggressive (90% of RAM -> screen many)

    verbose : bool, default False
        If True, print screening details for each branch pair.

    Returns
    -------
    critical_branches : list of int
        Sorted list of branch indices that are CBCOs and must be
        included in the security-constrained FBMC model.

    Raises
    ------
    ValueError
        If array shapes mismatch, RAM limits contain negatives, or
        ``branch_zone_map`` is missing.
    """
    n_branches = ptdf.shape[0]

    # ── Input validation ─────────────────────────────────────────
    if base_flows.shape != (n_branches,):
        raise ValueError(
            f"base_flows shape {base_flows.shape} must be ({n_branches},)"
        )
    if ram_limits.shape != (n_branches,):
        raise ValueError(
            f"ram_limits shape {ram_limits.shape} must be ({n_branches},)"
        )
    if np.any(ram_limits < 0):
        raise ValueError("All RAM limits must be non-negative")
    if threshold < 0:
        if verbose:
            print(f"  [screen_cbcos] threshold={threshold} < 0, all branches critical")

    # ── Edge case: empty system ──────────────────────────────────
    if n_branches == 0:
        return []

    # ── Compute LODF ─────────────────────────────────────────────
    lodf = compute_lodf(ptdf, branch_zone_map=branch_zone_map)

    # ── Screening logic ──────────────────────────────────────────
    critical_set: set[int] = set()

    for k in range(n_branches):  # outage branch
        base_k = base_flows[k]

        if verbose:
            print(f"  [screen_cbcos] Outage of branch {k} "
                  f"(base_flow={base_k:.1f} MW)")

        for l in range(n_branches):  # monitored branch
            # Base-case criticality (even without outages)
            if abs(base_flows[l]) >= threshold * ram_limits[l]:
                critical_set.add(l)
                if verbose:
                    print(f"    branch {l}: base flow {abs(base_flows[l]):.1f} >= "
                          f"{threshold * ram_limits[l]:.1f} "
                          f"(base-case critical)")
                continue

            # Skip self-outage for base-case (already checked above)
            if l == k:
                continue

            # Post-contingency impact
            lodf_lk = lodf[l, k]
            impact = abs(lodf_lk * base_k)
            post_contingency = abs(base_flows[l]) + impact

            threshold_flow = threshold * ram_limits[l]

            if post_contingency >= threshold_flow:
                critical_set.add(l)
                if verbose:
                    print(f"    branch {l}: |base|+|impact| = "
                          f"{abs(base_flows[l]):.1f} + {impact:.1f} = "
                          f"{post_contingency:.1f} >= {threshold_flow:.1f} "
                          f"(critical via LODF[{l},{k}]={lodf_lk:.4f})")
            elif verbose:
                print(f"    branch {l}: screened out "
                      f"({post_contingency:.1f} < {threshold_flow:.1f})")

    return sorted(critical_set)
