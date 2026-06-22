"""Alpha Vantage raw response parsing for the Step 0B endpoints.

Purpose:
    Classify only the five JSON core endpoints required by this spike. The
    parser avoids broad substring vendor-message detection and rejects generic
    CSV fallback because this spike does not call CSV endpoints.

Call graph:
    av_client/av_archive/comparison -> parse_av_response
"""

from __future__ import annotations

import json
from typing import Any


EXPECTED_ROOT_KEYS = {
    "OVERVIEW": {"Symbol"},
    "INCOME_STATEMENT": {"symbol", "annualReports", "quarterlyReports"},
    "BALANCE_SHEET": {"symbol", "annualReports", "quarterlyReports"},
    "CASH_FLOW": {"symbol", "annualReports", "quarterlyReports"},
    "EARNINGS": {"symbol", "annualEarnings", "quarterlyEarnings"},
}

VENDOR_KEYS = {"Information", "Note", "Error Message"}


def parse_av_response(*, endpoint: str, raw_text: str) -> dict[str, Any]:
    """Classify and parse one Alpha Vantage raw response.

    Args:
        endpoint: Alpha Vantage endpoint name.
        raw_text: Raw UTF-8 response body already saved to disk.

    Returns:
        Dict with classification, data, and optional message.
    """
    stripped = raw_text.strip()
    if stripped == "":
        return {"classification": "EMPTY", "data": None, "message": "empty body"}

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as error:
        return {
            "classification": "INVALID_JSON",
            "data": None,
            "message": f"json decode failed at {error.pos}",
        }

    if not isinstance(data, dict):
        return {
            "classification": "INVALID_JSON",
            "data": data,
            "message": "root is not an object",
        }

    for key in VENDOR_KEYS:
        if key in data:
            return {
                "classification": "VENDOR_RESPONSE",
                "data": data,
                "message": str(data[key]),
            }

    if endpoint not in EXPECTED_ROOT_KEYS:
        return {
            "classification": "UNSUPPORTED_ENDPOINT",
            "data": data,
            "message": endpoint,
        }

    missing = sorted(EXPECTED_ROOT_KEYS[endpoint] - set(data.keys()))
    if missing:
        return {
            "classification": "UNEXPECTED_JSON",
            "data": data,
            "message": ",".join(missing),
        }

    return {"classification": "DATA_JSON", "data": data, "message": ""}
