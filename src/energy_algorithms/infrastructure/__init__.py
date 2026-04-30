"""Infrastructure layer — cross-cutting concerns.

Hooks, options, metadata, and solver configuration
shared across all domain and application modules.
"""
from __future__ import annotations


from energy_algorithms.domain.hooks import (
    HookRegistry,
    register_hook,
    run_hooks,
    clear_hooks,
    PRE_SOLVE,
    POST_SOLVE,
    POST_EXTRACT,
)
from energy_algorithms.domain.options import (
    get_option,
    set_option,
    reset_options,
    get_options_dict,
)
from energy_algorithms.infrastructure.metadata import (
    VariableRegistry,
    ModelMetadata,
    get_model_summary,
)
from energy_algorithms.infrastructure.solver_config import (
    get_solver,
    list_available_solvers,
    solver_capabilities,
)

__all__ = [
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
    # Solver config
    "get_solver",
    "list_available_solvers",
    "solver_capabilities",
]
