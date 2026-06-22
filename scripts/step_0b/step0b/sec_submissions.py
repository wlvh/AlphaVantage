"""SEC submissions JSON helpers.

Purpose:
    Convert SEC submissions recent filing arrays into explicit rows and select
    latest 10-K / 10-Q documents without relying on positional magic outside
    the SEC-provided recent filing order.

Call graph:
    sec_client/comparison/narrative_evidence -> latest_filing
"""

from __future__ import annotations

from typing import Any


def recent_filing_rows(*, submissions: dict[str, Any]) -> list[dict[str, str]]:
    """Expand SEC submissions recent arrays into row dicts.

    Args:
        submissions: Decoded SEC submissions JSON.

    Returns:
        List of recent filing rows preserving SEC order.
    """
    recent = submissions["filings"]["recent"]
    accessions = recent["accessionNumber"]
    rows: list[dict[str, str]] = []
    for index, accession in enumerate(accessions):
        rows.append(
            {
                "accessionNumber": accession,
                "filingDate": recent["filingDate"][index],
                "reportDate": recent["reportDate"][index],
                "acceptanceDateTime": recent["acceptanceDateTime"][index],
                "form": recent["form"][index],
                "primaryDocument": recent["primaryDocument"][index],
            }
        )
    return rows


def latest_filing(
    *,
    submissions: dict[str, Any],
    forms: set[str],
    occurrence: int = 1,
) -> dict[str, str]:
    """Select the nth latest filing whose form is in the allowed set.

    Args:
        submissions: Decoded SEC submissions JSON.
        forms: Allowed SEC form names.
        occurrence: One-based occurrence within SEC recent filing order.

    Returns:
        Filing row dict.

    Raises:
        ValueError: If no matching filing exists.
    """
    seen = 0
    for row in recent_filing_rows(submissions=submissions):
        if row["form"] in forms:
            seen += 1
            if seen == occurrence:
                return row
    raise ValueError(f"No filing found for forms: {sorted(forms)}")
