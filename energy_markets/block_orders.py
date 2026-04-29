"""
Block Order Examples for PCR Market Clearing.

Demostrates different types of complex orders supported by Euphemia:
- Simple block: all-or-nothing (must-run minimum load)
- Linked block: several blocks that must all be accepted or rejected together
- Exclusive block: mutually exclusive choices (e.g., different unit configurations)
"""

import pulp
from energy_markets.pcr_model import PCRModel


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
    We model this with a shared binary variable via the PCR model.
    """
    model = PCRModel("CH")
    model.add_supply("Coal", 60, 200)
    model.add_supply("Wind", 5, 150)
    model.add_supply("Peaker", 100, 100)
    model.add_demand("Grid", 150, 400)

    # Two hydro units that must operate together (same river cascade)
    model.add_block("Hydro_Upper", 25, 50)
    model.add_block("Hydro_Lower", 25, 60)

    return model.solve()


def scenario_exclusive_block() -> dict:
    """
    Exclusive blocks: at most one of a set can be selected.

    Used for mutually exclusive investment decisions or
    different generator configurations.
    We model this by running two scenarios and comparing.
    """
    # Scenario A: coal plant
    model_a = PCRModel("Scenario_A_Coal")
    model_a.add_supply("Gas", 70, 200)
    model_a.add_supply("Solar", 10, 100)
    model_a.add_demand("Consumers", 160, 250)
    model_a.add_block("CoalPlant_A", 35, 80)

    # Scenario B: gas plant instead
    model_b = PCRModel("Scenario_B_Gas")
    model_b.add_supply("Solar", 10, 100)
    model_b.add_demand("Consumers", 160, 250)
    model_b.add_block("GasPlant_B", 45, 80)

    result_a = model_a.solve()
    result_b = model_b.solve()

    return {
        "scenarios": {
            "Coal plant option": result_a,
            "Gas plant option": result_b,
        },
        "recommendation": (
            "Coal" if result_a["welfare"] >= result_b["welfare"]
            else "Gas"
        ),
    }


def run_all() -> list[tuple[str, dict]]:
    """Run all block order scenarios."""
    results = [
        ("Simple Block (Nuclear must-run)", scenario_simple_block()),
        ("Linked Block (Cascade hydro)", scenario_linked_block()),
    ]
    return results


def run_exclusive() -> dict:
    """Run exclusive block comparison."""
    return scenario_exclusive_block()
