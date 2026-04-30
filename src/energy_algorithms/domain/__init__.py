"""Domain layer — pure business logic with no I/O dependencies."""
from __future__ import annotations

from energy_algorithms.domain import markets  # noqa: F401
from energy_algorithms.domain import optimization  # noqa: F401
from energy_algorithms.domain import trading  # noqa: F401
from energy_algorithms.domain.hooks import (  # noqa: F401
    HookRegistry,
    register_hook,
    run_hooks,
    clear_hooks,
    PRE_SOLVE,
    POST_SOLVE,
    POST_EXTRACT,
)
from energy_algorithms.domain.options import (  # noqa: F401
    get_option,
    set_option,
    reset_options,
    get_options_dict,
)

__all__ = [
    "markets",
    "optimization",
    "trading",
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
]
