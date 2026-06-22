"""Alpha Vantage raw artifact discovery and archive registration.

Purpose:
    Reuse IBM's existing raw fixture without modifying it, and locate live
    cached JPM/CAT responses under the spike data directory.

Call graph:
    cli/comparison -> ensure_ibm_manifests/av_raw_path/load_av_payload
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from step0b.av_parser import parse_av_response
from step0b.hashing import sha256_file
from step0b.models import DATA_DIR, REPO_DIR, Company, read_json_file, write_json_file


ENDPOINTS = [
    "OVERVIEW",
    "INCOME_STATEMENT",
    "BALANCE_SHEET",
    "CASH_FLOW",
    "EARNINGS",
]

IBM_ARCHIVE_FILES = {
    "OVERVIEW": "001_overview_ibm.txt",
    "INCOME_STATEMENT": "002_income_statement_ibm.txt",
    "BALANCE_SHEET": "003_balance_sheet_ibm.txt",
    "CASH_FLOW": "004_cash_flow_ibm.txt",
    "EARNINGS": "005_earnings_ibm.txt",
}

LIVE_FILE_NAMES = {
    "OVERVIEW": "overview",
    "INCOME_STATEMENT": "income_statement",
    "BALANCE_SHEET": "balance_sheet",
    "CASH_FLOW": "cash_flow",
    "EARNINGS": "earnings",
}


def utc_now() -> str:
    """Return the current UTC timestamp.

    Returns:
        ISO-8601 timestamp with UTC offset.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def ibm_archive_path(*, endpoint: str) -> Path:
    """Return IBM's existing repository raw fixture path.

    Args:
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Absolute path to the existing raw fixture.
    """
    return (
        REPO_DIR
        / "artifacts"
        / "alpha_vantage"
        / "raw"
        / "demo"
        / IBM_ARCHIVE_FILES[endpoint]
    )


def live_raw_path(*, symbol: str, endpoint: str) -> Path:
    """Return the spike raw path for live-or-cached AV responses.

    Args:
        symbol: Company ticker.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Absolute raw path under data/raw/alpha_vantage.
    """
    safe_symbol = symbol.lower()
    safe_endpoint = LIVE_FILE_NAMES[endpoint]
    return DATA_DIR / "raw" / "alpha_vantage" / f"{safe_symbol}_{safe_endpoint}.txt"


def av_manifest_path(*, symbol: str, endpoint: str) -> Path:
    """Return the AV manifest path for one cached raw file.

    Args:
        symbol: Company ticker.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Absolute manifest path under data/raw/alpha_vantage.
    """
    safe_symbol = symbol.lower()
    safe_endpoint = LIVE_FILE_NAMES[endpoint]
    return (
        DATA_DIR
        / "raw"
        / "alpha_vantage"
        / f"{safe_symbol}_{safe_endpoint}.manifest.json"
    )


def av_headers_path(*, symbol: str, endpoint: str) -> Path:
    """Return the AV response headers path for one cached raw file.

    Args:
        symbol: Company ticker.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Absolute headers path under data/raw/alpha_vantage.
    """
    safe_symbol = symbol.lower()
    safe_endpoint = LIVE_FILE_NAMES[endpoint]
    return (
        DATA_DIR
        / "raw"
        / "alpha_vantage"
        / f"{safe_symbol}_{safe_endpoint}.headers.json"
    )


def av_raw_path(*, company: Company, endpoint: str) -> Path:
    """Return the raw file path for a company and endpoint.

    Args:
        company: Experiment company.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Existing IBM archive path or spike live-cache path.
    """
    if company.av_source == "existing_archive":
        return ibm_archive_path(endpoint=endpoint)
    return live_raw_path(symbol=company.symbol, endpoint=endpoint)


def ensure_ibm_manifests(*, company: Company) -> None:
    """Write local manifests that reference IBM's immutable existing fixture.

    Args:
        company: IBM company config.

    Returns:
        None. Manifest files are written under the spike raw directory.
    """
    for endpoint in ENDPOINTS:
        raw_path = ibm_archive_path(endpoint=endpoint)
        raw_text = raw_path.read_text(encoding="utf-8")
        parsed = parse_av_response(endpoint=endpoint, raw_text=raw_text)
        write_json_file(
            path=av_manifest_path(symbol=company.symbol, endpoint=endpoint),
            payload={
                "endpoint": endpoint,
                "symbol": company.symbol,
                "http_status": 200,
                "fetched_at": None,
                "sha256": sha256_file(path=raw_path),
                "raw_file": str(raw_path),
                "source": "existing_archive",
                "classification": parsed["classification"],
                "request_parameters": {
                    "function": endpoint,
                    "symbol": company.symbol,
                    "apikey": "REDACTED",
                },
                "registered_at": utc_now(),
            },
        )


def load_av_payload(*, company: Company, endpoint: str) -> dict[str, Any]:
    """Load and parse one AV raw artifact.

    Args:
        company: Experiment company.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Parsed AV response data.

    Raises:
        FileNotFoundError: If the required raw artifact is missing.
        ValueError: If the artifact is not classified as DATA_JSON.
    """
    raw_path = av_raw_path(company=company, endpoint=endpoint)
    raw_text = raw_path.read_text(encoding="utf-8")
    parsed = parse_av_response(endpoint=endpoint, raw_text=raw_text)
    if parsed["classification"] != "DATA_JSON":
        raise ValueError(
            f"{company.symbol} {endpoint} is {parsed['classification']}: "
            f"{parsed['message']}"
        )
    return parsed["data"]


def load_av_manifest(*, symbol: str, endpoint: str) -> dict[str, Any]:
    """Load one AV raw manifest.

    Args:
        symbol: Company ticker.
        endpoint: Alpha Vantage endpoint name.

    Returns:
        Manifest dict.
    """
    return read_json_file(path=av_manifest_path(symbol=symbol, endpoint=endpoint))
