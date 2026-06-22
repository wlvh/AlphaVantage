"""Algorithm tests for Step 0B numeric comparison thresholds.

Purpose:
    Validate the acceptance thresholds for ordinary numeric metrics and EPS.

Call graph:
    unittest -> step0b.comparison difference/status helpers
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
STEP_DIR = REPO_DIR / "scripts" / "step_0b"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

from step0b.comparison import difference_values, numeric_status  # noqa: E402
from step0b.models import MetricConfig  # noqa: E402


def metric_config(*, canonical_metric: str) -> MetricConfig:
    """Build a minimal MetricConfig for threshold tests.

    Args:
        canonical_metric: Metric key under test.

    Returns:
        MetricConfig with irrelevant source mapping fields stubbed.
    """
    return MetricConfig(
        canonical_metric=canonical_metric,
        av_endpoint="INCOME_STATEMENT",
        av_field="value",
        period_type="duration",
        sec_candidates=["Value"],
        definition_risks={},
        requires_composition=False,
        normalization=None,
    )


class Step0BComparisonTest(unittest.TestCase):
    """Verify comparison status thresholds."""

    def test_regular_metric_uses_two_percent_near_match_threshold(self) -> None:
        """Check non-EPS NEAR_MATCH accepts <= 2 percent relative difference."""
        absolute, relative = difference_values(
            av_value=Decimal("100"),
            sec_value=Decimal("98.5"),
        )

        self.assertEqual(
            "NEAR_MATCH",
            numeric_status(
                metric=metric_config(canonical_metric="financial.revenue"),
                absolute_difference=absolute,
                relative_difference=relative,
            ),
        )

    def test_regular_metric_above_two_percent_is_different(self) -> None:
        """Check non-EPS values over 2 percent remain mismatches."""
        absolute, relative = difference_values(
            av_value=Decimal("100"),
            sec_value=Decimal("97.8"),
        )

        self.assertEqual(
            "DIFFERENT",
            numeric_status(
                metric=metric_config(canonical_metric="financial.revenue"),
                absolute_difference=absolute,
                relative_difference=relative,
            ),
        )

    def test_eps_uses_absolute_difference_thresholds(self) -> None:
        """Check EPS classification ignores large relative swings on small values."""
        absolute, relative = difference_values(
            av_value=Decimal("0.01"),
            sec_value=Decimal("0.04"),
        )

        self.assertEqual(
            "NEAR_MATCH",
            numeric_status(
                metric=metric_config(canonical_metric="earnings.diluted_eps"),
                absolute_difference=absolute,
                relative_difference=relative,
            ),
        )

    def test_eps_match_threshold_is_one_cent(self) -> None:
        """Check EPS MATCH threshold is <= 0.01 absolute difference."""
        absolute, relative = difference_values(
            av_value=Decimal("5.10"),
            sec_value=Decimal("5.11"),
        )

        self.assertEqual(
            "MATCH",
            numeric_status(
                metric=metric_config(canonical_metric="earnings.diluted_eps"),
                absolute_difference=absolute,
                relative_difference=relative,
            ),
        )


if __name__ == "__main__":
    unittest.main()
