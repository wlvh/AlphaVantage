#!/usr/bin/env python3
"""Verify Alpha Vantage response schemas from observed API responses.

Purpose:
    This script runs the single-goal verification plan in
    alpha_vantage_codex_single_goal_no_claude.txt. The default mode calls the
    planned endpoints, saves raw responses before parsing, derives observed
    JSON/CSV key schemas, and writes the required report artifacts. The
    --from-raw mode reparses existing raw responses without network calls.

Call graph:
    main -> call_endpoint -> fetch_once -> save_response_files -> parse_response
    main -> build_observed_output -> build_markdown_report

Inputs:
    Optional environment variable ALPHAVANTAGE_API_KEY for default network
    mode only. The --from-raw mode ignores environment keys and reads only
    artifacts/alpha_vantage/raw/.

Outputs:
    reports/alpha_vantage_observed_schema.md
    reports/alpha_vantage_observed_schema.json
    reports/alpha_vantage_next_run_queue.json
    artifacts/alpha_vantage/call_log.jsonl
    artifacts/alpha_vantage/state.json
"""

from __future__ import annotations

import csv
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any


BASE_URL = "https://www.alphavantage.co/query"
API_KEY_ENV = "ALPHAVANTAGE_API_KEY"
DEMO_KEY = "demo"
MAX_DEMO_CALLS = 20
MAX_REAL_CALLS = 6
TIMEOUT_SECONDS = 20
ARRAY_INSPECT_LIMIT = 10
EXAMPLE_LIMIT = 3
REQUEST_DELAY_SECONDS = 13.0

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT_DIR / "artifacts" / "alpha_vantage"
REPORT_DIR = ROOT_DIR / "reports"
CALL_LOG_PATH = ARTIFACT_DIR / "call_log.jsonl"
REPARSE_LOG_PATH = ARTIFACT_DIR / "reparse_log.jsonl"
REPARSE_STATE_PATH = ARTIFACT_DIR / "reparse_state.json"

NUMERIC_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NEWS_TIME_RE = re.compile(r"^\d{8}T\d{6}$")


@dataclass(frozen=True)
class Endpoint:
    """Describe one API endpoint planned by the execution spec.

    Args:
        endpoint_id: Stable local ID used for artifact names.
        api_function: Alpha Vantage function parameter.
        family: Logical report family used for grouping findings.
        params: Exact query parameters from the execution spec, excluding
            apikey. Values are strings.
    """

    endpoint_id: str
    api_function: str
    family: str
    params: dict[str, str]


ENDPOINTS = [
    Endpoint(
        endpoint_id="overview_ibm",
        api_function="OVERVIEW",
        family="fundamentals",
        params={"function": "OVERVIEW", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="income_statement_ibm",
        api_function="INCOME_STATEMENT",
        family="fundamentals",
        params={"function": "INCOME_STATEMENT", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="balance_sheet_ibm",
        api_function="BALANCE_SHEET",
        family="fundamentals",
        params={"function": "BALANCE_SHEET", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="cash_flow_ibm",
        api_function="CASH_FLOW",
        family="fundamentals",
        params={"function": "CASH_FLOW", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="earnings_ibm",
        api_function="EARNINGS",
        family="fundamentals",
        params={"function": "EARNINGS", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="dividends_ibm",
        api_function="DIVIDENDS",
        family="fundamentals",
        params={"function": "DIVIDENDS", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="insider_transactions_ibm",
        api_function="INSIDER_TRANSACTIONS",
        family="fundamentals",
        params={"function": "INSIDER_TRANSACTIONS", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="shares_outstanding_msft",
        api_function="SHARES_OUTSTANDING",
        family="shares_outstanding",
        params={"function": "SHARES_OUTSTANDING", "symbol": "MSFT"},
    ),
    Endpoint(
        endpoint_id="earnings_estimates_ibm",
        api_function="EARNINGS_ESTIMATES",
        family="estimates",
        params={"function": "EARNINGS_ESTIMATES", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="splits_ibm",
        api_function="SPLITS",
        family="splits",
        params={"function": "SPLITS", "symbol": "IBM"},
    ),
    Endpoint(
        endpoint_id="news_sentiment_aapl_latest",
        api_function="NEWS_SENTIMENT",
        family="news_sentiment",
        params={
            "function": "NEWS_SENTIMENT",
            "tickers": "AAPL",
            "sort": "LATEST",
            "limit": "10",
        },
    ),
    Endpoint(
        endpoint_id="news_sentiment_technology_latest",
        api_function="NEWS_SENTIMENT",
        family="news_sentiment",
        params={
            "function": "NEWS_SENTIMENT",
            "topics": "technology",
            "sort": "LATEST",
            "limit": "10",
        },
    ),
    Endpoint(
        endpoint_id="earnings_call_transcript_ibm_2024q1",
        api_function="EARNINGS_CALL_TRANSCRIPT",
        family="earnings_call_transcript",
        params={
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": "IBM",
            "quarter": "2024Q1",
        },
    ),
    Endpoint(
        endpoint_id="listing_status",
        api_function="LISTING_STATUS",
        family="listings",
        params={"function": "LISTING_STATUS"},
    ),
    Endpoint(
        endpoint_id="earnings_calendar_ibm_12month",
        api_function="EARNINGS_CALENDAR",
        family="earnings_calendar",
        params={
            "function": "EARNINGS_CALENDAR",
            "symbol": "IBM",
            "horizon": "12month",
        },
    ),
]

REAL_FALLBACK_PRIORITY = [
    "news_sentiment_aapl_latest",
    "news_sentiment_technology_latest",
    "shares_outstanding_msft",
    "earnings_calendar_ibm_12month",
    "overview_ibm",
    "income_statement_ibm",
    "balance_sheet_ibm",
    "cash_flow_ibm",
    "earnings_ibm",
    "dividends_ibm",
    "insider_transactions_ibm",
    "earnings_estimates_ibm",
    "splits_ibm",
    "earnings_call_transcript_ibm_2024q1",
]


def utc_now() -> str:
    """Return the current UTC timestamp.

    Returns:
        ISO-8601 timestamp with UTC offset.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def write_json_file(*, path: Path, payload: Any) -> None:
    """Write JSON with UTF-8 encoding and deterministic ordering.

    Args:
        path: Output file path.
        payload: JSON-serializable value.

    Returns:
        None. The file is written as UTF-8 text.
    """
    # Stable formatting makes reruns diffable and keeps review focused.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        data=json.dumps(obj=payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def ensure_output_dirs() -> None:
    """Create every output directory required by the execution spec.

    Returns:
        None. Missing directories are created.
    """
    # The raw directories are explicit because completion requires their paths.
    for path in [
        ARTIFACT_DIR / "raw" / "demo",
        ARTIFACT_DIR / "raw" / "real",
        ARTIFACT_DIR / "schema",
        REPORT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def endpoint_by_id() -> dict[str, Endpoint]:
    """Index endpoint definitions by local endpoint ID.

    Returns:
        Mapping of endpoint_id to Endpoint.
    """
    indexed: dict[str, Endpoint] = {}
    for endpoint in ENDPOINTS:
        indexed[endpoint.endpoint_id] = endpoint
    return indexed


def build_url(*, endpoint: Endpoint, api_key: str) -> str:
    """Build the concrete Alpha Vantage GET URL for one endpoint.

    Args:
        endpoint: Endpoint definition with exact spec parameters.
        api_key: API key value for the request. This value is never logged.

    Returns:
        Full request URL.
    """
    # The request needs the real key, but downstream logs use redacted_url only.
    params = dict(endpoint.params)
    params["apikey"] = api_key
    query = urllib.parse.urlencode(query=params)
    return f"{BASE_URL}?{query}"


def redacted_url(*, endpoint: Endpoint) -> str:
    """Build the redacted URL written to artifacts.

    Args:
        endpoint: Endpoint definition.

    Returns:
        URL with apikey=REDACTED.
    """
    # Redaction is centralized so no artifact can accidentally include the key.
    params = dict(endpoint.params)
    params["apikey"] = "REDACTED"
    query = urllib.parse.urlencode(query=params)
    return f"{BASE_URL}?{query}"


def is_timeout_error(*, error_text: str) -> bool:
    """Detect network timeout text eligible for one retry.

    Args:
        error_text: Captured network exception text.

    Returns:
        True when the error is a timeout before a response body exists.
    """
    lowered = error_text.lower()
    return "timed out" in lowered or "timeout" in lowered


def fetch_once(*, endpoint: Endpoint, api_key: str) -> dict[str, Any]:
    """Attempt one HTTP GET request.

    Args:
        endpoint: Endpoint definition.
        api_key: API key value, never returned.

    Returns:
        Dict containing status, headers, raw bytes, and network error metadata.
    """
    url = build_url(endpoint=endpoint, api_key=api_key)
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(url=request, timeout=TIMEOUT_SECONDS) as response:
            # Reading once ensures the body that gets classified is exactly saved.
            raw_bytes = response.read()
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "raw_bytes": raw_bytes,
                "network_error": None,
                "network_timeout": False,
            }
    except urllib.error.HTTPError as error:
        print(
            f"[http_error] {endpoint.endpoint_id} returned HTTP {error.code}; "
            "saving vendor body for classification."
        )
        return {
            "status": error.code,
            "headers": dict(error.headers.items()),
            "raw_bytes": error.read(),
            "network_error": None,
            "network_timeout": False,
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        error_text = str(error)
        print(
            f"[network_error] {endpoint.endpoint_id} failed before a usable "
            f"response body: {error.__class__.__name__}"
        )
        return {
            "status": None,
            "headers": {},
            "raw_bytes": b"",
            "network_error": error_text,
            "network_timeout": is_timeout_error(error_text=error_text),
        }


def decode_raw_bytes(*, endpoint_id: str, raw_bytes: bytes) -> str:
    """Decode response bytes as UTF-8 text.

    Args:
        endpoint_id: Endpoint ID used in diagnostic messages.
        raw_bytes: Raw response bytes.

    Returns:
        UTF-8 text, replacing invalid bytes only when decoding fails.
    """
    try:
        return raw_bytes.decode(encoding="utf-8")
    except UnicodeDecodeError as error:
        print(
            f"[decode_warning] {endpoint_id} had invalid UTF-8 bytes at "
            f"offset {error.start}; replacement decoding was used."
        )
        return raw_bytes.decode(encoding="utf-8", errors="replace")


def save_response_files(
    *,
    key_kind: str,
    sequence: int,
    endpoint: Endpoint,
    fetched: dict[str, Any],
) -> dict[str, str]:
    """Save raw response text and HTTP metadata before parsing.

    Args:
        key_kind: "demo" or "real".
        sequence: Monotonic request sequence for stable filenames.
        endpoint: Endpoint definition.
        fetched: Fetch result from fetch_once.

    Returns:
        Dict with raw_path and headers_path relative to repository root.
    """
    raw_text = decode_raw_bytes(
        endpoint_id=endpoint.endpoint_id,
        raw_bytes=fetched["raw_bytes"],
    )
    raw_base = ARTIFACT_DIR / "raw" / key_kind
    stem = f"{sequence:03d}_{endpoint.endpoint_id}"
    raw_path = raw_base / f"{stem}.txt"
    headers_path = raw_base / f"{stem}_headers.json"

    # Raw text is persisted before any schema or vendor-message parsing runs.
    raw_path.write_text(data=raw_text, encoding="utf-8")
    write_json_file(
        path=headers_path,
        payload={
            "endpoint_id": endpoint.endpoint_id,
            "fetched_at_utc": utc_now(),
            "headers": fetched["headers"],
            "key_kind": key_kind,
            "request_url": redacted_url(endpoint=endpoint),
            "status": fetched["status"],
        },
    )
    return {
        "raw_path": str(raw_path.relative_to(ROOT_DIR)),
        "headers_path": str(headers_path.relative_to(ROOT_DIR)),
        "raw_text": raw_text,
    }


def json_type_name(*, value: Any) -> str:
    """Return the observed JSON type name for one value.

    Args:
        value: JSON-decoded value.

    Returns:
        One of null, boolean, number, string, object, array, or unknown.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "unknown"


def semantic_type(*, value: Any) -> str:
    """Infer a compact semantic type from an observed value.

    Args:
        value: JSON or CSV scalar value.

    Returns:
        Semantic type such as numeric_string, date_yyyy_mm_dd, empty_string, or
        av_news_timestamp.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (dict, list)):
        return json_type_name(value=value)

    text = str(value)
    stripped = text.strip()
    if stripped == "":
        return "empty_string"
    if stripped == "None":
        return "literal_string_none"
    if DATE_RE.match(string=stripped):
        return "date_yyyy_mm_dd"
    if NEWS_TIME_RE.match(string=stripped):
        return "alpha_vantage_news_timestamp"
    if NUMERIC_RE.match(string=stripped):
        return "numeric_string"
    return "string"


def scalar_example(*, value: Any) -> str:
    """Convert an observed value into a bounded example string.

    Args:
        value: Observed JSON or CSV value.

    Returns:
        Example string capped to keep artifacts compact.
    """
    text = json.dumps(obj=value, ensure_ascii=False)
    if len(text) <= 140:
        return text
    return f"{text[:137]}..."


def add_unique(*, values: list[str], value: str) -> None:
    """Append a value only if it has not appeared before.

    Args:
        values: Mutable list of existing values.
        value: Candidate value.

    Returns:
        None. The list may be mutated.
    """
    # Preserving first-seen order keeps examples reviewable.
    if value not in values:
        values.append(value)


def ensure_field_record(
    *,
    fields: dict[str, dict[str, Any]],
    path: str,
) -> dict[str, Any]:
    """Create or return the schema record for a field path.

    Args:
        fields: Mutable schema mapping.
        path: JSONPath-like field path.

    Returns:
        Mutable field record.
    """
    if path not in fields:
        fields[path] = {
            "appearance_count": 0,
            "examples": [],
            "json_types": [],
            "semantic_types": [],
        }
    return fields[path]


def observe_json_value(
    *,
    fields: dict[str, dict[str, Any]],
    path: str,
    value: Any,
) -> None:
    """Record type, semantic type, example, and count for one JSON value.

    Args:
        fields: Mutable schema mapping.
        path: JSONPath-like location.
        value: JSON-decoded value at that path.

    Returns:
        None. The schema mapping is updated.
    """
    record = ensure_field_record(fields=fields, path=path)
    record["appearance_count"] += 1
    add_unique(values=record["json_types"], value=json_type_name(value=value))
    add_unique(values=record["semantic_types"], value=semantic_type(value=value))

    # Examples are bounded because long article summaries can dominate reports.
    if len(record["examples"]) < EXAMPLE_LIMIT:
        add_unique(values=record["examples"], value=scalar_example(value=value))

    if isinstance(value, dict):
        for key in sorted(value.keys()):
            observe_json_value(
                fields=fields,
                path=f"{path}.{key}",
                value=value[key],
            )
        return

    if isinstance(value, list):
        for item in value[:ARRAY_INSPECT_LIMIT]:
            observe_json_value(fields=fields, path=f"{path}[]", value=item)


def extract_json_schema(*, data: Any) -> dict[str, Any]:
    """Extract observed schema from a JSON response.

    Args:
        data: JSON-decoded response object.

    Returns:
        Schema dict with root keys and field-path observations.
    """
    fields: dict[str, dict[str, Any]] = {}
    observe_json_value(fields=fields, path="$", value=data)

    root_keys: list[str] = []
    if isinstance(data, dict):
        root_keys = sorted(data.keys())

    return {
        "format": "json",
        "root_keys": root_keys,
        "fields": fields,
    }


def parse_csv_rows(*, raw_text: str) -> dict[str, Any]:
    """Parse CSV text and inspect the first rows.

    Args:
        raw_text: Raw response text already saved to disk.

    Returns:
        Dict with header columns and sampled rows.
    """
    reader = csv.DictReader(f=StringIO(initial_value=raw_text))
    fieldnames: list[str] = []
    if reader.fieldnames is not None:
        fieldnames = [field for field in reader.fieldnames]

    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            cleaned[key] = ""
            if value is not None:
                cleaned[key] = value
        rows.append(cleaned)
        if len(rows) >= ARRAY_INSPECT_LIMIT:
            break

    return {"columns": fieldnames, "rows": rows}


def extract_csv_schema(*, raw_text: str) -> dict[str, Any]:
    """Extract observed schema from a CSV response.

    Args:
        raw_text: Raw response text already saved to disk.

    Returns:
        Schema dict with columns, examples, and blank behavior.
    """
    parsed = parse_csv_rows(raw_text=raw_text)
    columns = parsed["columns"]
    rows = parsed["rows"]
    column_records: dict[str, dict[str, Any]] = {}

    for column in columns:
        column_records[column] = {
            "appearance_count": 0,
            "blank_count": 0,
            "examples": [],
            "semantic_types": [],
        }

    for row in rows:
        for column in columns:
            value = ""
            if column in row:
                value = row[column]
            record = column_records[column]
            record["appearance_count"] += 1
            if value == "":
                record["blank_count"] += 1
            add_unique(
                values=record["semantic_types"],
                value=semantic_type(value=value),
            )
            if len(record["examples"]) < EXAMPLE_LIMIT:
                add_unique(values=record["examples"], value=scalar_example(value=value))

    return {
        "format": "csv",
        "columns": columns,
        "columns_observed": column_records,
        "rows_inspected": len(rows),
    }


def vendor_classification_from_text(*, text: str) -> str | None:
    """Classify known vendor messages in JSON scalar or short text responses.

    This function must not be used as a broad substring scanner over CSV
    payloads. Valid CSV bodies can contain words such as "Information" or
    "Note" in company names, security names, article titles, or summaries.

    Args:
        text: Response body or vendor-message scalar.

    Returns:
        Classification string, or None when no vendor message is detected.
    """
    stripped = text.strip()
    lowered = stripped.lower()

    # CSV/text vendor messages are short. Large tabular payloads should be
    # classified by CSV shape before any substring-based vendor heuristic.
    if len(stripped) > 5000 or stripped.count("\n") > 5:
        return None

    # Helper callers should get the same protection as parse_response: if a
    # short payload is still a valid table, schema extraction owns it.
    if csv_has_usable_shape(raw_text=stripped):
        return None

    if "rate limit" in lowered or "call frequency" in lowered or "quota" in lowered:
        return "rate_limit_or_quota"
    if "invalid api call" in lowered or "error message" in lowered:
        return "vendor_error"
    if "thank you for using alpha vantage" in lowered:
        return "vendor_information"
    if "premium" in lowered or "please visit" in lowered:
        return "vendor_information"

    # Only treat bare "information" / "note" as a vendor message when the
    # whole response is a short, non-tabular sentence. Do not match arbitrary
    # company names like "Cass Information Systems".
    if lowered.startswith("information") or lowered.startswith("{\"information\""):
        return "vendor_information"
    if lowered.startswith("note") or lowered.startswith("{\"note\""):
        return "vendor_note"
    return None


def classify_json_payload(*, data: Any) -> str:
    """Classify a decoded JSON response.

    Args:
        data: JSON-decoded response object.

    Returns:
        One required response classification.
    """
    if isinstance(data, dict):
        if "Information" in data:
            classified = vendor_classification_from_text(text=str(data["Information"]))
            if classified is not None:
                return classified
            return "vendor_information"
        if "Note" in data:
            classified = vendor_classification_from_text(text=str(data["Note"]))
            if classified is not None:
                return classified
            return "vendor_note"
        if "Error Message" in data:
            return "vendor_error"
        if len(data) == 0:
            return "empty_or_invalid"
        return "data_json"

    if isinstance(data, list) and len(data) > 0:
        return "data_json"
    return "empty_or_invalid"


def csv_has_usable_shape(*, raw_text: str) -> bool:
    """Decide whether text has a usable CSV table shape.

    Args:
        raw_text: Response text already saved to disk.

    Returns:
        True when a plausible multi-column CSV header exists.
    """
    parsed = parse_csv_rows(raw_text=raw_text)
    columns = [column.strip() for column in parsed["columns"]]
    if len(columns) < 2:
        return False

    # Reject comma-split vendor sentences such as "I,n,f,o,r,m,a...".
    if all(len(column) <= 1 for column in columns):
        return False

    lowered_columns = {column.lower() for column in columns}
    known_csv_headers = [
        {
            "symbol",
            "name",
            "exchange",
            "assettype",
            "ipodate",
            "delistingdate",
            "status",
        },
        {
            "symbol",
            "name",
            "reportdate",
            "fiscaldateending",
            "estimate",
            "currency",
            "timeoftheday",
        },
    ]
    if any(expected.issubset(lowered_columns) for expected in known_csv_headers):
        return True

    # For unknown CSV endpoints, require at least one data row to avoid treating
    # a comma-heavy vendor sentence as a table.
    return len(parsed["rows"]) >= 1


def parse_response(*, status: int | None, raw_text: str) -> dict[str, Any]:
    """Classify and parse a saved response body.

    Args:
        status: HTTP status, or None for network errors.
        raw_text: Raw response text already saved to disk.

    Returns:
        Dict with classification, parsed data, and schema where available.
    """
    if status is None:
        return {"classification": "network_error", "data": None, "schema": None}
    if status >= 400:
        return {"classification": "http_error", "data": None, "schema": None}

    stripped = raw_text.strip()
    if stripped == "":
        return {"classification": "empty_or_invalid", "data": None, "schema": None}

    if stripped.startswith(("{", "[")):
        try:
            data = json.loads(s=stripped)
        except json.JSONDecodeError as error:
            print(
                f"[json_parse_error] JSON-like response failed at char "
                f"{error.pos}; checking CSV fallback."
            )
        else:
            classification = classify_json_payload(data=data)
            schema = None
            if classification == "data_json":
                schema = extract_json_schema(data=data)
            return {
                "classification": classification,
                "data": data,
                "schema": schema,
            }

    if csv_has_usable_shape(raw_text=raw_text):
        return {
            "classification": "data_csv",
            "data": None,
            "schema": extract_csv_schema(raw_text=raw_text),
        }

    vendor_classification = vendor_classification_from_text(text=stripped)
    if vendor_classification is not None:
        return {
            "classification": vendor_classification,
            "data": None,
            "schema": None,
        }

    return {"classification": "empty_or_invalid", "data": None, "schema": None}


def append_call_log(*, entry: dict[str, Any]) -> None:
    """Append one JSONL call-log entry.

    Args:
        entry: Redacted, JSON-serializable request log entry.

    Returns:
        None. One line is appended to call_log.jsonl.
    """
    # JSONL keeps each attempted request auditable and countable.
    with CALL_LOG_PATH.open(mode="a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj=entry, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def call_endpoint(
    *,
    key_kind: str,
    sequence: int,
    endpoint: Endpoint,
    api_key: str,
) -> dict[str, Any]:
    """Call one endpoint once, persist raw files, parse, and log.

    Args:
        key_kind: "demo" or "real".
        sequence: Monotonic request sequence.
        endpoint: Endpoint definition.
        api_key: Request API key value, never written to artifacts.

    Returns:
        Request result with classification and optional schema.
    """
    fetched = fetch_once(endpoint=endpoint, api_key=api_key)
    saved = save_response_files(
        key_kind=key_kind,
        sequence=sequence,
        endpoint=endpoint,
        fetched=fetched,
    )
    parsed = parse_response(status=fetched["status"], raw_text=saved["raw_text"])

    schema_path = None
    if parsed["schema"] is not None:
        schema_path = (
            ARTIFACT_DIR / "schema" / f"{endpoint.endpoint_id}_{key_kind}.json"
        )
        write_json_file(
            path=schema_path,
            payload={
                "endpoint_id": endpoint.endpoint_id,
                "generated_at_utc": utc_now(),
                "key_kind": key_kind,
                "schema": parsed["schema"],
            },
        )

    log_entry = {
        "attempt_sequence": sequence,
        "classification": parsed["classification"],
        "endpoint_id": endpoint.endpoint_id,
        "family": endpoint.family,
        "function": endpoint.api_function,
        "headers_path": saved["headers_path"],
        "http_status": fetched["status"],
        "key_kind": key_kind,
        "network_error": fetched["network_error"],
        "raw_path": saved["raw_path"],
        "request_url": redacted_url(endpoint=endpoint),
        "schema_path": None,
        "timestamp_utc": utc_now(),
        "usable_schema": parsed["classification"] in ["data_json", "data_csv"],
    }
    if schema_path is not None:
        log_entry["schema_path"] = str(schema_path.relative_to(ROOT_DIR))
    append_call_log(entry=log_entry)

    result = dict(log_entry)
    result["data"] = parsed["data"]
    result["schema"] = parsed["schema"]
    result["network_timeout"] = fetched["network_timeout"]
    return result


def field_exists(*, schema: dict[str, Any] | None, field_path: str) -> bool:
    """Check whether an extracted JSON schema contains a field path.

    Args:
        schema: Extracted schema or None.
        field_path: JSONPath-like field path.

    Returns:
        True when the field path was observed.
    """
    if schema is None:
        return False
    if "fields" not in schema:
        return False
    return field_path in schema["fields"]


def path_semantic_types(*, schema: dict[str, Any] | None, field_path: str) -> list[str]:
    """Return semantic types for one JSON schema path.

    Args:
        schema: Extracted schema or None.
        field_path: JSONPath-like field path.

    Returns:
        Observed semantic types, or an empty list.
    """
    if schema is None:
        return []
    if "fields" not in schema:
        return []
    if field_path not in schema["fields"]:
        return []
    return schema["fields"][field_path]["semantic_types"]


def union_array_keys(*, data: Any, array_key: str) -> list[str]:
    """Return union of keys in the first sampled objects of a root array.

    Args:
        data: JSON-decoded response.
        array_key: Root array key to inspect.

    Returns:
        Sorted list of observed row keys.
    """
    if not isinstance(data, dict):
        return []
    if array_key not in data:
        return []
    if not isinstance(data[array_key], list):
        return []

    keys: set[str] = set()
    for item in data[array_key][:ARRAY_INSPECT_LIMIT]:
        if isinstance(item, dict):
            keys.update(item.keys())
    return sorted(keys)


def csv_columns(*, schema: dict[str, Any] | None) -> list[str]:
    """Return observed CSV header columns.

    Args:
        schema: Extracted schema or None.

    Returns:
        Header column names.
    """
    if schema is None:
        return []
    if "columns" not in schema:
        return []
    return schema["columns"]


def detect_duplicate_urls(*, data: Any) -> dict[str, Any]:
    """Detect duplicate article URLs in a NEWS_SENTIMENT feed.

    Args:
        data: JSON-decoded response.

    Returns:
        Duplicate counts and duplicate URLs.
    """
    if not isinstance(data, dict):
        return {"duplicate_count": 0, "duplicate_urls": []}
    if "feed" not in data:
        return {"duplicate_count": 0, "duplicate_urls": []}
    if not isinstance(data["feed"], list):
        return {"duplicate_count": 0, "duplicate_urls": []}

    seen: set[str] = set()
    duplicates: list[str] = []
    for item in data["feed"][:ARRAY_INSPECT_LIMIT]:
        if not isinstance(item, dict):
            continue
        if "url" not in item:
            continue
        url = str(item["url"])
        if url in seen and url not in duplicates:
            duplicates.append(url)
        seen.add(url)
    return {"duplicate_count": len(duplicates), "duplicate_urls": duplicates}


def source_domain_comparison(*, data: Any) -> dict[str, Any]:
    """Compare NEWS_SENTIMENT source_domain with parsed article URL domain.

    Args:
        data: JSON-decoded response.

    Returns:
        Sample comparisons from the first feed items.
    """
    if not isinstance(data, dict):
        return {"samples": []}
    if "feed" not in data:
        return {"samples": []}
    if not isinstance(data["feed"], list):
        return {"samples": []}

    samples: list[dict[str, Any]] = []
    for item in data["feed"][:ARRAY_INSPECT_LIMIT]:
        if not isinstance(item, dict):
            continue
        if "url" not in item or "source_domain" not in item:
            continue
        parsed = urllib.parse.urlparse(url=str(item["url"]))
        samples.append(
            {
                "parsed_domain": parsed.netloc,
                "source": item["source"] if "source" in item else None,
                "source_domain": item["source_domain"],
            }
        )
    return {"samples": samples}


def news_feed_count(*, data: Any) -> int | None:
    """Return the NEWS_SENTIMENT feed row count when present.

    Args:
        data: JSON-decoded NEWS_SENTIMENT response.

    Returns:
        Feed row count, or None when the payload is not a feed response.
    """
    if not isinstance(data, dict):
        return None
    if "feed" not in data:
        return None
    if not isinstance(data["feed"], list):
        return None
    return len(data["feed"])


def news_items_value(*, data: Any) -> Any:
    """Return the NEWS_SENTIMENT root items value when present.

    Args:
        data: JSON-decoded NEWS_SENTIMENT response.

    Returns:
        The root items value, or None when absent.
    """
    if not isinstance(data, dict):
        return None
    if "items" not in data:
        return None
    return data["items"]


def source_domain_differs_from_hostname(*, checks: dict[str, Any]) -> bool:
    """Detect whether source_domain values differ from parsed URL hostnames.

    Args:
        checks: Endpoint-specific NEWS_SENTIMENT checks.

    Returns:
        True when any sampled source_domain is not the parsed URL hostname.
    """
    if "source_domain_comparison" not in checks:
        return False
    comparison = checks["source_domain_comparison"]
    if "samples" not in comparison:
        return False

    for sample in comparison["samples"]:
        if "source_domain" not in sample or "parsed_domain" not in sample:
            continue
        if sample["source_domain"] != sample["parsed_domain"]:
            return True
    return False


def empty_array_paths(*, schema: dict[str, Any] | None) -> list[str]:
    """Find schema paths where an empty array example was observed.

    Args:
        schema: Extracted schema or None.

    Returns:
        List of field paths with [] examples.
    """
    if schema is None:
        return []
    if "fields" not in schema:
        return []

    paths: list[str] = []
    for path, record in schema["fields"].items():
        if "array" not in record["json_types"]:
            continue
        if "[]" in record["examples"]:
            paths.append(path)
    return sorted(paths)


def identify_columns(*, columns: list[str], keywords: list[str]) -> list[str]:
    """Find observed column names matching any keyword.

    Args:
        columns: Observed CSV or JSON keys.
        keywords: Lowercase keyword fragments.

    Returns:
        Matching column names.
    """
    matched: list[str] = []
    for column in columns:
        lowered = column.lower()
        for keyword in keywords:
            if keyword in lowered:
                matched.append(column)
                break
    return matched


def endpoint_specific_checks(
    *,
    endpoint: Endpoint,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run endpoint-specific observations required by the execution spec.

    Args:
        endpoint: Endpoint definition.
        result: Final usable result for the endpoint, or None.

    Returns:
        Dict of endpoint-specific observations derived from the response.
    """
    if result is None:
        return {"status": "no_usable_response"}
    if not result["usable_schema"]:
        return {"status": "no_usable_response"}

    schema = result["schema"]
    data = result["data"]
    endpoint_id = endpoint.endpoint_id

    if endpoint_id == "overview_ibm":
        fields = [
            "Symbol",
            "Name",
            "LatestQuarter",
            "MarketCapitalization",
            "PERatio",
            "DividendYield",
            "52WeekHigh",
            "50DayMovingAverage",
            "SharesOutstanding",
            "PercentInsiders",
            "PercentInstitutions",
        ]
        return {
            "required_field_presence": {
                field: field_exists(schema=schema, field_path=f"$.{field}")
                for field in fields
            }
        }

    if endpoint_id == "income_statement_ibm":
        annual_keys = union_array_keys(data=data, array_key="annualReports")
        quarterly_keys = union_array_keys(data=data, array_key="quarterlyReports")
        return {
            "annual_reports_keys_sampled": annual_keys,
            "quarterly_reports_keys_sampled": quarterly_keys,
            "root_has_annualReports": field_exists(
                schema=schema,
                field_path="$.annualReports",
            ),
            "root_has_quarterlyReports": field_exists(
                schema=schema,
                field_path="$.quarterlyReports",
            ),
            "costOfRevenue_present": "costOfRevenue" in annual_keys
            or "costOfRevenue" in quarterly_keys,
            "costofGoodsAndServicesSold_present": "costofGoodsAndServicesSold"
            in annual_keys
            or "costofGoodsAndServicesSold" in quarterly_keys,
            "costof GoodsAndServicesSold_with_space_present": (
                "costof GoodsAndServicesSold" in annual_keys
                or "costof GoodsAndServicesSold" in quarterly_keys
            ),
        }

    if endpoint_id == "balance_sheet_ibm":
        annual_keys = union_array_keys(data=data, array_key="annualReports")
        quarterly_keys = union_array_keys(data=data, array_key="quarterlyReports")
        all_keys = sorted(set(annual_keys + quarterly_keys))
        return {
            "otherNonCurrentAssets_present": "otherNonCurrentAssets" in all_keys,
            "otherNonCurrrentAssets_present": "otherNonCurrrentAssets" in all_keys,
            "shortLongTermDebtTotal_present": "shortLongTermDebtTotal" in all_keys,
            "commonStockSharesOutstanding_present": (
                "commonStockSharesOutstanding" in all_keys
            ),
        }

    if endpoint_id == "cash_flow_ibm":
        annual_keys = union_array_keys(data=data, array_key="annualReports")
        quarterly_keys = union_array_keys(data=data, array_key="quarterlyReports")
        all_keys = sorted(set(annual_keys + quarterly_keys))
        outflow_fields = [
            "capitalExpenditures",
            "dividendPayout",
            "dividendPayoutCommonStock",
            "cashflowFromInvestment",
            "cashflowFromFinancing",
        ]
        signs: dict[str, list[str]] = {}
        for field in outflow_fields:
            observed_signs: list[str] = []
            for path in [
                f"$.annualReports[].{field}",
                f"$.quarterlyReports[].{field}",
            ]:
                if not field_exists(schema=schema, field_path=path):
                    continue
                examples = schema["fields"][path]["examples"]
                for example in examples:
                    if str(example).startswith("\"-"):
                        add_unique(values=observed_signs, value="negative_string")
                    if str(example).startswith("\"") and not str(example).startswith(
                        "\"-"
                    ):
                        add_unique(values=observed_signs, value="non_negative_string")
            signs[field] = observed_signs
        return {
            "field_presence": {field: field in all_keys for field in [
                "operatingCashflow",
                "capitalExpenditures",
                "cashflowFromInvestment",
                "cashflowFromFinancing",
                "dividendPayout",
            ]},
            "outflow_sign_examples": signs,
        }

    if endpoint_id == "earnings_ibm":
        return {
            "annual_earnings_keys_sampled": union_array_keys(
                data=data,
                array_key="annualEarnings",
            ),
            "quarterly_earnings_keys_sampled": union_array_keys(
                data=data,
                array_key="quarterlyEarnings",
            ),
            "quarterly_required_presence": {
                field: field_exists(
                    schema=schema,
                    field_path=f"$.quarterlyEarnings[].{field}",
                )
                for field in [
                    "reportedDate",
                    "estimatedEPS",
                    "surprise",
                    "surprisePercentage",
                    "reportTime",
                ]
            },
        }

    if endpoint_id in ["dividends_ibm", "insider_transactions_ibm", "splits_ibm"]:
        row_keys = union_array_keys(data=data, array_key="data")
        checks: dict[str, Any] = {"data_row_keys_sampled": row_keys}
        if endpoint_id == "dividends_ibm":
            checks["required_row_key_presence"] = {
                field: field in row_keys
                for field in [
                    "ex_dividend_date",
                    "declaration_date",
                    "record_date",
                    "payment_date",
                    "amount",
                ]
            }
        if endpoint_id == "insider_transactions_ibm":
            candidate_keys = [
                field
                for field in row_keys
                if field.lower() in [
                    "transactiondate",
                    "executive",
                    "securitytype",
                    "acquisitionordisposal",
                    "shares",
                ]
            ]
            checks["natural_primary_key_candidate_fields"] = candidate_keys
        if endpoint_id == "splits_ibm":
            checks["date_fields"] = identify_columns(
                columns=row_keys,
                keywords=["date"],
            )
            checks["ratio_or_factor_fields"] = identify_columns(
                columns=row_keys,
                keywords=["factor", "ratio", "split"],
            )
        return checks

    if endpoint_id == "shares_outstanding_msft":
        annual_keys = union_array_keys(data=data, array_key="annualReports")
        quarterly_keys = union_array_keys(data=data, array_key="quarterlyReports")
        data_keys = union_array_keys(data=data, array_key="data")
        all_keys = sorted(set(annual_keys + quarterly_keys + data_keys))
        return {
            "date_fields": identify_columns(
                columns=all_keys,
                keywords=["date", "fiscal"],
            ),
            "basic_share_fields": identify_columns(
                columns=all_keys,
                keywords=["basic"],
            ),
            "diluted_share_fields": identify_columns(
                columns=all_keys,
                keywords=["diluted"],
            ),
            "all_report_keys_sampled": all_keys,
        }

    if endpoint_id == "earnings_estimates_ibm":
        row_keys = union_array_keys(data=data, array_key="estimates")
        return {
            "estimate_row_keys_sampled": row_keys,
            "eps_fields": identify_columns(columns=row_keys, keywords=["eps"]),
            "revenue_fields": identify_columns(columns=row_keys, keywords=["revenue"]),
            "analyst_count_fields": identify_columns(
                columns=row_keys,
                keywords=["analyst"],
            ),
            "revision_fields": identify_columns(
                columns=row_keys,
                keywords=["revision"],
            ),
            "fiscal_period_fields": identify_columns(
                columns=row_keys,
                keywords=["fiscal", "period", "date"],
            ),
        }

    if endpoint_id.startswith("news_sentiment"):
        feed_keys = union_array_keys(data=data, array_key="feed")
        return {
            "root_keys": schema["root_keys"] if "root_keys" in schema else [],
            "actual_feed_count": news_feed_count(data=data),
            "feed_keys_sampled": feed_keys,
            "items_value": news_items_value(data=data),
            "requested_limit": endpoint.params["limit"],
            "sentiment_score_types": path_semantic_types(
                schema=schema,
                field_path="$.feed[].overall_sentiment_score",
            ),
            "ticker_sentiment_score_types": path_semantic_types(
                schema=schema,
                field_path="$.feed[].ticker_sentiment[].ticker_sentiment_score",
            ),
            "topic_score_types": path_semantic_types(
                schema=schema,
                field_path="$.feed[].topics[].relevance_score",
            ),
            "source_domain_comparison": source_domain_comparison(data=data),
            "duplicate_urls": detect_duplicate_urls(data=data),
            "empty_array_paths": empty_array_paths(schema=schema),
            "topic_query_has_ticker_sentiment_arrays": field_exists(
                schema=schema,
                field_path="$.feed[].ticker_sentiment",
            ),
        }

    if endpoint_id == "earnings_call_transcript_ibm_2024q1":
        row_keys = union_array_keys(data=data, array_key="transcript")
        return {
            "root_keys": schema["root_keys"] if "root_keys" in schema else [],
            "transcript_row_keys_sampled": row_keys,
            "speaker_fields": identify_columns(
                columns=row_keys,
                keywords=["speaker", "name"],
            ),
            "title_or_role_fields": identify_columns(
                columns=row_keys,
                keywords=["title", "role"],
            ),
            "content_fields": identify_columns(
                columns=row_keys,
                keywords=["content", "text"],
            ),
            "symbol_present": field_exists(schema=schema, field_path="$.symbol"),
            "quarter_present": field_exists(schema=schema, field_path="$.quarter"),
        }

    if endpoint_id == "listing_status":
        columns = csv_columns(schema=schema)
        expected = [
            "symbol",
            "name",
            "exchange",
            "assetType",
            "ipoDate",
            "delistingDate",
            "status",
        ]
        return {
            "columns": columns,
            "expected_column_presence": {
                column: column in columns for column in expected
            },
        }

    if endpoint_id == "earnings_calendar_ibm_12month":
        columns = csv_columns(schema=schema)
        return {
            "columns": columns,
            "symbol_fields": identify_columns(columns=columns, keywords=["symbol"]),
            "company_name_fields": identify_columns(
                columns=columns,
                keywords=["name"],
            ),
            "report_date_fields": identify_columns(
                columns=columns,
                keywords=["report"],
            ),
            "fiscal_date_fields": identify_columns(
                columns=columns,
                keywords=["fiscal"],
            ),
            "estimate_fields": identify_columns(
                columns=columns,
                keywords=["estimate"],
            ),
            "currency_fields": identify_columns(
                columns=columns,
                keywords=["currency"],
            ),
        }

    return {"status": "no_endpoint_specific_check"}


def chosen_result(*, attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the final usable result for schema reporting.

    Args:
        attempts: Attempt results for one endpoint.

    Returns:
        First usable result, preferring demo when demo was usable.
    """
    for attempt in attempts:
        if attempt["usable_schema"]:
            return attempt
    return None


def public_attempt_result(*, attempt: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove parsed payloads from a selected attempt before report output.

    Args:
        attempt: Internal attempt result, or None.

    Returns:
        Public attempt metadata without parsed data or duplicated schema.
    """
    if attempt is None:
        return None
    public: dict[str, Any] = {}
    for key, value in attempt.items():
        if key in ["data", "schema", "network_timeout"]:
            continue
        public[key] = value
    return public


def build_key_value_dictionary(
    *,
    observed_endpoints: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a cross-endpoint key/value dictionary from observed schemas.

    Args:
        observed_endpoints: Final per-endpoint observations.

    Returns:
        Mapping keyed by observed field/column name.
    """
    dictionary: dict[str, Any] = {}
    for endpoint_id, endpoint_payload in observed_endpoints.items():
        if "schema" not in endpoint_payload:
            continue
        schema = endpoint_payload["schema"]
        if schema is None:
            continue
        if "fields" in schema:
            for path, record in schema["fields"].items():
                field_name = path.split(".")[-1].replace("[]", "")
                if field_name == "$":
                    field_name = "$"
                if field_name not in dictionary:
                    dictionary[field_name] = {
                        "examples": [],
                        "observed_at": [],
                        "semantic_types": [],
                    }
                add_unique(
                    values=dictionary[field_name]["observed_at"],
                    value=f"{endpoint_id}:{path}",
                )
                for semantic in record["semantic_types"]:
                    add_unique(
                        values=dictionary[field_name]["semantic_types"],
                        value=semantic,
                    )
                for example in record["examples"]:
                    if len(dictionary[field_name]["examples"]) < EXAMPLE_LIMIT:
                        add_unique(
                            values=dictionary[field_name]["examples"],
                            value=example,
                        )
        if "columns_observed" in schema:
            for column, record in schema["columns_observed"].items():
                if column not in dictionary:
                    dictionary[column] = {
                        "examples": [],
                        "observed_at": [],
                        "semantic_types": [],
                    }
                add_unique(
                    values=dictionary[column]["observed_at"],
                    value=f"{endpoint_id}:csv.{column}",
                )
                for semantic in record["semantic_types"]:
                    add_unique(
                        values=dictionary[column]["semantic_types"],
                        value=semantic,
                    )
                for example in record["examples"]:
                    if len(dictionary[column]["examples"]) < EXAMPLE_LIMIT:
                        add_unique(
                            values=dictionary[column]["examples"],
                            value=example,
                        )
    return dictionary


def schema_risks(*, observed_endpoints: dict[str, dict[str, Any]]) -> list[str]:
    """Summarize response-derived schema risks.

    Args:
        observed_endpoints: Final per-endpoint observations.

    Returns:
        Human-readable risk statements.
    """
    priority_risks: list[str] = []
    risks: list[str] = []
    source_domain_risk_added = False
    news_limit_risk_added = False
    for endpoint_id, payload in observed_endpoints.items():
        if "selected_result" not in payload:
            risks.append(f"{endpoint_id}: no usable response schema was observed.")
            continue
        result = payload["selected_result"]
        if result is None:
            risks.append(f"{endpoint_id}: no usable response schema was observed.")
            continue
        schema = payload["schema"]
        if schema is None:
            risks.append(f"{endpoint_id}: no schema payload was available.")
            continue
        checks = payload["specific_checks"]
        if endpoint_id.startswith("news_sentiment"):
            if (
                not source_domain_risk_added
                and source_domain_differs_from_hostname(checks=checks)
            ):
                priority_risks.append(
                    "NEWS_SENTIMENT source_domain 不是 hostname；样本显示其为"
                    "来源名称而不是 URL hostname。"
                )
                source_domain_risk_added = True
            if not news_limit_risk_added:
                requested_limit = int(checks["requested_limit"])
                actual_feed_count = checks["actual_feed_count"]
                items_value = checks["items_value"]
                if (
                    actual_feed_count is not None
                    and actual_feed_count > requested_limit
                ):
                    priority_risks.append(
                        f"NEWS_SENTIMENT 请求 limit={requested_limit}，但现有 "
                        f"raw 响应实际返回 {actual_feed_count} 条 feed/items"
                        f"（items={items_value}）。"
                    )
                    news_limit_risk_added = True
        if "fields" in schema:
            for path, record in schema["fields"].items():
                semantic_types = record["semantic_types"]
                if endpoint_id == "earnings_estimates_ibm":
                    if "null" in record["json_types"]:
                        priority_risks.append(
                            "EARNINGS_ESTIMATES 有 JSON null："
                            f"{path}。"
                        )
                if "literal_string_none" in semantic_types:
                    risks.append(
                        f"{endpoint_id} {path}: missing values can appear as "
                        "literal string \"None\"."
                    )
                if "empty_string" in semantic_types:
                    risks.append(
                        f"{endpoint_id} {path}: missing values can appear as "
                        "empty strings."
                    )
        if "columns_observed" in schema:
            if endpoint_id == "listing_status":
                columns_observed = schema["columns_observed"]
                if "delistingDate" in columns_observed:
                    delisting_record = columns_observed["delistingDate"]
                    if "\"null\"" in delisting_record["examples"]:
                        priority_risks.append(
                            "LISTING_STATUS delistingDate 是 \"null\" 字符串，"
                            "不是 JSON null 或空值。"
                        )
                if "status" in columns_observed:
                    status_record = columns_observed["status"]
                    if status_record["examples"] == ["\"Active\""]:
                        priority_risks.append(
                            "LISTING_STATUS 当前默认样本只有 Active；不要把 "
                            "status 建模成单值常量。"
                        )
            for column, record in schema["columns_observed"].items():
                if record["blank_count"] > 0:
                    risks.append(
                        f"{endpoint_id} csv.{column}: blank CSV values were observed."
                    )
    return (priority_risks + risks)[:40]


def database_implications(
    *,
    observed_endpoints: dict[str, dict[str, Any]],
) -> list[str]:
    """Derive database-design implications from observed schemas.

    Args:
        observed_endpoints: Final per-endpoint observations.

    Returns:
        List of concise implementation implications.
    """
    implications = [
        "Persist raw response text and parsed records separately so vendor "
        "messages do not corrupt typed tables.",
        "Normalize literal string \"None\" and empty strings at ingestion "
        "boundaries before numeric/date casts.",
        "Model array children such as feed.ticker_sentiment, feed.topics, "
        "annualReports, and quarterlyReports as child tables.",
        "Keep Alpha Vantage news time_published as raw text unless a separate "
        "timezone policy is introduced.",
    ]
    if "listing_status" in observed_endpoints:
        implications.append(
            "LISTING_STATUS and EARNINGS_CALENDAR are CSV-shaped and need a "
            "CSV ingestion path beside JSON fundamentals."
        )
    return implications


def build_next_run_queue(
    *,
    attempts_by_endpoint: dict[str, list[dict[str, Any]]],
    real_key_available: bool,
) -> list[dict[str, Any]]:
    """Build deferred endpoint queue for the next run.

    Args:
        attempts_by_endpoint: All attempted request results by endpoint.
        real_key_available: Whether this run had a real key in environment.

    Returns:
        Queue entries for endpoints without usable schema.
    """
    endpoint_index = endpoint_by_id()
    queue: list[dict[str, Any]] = []
    for endpoint in ENDPOINTS:
        attempts = attempts_by_endpoint[endpoint.endpoint_id]
        selected = chosen_result(attempts=attempts)
        if selected is not None:
            continue
        reason = "demo_unusable_real_key_absent"
        if real_key_available:
            reason = "unusable_after_allowed_calls_or_not_reached_by_real_priority"
        last_classification = "not_attempted"
        if len(attempts) > 0:
            last_classification = attempts[-1]["classification"]
        queue.append(
            {
                "endpoint_id": endpoint.endpoint_id,
                "family": endpoint.family,
                "function": endpoint.api_function,
                "last_classification": last_classification,
                "params": endpoint_index[endpoint.endpoint_id].params,
                "reason": reason,
                "request_url": redacted_url(endpoint=endpoint),
            }
        )
    return queue


def build_observed_output(
    *,
    attempts_by_endpoint: dict[str, list[dict[str, Any]]],
    demo_calls_used: int,
    real_calls_used: int,
    real_key_available: bool,
    source: str,
) -> dict[str, Any]:
    """Assemble the machine-readable observed schema report.

    Args:
        attempts_by_endpoint: All request attempts by endpoint.
        demo_calls_used: Number of demo attempts made.
        real_calls_used: Number of real-key attempts made.
        real_key_available: Whether a real key was present in the environment.
        source: Reader-facing description of the response source.

    Returns:
        JSON-serializable report payload.
    """
    observed_endpoints: dict[str, dict[str, Any]] = {}
    for endpoint in ENDPOINTS:
        attempts = attempts_by_endpoint[endpoint.endpoint_id]
        selected = chosen_result(attempts=attempts)
        schema = None
        if selected is not None:
            schema = selected["schema"]
        observed_endpoints[endpoint.endpoint_id] = {
            "attempts": [
                {
                    "attempt_sequence": attempt["attempt_sequence"],
                    "classification": attempt["classification"],
                    "http_status": attempt["http_status"],
                    "key_kind": attempt["key_kind"],
                    "raw_path": attempt["raw_path"],
                    "schema_path": attempt["schema_path"],
                    "usable_schema": attempt["usable_schema"],
                }
                for attempt in attempts
            ],
            "endpoint": {
                "family": endpoint.family,
                "function": endpoint.api_function,
                "params": endpoint.params,
                "request_url": redacted_url(endpoint=endpoint),
            },
            "schema": schema,
            "selected_result": public_attempt_result(attempt=selected),
            "specific_checks": endpoint_specific_checks(
                endpoint=endpoint,
                result=selected,
            ),
            "status": "observed" if selected is not None else "deferred",
        }

    dictionary = build_key_value_dictionary(observed_endpoints=observed_endpoints)
    next_queue = build_next_run_queue(
        attempts_by_endpoint=attempts_by_endpoint,
        real_key_available=real_key_available,
    )

    return {
        "generated_at_utc": utc_now(),
        "source": source,
        "limits": {
            "max_demo_calls": MAX_DEMO_CALLS,
            "max_real_calls": MAX_REAL_CALLS,
            "demo_calls_used": demo_calls_used,
            "real_calls_used": real_calls_used,
        },
        "real_key_available": real_key_available,
        "call_log_path": str(CALL_LOG_PATH.relative_to(ROOT_DIR)),
        "endpoints": observed_endpoints,
        "key_value_dictionary": dictionary,
        "schema_risks": schema_risks(observed_endpoints=observed_endpoints),
        "database_implications": database_implications(
            observed_endpoints=observed_endpoints,
        ),
        "next_run_queue": next_queue,
    }


def markdown_table_row(*, cells: list[Any]) -> str:
    """Format a Markdown table row.

    Args:
        cells: Cell values to stringify.

    Returns:
        Markdown table row.
    """
    escaped: list[str] = []
    for cell in cells:
        text = str(cell).replace("|", "\\|").replace("\n", " ")
        escaped.append(text)
    return "| " + " | ".join(escaped) + " |"


def summarize_schema_for_markdown(*, endpoint_payload: dict[str, Any]) -> list[str]:
    """Create compact Markdown bullets for one endpoint schema.

    Args:
        endpoint_payload: One endpoint payload from the JSON report.

    Returns:
        Markdown bullet lines.
    """
    schema = endpoint_payload["schema"]
    if schema is None:
        return ["- 未观察到可用 schema。"]
    lines: list[str] = []
    if "root_keys" in schema:
        lines.append(f"- root keys: `{', '.join(schema['root_keys'])}`")
    if "columns" in schema:
        lines.append(f"- CSV columns: `{', '.join(schema['columns'])}`")
    if "fields" in schema:
        field_count = len(schema["fields"])
        lines.append(f"- JSON field paths observed: `{field_count}`")
        sampled_paths = sorted(schema["fields"].keys())[:20]
        lines.append(f"- sampled paths: `{', '.join(sampled_paths)}`")
    checks = endpoint_payload["specific_checks"]
    lines.append(
        "- endpoint checks: "
        + json.dumps(obj=checks, ensure_ascii=False, sort_keys=True)[:1000]
    )
    return lines


def build_markdown_report(*, observed: dict[str, Any]) -> str:
    """Build the required Markdown report.

    Args:
        observed: Machine-readable observed schema payload.

    Returns:
        Markdown report text.
    """
    endpoints = observed["endpoints"]
    observed_count = sum(
        1 for payload in endpoints.values() if payload["status"] == "observed"
    )
    deferred_count = len(endpoints) - observed_count

    lines = [
        "# Alpha Vantage Observed Schema Verification Report",
        "",
        "## 1. Executive Summary",
        "",
        (
            f"- Generated at UTC `{observed['generated_at_utc']}` from "
            f"{observed['source']}."
        ),
        f"- Planned schemas usable: `{observed_count}` / `{len(endpoints)}`.",
        f"- Deferred checks: `{deferred_count}`.",
        (
            f"- Calls used: demo `{observed['limits']['demo_calls_used']}` / "
            f"`{observed['limits']['max_demo_calls']}`, real "
            f"`{observed['limits']['real_calls_used']}` / "
            f"`{observed['limits']['max_real_calls']}`."
        ),
        f"- Real key available to runner: `{observed['real_key_available']}`.",
        "",
        "## 2. Call Log Summary",
        "",
        markdown_table_row(
            cells=[
                "endpoint",
                "status",
                "attempts",
                "final classification",
                "raw",
            ]
        ),
        markdown_table_row(cells=["---", "---", "---", "---", "---"]),
    ]

    for endpoint_id, payload in endpoints.items():
        attempts = payload["attempts"]
        final_classification = "not_attempted"
        raw_path = ""
        if len(attempts) > 0:
            final_classification = attempts[-1]["classification"]
            raw_path = attempts[-1]["raw_path"]
        lines.append(
            markdown_table_row(
                cells=[
                    endpoint_id,
                    payload["status"],
                    len(attempts),
                    final_classification,
                    raw_path,
                ]
            )
        )

    lines.extend(["", "## 3. Observed Endpoint Schemas", ""])
    for endpoint_id, payload in endpoints.items():
        lines.extend([f"### {endpoint_id}", ""])
        lines.extend(summarize_schema_for_markdown(endpoint_payload=payload))
        lines.append("")

    lines.extend(["## 4. Key/Value Dictionary", ""])
    dictionary = observed["key_value_dictionary"]
    for key in sorted(dictionary.keys())[:200]:
        item = dictionary[key]
        lines.append(
            f"- `{key}`: semantic=`{', '.join(item['semantic_types'])}`; "
            f"observed_at=`{'; '.join(item['observed_at'][:5])}`; "
            f"examples=`{'; '.join(item['examples'][:3])}`"
        )
    if len(dictionary) > 200:
        lines.append(
            "- Dictionary truncated in Markdown at 200 keys; JSON contains "
            f"{len(dictionary)} keys."
        )

    lines.extend(["", "## 5. Schema Risks", ""])
    if len(observed["schema_risks"]) == 0:
        lines.append("- No response-derived risks observed.")
    for risk in observed["schema_risks"]:
        lines.append(f"- {risk}")

    lines.extend(["", "## 6. Database Implications", ""])
    for implication in observed["database_implications"]:
        lines.append(f"- {implication}")

    lines.extend(["", "## 7. Deferred Checks", ""])
    if len(observed["next_run_queue"]) == 0:
        lines.append("- None.")
    for item in observed["next_run_queue"]:
        lines.append(
            f"- `{item['endpoint_id']}`: {item['reason']} "
            f"(last classification: `{item['last_classification']}`)."
        )

    lines.extend(["", "## 8. Next Run Queue", ""])
    if len(observed["next_run_queue"]) == 0:
        lines.append("- Queue is empty.")
    for item in observed["next_run_queue"]:
        lines.append(
            f"- `{item['function']}` params="
            f"`{json.dumps(obj=item['params'], ensure_ascii=False, sort_keys=True)}`"
        )

    lines.append("")
    return "\n".join(lines)


def sleep_between_calls(*, sequence: int) -> None:
    """Pause between API calls to avoid avoidable frequency responses.

    Args:
        sequence: Attempt sequence that just completed.

    Returns:
        None. Sleeps for REQUEST_DELAY_SECONDS except before the first call.
    """
    if sequence <= 0:
        return
    # The execution spec forbids concurrency; a small serial delay preserves calls.
    time.sleep(REQUEST_DELAY_SECONDS)


def run_attempt_with_retry_policy(
    *,
    endpoint: Endpoint,
    key_kind: str,
    api_key: str,
    attempt_sequence: int,
    max_calls: int,
    calls_used: int,
) -> tuple[list[dict[str, Any]], int, int]:
    """Run one endpoint under the one-timeout-retry policy.

    Args:
        endpoint: Endpoint definition.
        key_kind: "demo" or "real".
        api_key: API key value, never logged.
        attempt_sequence: Current global attempt sequence.
        max_calls: Maximum calls allowed for this key kind.
        calls_used: Calls already used for this key kind.

    Returns:
        Tuple of attempts, updated attempt_sequence, and updated calls_used.
    """
    attempts: list[dict[str, Any]] = []
    retry_index = 0
    while retry_index < 2 and calls_used < max_calls:
        sleep_between_calls(sequence=attempt_sequence)
        attempt_sequence += 1
        calls_used += 1
        print(
            f"[call] {key_kind} #{calls_used}/{max_calls} "
            f"seq={attempt_sequence} endpoint={endpoint.endpoint_id}"
        )
        result = call_endpoint(
            key_kind=key_kind,
            sequence=attempt_sequence,
            endpoint=endpoint,
            api_key=api_key,
        )
        attempts.append(result)
        if not result["network_timeout"]:
            return attempts, attempt_sequence, calls_used
        retry_index += 1
        if retry_index < 2 and calls_used < max_calls:
            print(
                f"[retry] {endpoint.endpoint_id} had a timeout before body; "
                "one retry is allowed by spec."
            )
    return attempts, attempt_sequence, calls_used


def parse_raw_response_path(*, raw_path: Path) -> dict[str, Any]:
    """Parse sequence, key kind, and endpoint ID from a saved raw path.

    Args:
        raw_path: Existing response body path under artifacts/alpha_vantage/raw/.

    Returns:
        Metadata dict with sequence, key_kind, endpoint_id, and relative raw_path.
    """
    key_kind = raw_path.parent.name
    if key_kind not in ["demo", "real"]:
        raise ValueError(f"Unexpected raw response key kind: {raw_path}")

    name_parts = raw_path.stem.split("_", maxsplit=1)
    if len(name_parts) != 2:
        raise ValueError(f"Raw response filename lacks sequence prefix: {raw_path}")
    if not name_parts[0].isdigit():
        raise ValueError(f"Raw response sequence is not numeric: {raw_path}")

    # The sequence prefix is the durable ordering from the preserved call log.
    return {
        "endpoint_id": name_parts[1],
        "key_kind": key_kind,
        "raw_path": str(raw_path.relative_to(ROOT_DIR)),
        "sequence": int(name_parts[0]),
    }


def raw_response_sort_key(*, raw_path: Path) -> tuple[int, str, str]:
    """Return a stable sort key for existing raw response bodies.

    Args:
        raw_path: Existing response body path.

    Returns:
        Tuple sorted by original attempt sequence, key kind, and file path.
    """
    metadata = parse_raw_response_path(raw_path=raw_path)
    return (
        metadata["sequence"],
        metadata["key_kind"],
        metadata["raw_path"],
    )


def existing_raw_response_paths(*, raw_root: Path) -> list[Path]:
    """List existing saved response bodies under the raw artifact directory.

    Args:
        raw_root: Directory containing demo/ and real/ raw responses.

    Returns:
        Sequence-ordered raw .txt paths.
    """
    raw_paths = list(raw_root.rglob(pattern="*.txt"))
    keyed_paths: list[tuple[tuple[int, str, str], Path]] = []
    for raw_path in raw_paths:
        # Sorting through explicit keys avoids relying on filesystem traversal.
        keyed_paths.append(
            (
                raw_response_sort_key(raw_path=raw_path),
                raw_path,
            )
        )
    keyed_paths.sort()
    return [raw_path for _, raw_path in keyed_paths]


def read_raw_response_status(*, raw_path: Path) -> int | None:
    """Read the saved HTTP status beside a raw response body.

    Args:
        raw_path: Existing response body path.

    Returns:
        HTTP status integer, or None for previously saved network errors.
    """
    header_path = raw_path.with_name(f"{raw_path.stem}_headers.json")
    if not header_path.exists():
        raise FileNotFoundError(f"Missing raw response header file: {header_path}")

    # Header metadata is local evidence; it prevents invented status defaults.
    header_payload = json.loads(s=header_path.read_text(encoding="utf-8"))
    if "status" not in header_payload:
        raise KeyError(f"Header file lacks status: {header_path}")
    status = header_payload["status"]
    if status is not None and not isinstance(status, int):
        raise TypeError(f"Header status must be int or null: {header_path}")
    return status


def existing_schema_reference(
    *,
    endpoint: Endpoint,
    key_kind: str,
    schema: dict[str, Any] | None,
) -> str | None:
    """Return a schema artifact path, generating LISTING_STATUS when needed.

    Args:
        endpoint: Endpoint definition for the parsed response.
        key_kind: "demo" or "real" raw response bucket.
        schema: Parsed schema, or None for unusable responses.

    Returns:
        Relative schema path, or None when no existing schema artifact exists.
    """
    if schema is None:
        return None

    schema_path = ARTIFACT_DIR / "schema" / f"{endpoint.endpoint_id}_{key_kind}.json"
    if endpoint.endpoint_id == "listing_status" and key_kind == "demo":
        # LISTING_STATUS was the misclassified CSV; regenerating only this
        # missing schema keeps raw files and previous call artifacts intact.
        write_json_file(
            path=schema_path,
            payload={
                "endpoint_id": endpoint.endpoint_id,
                "generated_at_utc": utc_now(),
                "key_kind": key_kind,
                "schema": schema,
            },
        )
        return str(schema_path.relative_to(ROOT_DIR))

    if schema_path.exists():
        return str(schema_path.relative_to(ROOT_DIR))
    return None


def build_attempt_from_raw(
    *,
    raw_path: Path,
    endpoint_index: dict[str, Endpoint],
) -> dict[str, Any]:
    """Build one report attempt by reparsing an existing raw response.

    Args:
        raw_path: Existing response body path.
        endpoint_index: Mapping from endpoint ID to planned endpoint.

    Returns:
        Attempt dict compatible with build_observed_output.
    """
    metadata = parse_raw_response_path(raw_path=raw_path)
    endpoint_id = metadata["endpoint_id"]
    if endpoint_id not in endpoint_index:
        raise KeyError(f"Raw response endpoint is not planned: {raw_path}")

    endpoint = endpoint_index[endpoint_id]
    raw_text = raw_path.read_text(encoding="utf-8")
    parsed = parse_response(
        status=read_raw_response_status(raw_path=raw_path),
        raw_text=raw_text,
    )
    schema_path = existing_schema_reference(
        endpoint=endpoint,
        key_kind=metadata["key_kind"],
        schema=parsed["schema"],
    )

    # This mirrors call_endpoint metadata without fetching or touching call logs.
    return {
        "attempt_sequence": metadata["sequence"],
        "classification": parsed["classification"],
        "data": parsed["data"],
        "endpoint_id": endpoint.endpoint_id,
        "family": endpoint.family,
        "function": endpoint.api_function,
        "http_status": read_raw_response_status(raw_path=raw_path),
        "key_kind": metadata["key_kind"],
        "network_error": None,
        "network_timeout": False,
        "raw_path": metadata["raw_path"],
        "request_url": redacted_url(endpoint=endpoint),
        "schema": parsed["schema"],
        "schema_path": schema_path,
        "usable_schema": parsed["classification"] in ["data_json", "data_csv"],
    }


def write_reparse_log(*, attempts: list[dict[str, Any]]) -> None:
    """Write a JSONL audit log for the current local reparse run.

    Args:
        attempts: Attempts reconstructed from existing raw response files.

    Returns:
        None. artifacts/alpha_vantage/reparse_log.jsonl is overwritten.
    """
    # This is separate from call_log.jsonl because no HTTP request happened.
    REPARSE_LOG_PATH.write_text(data="", encoding="utf-8")
    with REPARSE_LOG_PATH.open(mode="a", encoding="utf-8") as handle:
        for attempt in attempts:
            entry = {
                "attempt_sequence": attempt["attempt_sequence"],
                "classification": attempt["classification"],
                "endpoint_id": attempt["endpoint_id"],
                "http_status": attempt["http_status"],
                "key_kind": attempt["key_kind"],
                "mode": "from_raw",
                "raw_path": attempt["raw_path"],
                "schema_path": attempt["schema_path"],
                "timestamp_utc": utc_now(),
                "usable_schema": attempt["usable_schema"],
            }
            handle.write(json.dumps(obj=entry, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_reparse_state(
    *,
    observed: dict[str, Any],
    raw_response_count: int,
) -> None:
    """Write the current local reparse completion state.

    Args:
        observed: Machine-readable observed schema payload.
        raw_response_count: Number of raw response bodies reparsed.

    Returns:
        None. artifacts/alpha_vantage/reparse_state.json is written.
    """
    endpoints = observed["endpoints"]
    usable_schema_count = sum(
        1 for payload in endpoints.values() if payload["status"] == "observed"
    )
    write_json_file(
        path=REPARSE_STATE_PATH,
        payload={
            "api_key_used": False,
            "completed_at_utc": utc_now(),
            "mode": "from_raw",
            "network_calls_made": 0,
            "next_run_queue_count": len(observed["next_run_queue"]),
            "outputs": [
                "artifacts/alpha_vantage/schema/listing_status_demo.json",
                "artifacts/alpha_vantage/reparse_log.jsonl",
                "artifacts/alpha_vantage/reparse_state.json",
                "reports/alpha_vantage_observed_schema.md",
                "reports/alpha_vantage_observed_schema.json",
                "reports/alpha_vantage_next_run_queue.json",
            ],
            "planned_schema_count": len(endpoints),
            "raw_response_count": raw_response_count,
            "source": observed["source"],
            "status": "complete",
            "usable_schema_count": usable_schema_count,
        },
    )


def reparse_existing_raw_responses() -> dict[str, Any]:
    """Rebuild observed schema output from saved raw responses only.

    Returns:
        Machine-readable observed schema payload.
    """
    raw_paths = existing_raw_response_paths(raw_root=ARTIFACT_DIR / "raw")
    if len(raw_paths) == 0:
        raise FileNotFoundError("No existing raw Alpha Vantage responses found.")

    endpoint_index = endpoint_by_id()
    attempts_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    for endpoint in ENDPOINTS:
        attempts_by_endpoint[endpoint.endpoint_id] = []

    for raw_path in raw_paths:
        # Every attempt is derived from disk so this path cannot issue requests.
        attempt = build_attempt_from_raw(
            raw_path=raw_path,
            endpoint_index=endpoint_index,
        )
        attempts_by_endpoint[attempt["endpoint_id"]].append(attempt)

    observed = build_observed_output(
        attempts_by_endpoint=attempts_by_endpoint,
        demo_calls_used=0,
        real_calls_used=0,
        real_key_available=False,
        source="existing Alpha Vantage raw responses only",
    )
    reparse_attempts: list[dict[str, Any]] = []
    for endpoint in ENDPOINTS:
        reparse_attempts.extend(attempts_by_endpoint[endpoint.endpoint_id])
    write_reparse_log(attempts=reparse_attempts)
    write_reparse_state(
        observed=observed,
        raw_response_count=len(raw_paths),
    )
    return observed


def write_report_outputs(*, observed: dict[str, Any]) -> None:
    """Write the required report files from an observed schema payload.

    Args:
        observed: Machine-readable observed schema payload.

    Returns:
        None. The three report files are written as UTF-8 text.
    """
    write_json_file(
        path=REPORT_DIR / "alpha_vantage_observed_schema.json",
        payload=observed,
    )
    write_json_file(
        path=REPORT_DIR / "alpha_vantage_next_run_queue.json",
        payload=observed["next_run_queue"],
    )
    markdown = build_markdown_report(observed=observed)
    (REPORT_DIR / "alpha_vantage_observed_schema.md").write_text(
        data=markdown,
        encoding="utf-8",
    )


def main() -> None:
    """Run the full verification workflow.

    Returns:
        None. Required artifacts are written to disk.
    """
    ensure_output_dirs()
    if len(sys.argv) > 2:
        raise ValueError("Expected at most one argument: --from-raw")
    if len(sys.argv) == 2:
        if sys.argv[1] != "--from-raw":
            raise ValueError(f"Unsupported argument: {sys.argv[1]}")
        observed = reparse_existing_raw_responses()
        write_report_outputs(observed=observed)
        print("[complete] Reports rebuilt from existing raw responses only.")
        return

    CALL_LOG_PATH.write_text(data="", encoding="utf-8")

    real_key_available = False
    real_key = ""
    if API_KEY_ENV in os.environ and os.environ[API_KEY_ENV].strip() != "":
        real_key_available = True
        real_key = os.environ[API_KEY_ENV].strip()

    attempts_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    for endpoint in ENDPOINTS:
        attempts_by_endpoint[endpoint.endpoint_id] = []

    attempt_sequence = 0
    demo_calls_used = 0
    real_calls_used = 0

    for endpoint in ENDPOINTS:
        if demo_calls_used >= MAX_DEMO_CALLS:
            print("[limit] demo call limit reached; stopping demo attempts.")
            break
        attempts, attempt_sequence, demo_calls_used = run_attempt_with_retry_policy(
            endpoint=endpoint,
            key_kind="demo",
            api_key=DEMO_KEY,
            attempt_sequence=attempt_sequence,
            max_calls=MAX_DEMO_CALLS,
            calls_used=demo_calls_used,
        )
        attempts_by_endpoint[endpoint.endpoint_id].extend(attempts)

    if real_key_available:
        endpoint_index = endpoint_by_id()
        for endpoint_id in REAL_FALLBACK_PRIORITY:
            if real_calls_used >= MAX_REAL_CALLS:
                print("[limit] real call limit reached; stopping fallback attempts.")
                break
            attempts = attempts_by_endpoint[endpoint_id]
            if chosen_result(attempts=attempts) is not None:
                continue
            endpoint = endpoint_index[endpoint_id]
            real_attempts, attempt_sequence, real_calls_used = (
                run_attempt_with_retry_policy(
                    endpoint=endpoint,
                    key_kind="real",
                    api_key=real_key,
                    attempt_sequence=attempt_sequence,
                    max_calls=MAX_REAL_CALLS,
                    calls_used=real_calls_used,
                )
            )
            attempts_by_endpoint[endpoint_id].extend(real_attempts)
    if not real_key_available:
        print("[real_key] ALPHAVANTAGE_API_KEY is absent; real checks deferred.")

    observed = build_observed_output(
        attempts_by_endpoint=attempts_by_endpoint,
        demo_calls_used=demo_calls_used,
        real_calls_used=real_calls_used,
        real_key_available=real_key_available,
        source="Alpha Vantage API responses only",
    )

    write_report_outputs(observed=observed)
    write_json_file(
        path=ARTIFACT_DIR / "state.json",
        payload={
            "completed_at_utc": utc_now(),
            "demo_calls_used": demo_calls_used,
            "max_demo_calls": MAX_DEMO_CALLS,
            "max_real_calls": MAX_REAL_CALLS,
            "outputs": [
                "reports/alpha_vantage_observed_schema.md",
                "reports/alpha_vantage_observed_schema.json",
                "reports/alpha_vantage_next_run_queue.json",
                "artifacts/alpha_vantage/call_log.jsonl",
                "artifacts/alpha_vantage/state.json",
            ],
            "real_calls_used": real_calls_used,
            "real_key_available": real_key_available,
            "status": "complete",
        },
    )
    print("[complete] Required reports and artifacts were written.")


if __name__ == "__main__":
    main()
