"""Alpha Vantage live fetcher with raw-first persistence.

Purpose:
    Fetch JPM/CAT core endpoints only when cached raw files are missing, write
    body and headers before parsing, and stop immediately on vendor responses.

Call graph:
    cli fetch-av -> fetch_alpha_vantage
"""

from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from step0b.av_archive import (
    ENDPOINTS,
    av_headers_path,
    av_manifest_path,
    live_raw_path,
)
from step0b.av_parser import parse_av_response
from step0b.hashing import sha256_bytes, sha256_file
from step0b.models import Company, write_json_file


BASE_URL = "https://www.alphavantage.co/query"
API_KEY_ENV = "ALPHAVANTAGE_API_KEY"
REQUEST_DELAY_SECONDS = 15.0
TIMEOUT_SECONDS = 30


def utc_now() -> str:
    """Return the current UTC timestamp.

    Returns:
        ISO-8601 timestamp with UTC offset.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def build_url(*, endpoint: str, symbol: str, api_key: str) -> str:
    """Build an Alpha Vantage URL with the real key for transport only.

    Args:
        endpoint: Alpha Vantage function.
        symbol: Company ticker.
        api_key: Secret API key read from environment.

    Returns:
        Full request URL. Callers must never persist this value.
    """
    params = {"function": endpoint, "symbol": symbol, "apikey": api_key}
    return f"{BASE_URL}?{urllib.parse.urlencode(query=params)}"


def redacted_parameters(*, endpoint: str, symbol: str) -> dict[str, str]:
    """Build safe request parameters for manifests.

    Args:
        endpoint: Alpha Vantage function.
        symbol: Company ticker.

    Returns:
        Dict with apikey redacted.
    """
    return {"function": endpoint, "symbol": symbol, "apikey": "REDACTED"}


def fetch_once(*, endpoint: str, symbol: str, api_key: str) -> dict[str, object]:
    """Fetch one Alpha Vantage endpoint.

    Args:
        endpoint: Alpha Vantage function.
        symbol: Company ticker.
        api_key: Secret API key read from environment.

    Returns:
        Dict containing status, headers, and raw bytes.
    """
    request = urllib.request.Request(
        url=build_url(endpoint=endpoint, symbol=symbol, api_key=api_key),
        method="GET",
    )
    with urllib.request.urlopen(url=request, timeout=TIMEOUT_SECONDS) as response:
        return {
            "status": response.status,
            "headers": dict(response.headers.items()),
            "raw_bytes": response.read(),
        }


def save_response(
    *,
    company: Company,
    endpoint: str,
    fetched: dict[str, object],
) -> str:
    """Persist raw body and headers before parsing.

    Args:
        company: Experiment company.
        endpoint: Alpha Vantage endpoint name.
        fetched: Transport result from fetch_once.

    Returns:
        Raw text decoded as UTF-8.
    """
    raw_bytes = fetched["raw_bytes"]
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes must be bytes")
    raw_text = raw_bytes.decode(encoding="utf-8", errors="replace")
    raw_path = live_raw_path(symbol=company.symbol, endpoint=endpoint)
    headers_path = av_headers_path(symbol=company.symbol, endpoint=endpoint)
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    # Raw body is saved before classification so failed parses remain auditable.
    raw_path.write_text(data=raw_text, encoding="utf-8")
    write_json_file(
        path=headers_path,
        payload={
            "endpoint": endpoint,
            "symbol": company.symbol,
            "http_status": fetched["status"],
            "headers": fetched["headers"],
            "fetched_at": utc_now(),
            "sha256": sha256_bytes(data=raw_bytes),
            "request_parameters": redacted_parameters(
                endpoint=endpoint,
                symbol=company.symbol,
            ),
        },
    )
    return raw_text


def write_manifest(
    *,
    company: Company,
    endpoint: str,
    status: int,
    raw_text: str,
    classification: str,
    message: str,
) -> None:
    """Write the safe AV manifest for one response.

    Args:
        company: Experiment company.
        endpoint: Alpha Vantage endpoint name.
        status: HTTP status code.
        raw_text: Saved raw response text.
        classification: Parser classification.
        message: Parser diagnostic message.

    Returns:
        None. Manifest is written beside raw.
    """
    raw_path = live_raw_path(symbol=company.symbol, endpoint=endpoint)
    write_json_file(
        path=av_manifest_path(symbol=company.symbol, endpoint=endpoint),
        payload={
            "endpoint": endpoint,
            "symbol": company.symbol,
            "http_status": status,
            "fetched_at": utc_now(),
            "sha256": sha256_file(path=raw_path),
            "raw_file": str(raw_path),
            "source": "live_or_cached",
            "classification": classification,
            "message": message,
            "request_parameters": redacted_parameters(
                endpoint=endpoint,
                symbol=company.symbol,
            ),
        },
    )


def fetch_alpha_vantage(
    *,
    companies: list[Company],
    refresh: bool,
    delay_seconds: float = REQUEST_DELAY_SECONDS,
) -> dict[str, int]:
    """Fetch missing JPM/CAT Alpha Vantage raw responses.

    Args:
        companies: Experiment companies.
        refresh: True to overwrite existing cached raw files.
        delay_seconds: Serial delay between live calls.

    Returns:
        Summary with live_call_count and skipped_count.

    Raises:
        RuntimeError: If the API key is missing or a vendor response appears.
    """
    if API_KEY_ENV not in os.environ or os.environ[API_KEY_ENV].strip() == "":
        raise RuntimeError(f"{API_KEY_ENV} is required for online AV fetch")
    api_key = os.environ[API_KEY_ENV]
    live_call_count = 0
    skipped_count = 0

    for company in companies:
        if company.av_source == "existing_archive":
            skipped_count += len(ENDPOINTS)
            continue
        for endpoint in ENDPOINTS:
            raw_path = live_raw_path(symbol=company.symbol, endpoint=endpoint)
            if raw_path.exists() and not refresh:
                skipped_count += 1
                continue
            if live_call_count > 0:
                time.sleep(delay_seconds)
            fetched = fetch_once(
                endpoint=endpoint,
                symbol=company.symbol,
                api_key=api_key,
            )
            raw_text = save_response(
                company=company,
                endpoint=endpoint,
                fetched=fetched,
            )
            parsed = parse_av_response(endpoint=endpoint, raw_text=raw_text)
            status = fetched["status"]
            if not isinstance(status, int):
                raise TypeError("http status must be int")
            write_manifest(
                company=company,
                endpoint=endpoint,
                status=status,
                raw_text=raw_text,
                classification=parsed["classification"],
                message=parsed["message"],
            )
            live_call_count += 1
            if parsed["classification"] == "VENDOR_RESPONSE":
                raise RuntimeError(
                    f"Alpha Vantage vendor response for "
                    f"{company.symbol} {endpoint}; stopped after saving raw"
                )
    return {"live_call_count": live_call_count, "skipped_count": skipped_count}
