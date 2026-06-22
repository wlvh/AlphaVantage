"""Value, period, and unit normalization helpers.

Purpose:
    Convert source strings into explicit Decimal/date values while preserving
    missing values as None and documenting any semantic normalization.

Call graph:
    comparison/sec_companyfacts/narrative_evidence/tests -> normalization
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any


MISSING_STRINGS = {"", "None", "none", "NULL", "null", "NaN", "nan"}


def normalize_missing(*, value: Any) -> Any:
    """Normalize configured missing-value tokens to None.

    Args:
        value: Source scalar value.

    Returns:
        None for configured null tokens; otherwise the original value.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() in MISSING_STRINGS:
        return None
    return value


def parse_decimal(*, value: Any) -> Decimal | None:
    """Parse a source scalar as Decimal without using float.

    Args:
        value: Source scalar value or null-like token.

    Returns:
        Decimal value, or None when the source value is explicitly missing.

    Raises:
        ValueError: If a non-missing value cannot be parsed as Decimal.
    """
    normalized = normalize_missing(value=value)
    if normalized is None:
        return None
    try:
        return Decimal(value=str(normalized).strip())
    except InvalidOperation as error:
        raise ValueError(f"Invalid decimal value: {normalized!r}") from error


def parse_iso_date(*, value: str) -> date:
    """Parse an ISO YYYY-MM-DD date.

    Args:
        value: Date string in YYYY-MM-DD format.

    Returns:
        date object.
    """
    return date.fromisoformat(value)


def decimal_to_text(*, value: Decimal | None) -> str:
    """Serialize a Decimal for CSV/JSON reports.

    Args:
        value: Decimal or None.

    Returns:
        Plain string, or empty string for None.
    """
    if value is None:
        return ""
    return format(value, "f")


def normalize_capex_outflow(*, value: Decimal | None) -> tuple[Decimal | None, str]:
    """Represent capital expenditure cash outflow as positive absolute value.

    Args:
        value: Source Decimal value or None.

    Returns:
        Tuple of normalized value and rule description.
    """
    if value is None:
        return None, "cash_outflow_absolute_positive; source_missing"
    return abs(value), "cash_outflow_absolute_positive"


def infer_annual_start(*, period_end: date) -> date:
    """Infer a calendar-style annual start from a fiscal year end.

    Args:
        period_end: Fiscal year end date.

    Returns:
        First day after the previous year end.
    """
    return date(year=period_end.year, month=1, day=1)


def is_full_year_duration(*, start: date, end: date) -> bool:
    """Check whether a SEC duration is close to a full fiscal year.

    Args:
        start: SEC fact start date.
        end: SEC fact end date.

    Returns:
        True when duration is between 300 and 380 days inclusive.
    """
    days = (end - start).days + 1
    return 300 <= days <= 380


def is_quarter_duration(*, start: date, end: date) -> bool:
    """Check whether a SEC duration is close to an independent quarter.

    Args:
        start: SEC fact start date.
        end: SEC fact end date.

    Returns:
        True when duration is between 75 and 110 days inclusive.
    """
    days = (end - start).days + 1
    return 75 <= days <= 110


def previous_day(*, value: date) -> date:
    """Return the day before a date.

    Args:
        value: Input date.

    Returns:
        Date minus one day.
    """
    return value - timedelta(days=1)
