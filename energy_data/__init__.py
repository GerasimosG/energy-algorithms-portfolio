"""Energy data pipeline — ENTSO-E Transparency Platform integration.

Fetches day-ahead electricity prices, generation mix, and load data
from the ENTSO-E Transparency Platform REST API.

Usage:
    from energy_data.fetcher import EntsoeClient
    client = EntsoeClient(api_key="your-key")
    prices = client.fetch_day_ahead_prices("10YBE----------2", "2024-01-01")
"""

from energy_data.config import ENTSOE_API_KEY
from energy_data.fetcher import EntsoeClient, fetch_demo_day_ahead, fetch_demo_generation_mix
from energy_data.demo import demo_energy_data
from energy_data.live_demo import demo_live_pipeline

__all__ = [
    "EntsoeClient", "ENTSOE_API_KEY", "fetch_demo_day_ahead",
    "fetch_demo_generation_mix", "demo_energy_data", "demo_live_pipeline",
]
