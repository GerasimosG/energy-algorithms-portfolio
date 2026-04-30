"""LP Optimization module — transportation, portfolio, unit commitment, storage,
OneInterval asset pattern, and physical invariant validation.

Classic operations research problems solved with PuLP and scipy.
Also provides solver-agnostic configuration, lifecycle hooks,
centralised options, and model metadata introspection.
"""

from lp_optimization.transportation import solve_transportation, demo_transportation
from lp_optimization.portfolio import (
    optimize_portfolio,
    optimize_portfolio_scipy,
    demo_portfolio,
)
from lp_optimization.scheduling import solve_unit_commitment, demo_uc
from lp_optimization.storage import solve_storage, demo_storage

# Solver-agnostic config
from lp_optimization.solver_config import (
    get_solver,
    list_available_solvers,
    solver_capabilities,
)

# Lifecycle hooks
from lp_optimization.hooks import (
    HookRegistry,
    register_hook,
    run_hooks,
    clear_hooks,
    PRE_SOLVE,
    POST_SOLVE,
    POST_EXTRACT,
)

# Centralised options
from lp_optimization.options import (
    get_option,
    set_option,
    reset_options,
    get_options_dict,
)

# Metadata / introspection
from lp_optimization.metadata import (
    VariableRegistry,
    ModelMetadata,
    get_model_summary,
)

# OneInterval asset pattern
from lp_optimization.assets import (
    Asset,
    BatteryAsset,
    GeneratorAsset,
    SpillAsset,
    build_site,
    demo_site,
)

# Physical invariant validation
from lp_optimization.invariants import (
    validate_energy_balance,
    validate_soc_bounds,
    validate_power_limits,
    assert_invariants,
)

__all__ = [
    # Original exports
    "solve_transportation",
    "demo_transportation",
    "optimize_portfolio",
    "optimize_portfolio_scipy",
    "demo_portfolio",
    "solve_unit_commitment",
    "demo_uc",
    "solve_storage",
    "demo_storage",
    # Solver config
    "get_solver",
    "list_available_solvers",
    "solver_capabilities",
    # Hooks
    "HookRegistry",
    "register_hook",
    "run_hooks",
    "clear_hooks",
    "PRE_SOLVE",
    "POST_SOLVE",
    "POST_EXTRACT",
    # Options
    "get_option",
    "set_option",
    "reset_options",
    "get_options_dict",
    # Metadata
    "VariableRegistry",
    "ModelMetadata",
    "get_model_summary",
    # OneInterval asset pattern
    "Asset",
    "BatteryAsset",
    "GeneratorAsset",
    "SpillAsset",
    "build_site",
    "demo_site",
    # Invariants
    "validate_energy_balance",
    "validate_soc_bounds",
    "validate_power_limits",
    "assert_invariants",
]
