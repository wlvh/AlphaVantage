"""Identity contract tests for Step 0B reports.

Purpose:
    Validate semantic key inputs, observation identity, and path stability in
    committed Step 0B outputs.

Call graph:
    unittest -> committed CSV and run_step_0b identity helpers
"""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
STEP_DIR = REPO_DIR / "scripts" / "step_0b"
REPORT_DIR = REPO_DIR / "spikes" / "step_0b" / "reports"
MATRIX_PATH = REPORT_DIR / "metric_alignment.csv"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

from run_step_0b import (  # noqa: E402
    dimensions_for_row,
    optional_repo_relative_text,
    period_start_for_row,
    row_has_observation,
    semantic_inputs_for_row,
)


def read_rows() -> list[dict[str, str]]:
    """Read committed metric alignment rows.

    Returns:
        CSV rows as dictionaries.
    """
    with MATRIX_PATH.open(mode="r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(f=handle)]


class Step0BIdentityTest(unittest.TestCase):
    """Verify semantic and source observation identity behavior."""

    def test_semantic_inputs_exclude_query_scope(self) -> None:
        """Check comparison_scope is a report context, not semantic identity."""
        row = {
            "company_id": "NYSE:IBM",
            "canonical_metric": "financial.revenue",
            "comparison_period_kind": "QUARTER",
            "period_end": "2026-03-31",
        }
        inputs = semantic_inputs_for_row(
            row=row,
            period_type="duration",
            period_start="2026-01-01",
            dimensions=dimensions_for_row(row=row),
        )

        self.assertNotIn("comparison_scope", inputs)
        self.assertEqual("NYSE:IBM", inputs["company_id"])
        self.assertEqual("financial.revenue", inputs["metric_key"])

    def test_period_start_fails_fast_when_missing(self) -> None:
        """Check canonical period_start cannot silently remain empty."""
        row = {
            "company_id": "NYSE:IBM",
            "canonical_metric": "financial.revenue",
            "comparison_period_kind": "QUARTER",
            "period_start": "",
            "period_end": "2026-03-31",
        }

        with self.assertRaises(ValueError):
            period_start_for_row(row=row, period_type="duration")

    def test_repo_relative_paths_are_stable(self) -> None:
        """Check absolute local paths are converted to repo-relative paths."""
        path_text = optional_repo_relative_text(
            path_text=str(REPO_DIR / "spikes" / "step_0b" / "reports"),
        )

        self.assertEqual("spikes/step_0b/reports", path_text)

    def test_committed_matrix_has_stable_identity_inputs(self) -> None:
        """Check generated report rows have source-free semantic keys."""
        rows = read_rows()

        for row in rows:
            semantic_inputs = json.loads(row["semantic_key_inputs"])
            self.assertNotIn("source_system", semantic_inputs)
            self.assertNotIn("comparison_scope", semantic_inputs)
            self.assertFalse(Path(row["av_raw_file"]).is_absolute())
            self.assertFalse(Path(row["sec_raw_file"]).is_absolute())
            self.assertTrue(row["period_start"])

    def test_missing_sec_rows_have_null_observation_identity(self) -> None:
        """Check missing SEC facts do not create empty-source observation IDs."""
        rows = read_rows()
        missing_rows = [
            row
            for row in rows
            if not row_has_observation(
                value_text=row["sec_raw_value"],
                artifact_hash=row["sec_source_artifact_hash"],
            )
        ]

        self.assertTrue(missing_rows)
        for row in missing_rows:
            self.assertEqual("", row["sec_observation_id"])
            self.assertEqual("", row["sec_observation_id_inputs"])


if __name__ == "__main__":
    unittest.main()
