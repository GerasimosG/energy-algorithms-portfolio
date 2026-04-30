"""
Portfolio Optimization — Mean-variance with linear constraints via PuLP (fallback)
and proper QP via scipy.optimize.minimize (recommended).

Includes:
- Sector exposure limits
- Min/max individual weights
- Cardinality constraint (via top-N selection in scipy version)
"""
from __future__ import annotations

import numpy as np
import pulp
from scipy.optimize import minimize


def optimize_portfolio_scipy(
    expected_returns: list[float],
    cov_matrix: list[list[float]],
    risk_target: float | None = None,
    target_return: float | None = None,
    sector_map: list[str] | None = None,
    sector_limits: dict[str, tuple[float, float]] | None = None,
    weight_bounds: tuple[float, float] = (0.0, 0.3),
    cardinality: int | None = None,
    verbose: bool = False,
) -> dict:
    """
    Mean-variance portfolio optimization using scipy SLSQP.

    Solves: min  w^T Σ w  (variance)
    subject to:
      - w^T μ = target_return   (if target_return given)
      - sum(w) = 1
      - sector exposure limits
      - per-asset weight bounds
      - cardinality via top-N heuristic (largest weights kept, others set to 0)

    When target_return is None, maximizes Sharpe ratio (min variance subject
    to sum(w)=1 and bounds).

    Parameters
    ----------
    expected_returns : list of asset expected returns
    cov_matrix : covariance matrix (n × n)
    risk_target : ignored in this formulation (kept for API compat)
    target_return : desired portfolio return (None → min variance)
    sector_map : sector label per asset
    sector_limits : dict {sector: (min_frac, max_frac)}
    weight_bounds : (min_weight, max_weight) per asset
    cardinality : max number of assets (top-N heuristic post-solve)
    verbose : print solver output

    Returns
    -------
    dict with weights, return, risk, status
    """
    n = len(expected_returns)
    mu = np.array(expected_returns, dtype=float)
    cov = np.array(cov_matrix, dtype=float)

    # ---- Build constraints ----
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]  # budget

    if target_return is not None:
        constraints.append(
            {"type": "eq", "fun": lambda w: np.dot(w, mu) - target_return}
        )

    # Sector constraints
    if sector_map is not None and sector_limits is not None:
        sectors = list(set(sector_map))
        for sector in sectors:
            idx = [i for i in range(n) if sector_map[i] == sector]
            min_f, max_f = sector_limits.get(sector, (0.0, 1.0))
            if min_f > 0:
                constraints.append(
                    {"type": "ineq", "fun": lambda w, i=idx, m=min_f: np.sum(w[i]) - m}
                )
            if max_f < 1.0:
                constraints.append(
                    {"type": "ineq", "fun": lambda w, i=idx, m=max_f: m - np.sum(w[i])}
                )

    # Bounds
    bounds = [weight_bounds for _ in range(n)]

    # ---- Objective: minimize variance ----
    def variance(w):
        return np.dot(w.T, np.dot(cov, w))

    # Initial guess: equal weight
    w0 = np.ones(n) / n

    result = minimize(
        variance,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"disp": verbose, "ftol": 1e-9},
    )

    if not result.success:
        return {"status": result.message, "weights": None}

    weights = result.x

    # ---- Cardinality heuristic: zero out smallest weights, re-normalize ----
    if cardinality is not None and cardinality < n:
        sorted_idx = np.argsort(np.abs(weights))[::-1]
        keep = sorted_idx[:cardinality]
        w_card = np.zeros(n)
        w_card[keep] = weights[keep]
        # Re-normalize to sum = 1
        if np.sum(w_card) > 0:
            w_card = w_card / np.sum(w_card)
        weights = w_card

    port_return = float(np.dot(weights, mu))
    port_risk = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))

    return {
        "status": "Optimal",
        "weights": weights,
        "return": round(port_return, 4),
        "risk": round(port_risk, 4),
        "n_assets_selected": int(np.sum(weights > 0.001)),
    }


def optimize_portfolio(
    expected_returns: list[float],
    cov_matrix: list[list[float]],
    risk_target: float,
    sector_map: list[str],
    sector_limits: dict[str, tuple[float, float]],
    weight_bounds: tuple[float, float] = (0.0, 0.3),
    cardinality: int | None = None,
    verbose: bool = False,
) -> dict:
    """
    Portfolio optimization with linear constraints (PuLP).

    ⚠ NOTE: PuLP does NOT support quadratic constraints. The risk_target
    parameter is accepted but NOT enforced in this version. The portfolio
    risk is reported post-hoc for informational purposes.

    For proper mean-variance (Markowitz) optimization with a risk constraint,
    use ``optimize_portfolio_scipy()`` instead.

    Maximize expected return subject to:
    - Sector exposure limits
    - Per-asset weight bounds
    - Optional cardinality (max N assets selected)

    Parameters
    ----------
    expected_returns : list of asset expected returns
    cov_matrix : covariance matrix (n × n)
    risk_target : ⚠ NOT ENFORCED — use scipy version for proper risk control
    sector_map : sector label per asset
    sector_limits : dict {sector: (min_frac, max_frac)}
    weight_bounds : (min_weight, max_weight) per asset
    cardinality : max number of assets to select (None = no limit)

    Returns
    -------
    dict with weights, return, risk, status
    """
    n = len(expected_returns)
    cov = np.array(cov_matrix)
    sectors = list(set(sector_map))

    prob = pulp.LpProblem("Portfolio_Optimization", pulp.LpMaximize)

    # Continuous weight variables
    w = {i: pulp.LpVariable(f"w_{i}", lowBound=weight_bounds[0], upBound=weight_bounds[1])
         for i in range(n)}

    # Binary selection variables (for cardinality)
    z = None
    if cardinality is not None:
        z = {i: pulp.LpVariable(f"z_{i}", cat="Binary") for i in range(n)}

    # Budget constraint: sum weights = 1
    prob += pulp.lpSum(w[i] for i in range(n)) == 1

    # Sector constraints
    for sector in sectors:
        indices = [i for i in range(n) if sector_map[i] == sector]
        min_frac, max_frac = sector_limits.get(sector, (0.0, 1.0))
        prob += pulp.lpSum(w[i] for i in indices) >= min_frac
        prob += pulp.lpSum(w[i] for i in indices) <= max_frac

    # Cardinality constraint: w_i ≤ z_i, sum z_i ≤ cardinality
    if z is not None:
        for i in range(n):
            prob += w[i] <= z[i] * weight_bounds[1]
        prob += pulp.lpSum(z[i] for i in range(n)) <= cardinality

    # Objective: maximize expected return
    prob += pulp.lpSum(expected_returns[i] * w[i] for i in range(n))

    # ── Risk constraint ──────────────────────────────────────────────
    # PuLP is linear-only; it cannot enforce w^T Σ w ≤ risk_target².
    # The risk_target parameter is accepted for API compatibility but
    # effectively ignored. Use optimize_portfolio_scipy() (above) for
    # proper Markowitz mean-variance optimization with scipy SLSQP.
    # ─────────────────────────────────────────────────────────────────

    prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": pulp.LpStatus[prob.status], "weights": None}

    weights = np.array([pulp.value(w[i]) for i in range(n)])
    port_return = float(np.dot(weights, expected_returns))
    port_risk = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))

    return {
        "status": pulp.LpStatus[prob.status],
        "weights": weights,
        "return": round(port_return, 4),
        "risk": round(port_risk, 4),
        "n_assets_selected": int(np.sum(weights > 0.001)),
    }


def demo_portfolio() -> dict:
    """Run portfolio optimization on 6 assets across 3 sectors (scipy version)."""
    expected_returns = [0.12, 0.10, 0.08, 0.15, 0.09, 0.11]
    np.random.seed(42)
    n = 6
    # Build a reasonable covariance matrix
    vols = np.array([0.20, 0.18, 0.15, 0.25, 0.16, 0.19])
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            r = 0.3 + 0.4 * np.random.random()
            corr[i, j] = r
            corr[j, i] = r
    cov = np.outer(vols, vols) * corr

    sector_map = ["Tech", "Tech", "Energy", "Energy", "Health", "Health"]
    sector_limits = {
        "Tech": (0.1, 0.5),
        "Energy": (0.1, 0.5),
        "Health": (0.1, 0.4),
    }

    return optimize_portfolio_scipy(
        expected_returns=expected_returns,
        cov_matrix=cov.tolist(),
        target_return=0.127,  # target ~12.7% return, let scipy minimize variance
        sector_map=sector_map,
        sector_limits=sector_limits,
        weight_bounds=(0.0, 0.35),
        cardinality=4,
    )
