"""ENTSO-E Transparency Platform API client.

Fetches electricity market data: day-ahead prices, generation mix,
installed capacity, and load forecasts for European bidding zones.

API docs: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
"""
from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any

# ENTSO-E API endpoints
BASE_URL = "https://web-api.tp.entsoe.eu/api"

# Standard document types (documentType)
DOC_DAY_AHEAD_PRICES = "A44"            # Day-ahead prices [12.1.D]
DOC_ACTUAL_GENERATION = "A75"           # Actual generation per type [16.1.B&C]
DOC_LOAD_FORECAST = "A65"               # Day-ahead load forecast [8.1.A]
DOC_INSTALLED_CAPACITY = "A68"          # Installed capacity per type [14.1.A]
DOC_CROSSBORDER_FLOWS = "A11"           # Scheduled commercial exchanges [11.1.A]

# Process types
PROCESS_DAY_AHEAD = "A01"
PROCESS_REALISED = "A16"

# Common EIC codes (bidding zones)
BIDDING_ZONES = {
    "BE": "10YBE----------2",   # Belgium
    "DE": "10Y1001A1001A82H",   # Germany
    "FR": "10YFR-RTE------C",   # France
    "NL": "10YNL----------L",   # Netherlands
    "UK": "10YGB----------A",   # United Kingdom
    "ES": "10YES-REE------0",   # Spain
    "IT": "10YIT-GRTN-----B",   # Italy
    "PL": "10YPL-AREA-----S",   # Poland
}

# PsrType codes for generation types
PSR_TYPES = {
    "B01": "Biomass",
    "B02": "Fossil Brown coal/Lignite",
    "B03": "Fossil Coal-derived gas",
    "B04": "Fossil Gas",
    "B05": "Fossil Hard coal",
    "B06": "Fossil Oil",
    "B07": "Fossil Oil shale",
    "B08": "Fossil Peat",
    "B09": "Geothermal",
    "B10": "Hydro Pumped Storage",
    "B11": "Hydro Run-of-river and poundage",
    "B12": "Hydro Water Reservoir",
    "B13": "Marine",
    "B14": "Nuclear",
    "B15": "Other renewable",
    "B16": "Solar",
    "B17": "Waste",
    "B18": "Wind Offshore",
    "B19": "Wind Onshore",
    "B20": "Other",
}


class EntsoeClient:
    """Client for the ENTSO-E Transparency Platform REST API.

    Requires a security token (API key) from:
    https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_authentication_and_authorisation

    Parameters
    ----------
    api_key : str
        ENTSO-E security token (base64-encoded string).
        Register at https://transparency.entsoe.eu → My Account → Web API.
    timeout : int
        Request timeout in seconds (default: 30).
    """

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    # ---- Public API --------------------------------------------------

    def fetch_day_ahead_prices(
        self,
        area: str,
        date: str,
    ) -> dict[str, Any]:
        """Fetch day-ahead electricity prices for a bidding zone.

        Parameters
        ----------
        area : str
            EIC code of the bidding zone (e.g., '10YBE----------2' for Belgium).
            Use BIDDING_ZONES dict for common codes.
        date : str
            Date in 'YYYY-MM-DD' format.

        Returns
        -------
        dict with keys: status, area, date, prices (list of {hour, price_eur_mwh}),
        currency, unit
        """
        return self._query(
            document_type=DOC_DAY_AHEAD_PRICES,
            process_type=PROCESS_DAY_AHEAD,
            area=area,
            date=date,
        )

    def fetch_generation_mix(
        self,
        area: str,
        date: str,
    ) -> dict[str, Any]:
        """Fetch actual generation output per production type.

        Parameters
        ----------
        area : str
            EIC code of the bidding zone.
        date : str
            Date in 'YYYY-MM-DD' format.

        Returns
        -------
        dict with keys: status, area, date, generation (list of {type, mw, psr_code}),
        total_mw
        """
        return self._query(
            document_type=DOC_ACTUAL_GENERATION,
            process_type=PROCESS_REALISED,
            area=area,
            date=date,
        )

    def fetch_load_forecast(
        self,
        area: str,
        date: str,
    ) -> dict[str, Any]:
        """Fetch day-ahead total load forecast.

        Parameters
        ----------
        area : str
            EIC code of the bidding zone.
        date : str
            Date in 'YYYY-MM-DD' format.

        Returns
        -------
        dict with keys: status, area, date, load (list of {hour, mw})
        """
        return self._query(
            document_type=DOC_LOAD_FORECAST,
            process_type=PROCESS_DAY_AHEAD,
            area=area,
            date=date,
        )

    # ---- Internal ----------------------------------------------------

    def _build_url(
        self,
        document_type: str,
        process_type: str,
        area: str,
        date: str,
    ) -> str:
        """Build the ENTSO-E API request URL.

        Parameters
        ----------
        document_type : str
            ENTSO-E document type code (e.g., 'A44' for day-ahead prices).
        process_type : str
            Process type ('A01' for day-ahead, 'A16' for realised).
        area : str
            EIC code of the bidding zone.
        date : str
            Date string in 'YYYY-MM-DD' format.

        Returns
        -------
        Full URL for the API request.
        """
        dt = datetime.strptime(date, "%Y-%m-%d")
        dt_end = dt + timedelta(days=1)
        period_start = dt.strftime("%Y%m%d0000")
        period_end = dt_end.strftime("%Y%m%d0000")

        params = {
            "securityToken": self.api_key,
            "documentType": document_type,
            "processType": process_type,
            "in_Domain": area,
            "out_Domain": area,
            "periodStart": period_start,
            "periodEnd": period_end,
        }
        return f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    def _query(
        self,
        document_type: str,
        process_type: str,
        area: str,
        date: str,
    ) -> dict[str, Any]:
        """Execute an ENTSO-E API query and parse the XML response.

        Parameters
        ----------
        document_type, process_type, area, date : str
            See _build_url.

        Returns
        -------
        dict with status, area, date, and parsed data.
        """
        url = self._build_url(document_type, process_type, area, date)

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                xml_text = resp.read().decode("utf-8")

            return self._parse_response(xml_text, document_type, area, date)

        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {
                    "status": "error",
                    "error": "Unauthorized — check your API key",
                    "area": area,
                    "date": date,
                }
            return {
                "status": "error",
                "error": f"HTTP {e.code}: {e.reason}",
                "area": area,
                "date": date,
            }
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error": f"Network error: {e.reason}",
                "area": area,
                "date": date,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "area": area,
                "date": date,
            }

    def _parse_response(
        self,
        xml_text: str,
        document_type: str,
        area: str,
        date: str,
    ) -> dict[str, Any]:
        """Parse ENTSO-E XML response into structured data.

        Parameters
        ----------
        xml_text : str
            Raw XML response from ENTSO-E API.
        document_type : str
            Document type code — determines parsing strategy.
        area, date : str
            Passed through to result.

        Returns
        -------
        dict with status and parsed data.
        """
        ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0"}

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return {
                "status": "error",
                "error": f"XML parse error: {e}",
                "area": area,
                "date": date,
            }

        # Check for acknowledgment / error response
        reason = root.find(".//ns:Reason/ns:text", ns)
        if reason is not None and reason.text:
            code_elem = reason.find("../ns:code", ns)
            code = code_elem.text if code_elem is not None else "unknown"
            return {
                "status": "error",
                "error": f"ENTSO-E API: [{code}] {reason.text}",
                "area": area,
                "date": date,
            }

        # ---- Day-ahead prices ----------------------------------------
        if document_type == DOC_DAY_AHEAD_PRICES:
            prices = []
            currency = "EUR"
            unit = "MWh"

            for ts in root.findall(".//ns:TimeSeries", ns):
                currency_elem = ts.find(".//ns:currency_Unit.name", ns)
                unit_elem = ts.find(".//ns:price_Measure_Unit.name", ns)
                if currency_elem is not None:
                    currency = currency_elem.text
                if unit_elem is not None:
                    unit = unit_elem.text

                for point in ts.findall(".//ns:Point", ns):
                    pos = int(point.find("ns:position", ns).text or "0")
                    price_elem = point.find("ns:price.amount", ns)
                    if price_elem is not None:
                        prices.append({
                            "hour": pos,
                            "price_eur_mwh": float(price_elem.text),
                        })

            prices.sort(key=lambda p: p["hour"])
            return {
                "status": "ok",
                "area": area,
                "date": date,
                "prices": prices,
                "currency": currency,
                "unit": unit,
                "avg_price": round(sum(p["price_eur_mwh"] for p in prices) / len(prices), 2) if prices else 0,
                "min_price": min((p["price_eur_mwh"] for p in prices), default=0),
                "max_price": max((p["price_eur_mwh"] for p in prices), default=0),
            }

        # ---- Actual generation mix -----------------------------------
        elif document_type == DOC_ACTUAL_GENERATION:
            generation = []
            total_mw = 0.0

            for ts in root.findall(".//ns:TimeSeries", ns):
                psr_elem = ts.find(".//ns:MktPSRType/ns:psrType", ns)
                psr_code = psr_elem.text if psr_elem is not None else "???"
                gen_type = PSR_TYPES.get(psr_code, f"Unknown ({psr_code})")

                values = []
                for point in ts.findall(".//ns:Point", ns):
                    qty_elem = point.find("ns:quantity", ns)
                    if qty_elem is not None:
                        values.append(float(qty_elem.text))

                avg_mw = round(sum(values) / len(values), 1) if values else 0.0
                generation.append({
                    "type": gen_type,
                    "mw": avg_mw,
                    "psr_code": psr_code,
                })
                total_mw += avg_mw

            generation.sort(key=lambda g: g["mw"], reverse=True)
            return {
                "status": "ok",
                "area": area,
                "date": date,
                "generation": generation,
                "total_mw": round(total_mw, 1),
            }

        # ---- Load forecast --------------------------------------------
        elif document_type == DOC_LOAD_FORECAST:
            load = []

            for ts in root.findall(".//ns:TimeSeries", ns):
                for point in ts.findall(".//ns:Point", ns):
                    pos = int(point.find("ns:position", ns).text or "0")
                    qty_elem = point.find("ns:quantity", ns)
                    if qty_elem is not None:
                        load.append({
                            "hour": pos,
                            "mw": float(qty_elem.text),
                        })

            load.sort(key=lambda p: p["hour"])
            return {
                "status": "ok",
                "area": area,
                "date": date,
                "load": load,
                "peak_mw": max((p["mw"] for p in load), default=0),
                "avg_mw": round(sum(p["mw"] for p in load) / len(load), 2) if load else 0,
            }

        # Fallback: return raw structure
        return {
            "status": "ok",
            "area": area,
            "date": date,
            "note": "Unsupported document type — returning raw data",
            "raw_series_count": len(root.findall(".//ns:TimeSeries", ns)),
        }


# ---- Demo data (no API key needed) ------------------------------------


def fetch_demo_day_ahead() -> dict[str, Any]:
    """Return realistic demo day-ahead prices for Belgium (March 2024).

    These are representative Belgian day-ahead market prices — not live data.
    For live data, use EntsoeClient with a valid API key.

    Returns
    -------
    dict with prices, area, date, and summary stats.
    """
    # Realistic Belgian day-ahead price profile (€/MWh)
    # Night trough, morning ramp, evening peak, night drop
    demo_prices = [
        65.2, 58.1, 52.3, 47.8, 45.6, 48.9,   # 00-05
        62.4, 78.5, 95.3, 102.7, 98.6, 88.2,  # 06-11
        82.1, 79.4, 76.8, 80.5, 94.2, 115.7,  # 12-17
        132.4, 125.8, 110.3, 95.6, 82.1, 70.4, # 18-23
    ]
    prices = [
        {"hour": h + 1, "price_eur_mwh": p}
        for h, p in enumerate(demo_prices)
    ]
    return {
        "status": "ok (demo)",
        "area": "10YBE----------2",
        "date": "2024-03-15",
        "prices": prices,
        "currency": "EUR",
        "unit": "MWh",
        "avg_price": round(sum(demo_prices) / len(demo_prices), 2),
        "min_price": min(demo_prices),
        "max_price": max(demo_prices),
        "note": "Demo data — use EntsoeClient with API key for live data",
    }


def fetch_demo_generation_mix() -> dict[str, Any]:
    """Return realistic demo generation mix for Belgium.

    Based on typical Belgian generation mix proportions (~12 GW peak demand).
    Nuclear dominates baseload, gas and wind provide the rest.

    Returns
    -------
    dict with generation breakdown by type.
    """
    generation = [
        {"type": "Nuclear", "mw": 4800, "psr_code": "B14"},
        {"type": "Fossil Gas", "mw": 2100, "psr_code": "B04"},
        {"type": "Wind Onshore", "mw": 1500, "psr_code": "B19"},
        {"type": "Wind Offshore", "mw": 900, "psr_code": "B18"},
        {"type": "Solar", "mw": 600, "psr_code": "B16"},
        {"type": "Hydro Run-of-river", "mw": 200, "psr_code": "B11"},
        {"type": "Biomass", "mw": 350, "psr_code": "B01"},
        {"type": "Hydro Pumped Storage", "mw": 150, "psr_code": "B10"},
        {"type": "Fossil Hard coal", "mw": 0, "psr_code": "B05"},  # Belgium phased out coal
    ]
    return {
        "status": "ok (demo)",
        "area": "10YBE----------2",
        "date": "2024-03-15",
        "generation": generation,
        "total_mw": sum(g["mw"] for g in generation),
        "note": "Demo data — use EntsoeClient with API key for live data",
    }
