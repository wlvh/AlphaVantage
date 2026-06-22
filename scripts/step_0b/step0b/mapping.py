"""Mapping policy helpers for canonical metrics.

Purpose:
    Keep archetype applicability, SEC unit preference, and candidate summaries
    in one place so comparison rows explain decisions consistently.

Call graph:
    comparison/sec_companyfacts/reporting/tests -> mapping
"""

from __future__ import annotations

from step0b.models import MetricConfig


def metric_applicability(*, metric: MetricConfig, company_archetype: str) -> str:
    """Return APPLICABLE or NOT_APPLICABLE for a company archetype.

    Args:
        metric: Canonical metric config.
        company_archetype: Company archetype.

    Returns:
        Applicability string for matrix output.
    """
    if company_archetype in metric.definition_risks:
        if metric.definition_risks[company_archetype] == "NOT_APPLICABLE":
            return "NOT_APPLICABLE"
    return "APPLICABLE"


def definition_status_override(
    *,
    metric: MetricConfig,
    company_archetype: str,
) -> str | None:
    """Return an archetype-specific comparison status override.

    Args:
        metric: Canonical metric config.
        company_archetype: Company archetype.

    Returns:
        Status override or None.
    """
    if company_archetype in metric.definition_risks:
        return metric.definition_risks[company_archetype]
    return None


def sec_unit_preferences(*, metric: MetricConfig) -> list[str]:
    """Return preferred SEC units for a metric.

    Args:
        metric: Canonical metric config.

    Returns:
        Ordered unit names.
    """
    if metric.canonical_metric == "earnings.diluted_eps":
        return ["USD/shares"]
    return ["USD", "USD/shares"]


def candidate_summary(
    *,
    candidates: list[str],
    present: list[str],
) -> str:
    """Render SEC candidate concept presence for CSV output.

    Args:
        candidates: Ordered configured candidate concepts.
        present: Candidate concepts observed in companyfacts.

    Returns:
        Semicolon-delimited concept:present/missing string.
    """
    parts: list[str] = []
    for concept in candidates:
        status = "present" if concept in present else "missing"
        parts.append(f"{concept}:{status}")
    return "; ".join(parts)
