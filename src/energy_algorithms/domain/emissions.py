"""CO₂ emissions factors and costs for European power generation.

Adds carbon cost pass-through to marginal cost calculations.
Based on EU ETS pricing (€60-80/ton in 2025-2026).

References:
- European Commission: EU ETS carbon price projections
- IEA: CO₂ emissions factors for electricity generation
- EEX: EUA (European Emission Allowance) market data
"""

# CO₂ emissions factors (tonnes per MWh electrical output)
# Based on typical EU power plant efficiencies
EMISSION_FACTORS: dict[str, float] = {
    # Fossil fuels
    "Fossil Gas": 0.40,                # CCGT, ~45% efficiency
    "Fossil Hard coal": 0.82,          # Hard coal, ~38% efficiency
    "Fossil Brown coal/Lignite": 1.05, # Lignite, ~35% efficiency
    "Fossil Oil": 0.75,                # Oil-fired, ~35% efficiency
    "Fossil Coal-derived gas": 0.45,   # Synthetic gas from coal
    "Fossil Oil shale": 0.90,          # Oil shale
    "Fossil Peat": 0.95,               # Peat-fired
    # Waste/biomass (partial CO₂ accounting)
    "Waste": 0.30,                     # Waste-to-energy (biogenic fraction exempt)
    "Biomass": 0.0,                    # Biogenic CO₂ — exempt under EU ETS
    "Other": 0.40,                     # Conservative estimate for unknown fossil
    # Zero-carbon sources
    "Nuclear": 0.0,
    "Wind Onshore": 0.0,
    "Wind Offshore": 0.0,
    "Solar": 0.0,
    "Hydro Run-of-river and poundage": 0.0,
    "Hydro Water Reservoir": 0.0,
    "Hydro Pumped Storage": 0.0,
    "Geothermal": 0.0,
    "Marine": 0.0,
    "Other renewable": 0.0,
}

# Default emission factor for unknown generation types
DEFAULT_EMISSION_FACTOR = 0.4


def co2_adjusted_marginal_cost(
    fuel_cost: float,
    emission_factor: float | None = None,
    co2_price: float = 70.0,
) -> float:
    """Add CO₂ cost pass-through to a fuel marginal cost.

    Parameters
    ----------
    fuel_cost : float
        Short-run marginal fuel cost in €/MWh.
    emission_factor : float | None
        Tonnes CO₂ per MWh produced. If None, uses fuel_cost-based heuristic.
    co2_price : float
        EUA carbon price in €/tonne CO₂ (default: 70).

    Returns
    -------
    float
        Fuel cost + CO₂ cost in €/MWh.

    Notes
    -----
    This is the standard "clean spark spread" / "clean dark spread"
    calculation used by European energy trading desks:

        CleanSparkSpread = PowerPrice - (GasPrice + CO₂Price × EmissionFactor) / Efficiency

    Here we only compute the cost component.
    """
    if emission_factor is None:
        # Heuristic: if fuel_cost > 30, it's likely fossil, assume 0.4 t/MWh
        emission_factor = 0.4 if fuel_cost > 30 else 0.0

    co2_cost = emission_factor * co2_price
    return fuel_cost + co2_cost


def co2_cost_per_mwh(gen_type: str, co2_price: float = 70.0) -> float:
    """CO₂ cost component for a given generation type.

    Parameters
    ----------
    gen_type : str
        Generation type name from ENTSO-E PSR types.
    co2_price : float
        EUA carbon price in €/tonne.

    Returns
    -------
    float
        CO₂ cost adder in €/MWh.
    """
    factor = EMISSION_FACTORS.get(gen_type, DEFAULT_EMISSION_FACTOR)
    return round(factor * co2_price, 2)


def adjusted_marginal_cost(
    gen_type: str,
    fuel_cost: float,
    co2_price: float = 70.0,
) -> float:
    """Full marginal cost including CO₂ for any generation type.

    Parameters
    ----------
    gen_type : str
        Generation type name.
    fuel_cost : float
        Short-run marginal fuel cost (€/MWh).
    co2_price : float
        EUA carbon price.

    Returns
    -------
    float
        Total marginal cost including CO₂ (€/MWh).
    """
    co2_adder = co2_cost_per_mwh(gen_type, co2_price)
    return round(fuel_cost + co2_adder, 2)
