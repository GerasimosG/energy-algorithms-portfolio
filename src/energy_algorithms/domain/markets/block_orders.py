"""Block Order Examples for PCR Market Clearing.

Demostrates different types of complex orders supported by Euphemia:
- Simple block: all-or-nothing (must-run minimum load)
- Linked block: several blocks that must all be accepted or rejected together
- Exclusive block: mutually exclusive choices (e.g., different unit configurations)
"""
from __future__ import annotations

from energy_algorithms.domain.markets.pcr_model import PCRModel


def scenario_simple_block() -> dict:
    """
    Market with a simple block order (must-run baseload plant).

    A nuclear plant must run at 80 MW minimum or not at all.
    The market decides if including it maximizes social welfare.
    """
    model = PCRModel("FR")
    model.add_supply("Gas", 80, 200)
    model.add_supply("Solar", 15, 100)
    model.add_supply("Hydro", 30, 80)
    model.add_demand("Industry", 180, 250)
    model.add_demand("Residential", 120, 150)
    model.add_block("Nuclear", 40, 80)  # all-or-nothing

    return model.solve()


def scenario_linked_block() -> dict:
    """
    Linked blocks: several blocks must all be accepted or all rejected.

    Used for cascading hydro plants or multi-unit power stations.
    Both blocks share the same group="cascade", enforcing identical binary value.
    """
    model = PCRModel("CH")
    model.add_supply("Coal", 60, 200)
    model.add_supply("Wind", 5, 150)
    model.add_supply("Peaker", 100, 100)
    model.add_demand("Grid", 150, 400)

    # Two hydro units that must operate together (same river cascade)
    model.add_block("Hydro_Upper", 25, 50, group="cascade")
    model.add_block("Hydro_Lower", 25, 60, group="cascade")

    return model.solve()


def scenario_exclusive_block() -> dict:
    """
    Exclusive blocks: at most one of a set can be selected.

    Uses a single model with identical supply curves for both options.
    The exclusive group constraint (group='excl_X') ensures at most one
    block is accepted — the solver picks the welfare-maximizing choice.
    Used for mutually exclusive investment decisions or
    different generator configurations.
    """
    model = PCRModel("Exclusive")
    # Identical supply curves for both options
    model.add_supply("Gas", 70, 200)
    model.add_supply("Solar", 10, 100)
    model.add_demand("Consumers", 160, 250)

    # Mutually exclusive blocks with identical supply curves
    model.add_block("CoalPlant", 35, 80, group="excl_1")
    model.add_block("GasPlant", 45, 80, group="excl_1")

    return model.solve()


def run_all() -> list[tuple[str, dict]]:
    """Run all block order scenarios."""
    results = [
        ("Simple Block (Nuclear must-run)", scenario_simple_block()),
        ("Linked Block (Cascade hydro)", scenario_linked_block()),
        ("Exclusive Block (Coal vs Gas)", scenario_exclusive_block()),
    ]
    return results


def run_exclusive() -> dict:
    """Run exclusive block comparison (single model with exclusive group constraint)."""
    result = scenario_exclusive_block()
    accepted = [bid for bid, info in result["orders"]["blocks"].items() if info["accepted"]]
    return {
        "result": result,
        "recommendation": accepted[0] if accepted else "None",
    }
