"""Algorithm tests for Step 0B value and period normalization.

Purpose:
    Exercise normalization rules directly without depending on generated reports.

Call graph:
    unittest -> step0b.normalization helpers
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
STEP_DIR = REPO_DIR / "scripts" / "step_0b"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

from step0b.normalization import (  # noqa: E402
    comparison_rule_for_metric,
    comparison_value_for_metric,
    infer_quarter_start,
    normalize_capex_outflow,
    parse_decimal,
)


class Step0BNormalizationTest(unittest.TestCase):
    """Verify source-honest normalization helpers."""

    def test_capex_preserves_raw_value_and_normalizes_comparison_value(self) -> None:
        """Check Capex sign policy keeps raw value separate from comparison value."""
        raw_value = parse_decimal(value="-1000")
        comparison_value = comparison_value_for_metric(
            canonical_metric="cashflow.capital_expenditure",
            normalization_rule="preserve_source_sign_explain_only",
            value=raw_value,
        )
        direct_value, rule = normalize_capex_outflow(value=raw_value)

        self.assertEqual(Decimal("-1000"), raw_value)
        self.assertEqual(Decimal("1000"), comparison_value)
        self.assertEqual(Decimal("1000"), direct_value)
        self.assertIn("raw_value_preserved", rule)

    def test_non_capex_value_is_not_changed_for_comparison(self) -> None:
        """Check ordinary metrics do not get sign normalization."""
        raw_value = parse_decimal(value="-25")

        self.assertEqual(
            Decimal("-25"),
            comparison_value_for_metric(
                canonical_metric="financial.net_income",
                normalization_rule=None,
                value=raw_value,
            ),
        )

    def test_capex_rule_text_is_explicit(self) -> None:
        """Check report rule text explains comparison-only normalization."""
        rule = comparison_rule_for_metric(
            canonical_metric="cashflow.capital_expenditure",
            normalization_rule="preserve_source_sign_explain_only",
        )

        self.assertIn("preserve_source_sign_explain_only", rule)
        self.assertIn("comparison_value_abs_cash_outflow", rule)

    def test_quarter_start_is_inferred_without_sec_fact(self) -> None:
        """Check canonical quarter start is independent of SEC fact selection."""
        self.assertEqual(
            date(year=2026, month=1, day=1),
            infer_quarter_start(period_end=date(year=2026, month=3, day=31)),
        )


if __name__ == "__main__":
    unittest.main()
