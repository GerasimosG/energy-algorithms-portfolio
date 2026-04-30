"""Tests for lp_optimization.options — centralised options dict."""
from __future__ import annotations

import pytest

from energy_algorithms.domain.options import (
    get_option,
    get_options_dict,
    reset_options,
    set_option,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_after_test():
    """Ensure options are at defaults before and after each test."""
    reset_options()
    yield
    reset_options()

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetOption:
    """Tests for get_option()."""

    def test_defaults(self):
        """Default values are returned for known keys."""
        assert get_option("solver") == "cbc"
        assert get_option("verbose") is False
        assert get_option("time_limit") is None

    def test_unknown_key_with_default(self):
        """When key is unknown, the provided default is returned."""
        val = get_option("nonexistent", default=42)
        assert val == 42

    def test_unknown_key_raises_without_default(self):
        """Unknown key raises KeyError when no default is given."""
        with pytest.raises(KeyError, match="Unknown option"):
            get_option("no_such_option")

    def test_set_then_get(self):
        """get_option reflects a previously set value."""
        set_option("verbose", True)
        assert get_option("verbose") is True

    def test_get_options_dict_is_copy(self):
        """get_options_dict returns a copy — mutations don't affect store."""
        d = get_options_dict()
        d["solver"] = "highs"
        assert get_option("solver") == "cbc"  # unchanged

class TestSetOption:
    """Tests for set_option()."""

    def test_set_valid_option(self):
        """A valid key can be set."""
        set_option("time_limit", 120)
        assert get_option("time_limit") == 120

    def test_set_unknown_option_raises(self):
        """Setting an unknown key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown option"):
            set_option("bogus_key", True)

class TestResetOptions:
    """Tests for reset_options()."""

    def test_reset_restores_defaults(self):
        """After modifications, reset restores factory defaults."""
        set_option("solver", "highs")
        set_option("verbose", True)
        set_option("time_limit", 60)

        reset_options()

        assert get_option("solver") == "cbc"
        assert get_option("verbose") is False
        assert get_option("time_limit") is None

    def test_reset_is_idempotent(self):
        """Calling reset twice is safe."""
        set_option("solver", "highs")
        reset_options()
        reset_options()
        assert get_option("solver") == "cbc"

class TestOptionsIntegration:
    """Integration-style tests for the options module."""

    def test_all_known_keys_are_readable(self):
        """Every key defined in defaults is retrievable."""
        for key in get_options_dict():
            # None of these should raise
            _ = get_option(key)

    def test_solver_kwargs_are_preserved(self):
        """The solver_kwargs dict can hold arbitrary sub-options."""
        set_option("solver_kwargs", {"threads": 4, "mipgap": 0.01})
        kwargs = get_option("solver_kwargs")
        assert kwargs["threads"] == 4
        assert kwargs["mipgap"] == 0.01
