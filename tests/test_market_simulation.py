"""Tests for the agent-based market simulation module.

Tests Agent bidding strategies, MarketSession execution,
and the create_default_market() factory.
"""
from __future__ import annotations


class TestAgent:
    """Tests for the Agent dataclass and its bid() method."""

    def test_renewable_bid_daytime(self):
        """Renewable agent bids near-zero during daytime hours."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Solar", "renewable", capacity_mw=2000, marginal_cost=1.0)
        price, qty = agent.bid(hour=12)
        assert price == 0.5
        assert qty > 0
        assert qty <= 2000

    def test_renewable_bid_night(self):
        """Renewable agent bids small quantity at night."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Solar", "renewable", capacity_mw=2000)
        price, qty = agent.bid(hour=0)
        assert price == 0.5
        assert qty > 0  # 0.1 factor at night

    def test_gas_bid_no_market_price(self):
        """Gas agent bids at marginal cost without market price signal."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Gas", "gas", capacity_mw=1500, marginal_cost=70.0)
        price, qty = agent.bid(hour=10)
        assert price == 70.0
        assert qty == 1500

    def test_gas_bid_with_market_price(self):
        """Gas agent learns from market price and adjusts bid."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Gas", "gas", capacity_mw=1500, marginal_cost=70.0, learning_rate=0.1)
        # First bid with no history
        price1, qty1 = agent.bid(hour=10, market_price=None)
        assert price1 == 70.0

        # Second bid with a high market price — bias increases
        price2, qty2 = agent.bid(hour=11, market_price=100.0)
        assert price2 > 70.0  # Learned to bid higher
        assert qty2 == 1500

    def test_gas_bid_learning_clamped(self):
        """Gas agent learning bias is clamped to [-10, 10]."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0, learning_rate=0.5)
        # Repeatedly bid with extreme market price
        for _ in range(100):
            agent.bid(hour=10, market_price=500.0)
        # Bias should be clamped at +10
        price, _ = agent.bid(hour=10, market_price=500.0)
        assert price <= 60.0  # 50 + 10

    def test_nuclear_bid(self):
        """Nuclear agent bids at marginal cost, full capacity."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Nuclear", "nuclear", capacity_mw=4000, marginal_cost=7.0)
        price, qty = agent.bid(hour=5)
        assert price == 7.0
        assert qty == 4000

    def test_hydro_bid(self):
        """Hydro agent bids with sinusoidal output pattern."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Hydro", "hydro", capacity_mw=800, marginal_cost=10.0)
        price, qty = agent.bid(hour=6)
        assert price == 15.0  # marginal_cost + 5
        assert qty > 0

    def test_demand_bid_peak(self):
        """Demand agent bids high willingness-to-pay during peak."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Demand", "demand", capacity_mw=5000)
        price, qty = agent.bid(hour=10)  # morning peak
        assert price == 150.0
        assert qty == 5000

    def test_demand_bid_offpeak(self):
        """Demand agent bids low willingness-to-pay during off-peak."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Demand", "demand", capacity_mw=5000)
        price, qty = agent.bid(hour=3)  # off-peak
        assert price == 45.0
        assert qty == 5000

    def test_speculator_bid_night(self):
        """Speculator bids cheap at night."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Spec", "speculator", capacity_mw=1000)
        price, qty = agent.bid(hour=2)
        assert price == 20.0
        assert qty == 500.0  # 1000 * 0.5

    def test_speculator_bid_peak(self):
        """Speculator offers expensive during evening peak."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Spec", "speculator", capacity_mw=1000)
        price, qty = agent.bid(hour=19)
        assert price == 130.0
        assert qty == 300.0  # 1000 * 0.3

    def test_unknown_strategy_fallback(self):
        """Unknown strategy type falls back to marginal cost."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Test", "unknown_type", capacity_mw=500, marginal_cost=42.0)
        price, qty = agent.bid(hour=10)
        assert price == 42.0
        assert qty == 500

    def test_use_negative_sign_property(self):
        """_use_negative_sign property returns False."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Demand", "demand")
        assert agent._use_negative_sign is False

    def test_trade_history_default(self):
        """Agent starts with empty trade history."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Test", "renewable")
        assert agent.trade_history == []

    def test_demand_mid_bid(self):
        """Demand agent bids moderate willingness-to-pay during midday."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Demand", "demand", capacity_mw=5000)
        price, qty = agent.bid(hour=14)
        assert price == 80.0
        assert qty == 5000

    def test_speculator_other_hours(self):
        """Speculator bids moderate during non-peak/non-night hours."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Spec", "speculator", capacity_mw=1000)
        price, qty = agent.bid(hour=10)
        assert price == 60.0
        assert qty == 100.0  # 1000 * 0.1

    def test_gas_bid_no_learning(self):
        """Gas agent with learning_rate=0 never changes bid."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Gas", "gas", capacity_mw=1500, marginal_cost=70.0, learning_rate=0.0)
        price1, _ = agent.bid(hour=10, market_price=100.0)
        price2, _ = agent.bid(hour=11, market_price=50.0)
        assert price1 == 70.0
        assert price2 == 70.0

    def test_renewable_bid_morning(self):
        """Renewable output ramps up in the morning."""
        from energy_algorithms.adapters.market_simulation import Agent

        agent = Agent("Solar", "renewable", capacity_mw=2000)
        price, qty = agent.bid(hour=7)  # sin(pi*1/12) > 0
        assert price == 0.5
        assert qty < 2000  # Not full capacity at 7am
        assert qty > 0


class TestMarketSession:
    """Tests for MarketSession."""

    def test_run_with_minimal_agents(self):
        """Run a market session with the minimum viable set of agents."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, area="BE", hour_count=4)
        result = session.run(verbose=False)

        assert "hourly_results" in result
        assert "agent_profits" in result
        assert "total_welfare" in result
        assert "total_volume" in result
        assert "avg_mcp" in result
        assert "num_agents" in result
        assert result["num_agents"] == 2
        assert len(result["hourly_results"]) == 4

    def test_run_with_default_market(self):
        """Run the default 7-agent market for a few hours."""
        from energy_algorithms.adapters.market_simulation import create_default_market

        session = create_default_market()
        assert len(session.agents) == 7
        session.hour_count = 3  # Run only 3 hours for speed
        result = session.run(verbose=False)

        assert result["total_volume"] >= 0
        assert result["total_welfare"] >= 0
        assert result["avg_mcp"] > 0
        assert result["min_mcp"] >= 0
        assert result["max_mcp"] >= 0
        assert "generator_profits" in result

    def test_run_24h_default_market(self):
        """Default market runs all 24 hours without error."""
        from energy_algorithms.adapters.market_simulation import create_default_market

        session = create_default_market()
        result = session.run(verbose=False)
        assert len(result["hourly_results"]) == 24

    def test_result_structure(self):
        """Verify all expected keys in the result dict."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, hour_count=2)
        result = session.run()
        expected_keys = {
            "hourly_results", "agent_profits", "total_welfare",
            "total_volume", "avg_mcp", "min_mcp", "max_mcp",
            "num_agents", "generator_profits",
        }
        assert set(result.keys()) == expected_keys

    def test_hourly_results_detail(self):
        """Each hourly result has the expected sub-keys."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, hour_count=2)
        result = session.run()
        for hr in result["hourly_results"]:
            assert "hour" in hr
            assert "mcp" in hr or "status" in hr

    def test_generator_profits(self):
        """Generator profits dict only includes non-demand agents."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gen1", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, hour_count=3)
        result = session.run()
        assert "Gen1" in result["generator_profits"]
        assert "Demand" not in result["generator_profits"]

    def test_agent_profit_tracking(self):
        """Agents accumulate profit and track trade history."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, hour_count=4)
        session.run()

        gas_agent = agents[0]
        if gas_agent.total_profit != 0:
            assert gas_agent.accepted_qty > 0
            assert gas_agent.total_revenue > 0
            assert len(gas_agent.trade_history) > 0

    def test_verbose_output(self):
        """Running with verbose=True does not crash."""
        from energy_algorithms.adapters.market_simulation import Agent, MarketSession

        agents = [
            Agent("Gas", "gas", capacity_mw=1000, marginal_cost=50.0),
            Agent("Demand", "demand", capacity_mw=2000, marginal_cost=0.0),
        ]
        session = MarketSession(agents, hour_count=2)
        result = session.run(verbose=True)
        assert result is not None
