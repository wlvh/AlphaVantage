"""Shared models and configuration loaders for the Step 0B spike.

Purpose:
    Keep path, status, company, and metric definitions centralized so fetch,
    selection, comparison, and reporting use one contract.

Call graph:
    cli -> load_companies/load_metrics -> fetch/analyze/report modules
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SPIKE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = Path(__file__).resolve().parents[4]
CONFIG_DIR = SPIKE_DIR / "config"
DATA_DIR = SPIKE_DIR / "data"
OUTPUT_DIR = SPIKE_DIR / "outputs"

ANNUAL = "ANNUAL"
QUARTER = "QUARTER"
QUARTERLY_METRICS = {
    "financial.revenue",
    "financial.net_income",
    "balance.total_assets",
    "balance.total_equity",
    "cashflow.operating_cash_flow",
    "earnings.diluted_eps",
}

COMPARISON_STATUSES = {
    "MATCH",
    "NEAR_MATCH",
    "DIFFERENT",
    "NOT_APPLICABLE",
    "MISSING_AV",
    "MISSING_SEC",
    "PERIOD_MISMATCH",
    "DEFINITION_MISMATCH",
    "REQUIRES_COMPOSITION",
    "REQUIRES_DERIVATION",
    "MANUAL_REVIEW",
}


@dataclass(frozen=True)
class Company:
    """Describe one fixed experiment company.

    Args:
        company_id: Stable internal ID such as NYSE:IBM.
        name: Human-readable legal or issuer name.
        symbol: Alpha Vantage ticker.
        exchange: Listing exchange.
        cik10: SEC CIK as a ten-digit string.
        archetype: Business archetype used for applicability checks.
        fiscal_year_end_month_day: MM-DD fiscal year-end marker.
        av_source: existing_archive for IBM, live_or_cached otherwise.
    """

    company_id: str
    name: str
    symbol: str
    exchange: str
    cik10: str
    archetype: str
    fiscal_year_end_month_day: str
    av_source: str


@dataclass(frozen=True)
class MetricConfig:
    """Describe one canonical metric and source mapping candidates.

    Args:
        canonical_metric: Source-free canonical metric key.
        av_endpoint: Alpha Vantage endpoint name.
        av_field: Alpha Vantage report field.
        period_type: duration or instant.
        sec_candidates: Ordered SEC us-gaap concept candidates.
        definition_risks: Archetype-specific status overrides.
        requires_composition: True when SEC should be represented by formula.
        normalization: Optional normalization rule name.
    """

    canonical_metric: str
    av_endpoint: str
    av_field: str
    period_type: str
    sec_candidates: list[str]
    definition_risks: dict[str, str]
    requires_composition: bool
    normalization: str | None


def read_json_file(*, path: Path) -> Any:
    """Read a UTF-8 JSON file.

    Args:
        path: JSON file path.

    Returns:
        Decoded JSON value.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(*, path: Path, payload: Any) -> None:
    """Write a deterministic UTF-8 JSON file.

    Args:
        path: Destination file path.
        payload: JSON-serializable value.

    Returns:
        None. The file is written with stable key ordering.
    """
    # Deterministic JSON keeps rerun diffs focused on data changes.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        data=json.dumps(obj=payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_companies() -> list[Company]:
    """Load fixed experiment companies from config.

    Returns:
        List of Company records in configured order.
    """
    rows = read_json_file(path=CONFIG_DIR / "companies.json")
    companies: list[Company] = []
    for row in rows:
        companies.append(
            Company(
                company_id=row["company_id"],
                name=row["name"],
                symbol=row["symbol"],
                exchange=row["exchange"],
                cik10=row["cik10"],
                archetype=row["archetype"],
                fiscal_year_end_month_day=row["fiscal_year_end_month_day"],
                av_source=row["av_source"],
            )
        )
    return companies


def load_metrics() -> list[MetricConfig]:
    """Load canonical metric definitions from config.

    Returns:
        List of MetricConfig records in configured order.
    """
    rows = read_json_file(path=CONFIG_DIR / "canonical_metrics.json")
    metrics: list[MetricConfig] = []
    for row in rows:
        requires_composition = False
        if "requires_composition" in row:
            requires_composition = bool(row["requires_composition"])
        normalization = None
        if "normalization" in row:
            normalization = row["normalization"]
        metrics.append(
            MetricConfig(
                canonical_metric=row["canonical_metric"],
                av_endpoint=row["av_endpoint"],
                av_field=row["av_field"],
                period_type=row["period_type"],
                sec_candidates=list(row["sec_candidates"]),
                definition_risks=dict(row["definition_risks"]),
                requires_composition=requires_composition,
                normalization=normalization,
            )
        )
    return metrics
