"""Build the AV / SEC canonical metric alignment matrix.

Purpose:
    Join source observations by canonical metric and period, preserve source
    metadata, and classify differences without silently forcing equivalence.

Call graph:
    cli analyze/verify -> build_alignment_rows
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from step0b.av_archive import ENDPOINTS, av_raw_path, load_av_payload
from step0b.mapping import definition_status_override, metric_applicability
from step0b.models import ANNUAL, QUARTER, QUARTERLY_METRICS, Company, MetricConfig
from step0b.normalization import (
    comparison_rule_for_metric,
    comparison_value_for_metric,
    decimal_to_text,
    infer_annual_start,
    infer_quarter_start,
    parse_decimal,
    parse_iso_date,
)
from step0b.period_selection import (
    reports_sorted_desc,
    select_annual_eps_row,
)
from step0b.sec_client import companyfacts_path, submissions_path
from step0b.sec_companyfacts import (
    SecSelection,
    compose_total_debt,
    select_sec_fact,
)
from step0b.sec_submissions import latest_filing
from step0b.models import read_json_file


MONEY_UNIT = "USD"
EPS_UNIT = "USD/share"


def metric_periods(*, metric: MetricConfig) -> list[str]:
    """Return comparison period scopes for one metric.

    Args:
        metric: Canonical metric config.

    Returns:
        ANNUAL plus QUARTER when required by the spike.
    """
    periods = [ANNUAL]
    if metric.canonical_metric in QUARTERLY_METRICS:
        periods.append(QUARTER)
    return periods


def load_av_bundle(*, company: Company) -> dict[str, dict[str, Any]]:
    """Load all five AV endpoint payloads for one company.

    Args:
        company: Experiment company.

    Returns:
        Mapping of endpoint name to parsed JSON payload.
    """
    bundle: dict[str, dict[str, Any]] = {}
    for endpoint in ENDPOINTS:
        bundle[endpoint] = load_av_payload(company=company, endpoint=endpoint)
    return bundle


def find_report_by_end(
    *,
    rows: list[dict[str, Any]],
    target_end: date,
) -> dict[str, Any] | None:
    """Find an AV report row by fiscalDateEnding.

    Args:
        rows: AV report rows.
        target_end: Target period end date.

    Returns:
        Matching row or None.
    """
    for row in reports_sorted_desc(rows=rows):
        if parse_iso_date(value=row["fiscalDateEnding"]) == target_end:
            return row
    return None


def av_currency(*, av_bundle: dict[str, dict[str, Any]]) -> str:
    """Return AV reporting currency from OVERVIEW when available.

    Args:
        av_bundle: Parsed AV endpoint payloads.

    Returns:
        Currency code, defaulting to USD only when the field is absent.
    """
    overview = av_bundle["OVERVIEW"]
    if "Currency" in overview and str(overview["Currency"]).strip() != "":
        return str(overview["Currency"]).strip()
    return MONEY_UNIT


def av_rows_for_metric(
    *,
    av_bundle: dict[str, dict[str, Any]],
    metric: MetricConfig,
    period_kind: str,
) -> list[dict[str, Any]]:
    """Return AV rows for one metric endpoint and period scope.

    Args:
        av_bundle: Parsed AV endpoint payloads.
        metric: Canonical metric config.
        period_kind: ANNUAL or QUARTER.

    Returns:
        AV report rows.
    """
    payload = av_bundle[metric.av_endpoint]
    if metric.av_endpoint == "EARNINGS":
        if period_kind == ANNUAL:
            return list(payload["annualEarnings"])
        return list(payload["quarterlyEarnings"])
    if period_kind == ANNUAL:
        return list(payload["annualReports"])
    return list(payload["quarterlyReports"])


def av_period_start(*, period_kind: str, period_end: date) -> date | None:
    """Infer period start for matrix display.

    Args:
        period_kind: ANNUAL or QUARTER.
        period_end: Period end date.

    Returns:
        Annual inferred start or None for quarter when source does not provide
        an independent start date.
    """
    if period_kind == ANNUAL:
        return infer_annual_start(period_end=period_end)
    return None


def av_value_for_metric(
    *,
    company: Company,
    av_bundle: dict[str, dict[str, Any]],
    metric: MetricConfig,
    period_kind: str,
    target_end: date,
) -> dict[str, Any]:
    """Extract and normalize one AV metric value.

    Args:
        company: Experiment company.
        av_bundle: Parsed AV endpoint payloads.
        metric: Canonical metric config.
        period_kind: ANNUAL or QUARTER.
        target_end: Target period end date.

    Returns:
        Dict containing Decimal value, unit, raw file, and notes.
    """
    rows = av_rows_for_metric(
        av_bundle=av_bundle,
        metric=metric,
        period_kind=period_kind,
    )
    if metric.av_endpoint == "EARNINGS" and period_kind == ANNUAL:
        row = select_annual_eps_row(
            annual_rows=rows,
            quarterly_rows=list(av_bundle["EARNINGS"]["quarterlyEarnings"]),
            fiscal_year_end_month_day=company.fiscal_year_end_month_day,
            target_end=target_end,
        )
        duplicate_note = "annualEarnings quarterly duplicate excluded when detected"
    else:
        row = find_report_by_end(rows=rows, target_end=target_end)
        duplicate_note = ""

    if row is None:
        return {
            "raw_value": None,
            "value": None,
            "unit": (
                EPS_UNIT
                if metric.av_endpoint == "EARNINGS"
                else av_currency(av_bundle=av_bundle)
            ),
            "raw_file": str(av_raw_path(company=company, endpoint=metric.av_endpoint)),
            "status": "MISSING_AV",
            "notes": f"no AV row for {target_end.isoformat()}",
            "period_start": av_period_start(
                period_kind=period_kind,
                period_end=target_end,
            ),
            "period_end": target_end,
        }

    raw_value = None
    if metric.av_field in row:
        raw_value = row[metric.av_field]
    raw_decimal = parse_decimal(value=raw_value)
    comparison_value = comparison_value_for_metric(
        canonical_metric=metric.canonical_metric,
        normalization_rule=metric.normalization,
        value=raw_decimal,
    )
    normalization_rule = comparison_rule_for_metric(
        canonical_metric=metric.canonical_metric,
        normalization_rule=metric.normalization,
    )
    unit = EPS_UNIT if metric.av_endpoint == "EARNINGS" else av_currency(av_bundle=av_bundle)
    if "reportedCurrency" in row and metric.av_endpoint != "EARNINGS":
        unit = row["reportedCurrency"]

    notes = duplicate_note
    if normalization_rule:
        notes = f"{notes}; {normalization_rule}".strip("; ")

    return {
        "raw_value": raw_decimal,
        "value": comparison_value,
        "unit": unit,
        "raw_file": str(av_raw_path(company=company, endpoint=metric.av_endpoint)),
        "status": "OK" if raw_decimal is not None else "MISSING_AV",
        "notes": notes,
        "period_start": av_period_start(period_kind=period_kind, period_end=target_end),
        "period_end": target_end,
    }


def select_sec_for_metric(
    *,
    metric: MetricConfig,
    companyfacts: dict[str, Any],
    target_end: date,
    period_kind: str,
) -> SecSelection:
    """Select or compose the SEC observation for one metric.

    Args:
        metric: Canonical metric config.
        companyfacts: Decoded SEC companyfacts JSON.
        target_end: Target period end.
        period_kind: ANNUAL or QUARTER.

    Returns:
        SEC selection result.
    """
    if metric.requires_composition:
        return compose_total_debt(
            metric=metric,
            companyfacts=companyfacts,
            target_end=target_end,
            period_kind=period_kind,
        )
    return select_sec_fact(
        metric=metric,
        companyfacts=companyfacts,
        target_end=target_end,
        period_kind=period_kind,
    )


def normalized_unit_for_metric(*, metric: MetricConfig, av_unit: str, sec_unit: str) -> str:
    """Return the matrix normalized unit label.

    Args:
        metric: Canonical metric config.
        av_unit: AV unit/currency.
        sec_unit: SEC unit.

    Returns:
        Unit label used for comparison.
    """
    if metric.canonical_metric == "earnings.diluted_eps":
        return EPS_UNIT
    if av_unit == sec_unit and av_unit != "":
        return av_unit
    if av_unit == MONEY_UNIT and sec_unit == MONEY_UNIT:
        return MONEY_UNIT
    return ""


def difference_values(
    *,
    av_value: Decimal | None,
    sec_value: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Compute absolute and relative differences.

    Args:
        av_value: AV Decimal value.
        sec_value: SEC Decimal value.

    Returns:
        Tuple of absolute difference and relative difference.
    """
    if av_value is None or sec_value is None:
        return None, None
    absolute = abs(av_value - sec_value)
    denominator = max(abs(av_value), abs(sec_value), Decimal("1"))
    return absolute, absolute / denominator


def numeric_status(
    *,
    metric: MetricConfig,
    absolute_difference: Decimal | None,
    relative_difference: Decimal | None,
) -> str:
    """Classify numeric difference using spike thresholds.

    Args:
        metric: Canonical metric config.
        absolute_difference: Absolute numeric difference.
        relative_difference: Relative difference or None.

    Returns:
        MATCH, NEAR_MATCH, DIFFERENT, or MANUAL_REVIEW.
    """
    if absolute_difference is None or relative_difference is None:
        return "MANUAL_REVIEW"
    if metric.canonical_metric == "earnings.diluted_eps":
        if absolute_difference <= Decimal("0.01"):
            return "MATCH"
        if absolute_difference <= Decimal("0.05"):
            return "NEAR_MATCH"
        return "DIFFERENT"
    if relative_difference <= Decimal("0.001"):
        return "MATCH"
    if relative_difference <= Decimal("0.02"):
        return "NEAR_MATCH"
    return "DIFFERENT"


def sec_comparison_value(
    *,
    metric: MetricConfig,
    sec_result: SecSelection,
) -> Decimal | None:
    """Return the SEC value used for numeric comparison.

    Args:
        metric: Canonical metric config.
        sec_result: Selected SEC fact or empty selection.

    Returns:
        Decimal comparison value or None.
    """
    return comparison_value_for_metric(
        canonical_metric=metric.canonical_metric,
        normalization_rule=metric.normalization,
        value=sec_result.value,
    )


def comparison_status(
    *,
    company: Company,
    metric: MetricConfig,
    av_result: dict[str, Any],
    sec_result: SecSelection,
    normalized_unit: str,
) -> str:
    """Decide the row comparison status.

    Args:
        company: Experiment company.
        metric: Canonical metric config.
        av_result: AV extraction result.
        sec_result: SEC selection result.
        normalized_unit: Unit label used for comparison.

    Returns:
        One allowed comparison status.
    """
    applicability = metric_applicability(
        metric=metric,
        company_archetype=company.archetype,
    )
    if applicability == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if av_result["status"] == "MISSING_AV":
        return "MISSING_AV"
    if metric.requires_composition:
        return "REQUIRES_COMPOSITION"
    if sec_result.status == "REQUIRES_DERIVATION":
        return "REQUIRES_DERIVATION"
    if sec_result.status != "OK":
        return "MISSING_SEC"
    override = definition_status_override(
        metric=metric,
        company_archetype=company.archetype,
    )
    if override is not None:
        return override
    if normalized_unit == "":
        return "MANUAL_REVIEW"
    absolute, relative = difference_values(
        av_value=av_result["value"],
        sec_value=sec_comparison_value(metric=metric, sec_result=sec_result),
    )
    return numeric_status(
        metric=metric,
        absolute_difference=absolute,
        relative_difference=relative,
    )


def difference_reason(
    *,
    status: str,
    company: Company,
    metric: MetricConfig,
    sec_result: SecSelection,
    av_notes: str,
) -> str:
    """Build a concise difference rationale.

    Args:
        status: Comparison status.
        company: Experiment company.
        metric: Canonical metric config.
        sec_result: SEC selection result.
        av_notes: AV extraction notes.

    Returns:
        Human-readable rationale.
    """
    override = definition_status_override(
        metric=metric,
        company_archetype=company.archetype,
    )
    reasons: list[str] = []
    if status == "NOT_APPLICABLE":
        reasons.append(f"{company.archetype} archetype does not report this metric cleanly")
    if status == "REQUIRES_COMPOSITION":
        reasons.append("SEC total debt requires explicit component formula")
    if override == "DEFINITION_MISMATCH":
        reasons.append(f"{company.archetype} source definitions are not equivalent")
    if sec_result.selection_reason:
        reasons.append(sec_result.selection_reason)
    if av_notes:
        reasons.append(av_notes)
    if not reasons:
        reasons.append(status.lower())
    return "; ".join(reasons)


def row_period_dates(
    *,
    av_result: dict[str, Any],
    sec_result: SecSelection,
) -> tuple[str, str]:
    """Choose display period start/end for one matrix row.

    Args:
        av_result: AV extraction result.
        sec_result: SEC selection result.

    Returns:
        Tuple of ISO period_start and period_end strings.
    """
    start = av_result["period_start"]
    end = av_result["period_end"]
    if sec_result.period_start is not None:
        start = sec_result.period_start
    if sec_result.period_end is not None:
        end = sec_result.period_end
    start_text = "" if start is None else start.isoformat()
    return start_text, end.isoformat()


def canonical_period_dates(
    *,
    metric: MetricConfig,
    period_kind: str,
    target_end: date,
) -> tuple[str, str]:
    """Return source-independent canonical period dates for identity.

    Args:
        metric: Canonical metric config.
        period_kind: ANNUAL or QUARTER.
        target_end: Target period end.

    Returns:
        Tuple of ISO period_start and period_end.
    """
    if metric.period_type == "instant":
        start = target_end
    elif period_kind == ANNUAL:
        start = infer_annual_start(period_end=target_end)
    else:
        start = infer_quarter_start(period_end=target_end)
    return start.isoformat(), target_end.isoformat()


def build_row(
    *,
    company: Company,
    metric: MetricConfig,
    period_kind: str,
    av_result: dict[str, Any],
    sec_result: SecSelection,
    sec_raw_file: Path,
    period_start: str,
    period_end: str,
) -> dict[str, str]:
    """Build one CSV-ready comparison row.

    Args:
        company: Experiment company.
        metric: Canonical metric config.
        period_kind: ANNUAL or QUARTER.
        av_result: AV extraction result.
        sec_result: SEC selection result.
        sec_raw_file: SEC companyfacts raw file path.
        period_start: Canonical source-independent period start.
        period_end: Canonical source-independent period end.

    Returns:
        Dict with matrix columns.
    """
    normalized_unit = normalized_unit_for_metric(
        metric=metric,
        av_unit=av_result["unit"],
        sec_unit=sec_result.unit,
    )
    status = comparison_status(
        company=company,
        metric=metric,
        av_result=av_result,
        sec_result=sec_result,
        normalized_unit=normalized_unit,
    )
    absolute, relative = difference_values(
        av_value=av_result["value"],
        sec_value=sec_comparison_value(metric=metric, sec_result=sec_result),
    )
    manual_notes = sec_result.rejected_candidates
    if sec_result.components:
        manual_notes = json.dumps(
            obj={"components": sec_result.components, "rejected": manual_notes},
            ensure_ascii=False,
            sort_keys=True,
        )
    return {
        "company_id": company.company_id,
        "symbol": company.symbol,
        "company_archetype": company.archetype,
        "canonical_metric": metric.canonical_metric,
        "metric_applicability": metric_applicability(
            metric=metric,
            company_archetype=company.archetype,
        ),
        "comparison_period_kind": period_kind,
        "period_start": period_start,
        "period_end": period_end,
        "av_endpoint": metric.av_endpoint,
        "av_field": metric.av_field,
        "av_value": decimal_to_text(value=av_result["raw_value"]),
        "av_raw_value": decimal_to_text(value=av_result["raw_value"]),
        "av_comparison_value": decimal_to_text(value=av_result["value"]),
        "av_currency": av_result["unit"],
        "av_unit": av_result["unit"],
        "av_raw_file": av_result["raw_file"],
        "sec_taxonomy": "us-gaap",
        "sec_candidate_concepts": sec_result.all_candidate_concepts,
        "sec_selected_concept": sec_result.selected_concept,
        "sec_value": decimal_to_text(value=sec_result.value),
        "sec_raw_value": decimal_to_text(value=sec_result.value),
        "sec_comparison_value": decimal_to_text(
            value=sec_comparison_value(metric=metric, sec_result=sec_result),
        ),
        "sec_unit": sec_result.unit,
        "normalized_unit": normalized_unit,
        "sec_form": sec_result.form,
        "sec_accession": sec_result.accession,
        "sec_filed_at": sec_result.filed_at,
        "sec_raw_file": str(sec_raw_file),
        "normalization_rule": comparison_rule_for_metric(
            canonical_metric=metric.canonical_metric,
            normalization_rule=metric.normalization,
        ),
        "absolute_difference": decimal_to_text(value=absolute),
        "relative_difference": decimal_to_text(value=relative),
        "comparison_status": status,
        "difference_reason": difference_reason(
            status=status,
            company=company,
            metric=metric,
            sec_result=sec_result,
            av_notes=av_result["notes"],
        ),
        "manual_notes": manual_notes,
    }


def target_period_end(
    *,
    submissions: dict[str, Any],
    period_kind: str,
) -> date:
    """Read target period end from latest SEC filing report date.

    Args:
        submissions: Decoded SEC submissions JSON.
        period_kind: ANNUAL or QUARTER.

    Returns:
        Period end date.
    """
    if period_kind == ANNUAL:
        filing = latest_filing(submissions=submissions, forms={"10-K", "10-K/A"})
    else:
        filing = latest_filing(submissions=submissions, forms={"10-Q", "10-Q/A"})
    return parse_iso_date(value=filing["reportDate"])


def build_company_rows(
    *,
    company: Company,
    metrics: list[MetricConfig],
) -> list[dict[str, str]]:
    """Build all matrix rows for one company.

    Args:
        company: Experiment company.
        metrics: Canonical metric configs.

    Returns:
        CSV-ready matrix rows.
    """
    av_bundle = load_av_bundle(company=company)
    submissions = read_json_file(path=submissions_path(company=company))
    companyfacts = read_json_file(path=companyfacts_path(company=company))
    rows: list[dict[str, str]] = []
    for metric in metrics:
        for period_kind in metric_periods(metric=metric):
            target_end = target_period_end(
                submissions=submissions,
                period_kind=period_kind,
            )
            av_result = av_value_for_metric(
                company=company,
                av_bundle=av_bundle,
                metric=metric,
                period_kind=period_kind,
                target_end=target_end,
            )
            sec_result = select_sec_for_metric(
                metric=metric,
                companyfacts=companyfacts,
                target_end=target_end,
                period_kind=period_kind,
            )
            period_start, period_end = canonical_period_dates(
                metric=metric,
                period_kind=period_kind,
                target_end=target_end,
            )
            rows.append(
                build_row(
                    company=company,
                    metric=metric,
                    period_kind=period_kind,
                    av_result=av_result,
                    sec_result=sec_result,
                    sec_raw_file=companyfacts_path(company=company),
                    period_start=period_start,
                    period_end=period_end,
                )
            )
    return rows


def build_alignment_rows(
    *,
    companies: list[Company],
    metrics: list[MetricConfig],
) -> list[dict[str, str]]:
    """Build the full alignment matrix.

    Args:
        companies: Experiment companies.
        metrics: Canonical metric configs.

    Returns:
        54 CSV-ready rows for the configured spike.
    """
    rows: list[dict[str, str]] = []
    for company in companies:
        rows.extend(build_company_rows(company=company, metrics=metrics))
    return rows
