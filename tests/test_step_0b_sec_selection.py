"""Algorithm tests for Step 0B SEC Company Facts selection.

Purpose:
    Validate period, amendment, unit, and composite lineage behavior without
    using live SEC artifacts.

Call graph:
    unittest -> step0b.sec_companyfacts selection helpers
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_DIR = Path(__file__).resolve().parents[1]
STEP_DIR = REPO_DIR / "scripts" / "step_0b"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

from step0b.models import MetricConfig  # noqa: E402
from step0b.sec_companyfacts import compose_total_debt, select_sec_fact  # noqa: E402


def metric_config(
    *,
    canonical_metric: str,
    period_type: str,
    candidates: list[str],
    requires_composition: bool = False,
) -> MetricConfig:
    """Build a minimal MetricConfig for SEC selection tests.

    Args:
        canonical_metric: Canonical metric key.
        period_type: duration or instant.
        candidates: SEC concept candidates.
        requires_composition: Whether the metric requires a formula.

    Returns:
        MetricConfig with irrelevant AV fields stubbed.
    """
    return MetricConfig(
        canonical_metric=canonical_metric,
        av_endpoint="INCOME_STATEMENT",
        av_field="value",
        period_type=period_type,
        sec_candidates=candidates,
        definition_risks={},
        requires_composition=requires_composition,
        normalization=None,
    )


def companyfacts(*, concept: str, unit: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a minimal companyfacts payload.

    Args:
        concept: SEC concept name.
        unit: SEC unit key.
        rows: Fact rows.

    Returns:
        SEC Company Facts-shaped dict.
    """
    return {"facts": {"us-gaap": {concept: {"units": {unit: rows}}}}}


def instant_row(
    *,
    value: int,
    end: str,
    filed: str,
    accession: str,
    form: str = "10-K",
) -> dict[str, Any]:
    """Build an instant SEC fact row.

    Args:
        value: Numeric fact value.
        end: Fact end date.
        filed: SEC filed date.
        accession: SEC accession number.
        form: SEC form.

    Returns:
        SEC fact row.
    """
    return {
        "val": value,
        "end": end,
        "filed": filed,
        "accn": accession,
        "form": form,
    }


def duration_row(
    *,
    value: int,
    start: str,
    end: str,
    filed: str,
    accession: str,
    form: str,
) -> dict[str, Any]:
    """Build a duration SEC fact row.

    Args:
        value: Numeric fact value.
        start: Fact start date.
        end: Fact end date.
        filed: SEC filed date.
        accession: SEC accession number.
        form: SEC form.

    Returns:
        SEC fact row.
    """
    row = instant_row(
        value=value,
        end=end,
        filed=filed,
        accession=accession,
        form=form,
    )
    row["start"] = start
    return row


class Step0BSecSelectionTest(unittest.TestCase):
    """Verify SEC fact selection policy."""

    def test_latest_filed_amendment_wins_for_same_period(self) -> None:
        """Check restatement/amendment policy chooses latest filed observation."""
        metric = metric_config(
            canonical_metric="financial.revenue",
            period_type="duration",
            candidates=["Revenue"],
        )
        facts = companyfacts(
            concept="Revenue",
            unit="USD",
            rows=[
                duration_row(
                    value=100,
                    start="2025-01-01",
                    end="2025-12-31",
                    filed="2026-02-01",
                    accession="old",
                    form="10-K",
                ),
                duration_row(
                    value=110,
                    start="2025-01-01",
                    end="2025-12-31",
                    filed="2026-03-01",
                    accession="amended",
                    form="10-K/A",
                ),
            ],
        )

        selected = select_sec_fact(
            metric=metric,
            companyfacts=facts,
            target_end=date(year=2025, month=12, day=31),
            period_kind="ANNUAL",
        )

        self.assertEqual("OK", selected.status)
        self.assertEqual("amended", selected.accession)
        self.assertEqual(Decimal("110"), selected.value)

    def test_ytd_quarter_fact_requires_derivation(self) -> None:
        """Check 10-Q YTD facts are not silently treated as quarters."""
        metric = metric_config(
            canonical_metric="financial.revenue",
            period_type="duration",
            candidates=["Revenue"],
        )
        facts = companyfacts(
            concept="Revenue",
            unit="USD",
            rows=[
                duration_row(
                    value=200,
                    start="2026-01-01",
                    end="2026-06-30",
                    filed="2026-08-01",
                    accession="q2-ytd",
                    form="10-Q",
                ),
            ],
        )

        selected = select_sec_fact(
            metric=metric,
            companyfacts=facts,
            target_end=date(year=2026, month=6, day=30),
            period_kind="QUARTER",
        )

        self.assertEqual("REQUIRES_DERIVATION", selected.status)

    def test_wrong_unit_is_rejected_for_money_metric(self) -> None:
        """Check monetary metrics do not accept per-share SEC units."""
        metric = metric_config(
            canonical_metric="financial.revenue",
            period_type="duration",
            candidates=["Revenue"],
        )
        facts = companyfacts(
            concept="Revenue",
            unit="USD/shares",
            rows=[
                duration_row(
                    value=5,
                    start="2025-01-01",
                    end="2025-12-31",
                    filed="2026-02-01",
                    accession="bad-unit",
                    form="10-K",
                ),
            ],
        )

        selected = select_sec_fact(
            metric=metric,
            companyfacts=facts,
            target_end=date(year=2025, month=12, day=31),
            period_kind="ANNUAL",
        )

        self.assertEqual("MISSING_SEC", selected.status)

    def test_composite_total_debt_keeps_component_lineage(self) -> None:
        """Check composed debt includes component concept lineage."""
        metric = metric_config(
            canonical_metric="balance.total_debt",
            period_type="instant",
            candidates=[
                "LongTermDebtAndFinanceLeaseObligationsCurrent",
                "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            ],
            requires_composition=True,
        )
        facts = {
            "facts": {
                "us-gaap": {
                    "LongTermDebtAndFinanceLeaseObligationsCurrent": {
                        "units": {
                            "USD": [
                                instant_row(
                                    value=40,
                                    end="2025-12-31",
                                    filed="2026-02-01",
                                    accession="acc",
                                ),
                            ],
                        },
                    },
                    "LongTermDebtAndFinanceLeaseObligationsNoncurrent": {
                        "units": {
                            "USD": [
                                instant_row(
                                    value=60,
                                    end="2025-12-31",
                                    filed="2026-02-01",
                                    accession="acc",
                                ),
                            ],
                        },
                    },
                },
            },
        }

        selected = compose_total_debt(
            metric=metric,
            companyfacts=facts,
            target_end=date(year=2025, month=12, day=31),
            period_kind="ANNUAL",
        )

        self.assertEqual("OK", selected.status)
        self.assertEqual(Decimal("100"), selected.value)
        self.assertEqual(2, len(selected.components))
        self.assertEqual(
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            selected.components[0]["concept"],
        )


if __name__ == "__main__":
    unittest.main()
