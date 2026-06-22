"""SEC raw-first downloader for submissions, companyfacts, and filings.

Purpose:
    Fetch the minimal SEC artifacts required by the spike with a declared
    User-Agent, local 2 req/sec pacing, and raw body persistence before parse.

Call graph:
    cli fetch-sec -> fetch_sec_artifacts
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from step0b.hashing import sha256_bytes, sha256_file
from step0b.models import Company, read_json_file, write_json_file
from step0b.sec_filing import (
    filing_url,
    sec_filing_raw_path,
    sec_headers_path,
    sec_manifest_path,
    sec_raw_path,
)
from step0b.sec_submissions import latest_filing


SEC_USER_AGENT_ENV = "SEC_USER_AGENT"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
TIMEOUT_SECONDS = 45
SEC_DELAY_SECONDS = 0.55


def utc_now() -> str:
    """Return the current UTC timestamp.

    Returns:
        ISO-8601 timestamp with UTC offset.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def require_sec_user_agent() -> str:
    """Read and validate SEC_USER_AGENT.

    Returns:
        User-Agent string.

    Raises:
        RuntimeError: If SEC_USER_AGENT is missing.
    """
    if SEC_USER_AGENT_ENV not in os.environ:
        raise RuntimeError(f"{SEC_USER_AGENT_ENV} is required for online SEC fetch")
    user_agent = os.environ[SEC_USER_AGENT_ENV].strip()
    if user_agent == "":
        raise RuntimeError(f"{SEC_USER_AGENT_ENV} is required for online SEC fetch")
    return user_agent


def fetch_url(*, url: str, user_agent: str) -> dict[str, Any]:
    """Fetch one SEC URL.

    Args:
        url: SEC URL.
        user_agent: Declared identity string from environment.

    Returns:
        Dict containing status, headers, and raw bytes.
    """
    request = urllib.request.Request(
        url=url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json, text/html, */*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(url=request, timeout=TIMEOUT_SECONDS) as response:
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "raw_bytes": response.read(),
            }
    except urllib.error.HTTPError as error:
        # SEC error bodies are still source artifacts for diagnosing fetch policy.
        return {
            "status": error.code,
            "headers": dict(error.headers.items()),
            "raw_bytes": error.read(),
        }


def save_sec_response(
    *,
    raw_path: Path,
    fetched: dict[str, Any],
    url: str,
) -> None:
    """Persist SEC raw body, headers, and safe manifest.

    Args:
        raw_path: Destination raw path.
        fetched: Transport result from fetch_url.
        url: Request URL, safe because SEC has no API key.

    Returns:
        None. Raw files are written before any parsing happens.
    """
    raw_bytes = fetched["raw_bytes"]
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes must be bytes")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(data=raw_bytes)
    write_json_file(
        path=sec_headers_path(raw_path=raw_path),
        payload={
            "http_status": fetched["status"],
            "headers": fetched["headers"],
            "sha256": sha256_bytes(data=raw_bytes),
            "fetched_at": utc_now(),
        },
    )
    write_json_file(
        path=sec_manifest_path(raw_path=raw_path),
        payload={
            "url": url,
            "raw_file": str(raw_path),
            "http_status": fetched["status"],
            "sha256": sha256_file(path=raw_path),
            "fetched_at": utc_now(),
            "user_agent_supplied": True,
        },
    )


def fetch_if_needed(
    *,
    raw_path: Path,
    url: str,
    user_agent: str,
    refresh: bool,
) -> bool:
    """Fetch a SEC URL unless a cached raw file can be reused.

    Args:
        raw_path: Destination raw path.
        url: SEC URL.
        user_agent: Declared identity string from environment.
        refresh: True to overwrite existing raw files.

    Returns:
        True if a network request was made; False if skipped.
    """
    if raw_path.exists() and not refresh:
        return False
    fetched = fetch_url(url=url, user_agent=user_agent)
    save_sec_response(raw_path=raw_path, fetched=fetched, url=url)
    if fetched["status"] != 200:
        raise RuntimeError(f"SEC fetch returned HTTP {fetched['status']} for {url}")
    return True


def submissions_path(*, company: Company) -> Path:
    """Return the SEC submissions raw path for one company.

    Args:
        company: Experiment company.

    Returns:
        Raw JSON path.
    """
    return sec_raw_path(symbol=company.symbol, artifact_kind="submissions", suffix="json")


def companyfacts_path(*, company: Company) -> Path:
    """Return the SEC companyfacts raw path for one company.

    Args:
        company: Experiment company.

    Returns:
        Raw JSON path.
    """
    return sec_raw_path(
        symbol=company.symbol,
        artifact_kind="companyfacts",
        suffix="json",
    )


def fetch_company_sec(
    *,
    company: Company,
    user_agent: str,
    refresh: bool,
) -> int:
    """Fetch all required SEC artifacts for one company.

    Args:
        company: Experiment company.
        user_agent: Declared identity string from environment.
        refresh: True to overwrite existing raw files.

    Returns:
        Number of network calls made.
    """
    call_count = 0
    submissions_url = SEC_SUBMISSIONS.format(cik10=company.cik10)
    facts_url = SEC_COMPANYFACTS.format(cik10=company.cik10)
    if fetch_if_needed(
        raw_path=submissions_path(company=company),
        url=submissions_url,
        user_agent=user_agent,
        refresh=refresh,
    ):
        call_count += 1
        time.sleep(SEC_DELAY_SECONDS)
    if fetch_if_needed(
        raw_path=companyfacts_path(company=company),
        url=facts_url,
        user_agent=user_agent,
        refresh=refresh,
    ):
        call_count += 1
        time.sleep(SEC_DELAY_SECONDS)

    submissions = read_json_file(path=submissions_path(company=company))
    for forms in [{"10-K", "10-K/A"}, {"10-Q", "10-Q/A"}]:
        filing = latest_filing(submissions=submissions, forms=forms)
        url = filing_url(
            cik10=company.cik10,
            accession=filing["accessionNumber"],
            primary_document=filing["primaryDocument"],
        )
        raw_path = sec_filing_raw_path(
            symbol=company.symbol,
            form=filing["form"],
            accession=filing["accessionNumber"],
        )
        if fetch_if_needed(
            raw_path=raw_path,
            url=url,
            user_agent=user_agent,
            refresh=refresh,
        ):
            call_count += 1
            time.sleep(SEC_DELAY_SECONDS)
    return call_count


def fetch_sec_artifacts(*, companies: list[Company], refresh: bool) -> dict[str, int]:
    """Fetch all required SEC artifacts.

    Args:
        companies: Experiment companies.
        refresh: True to overwrite existing raw files.

    Returns:
        Summary with sec_call_count.
    """
    user_agent = require_sec_user_agent()
    sec_call_count = 0
    for company in companies:
        sec_call_count += fetch_company_sec(
            company=company,
            user_agent=user_agent,
            refresh=refresh,
        )
    return {"sec_call_count": sec_call_count}
