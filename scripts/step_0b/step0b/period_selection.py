"""Period selection helpers for AV reports and SEC facts.

Purpose:
    Keep annual, quarterly, instant, and AV annualEarnings duplicate rules
    explicit and testable.

Call graph:
    comparison/tests -> period_selection
"""

from __future__ import annotations

from datetime import date
from typing import Any

from step0b.normalization import parse_decimal, parse_iso_date


def fiscal_month_day(*, value: str) -> str:
    """Normalize a fiscal year-end month-day marker.

    Args:
        value: MM-DD string.

    Returns:
        Same MM-DD string after basic validation.
    """
    if len(value) != 5 or value[2] != "-":
        raise ValueError(f"Invalid fiscal month-day: {value}")
    return value


def date_month_day(*, value: str) -> str:
    """Return MM-DD from an ISO date string.

    Args:
        value: YYYY-MM-DD date string.

    Returns:
        MM-DD substring.
    """
    parsed = parse_iso_date(value=value)
    return f"{parsed.month:02d}-{parsed.day:02d}"


def reports_sorted_desc(*, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort AV report rows by fiscalDateEnding descending.

    Args:
        rows: AV report row dicts.

    Returns:
        Sorted list. Rows without fiscalDateEnding are ignored.
    """
    usable: list[dict[str, Any]] = []
    for row in rows:
        if "fiscalDateEnding" in row:
            usable.append(row)
    return sorted(
        usable,
        key=lambda item: parse_iso_date(value=item["fiscalDateEnding"]),
        reverse=True,
    )


def select_latest_report(*, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the latest AV report row.

    Args:
        rows: AV annualReports or quarterlyReports rows.

    Returns:
        Latest report row.

    Raises:
        ValueError: If no dated row exists.
    """
    sorted_rows = reports_sorted_desc(rows=rows)
    if not sorted_rows:
        raise ValueError("No dated AV report rows")
    return sorted_rows[0]


def is_quarterly_duplicate_annual_eps(
    *,
    annual_row: dict[str, Any],
    quarterly_rows: list[dict[str, Any]],
    fiscal_year_end_month_day: str,
) -> bool:
    """Detect AV annualEarnings rows that are actually quarterly duplicates.

    Args:
        annual_row: One AV annualEarnings row.
        quarterly_rows: AV quarterlyEarnings rows.
        fiscal_year_end_month_day: Company fiscal year end as MM-DD.

    Returns:
        True when the annual row date is not fiscal year end and the same date
        and EPS exist in quarterlyEarnings.
    """
    if "fiscalDateEnding" not in annual_row or "reportedEPS" not in annual_row:
        return False
    annual_date = annual_row["fiscalDateEnding"]
    if date_month_day(value=annual_date) == fiscal_month_day(
        value=fiscal_year_end_month_day,
    ):
        return False
    annual_eps = parse_decimal(value=annual_row["reportedEPS"])
    for quarter_row in quarterly_rows:
        if "fiscalDateEnding" not in quarter_row or "reportedEPS" not in quarter_row:
            continue
        quarter_eps = parse_decimal(value=quarter_row["reportedEPS"])
        if quarter_row["fiscalDateEnding"] == annual_date and quarter_eps == annual_eps:
            return True
    return False


def select_annual_eps_row(
    *,
    annual_rows: list[dict[str, Any]],
    quarterly_rows: list[dict[str, Any]],
    fiscal_year_end_month_day: str,
    target_end: date,
) -> dict[str, Any] | None:
    """Select a valid AV annual EPS row aligned to target year end.

    Args:
        annual_rows: AV annualEarnings rows.
        quarterly_rows: AV quarterlyEarnings rows.
        fiscal_year_end_month_day: Company fiscal year end as MM-DD.
        target_end: Target fiscal year end.

    Returns:
        Matching non-duplicate annual EPS row, or None.
    """
    for row in reports_sorted_desc(rows=annual_rows):
        if parse_iso_date(value=row["fiscalDateEnding"]) != target_end:
            continue
        duplicate = is_quarterly_duplicate_annual_eps(
            annual_row=row,
            quarterly_rows=quarterly_rows,
            fiscal_year_end_month_day=fiscal_year_end_month_day,
        )
        if not duplicate:
            return row
    return None
