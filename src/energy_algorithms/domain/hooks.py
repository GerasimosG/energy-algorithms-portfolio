"""
Lifecycle hooks for LP/MIP optimisation pipelines.

Allows users to register callables that fire at well-defined points
during the model-solve-extract cycle, enabling logging, debugging,
custom preprocessing, metric collection, or persistence without
modifying solver internals.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class HookRegistry:
    """
    A thread-safe registry that maps event names to ordered lists of
    callables (hooks).

    Usage::

        registry = HookRegistry()
        registry.register("pre_solve", my_logger)
        registry.run("pre_solve", prob=solver_prob)
    """

    def __init__(self) -> None:
        """Initialise an empty hook registry."""
        self._hooks: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def register(self, event: str, fn: Callable[..., Any]) -> None:
        """
        Register a hook function for an event.

        Parameters
        ----------
        event : str
            Event name (e.g. ``"pre_solve"``, ``"post_solve"``).
        fn : callable
            The function to invoke when *event* fires.  It should
            accept ``**kwargs`` so that extra context can be passed
            without breaking compatibility.

        Raises
        ------
        TypeError
            If *fn* is not callable.
        """
        if not callable(fn):
            raise TypeError(f"Hook must be callable, got {type(fn).__name__}")
        self._hooks[event].append(fn)

    def run(self, event: str, **context: Any) -> None:
        """
        Execute all hooks registered for *event*, passing *context*
        as keyword arguments.

        Parameters
        ----------
        event : str
            Event name whose hooks should be invoked.
        **context
            Arbitrary keyword arguments forwarded to each hook.  Common
            keys include ``prob`` (the PuLP LpProblem), ``solver``,
            ``status``, ``schedule``, etc.

        Notes
        -----
        - Hooks are executed in the order they were registered.
        - Exceptions raised by a hook are logged but do **not**
          prevent subsequent hooks from running.  If a hook must
          halt the pipeline it should raise a dedicated exception
          and the caller should catch it.
        """
        if event not in self._hooks:
            return

        for idx, hook in enumerate(self._hooks[event]):
            try:
                hook(**context)
            except Exception:
                logger.exception(
                    "Hook #%d for event '%s' raised an exception",
                    idx,
                    event,
                )

    def clear(self, event: str | None = None) -> None:
        """
        Remove all hooks, or only those for a specific event.

        Parameters
        ----------
        event : str or None
            If ``None``, clear every event.  Otherwise clear only
            *event*.
        """
        if event is None:
            self._hooks.clear()
        else:
            self._hooks.pop(event, None)

    @property
    def events(self) -> list[str]:
        """List of events that have at least one registered hook."""
        return sorted(self._hooks.keys())

    def count(self, event: str | None = None) -> int:
        """
        Return the number of registered hook functions.

        Parameters
        ----------
        event : str or None
            If *event* is given, return the count for that event only.
            Otherwise return the total across all events.

        Returns
        -------
        int
        """
        if event is not None:
            return len(self._hooks.get(event, []))
        return sum(len(hooks) for hooks in self._hooks.values())


# ---------------------------------------------------------------------------
# Global convenience instance
# ---------------------------------------------------------------------------

_global_registry = HookRegistry()

# Well-known event names
PRE_SOLVE = "pre_solve"
POST_SOLVE = "post_solve"
POST_EXTRACT = "post_extract"


def register_hook(event: str, fn: Callable[..., Any]) -> None:
    """
    Register *fn* as a hook for *event* on the global registry.

    Parameters
    ----------
    event : str
        One of the well-known events (``"pre_solve"``, ``"post_solve"``,
        ``"post_extract"``) or a custom event name.
    fn : callable
        Hook function that accepts ``**kwargs``.
    """
    _global_registry.register(event, fn)


def run_hooks(event: str, **context: Any) -> None:
    """
    Execute all hooks registered for *event* on the global registry.

    Parameters
    ----------
    event : str
        Event name.
    **context
        Keyword arguments forwarded to each hook.
    """
    _global_registry.run(event, **context)


def clear_hooks(event: str | None = None) -> None:
    """
    Clear hooks from the global registry.

    Parameters
    ----------
    event : str or None
        If ``None``, clear all hooks.  Otherwise clear only *event*.
    """
    _global_registry.clear(event)
