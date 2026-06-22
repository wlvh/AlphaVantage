"""SEC Company Facts concept and fact selection.

Purpose:
    Select facts by concept, form, period end, duration type, unit, and filed
    date instead of taking the last fact array element.

Call graph:
    comparison/tests -> select_sec_fact/compose_total_debt
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from step0b.mapping import candidate_summary, sec_unit_preferences
from step0b.models import MetricConfig
from step0b.normalization import (
    is_full_year_duration,
    is_quarter_duration,
    parse_decimal,
    parse_iso_date,
)


@dataclass(frozen=True)
class SecSelection:
    """Represent the result of SEC fact selection.

    Args:
        status: OK, MISSING_SEC, or REQUIRES_DERIVATION.
        all_candidate_concepts: Presence summary for output.
        selected_concept: Chosen concept or formula.
        rejected_candidates: Rejection rationale.
        selection_reason: Human-readable selection reason.
        value: Selected Decimal value.
        unit: SEC unit.
        form: SEC form.
        accession: SEC accession number.
        filed_at: SEC filed date.
        period_start: Fact start date.
        period_end: Fact end date.
        components: Formula components for composed metrics.
    """

    status: str
    all_candidate_concepts: str
    selected_concept: str
    rejected_candidates: str
    selection_reason: str
    value: Decimal | None
    unit: str
    form: str
    accession: str
    filed_at: str
    period_start: date | None
    period_end: date | None
    components: list[dict[str, str]]


def us_gaap_facts(*, companyfacts: dict[str, Any]) -> dict[str, Any]:
    """Return the us-gaap facts object.

    Args:
        companyfacts: Decoded SEC companyfacts JSON.

    Returns:
        Mapping of concept name to concept facts.
    """
    return companyfacts["facts"]["us-gaap"]


def present_candidates(
    *,
    companyfacts: dict[str, Any],
    candidates: list[str],
) -> list[str]:
    """Return configured candidates present in companyfacts.

    Args:
        companyfacts: Decoded SEC companyfacts JSON.
        candidates: Candidate concept names.

    Returns:
        Present candidate names in configured order.
    """
    facts = us_gaap_facts(companyfacts=companyfacts)
    present: list[str] = []
    for concept in candidates:
        if concept in facts:
            present.append(concept)
    return present


def fact_unit_rows(
    *,
    companyfacts: dict[str, Any],
    concept: str,
    preferred_units: list[str],
) -> list[dict[str, Any]]:
    """Return fact rows for preferred units in priority order.

    Args:
        companyfacts: Decoded SEC companyfacts JSON.
        concept: SEC us-gaap concept.
        preferred_units: Ordered allowed units.

    Returns:
        Rows with an added _unit key.
    """
    facts = us_gaap_facts(companyfacts=companyfacts)
    if concept not in facts:
        return []
    units = facts[concept]["units"]
    rows: list[dict[str, Any]] = []
    for unit in preferred_units:
        if unit not in units:
            continue
        for row in units[unit]:
            row_copy = dict(row)
            row_copy["_unit"] = unit
            rows.append(row_copy)
    return rows


def fact_form_allowed(*, row: dict[str, Any], period_kind: str) -> bool:
    """Check SEC form eligibility for annual or quarter comparison.

    Args:
        row: SEC fact row.
        period_kind: ANNUAL or QUARTER.

    Returns:
        True when row form is eligible.
    """
    if "form" not in row:
        return False
    if period_kind == "ANNUAL":
        return row["form"] in {"10-K", "10-K/A"}
    return row["form"] in {"10-Q", "10-Q/A"}


def row_end_date(*, row: dict[str, Any]) -> date | None:
    """Return a SEC fact end date.

    Args:
        row: SEC fact row.

    Returns:
        Date or None when unavailable.
    """
    if "end" not in row:
        return None
    return parse_iso_date(value=row["end"])


def row_start_date(*, row: dict[str, Any]) -> date | None:
    """Return a SEC fact start date.

    Args:
        row: SEC fact row.

    Returns:
        Date or None when unavailable.
    """
    if "start" not in row:
        return None
    return parse_iso_date(value=row["start"])


def row_matches_period(
    *,
    row: dict[str, Any],
    target_end: date,
    period_kind: str,
    metric_period_type: str,
) -> bool:
    """Check SEC fact period alignment.

    Args:
        row: SEC fact row.
        target_end: Target period end date.
        period_kind: ANNUAL or QUARTER.
        metric_period_type: duration or instant.

    Returns:
        True when end, form, and duration semantics align.
    """
    if "val" not in row or not fact_form_allowed(row=row, period_kind=period_kind):
        return False
    end = row_end_date(row=row)
    if end != target_end:
        return False
    if metric_period_type == "instant":
        return True
    start = row_start_date(row=row)
    if start is None:
        return False
    if period_kind == "ANNUAL":
        return is_full_year_duration(start=start, end=end)
    return is_quarter_duration(start=start, end=end)


def row_is_ytd_duration(
    *,
    row: dict[str, Any],
    target_end: date,
    period_kind: str,
) -> bool:
    """Detect a duration row that aligns by end date but is not a quarter.

    Args:
        row: SEC fact row.
        target_end: Target period end.
        period_kind: ANNUAL or QUARTER.

    Returns:
        True for likely 10-Q YTD rows that require derivation.
    """
    if period_kind != "QUARTER":
        return False
    end = row_end_date(row=row)
    start = row_start_date(row=row)
    if end != target_end or start is None:
        return False
    return not is_quarter_duration(start=start, end=end)


def select_best_row(
    *,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select latest filed SEC fact row from eligible rows.

    Args:
        rows: Eligible SEC fact rows.

    Returns:
        Row with latest filed date and accession tie-breaker.
    """
    return sorted(
        rows,
        key=lambda item: (item["filed"], item["accn"]),
        reverse=True,
    )[0]


def selection_from_row(
    *,
    metric: MetricConfig,
    companyfacts: dict[str, Any],
    concept: str,
    row: dict[str, Any],
    rejected: list[str],
    reason: str,
) -> SecSelection:
    """Build a SecSelection from one chosen fact row.

    Args:
        metric: Canonical metric config.
        companyfacts: Decoded SEC companyfacts JSON.
        concept: Selected SEC concept.
        row: Selected fact row.
        rejected: Rejection rationale list.
        reason: Selection reason.

    Returns:
        SecSelection with Decimal value.
    """
    present = present_candidates(
        companyfacts=companyfacts,
        candidates=metric.sec_candidates,
    )
    start = row_start_date(row=row)
    end = row_end_date(row=row)
    return SecSelection(
        status="OK",
        all_candidate_concepts=candidate_summary(
            candidates=metric.sec_candidates,
            present=present,
        ),
        selected_concept=concept,
        rejected_candidates="; ".join(rejected),
        selection_reason=reason,
        value=parse_decimal(value=row["val"]),
        unit=row["_unit"],
        form=row["form"],
        accession=row["accn"],
        filed_at=row["filed"],
        period_start=start,
        period_end=end,
        components=[],
    )


def missing_selection(
    *,
    metric: MetricConfig,
    companyfacts: dict[str, Any],
    rejected: list[str],
    status: str,
    reason: str,
) -> SecSelection:
    """Build an empty SecSelection with candidate diagnostics.

    Args:
        metric: Canonical metric config.
        companyfacts: Decoded SEC companyfacts JSON.
        rejected: Rejection rationale list.
        status: MISSING_SEC or REQUIRES_DERIVATION.
        reason: Selection reason.

    Returns:
        SecSelection without value.
    """
    present = present_candidates(
        companyfacts=companyfacts,
        candidates=metric.sec_candidates,
    )
    return SecSelection(
        status=status,
        all_candidate_concepts=candidate_summary(
            candidates=metric.sec_candidates,
            present=present,
        ),
        selected_concept="",
        rejected_candidates="; ".join(rejected),
        selection_reason=reason,
        value=None,
        unit="",
        form="",
        accession="",
        filed_at="",
        period_start=None,
        period_end=None,
        components=[],
    )


def select_sec_fact(
    *,
    metric: MetricConfig,
    companyfacts: dict[str, Any],
    target_end: date,
    period_kind: str,
) -> SecSelection:
    """Select one SEC fact for a metric and target period.

    Args:
        metric: Canonical metric config.
        companyfacts: Decoded SEC companyfacts JSON.
        target_end: Target period end.
        period_kind: ANNUAL or QUARTER.

    Returns:
        SecSelection with OK, MISSING_SEC, or REQUIRES_DERIVATION status.
    """
    preferred_units = sec_unit_preferences(metric=metric)
    rejected: list[str] = []
    saw_ytd = False
    facts = us_gaap_facts(companyfacts=companyfacts)
    for concept in metric.sec_candidates:
        if concept not in facts:
            rejected.append(f"{concept}: concept absent")
            continue
        rows = fact_unit_rows(
            companyfacts=companyfacts,
            concept=concept,
            preferred_units=preferred_units,
        )
        eligible: list[dict[str, Any]] = []
        for row in rows:
            if row_matches_period(
                row=row,
                target_end=target_end,
                period_kind=period_kind,
                metric_period_type=metric.period_type,
            ):
                eligible.append(row)
            elif row_is_ytd_duration(
                row=row,
                target_end=target_end,
                period_kind=period_kind,
            ):
                saw_ytd = True
        if eligible:
            selected = select_best_row(rows=eligible)
            return selection_from_row(
                metric=metric,
                companyfacts=companyfacts,
                concept=concept,
                row=selected,
                rejected=rejected,
                reason=(
                    f"selected {concept} by form/end/duration/unit; "
                    "latest filed observation wins"
                ),
            )
        rejected.append(f"{concept}: no eligible {period_kind.lower()} fact")

    if period_kind == "QUARTER" and metric.period_type == "duration" and saw_ytd:
        return missing_selection(
            metric=metric,
            companyfacts=companyfacts,
            rejected=rejected,
            status="REQUIRES_DERIVATION",
            reason="10-Q YTD fact found but no reliable independent quarter fact",
        )
    return missing_selection(
        metric=metric,
        companyfacts=companyfacts,
        rejected=rejected,
        status="MISSING_SEC",
        reason="no candidate concept produced an eligible fact",
    )


def component_selection(
    *,
    companyfacts: dict[str, Any],
    concept: str,
    target_end: date,
    period_kind: str,
) -> SecSelection | None:
    """Select one component concept for total debt composition.

    Args:
        companyfacts: Decoded SEC companyfacts JSON.
        concept: Component concept.
        target_end: Target period end.
        period_kind: ANNUAL or QUARTER.

    Returns:
        SecSelection for the component or None.
    """
    component_metric = MetricConfig(
        canonical_metric="balance.total_debt.component",
        av_endpoint="BALANCE_SHEET",
        av_field="",
        period_type="instant",
        sec_candidates=[concept],
        definition_risks={},
        requires_composition=False,
        normalization=None,
    )
    selected = select_sec_fact(
        metric=component_metric,
        companyfacts=companyfacts,
        target_end=target_end,
        period_kind=period_kind,
    )
    if selected.status == "OK":
        return selected
    return None


def compose_total_debt(
    *,
    metric: MetricConfig,
    companyfacts: dict[str, Any],
    target_end: date,
    period_kind: str,
) -> SecSelection:
    """Compose total debt from transparent SEC component concepts.

    Args:
        metric: Canonical total debt metric config.
        companyfacts: Decoded SEC companyfacts JSON.
        target_end: Target period end.
        period_kind: ANNUAL or QUARTER.

    Returns:
        SecSelection whose status is OK when a formula value can be computed,
        with components populated for output.
    """
    formulas = [
        [
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        ],
        ["LongTermDebtCurrent", "LongTermDebtNoncurrent", "ShortTermBorrowings"],
        ["CurrentDebt", "LongTermDebtNoncurrent"],
        ["LongTermDebt", "ShortTermBorrowings"],
    ]
    rejected: list[str] = []
    for formula in formulas:
        components: list[SecSelection] = []
        missing: list[str] = []
        for concept in formula:
            selected = component_selection(
                companyfacts=companyfacts,
                concept=concept,
                target_end=target_end,
                period_kind=period_kind,
            )
            if selected is None:
                missing.append(concept)
            else:
                components.append(selected)
        if missing:
            rejected.append(f"{' + '.join(formula)} missing {','.join(missing)}")
            continue
        total = Decimal("0")
        component_rows: list[dict[str, str]] = []
        for component in components:
            if component.value is None:
                raise ValueError("Debt component value cannot be None")
            total += component.value
            component_rows.append(
                {
                    "concept": component.selected_concept,
                    "value": format(component.value, "f"),
                    "unit": component.unit,
                    "accession": component.accession,
                }
            )
        present = present_candidates(
            companyfacts=companyfacts,
            candidates=metric.sec_candidates,
        )
        return SecSelection(
            status="OK",
            all_candidate_concepts=candidate_summary(
                candidates=metric.sec_candidates,
                present=present,
            ),
            selected_concept=" + ".join(formula),
            rejected_candidates="; ".join(rejected),
            selection_reason="composed total debt from explicit component facts",
            value=total,
            unit=components[0].unit,
            form=components[0].form,
            accession=components[0].accession,
            filed_at=components[0].filed_at,
            period_start=None,
            period_end=target_end,
            components=component_rows,
        )

    return missing_selection(
        metric=metric,
        companyfacts=companyfacts,
        rejected=rejected,
        status="MISSING_SEC",
        reason="no configured debt component formula was complete",
    )
