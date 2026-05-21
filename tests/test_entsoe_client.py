"""Tests for the ENTSO-E Transparency Platform API client.

Uses unittest.mock to patch urllib.request.urlopen since the
client uses urllib (not requests) for HTTP calls.  Tests cover
successful parsing, error paths, and edge cases for all
document types.
"""
from __future__ import annotations

import unittest.mock
from urllib.error import HTTPError, URLError

import pytest

from energy_algorithms.adapters.entsoe_client import (
    EntsoeClient,
    fetch_demo_day_ahead,
    fetch_demo_generation_mix,
    BIDDING_ZONES,
    PSR_TYPES,
)

# ── XML response templates ─────────────────────────────────────────────

PRICE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <TimeSeries>
    <currency_Unit.name>EUR</currency_Unit.name>
    <price_Measure_Unit.name>MWh</price_Measure_Unit.name>
    <Period>
      <Point>
        <position>1</position>
        <price.amount>50.00</price.amount>
      </Point>
      <Point>
        <position>2</position>
        <price.amount>48.50</price.amount>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

GENERATION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <TimeSeries>
    <MktPSRType>
      <psrType>B14</psrType>
    </MktPSRType>
    <Period>
      <Point>
        <position>1</position>
        <quantity>4800.0</quantity>
      </Point>
      <Point>
        <position>2</position>
        <quantity>4750.0</quantity>
      </Point>
    </Period>
  </TimeSeries>
  <TimeSeries>
    <MktPSRType>
      <psrType>B04</psrType>
    </MktPSRType>
    <Period>
      <Point>
        <position>1</position>
        <quantity>2100.0</quantity>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

LOAD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <TimeSeries>
    <Period>
      <Point>
        <position>1</position>
        <quantity>8500.0</quantity>
      </Point>
      <Point>
        <position>2</position>
        <quantity>8200.0</quantity>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

ERROR_ACK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <Reason>
    <code>999</code>
    <text>No matching data found</text>
  </Reason>
</Acknowledgement_MarketDocument>"""


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_mock_response(xml_text: str, status: int = 200):
    """Create a mock HTTP response that returns the given XML text."""
    mock_resp = unittest.mock.MagicMock()
    mock_resp.read.return_value = xml_text.encode("utf-8")
    mock_resp.status = status
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def _make_mock_error_response(status_code: int, reason: str = "Bad Request"):
    """Create a mock that raises HTTPError."""
    import urllib.error

    error = urllib.error.HTTPError(
        "url", status_code, reason, {}, None
    )
    return error


# ── Tests ────────────────────────────────────────────────────────────────


class TestBuildUrl:
    """Tests for _build_url()."""

    def test_build_url_contains_all_params(self):
        """URL contains security token, document type, period, etc."""
        client = EntsoeClient(api_key="test-key-123")
        url = client._build_url("A44", "A01", BIDDING_ZONES["BE"], "2024-03-15")
        assert "securityToken=test-key-123" in url
        assert "documentType=A44" in url
        assert "processType=A01" in url
        assert "in_Domain=10YBE----------2" in url
        assert "periodStart=202403150000" in url
        assert "periodEnd=202403160000" in url


class TestFetchDayAheadPrices:
    """Tests for fetch_day_ahead_prices()."""

    def test_successful_parse(self):
        """Successfully parse day-ahead price XML."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen", return_value=_make_mock_response(PRICE_XML)
        ):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "ok"
        assert result["area"] == BIDDING_ZONES["BE"]
        assert result["date"] == "2024-03-15"
        assert len(result["prices"]) == 2
        assert result["prices"][0] == {"hour": 1, "price_eur_mwh": 50.0}
        assert result["prices"][1] == {"hour": 2, "price_eur_mwh": 48.5}
        assert result["currency"] == "EUR"
        assert result["unit"] == "MWh"
        assert result["avg_price"] > 0
        assert result["min_price"] > 0
        assert result["max_price"] > 0

    def test_http_401_error(self):
        """HTTP 401 returns Unauthorized error."""
        client = EntsoeClient(api_key="bad-key")
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.side_effect = HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        mock_resp.__enter__.return_value = mock_resp

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "Unauthorized" in result["error"]

    def test_http_other_error(self):
        """Other HTTP errors return status with error code."""
        client = EntsoeClient(api_key="test")
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.side_effect = HTTPError(
            "url", 404, "Not Found", {}, None
        )
        mock_resp.__enter__.return_value = mock_resp

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "HTTP 404" in result["error"]

    def test_network_error(self):
        """URLError returns network error message."""
        client = EntsoeClient(api_key="test")
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.side_effect = URLError(
            reason="Connection refused"
        )
        mock_resp.__enter__.return_value = mock_resp

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "Network error" in result["error"]

    def test_generic_exception(self):
        """Any other exception is caught and returned as error."""
        client = EntsoeClient(api_key="test")
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.side_effect = ValueError("Something went wrong")
        mock_resp.__enter__.return_value = mock_resp

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "Something went wrong" in result["error"]

    def test_xml_parse_error(self):
        """Invalid XML returns parse error."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_make_mock_response("not valid xml {{{"),
        ):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "XML parse error" in result["error"]

    def test_ack_error_response(self):
        """API acknowledgment with Reason element returns error."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_make_mock_response(ERROR_ACK_XML),
        ):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "error"
        assert "ENTSO-E API" in result["error"]

    def test_empty_prices(self):
        """Price XML with no Points returns empty prices list."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
          <TimeSeries>
            <currency_Unit.name>EUR</currency_Unit.name>
            <price_Measure_Unit.name>MWh</price_Measure_Unit.name>
          </TimeSeries>
        </Publication_MarketDocument>"""

        client = EntsoeClient(api_key="test")
        with unittest.mock.patch(
            "urllib.request.urlopen", return_value=_make_mock_response(xml)
        ):
            result = client.fetch_day_ahead_prices(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "ok"
        assert result["prices"] == []
        assert result["avg_price"] == 0


class TestFetchGenerationMix:
    """Tests for fetch_generation_mix()."""

    def test_successful_parse(self):
        """Successfully parse actual generation XML."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_make_mock_response(GENERATION_XML),
        ):
            result = client.fetch_generation_mix(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "ok"
        assert "generation" in result
        assert "total_mw" in result
        assert result["total_mw"] > 0
        # Should have nuclear and gas
        types = [g["type"] for g in result["generation"]]
        assert "Nuclear" in types
        assert "Fossil Gas" in types

    def test_psr_type_mapping(self):
        """PSR code maps to readable type name."""
        client = EntsoeClient(api_key="test")

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
          <TimeSeries>
            <MktPSRType>
              <psrType>B16</psrType>
            </MktPSRType>
            <Period>
              <Point>
                <position>1</position>
                <quantity>1000.0</quantity>
              </Point>
            </Period>
          </TimeSeries>
        </Publication_MarketDocument>"""

        with unittest.mock.patch(
            "urllib.request.urlopen", return_value=_make_mock_response(xml)
        ):
            result = client.fetch_generation_mix(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["generation"][0]["type"] == "Solar"

    def test_unknown_psr_type(self):
        """Unknown PSR code gets a fallback label."""
        client = EntsoeClient(api_key="test")

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
          <TimeSeries>
            <MktPSRType>
              <psrType>ZZZ</psrType>
            </MktPSRType>
            <Period>
              <Point>
                <position>1</position>
                <quantity>500.0</quantity>
              </Point>
            </Period>
          </TimeSeries>
        </Publication_MarketDocument>"""

        with unittest.mock.patch(
            "urllib.request.urlopen", return_value=_make_mock_response(xml)
        ):
            result = client.fetch_generation_mix(BIDDING_ZONES["BE"], "2024-03-15")

        assert "Unknown" in result["generation"][0]["type"]


class TestFetchLoadForecast:
    """Tests for fetch_load_forecast()."""

    def test_successful_parse(self):
        """Successfully parse load forecast XML."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_make_mock_response(LOAD_XML),
        ):
            result = client.fetch_load_forecast(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "ok"
        assert "load" in result
        assert len(result["load"]) == 2
        assert result["load"][0] == {"hour": 1, "mw": 8500.0}
        assert result["load"][1] == {"hour": 2, "mw": 8200.0}
        assert result["peak_mw"] == 8500.0
        assert result["avg_mw"] > 0

    def test_empty_load(self):
        """Load XML with no Points returns empty list."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
          <TimeSeries>
          </TimeSeries>
        </Publication_MarketDocument>"""

        client = EntsoeClient(api_key="test")
        with unittest.mock.patch(
            "urllib.request.urlopen", return_value=_make_mock_response(xml)
        ):
            result = client.fetch_load_forecast(BIDDING_ZONES["BE"], "2024-03-15")

        assert result["status"] == "ok"
        assert result["load"] == []
        assert result["peak_mw"] == 0
        assert result["avg_mw"] == 0


class TestUnsupportedDocumentType:
    """Test fallback for unsupported document types."""

    def test_unsupported_doc_type(self):
        """Unsupported document type returns raw data note."""
        client = EntsoeClient(api_key="test")

        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_make_mock_response(PRICE_XML),
        ):
            result = client._query(
                document_type="XXX",
                process_type="A01",
                area=BIDDING_ZONES["BE"],
                date="2024-03-15",
            )

        assert result["status"] == "ok"
        assert "Unsupported document type" in result["note"]
        assert result["raw_series_count"] == 1


class TestDemoFunctions:
    """Tests for the standalone demo data functions."""

    def test_fetch_demo_day_ahead(self):
        """Demo day-ahead prices contain 24 hours of realistic data."""
        result = fetch_demo_day_ahead()
        assert result["status"] == "ok (demo)"
        assert len(result["prices"]) == 24
        assert result["avg_price"] > 0
        assert result["min_price"] > 0
        assert result["max_price"] > result["min_price"]
        assert all(1 <= p["hour"] <= 24 for p in result["prices"])

    def test_fetch_demo_generation_mix(self):
        """Demo generation mix contains realistic Belgian mix."""
        result = fetch_demo_generation_mix()
        assert result["status"] == "ok (demo)"
        assert len(result["generation"]) > 0
        assert result["total_mw"] > 0
        # Nuclear should be the largest source
        nuclear = [g for g in result["generation"] if g["type"] == "Nuclear"]
        assert len(nuclear) > 0
        assert nuclear[0]["mw"] > 0


class TestConstants:
    """Tests for module-level constants."""

    def test_bidding_zones(self):
        """Common bidding zones are defined."""
        assert "BE" in BIDDING_ZONES
        assert "DE" in BIDDING_ZONES
        assert "FR" in BIDDING_ZONES
        assert len(BIDDING_ZONES) >= 8

    def test_psr_types(self):
        """PSR type mapping covers all common generation types."""
        assert "B14" in PSR_TYPES  # Nuclear
        assert "B04" in PSR_TYPES  # Fossil Gas
        assert "B16" in PSR_TYPES  # Solar
        assert "B19" in PSR_TYPES  # Wind Onshore
