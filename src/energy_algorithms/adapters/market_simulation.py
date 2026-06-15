"""OpenSpace-inspired agent-based market simulation for power markets.

Simulates multiple trading agents submitting bids to the PCR (Euphemia-style)
market clearing mechanism, each with different strategies. Agents learn and
adapt their bidding over multiple sessions.

Inspired by:
- OpenSpace / Energy Market Games (agent-based power market simulation)
- Euphemia: multiple participants submit orders → welfare maximization
- Reinforcement learning for bidding in electricity markets

This is NOT a full OpenSpace port — it's a demo of the concept that shows
understanding of agent-based power market simulation, which is highly relevant
for energy-market interviews.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from energy_algorithms.domain.markets.pcr_model import PCRModel


@dataclass
class Agent:
    """A market participant with a bidding strategy.

    Parameters
    ----------
    name : str
        Agent identifier.
    strategy_type : str
        One of: 'renewable', 'gas', 'nuclear', 'hydro', 'demand', 'speculator'.
    capacity_mw : float
        Generation capacity (0 for demand/speculator).
    marginal_cost : float
        True marginal cost (for generators).
    learning_rate : float
        How quickly the agent adapts its bid price (0 = never, 1 = instantly).
    """

    name: str
    strategy_type: str
    capacity_mw: float = 0.0
    marginal_cost: float = 50.0
    learning_rate: float = 0.1
    bid_price: float = 50.0
    accepted_qty: float = 0.0
    total_profit: float = 0.0
    total_revenue: float = 0.0
    trade_history: list[dict] = field(default_factory=list)
    _bias: float = 0.0  # accumulated learning signal

    def bid(self, hour: int, market_price: float | None = None) -> tuple[float, float]:
        """Generate a bid (price, quantity) based on strategy type.

        Parameters
        ----------
        hour : int
            Current hour (0-23), affects renewable output.
        market_price : float or None
            Previous clearing price (for learning).

        Returns
        -------
        tuple[float, float]
            (bid_price, bid_quantity).
        """
        if self.strategy_type == "renewable":
            # Solar/wind: bid at near-zero price, output depends on hour
            factor = max(0.0, np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.1
            qty = self.capacity_mw * factor
            return (0.5, qty)  # Near-zero to ensure dispatch

        elif self.strategy_type == "gas":
            # Gas: bid at marginal cost + learning bias
            gas_price = self.marginal_cost
            if market_price is not None and self.learning_rate > 0:
                # Learn: if we were accepted, increase price slightly
                self._bias += self.learning_rate * (market_price - gas_price) * 0.1
                self._bias = np.clip(self._bias, -10, 10)
            return (gas_price + self._bias, self.capacity_mw)

        elif self.strategy_type == "nuclear":
            # Nuclear: must-run, always bid low
            return (self.marginal_cost, self.capacity_mw)

        elif self.strategy_type == "hydro":
            # Hydro: limited water, bid based on storage
            qty = self.capacity_mw * (0.5 + 0.5 * np.sin(np.pi * hour / 6))
            return (self.marginal_cost + 5, qty)

        elif self.strategy_type == "demand":
            # Demand: willingness-to-pay based on hour
            if 8 <= hour <= 11 or 17 <= hour <= 20:
                wpp = 150.0  # Peak: high willingness
            elif 12 <= hour <= 16:
                wpp = 80.0  # Mid: moderate
            else:
                wpp = 45.0  # Off-peak: low
            return (-wpp if self._use_negative_sign else wpp, self.capacity_mw)

        elif self.strategy_type == "speculator":
            # Speculator: tries to predict and exploit spreads
            if 0 <= hour <= 5:
                # Night: bid cheap, buy
                qty = self.capacity_mw * 0.5
                return (20.0, qty)
            elif 18 <= hour <= 21:
                # Evening peak: offer expensive, sell
                qty = self.capacity_mw * 0.3
                return (130.0, qty)
            else:
                return (60.0, self.capacity_mw * 0.1)

        return (self.marginal_cost, self.capacity_mw)

    @property
    def _use_negative_sign(self) -> bool:
        """Demand orders use positive price in PCRModel (bid price)."""
        return False


@dataclass
class MarketSession:
    """One market session (24 hours) with multiple agents.

    Runs the PCR market clearing for each hour and records results.
    """

    agents: list[Agent]
    area: str = "BE"
    hour_count: int = 24

    def run(self, verbose: bool = False) -> dict[str, Any]:
        """Run the 24-hour market simulation.

        For each hour:
        1. Each agent submits a bid
        2. PCR model clears the market
        3. Agents learn from the clearing price
        4. Record P&L

        Returns
        -------
        dict with hourly_results, agent_profits, social_welfare
        """
        hourly_results = []
        agent_profits: dict[str, float] = {a.name: 0.0 for a in self.agents}
        total_welfare = 0.0
        total_volume = 0.0
        clearing_prices = []

        for hour in range(self.hour_count):
            model = PCRModel(area=self.area)

            for agent in self.agents:
                price, qty = agent.bid(
                    hour,
                    market_price=clearing_prices[-1] if clearing_prices else None,
                )
                if agent.strategy_type == "demand":
                    model.add_demand(agent.name, price=price, qty=qty)
                else:
                    model.add_supply(agent.name, price=price, qty=qty)

            result = model.solve()
            mcp = result.get("mcp", 0)
            status = result.get("status", "unknown")

            if status != "Optimal":
                clearing_prices.append(clearing_prices[-1] if clearing_prices else 50.0)
                hourly_results.append({"hour": hour, "status": status, "mcp": 0})
                continue

            clearing_prices.append(mcp)
            welfare = result.get("welfare", 0) or 0
            volume = result.get("traded", 0) or 0
            orders = result.get("orders", {})

            # Compute per-agent P&L for this hour
            hour_profits = {}
            for agent in self.agents:
                if agent.strategy_type == "demand":
                    continue  # demand doesn't have P&L in same way
                order = orders.get("supply", {}).get(agent.name, {})
                filled_qty = order.get("filled_qty", 0)
                if filled_qty > 0:
                    # Profit = (MCP - bid_price) × filled_qty
                    profit = (mcp - agent.bid_price) * filled_qty
                    agent_profits[agent.name] += profit
                    agent.accepted_qty += filled_qty
                    agent.total_revenue += mcp * filled_qty
                    agent.total_profit += profit
                    agent.trade_history.append({
                        "hour": hour, "mcp": mcp, "bid": agent.bid_price,
                        "filled": filled_qty, "profit": profit,
                    })
                    hour_profits[agent.name] = profit

            total_welfare += welfare
            total_volume += volume

            hourly_results.append({
                "hour": hour,
                "mcp": mcp,
                "welfare": welfare,
                "volume": volume,
                "agent_profits": hour_profits,
            })

        return {
            "hourly_results": hourly_results,
            "agent_profits": agent_profits,
            "total_welfare": total_welfare,
            "total_volume": total_volume,
            "avg_mcp": np.mean(clearing_prices) if clearing_prices else 0,
            "min_mcp": min(clearing_prices) if clearing_prices else 0,
            "max_mcp": max(clearing_prices) if clearing_prices else 0,
            "num_agents": len(self.agents),
            "generator_profits": {a.name: agent_profits[a.name] for a in self.agents
                                  if a.strategy_type != "demand"},
        }


# ── Setup Fixtures ──────────────────────────────────────────────


def create_default_market() -> MarketSession:
    """Create a default 7-agent Belgian-style power market with flexible demand."""
    agents = [
        Agent("Solar Farm", "renewable", capacity_mw=2000, marginal_cost=1.0),
        Agent("Wind Farm", "renewable", capacity_mw=1800, marginal_cost=2.0),
        Agent("Nuclear Plant", "nuclear", capacity_mw=4000, marginal_cost=7.0),
        Agent("Gas Peaker", "gas", capacity_mw=1500, marginal_cost=70.0),
        Agent("Gas CCGT", "gas", capacity_mw=2500, marginal_cost=55.0, learning_rate=0.05),
        Agent("Hydro Dam", "hydro", capacity_mw=800, marginal_cost=10.0),
        Agent("Base Demand", "demand", capacity_mw=5000, marginal_cost=0.0),
    ]
    return MarketSession(agents)
