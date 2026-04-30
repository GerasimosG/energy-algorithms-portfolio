"""Tests for lp_optimization.hooks — lifecycle hook registry."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from energy_algorithms.infrastructure.hooks import (
    HookRegistry,
    register_hook,
    run_hooks,
    clear_hooks,
    PRE_SOLVE,
    POST_SOLVE,
    POST_EXTRACT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Tracker:
    """Simple callable that records that it was invoked and with what."""

    def __init__(self):
        self.calls = []

    def __call__(self, **context):
        self.calls.append(context)


# ---------------------------------------------------------------------------
# Tests — HookRegistry class
# ---------------------------------------------------------------------------


class TestHookRegistry:
    """Tests for the HookRegistry class."""

    def test_register_and_run(self):
        """Registered hook is called when the event fires."""
        reg = HookRegistry()
        tracker = _Tracker()

        reg.register("test_event", tracker)
        reg.run("test_event", key="value")

        assert len(tracker.calls) == 1
        assert tracker.calls[0] == {"key": "value"}

    def test_multiple_hooks_same_event(self):
        """Multiple hooks for the same event all fire in order."""
        reg = HookRegistry()
        order = []

        def hook_a(**ctx):
            order.append("A")

        def hook_b(**ctx):
            order.append("B")

        reg.register("ev", hook_a)
        reg.register("ev", hook_b)
        reg.run("ev")

        assert order == ["A", "B"]

    def test_hooks_receive_context(self):
        """All context kwargs are passed to hooks."""
        reg = HookRegistry()
        received = {}

        def hook(**ctx):
            received.update(ctx)

        reg.register("ev", hook)
        reg.run("ev", prob="my_prob", solver="cbc", status="Optimal")

        assert received == {"prob": "my_prob", "solver": "cbc", "status": "Optimal"}

    def test_no_hooks_no_error(self):
        """Running an event with no registered hooks is a no-op."""
        reg = HookRegistry()
        reg.run("no_such_event")  # should not raise

    def test_clear_single_event(self):
        """clear(event) removes hooks for that event only."""
        reg = HookRegistry()
        t1, t2 = _Tracker(), _Tracker()

        reg.register("a", t1)
        reg.register("b", t2)
        reg.clear("a")

        reg.run("a")
        reg.run("b")

        assert len(t1.calls) == 0  # cleared
        assert len(t2.calls) == 1  # still registered

    def test_clear_all(self):
        """clear() removes all hooks."""
        reg = HookRegistry()
        t = _Tracker()
        reg.register("ev", t)
        reg.clear()
        reg.run("ev")
        assert len(t.calls) == 0

    def test_register_non_callable_raises(self):
        """Registering a non-callable raises TypeError."""
        reg = HookRegistry()
        with pytest.raises(TypeError, match="callable"):
            reg.register("ev", "not_a_function")

    def test_events_property(self):
        """events property returns sorted event names with hooks."""
        reg = HookRegistry()
        assert reg.events == []

        reg.register("post_solve", _Tracker())
        reg.register("pre_solve", _Tracker())
        assert reg.events == ["post_solve", "pre_solve"]

    def test_count(self):
        """count() returns correct numbers."""
        reg = HookRegistry()
        assert reg.count() == 0

        reg.register("a", _Tracker())
        reg.register("a", _Tracker())
        reg.register("b", _Tracker())

        assert reg.count("a") == 2
        assert reg.count("b") == 1
        assert reg.count() == 3
        assert reg.count("nonexistent") == 0

    def test_exception_in_hook_is_logged_not_raised(self):
        """A hook that raises doesn't prevent subsequent hooks."""
        reg = HookRegistry()
        t = _Tracker()

        def bad_hook(**ctx):
            raise ValueError("boom")

        reg.register("ev", bad_hook)
        reg.register("ev", t)
        # Should not raise — hook exceptions are caught and logged.
        reg.run("ev")
        assert len(t.calls) == 1  # second hook still ran


# ---------------------------------------------------------------------------
# Tests — global convenience functions
# ---------------------------------------------------------------------------


class TestGlobalHooks:
    """Tests for the module-level convenience functions."""

    def setup_method(self):
        """Clear global registry before each test."""
        clear_hooks()

    def test_register_and_run_global(self):
        """register_hook / run_hooks use the global registry."""
        tracker = _Tracker()
        register_hook("my_event", tracker)
        run_hooks("my_event", data=42)

        assert len(tracker.calls) == 1
        assert tracker.calls[0]["data"] == 42

    def test_well_known_event_constants(self):
        """Module exports PRE_SOLVE, POST_SOLVE, POST_EXTRACT."""
        for ev in [PRE_SOLVE, POST_SOLVE, POST_EXTRACT]:
            assert isinstance(ev, str)
            assert len(ev) > 0


# ---------------------------------------------------------------------------
# Tests — integration with scheduling demo
# ---------------------------------------------------------------------------


class TestHooksInScheduling:
    """Verify hooks fire during the scheduling solve cycle."""

    def setup_method(self):
        clear_hooks()

    def test_hooks_fire_during_uc_demo(self):
        """Pre/post solve hooks fire when running demo_uc()."""
        from energy_algorithms.domain.optimization.scheduling import demo_uc

        tracker = _Tracker()
        register_hook(PRE_SOLVE, tracker)
        register_hook(POST_SOLVE, tracker)

        result = demo_uc()
        assert result["status"] == "Optimal"

        assert len(tracker.calls) == 2
        # First call should have 'prob', second should have 'status'
        assert "prob" in tracker.calls[0]
        assert tracker.calls[1].get("status") == "Optimal"
