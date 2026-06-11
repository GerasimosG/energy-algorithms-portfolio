"""Domain layer — pure business logic with no I/O dependencies."""
from __future__ import annotations

from energy_algorithms.domain import ( # noqa: F401
 markets,
 optimization,
)

try:
 from energy_algorithms.domain import trading # noqa: F401
except ImportError:
 pass
from energy_algorithms.domain.hooks import ( # noqa: F401
 POST_EXTRACT,
 POST_SOLVE,
 PRE_SOLVE,
 HookRegistry,
 clear_hooks,
 register_hook,
 run_hooks,
)
from energy_algorithms.domain.options import ( # noqa: F401
 get_option,
 get_options_dict,
 reset_options,
 set_option,
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
