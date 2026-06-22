"""Acceptance tests for the local Step 0B AV / SEC spike.

Purpose:
    Validate the committed Step 0B report contract without requiring ignored
    raw SEC / Alpha Vantage artifacts in clean checkouts.

Call graph:
    unittest -> committed report checks
"""

from __future__ import annotations

import csv
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


REPO_DIR = Path(__file__).resolve().parents[1]
STEP_DIR = REPO_DIR / "scripts" / "step_0b"
REPORT_DIR = REPO_DIR / "spikes" / "step_0b" / "reports"
MATRIX_PATH = REPORT_DIR / "metric_alignment.csv"
FINDING_PATH = REPORT_DIR / "narrative_finding.json"
SUMMARY_PATH = REPORT_DIR / "run_summary.json"
if str(STEP_DIR) not in sys.path:
    sys.path.insert(0, str(STEP_DIR))

import run_step_0b  # noqa: E402
ALLOWED_STATUSES = {
    "MATCH",
    "NEAR_MATCH",
    "MISMATCH",
    "MISSING_AV",
    "MISSING_SEC",
    "NOT_APPLICABLE",
    "NOT_COMPARABLE_PERIOD",
    "COMPOSITE_REQUIRED",
    "AMBIGUOUS_MAPPING",
    "IDENTIFIER_MISMATCH",
}


class Step0BAcceptanceTest(unittest.TestCase):
    """Verify Step 0B reports against blocking acceptance checks."""

    def read_rows(self) -> list[dict[str, str]]:
        """Read the generated metric alignment rows.

        Returns:
            CSV rows as dictionaries.
        """
        with MATRIX_PATH.open(mode="r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(f=handle)]

    def test_matrix_shape_and_statuses(self) -> None:
        """Check 72-row matrix completeness and status vocabulary."""
        rows = self.read_rows()
        self.assertEqual(72, len(rows))
        self.assertEqual(3, len({row["company_key"] for row in rows}))
        self.assertEqual(12, len({row["canonical_metric"] for row in rows}))
        self.assertEqual(
            Counter({"LATEST_COMMON_ANNUAL": 36, "LATEST_COMMON_QUARTER": 36}),
            Counter(row["comparison_scope"] for row in rows),
        )
        for row in rows:
            self.assertIn(row["comparison_status"], ALLOWED_STATUSES)
            if row["comparison_status"] != "MATCH":
                self.assertTrue(row["rationale"].strip())

    def test_semantic_key_and_observation_id_are_separate(self) -> None:
        """Check representative comparable rows for identity separation."""
        rows = self.read_rows()
        row_index = {
            (row["company_key"], row["canonical_metric"], row["comparison_scope"]): row
            for row in rows
        }
        checks = [
            ("NYSE:IBM", "financial.revenue", "LATEST_COMMON_ANNUAL"),
            ("NYSE:IBM", "financial.net_income", "LATEST_COMMON_QUARTER"),
            ("NYSE:CAT", "balance.total_assets", "LATEST_COMMON_ANNUAL"),
            (
                "NYSE:CAT",
                "cashflow.operating_cash_flow",
                "LATEST_COMMON_QUARTER",
            ),
            ("NYSE:JPM", "balance.total_equity", "LATEST_COMMON_ANNUAL"),
        ]
        for key in checks:
            row = row_index[key]
            semantic_inputs = json.loads(row["semantic_key_inputs"])
            av_inputs = json.loads(row["av_observation_id_inputs"])
            self.assertEqual(row["av_semantic_key"], row["sec_semantic_key"])
            self.assertNotEqual(row["av_observation_id"], row["sec_observation_id"])
            self.assertNotIn("source_system", semantic_inputs)
            self.assertNotIn("comparison_scope", semantic_inputs)
            self.assertIn("source_system", av_inputs)
            if row["sec_observation_id_inputs"] != "":
                sec_inputs = json.loads(row["sec_observation_id_inputs"])
                self.assertIn("source_system", sec_inputs)

    def test_jpm_gross_profit_not_forced_to_match(self) -> None:
        """Ensure the banking gross profit boundary remains explicit."""
        rows = self.read_rows()
        statuses = [
            row["comparison_status"]
            for row in rows
            if row["company_key"] == "NYSE:JPM"
            and row["canonical_metric"] == "financial.gross_profit"
        ]
        self.assertEqual(["NOT_APPLICABLE", "NOT_APPLICABLE"], statuses)

    def test_narrative_evidence_offsets_recover_text(self) -> None:
        """Verify evidence fields and local span when normalized text exists."""
        finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
        text_path = REPO_DIR / finding["normalized_text_path"]
        self.assertTrue(finding["evidence_text"].strip())
        self.assertLess(finding["evidence_start"], finding["evidence_end"])
        self.assertTrue(text_path.exists())
        text = text_path.read_text(encoding="utf-8")
        start = finding["evidence_start"]
        end = finding["evidence_end"]
        self.assertEqual(text[start:end], finding["evidence_text"])
        if finding["amount_text"] is not None:
            self.assertIn(finding["amount_text"], finding["evidence_text"])
        self.assertEqual("PROGRAMMATICALLY_VERIFIED", finding["validation_status"])

    def test_run_summary_contains_required_fields(self) -> None:
        """Check offline run summary and redaction bookkeeping."""
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        for field in [
            "run_id",
            "online",
            "started_at",
            "ended_at",
            "call_budget",
            "raw_hashes",
            "output_hashes",
            "warnings",
            "unresolved_mappings",
            "key_redaction_check",
        ]:
            self.assertIn(field, summary)
        self.assertFalse(summary["online"])
        self.assertLessEqual(summary["call_budget"]["av_call_count"], 10)
        self.assertTrue(summary["key_redaction_check"]["passed"])

    def test_verify_offline_does_not_rebuild_from_raw_cache(self) -> None:
        """Ensure clean-checkout verify validates committed reports only."""
        args = mock.Mock(offline=True)
        with mock.patch.object(
            run_step_0b,
            "WORK_DIR",
            REPO_DIR / "does-not-exist-step-0b-work",
        ):
            with mock.patch.object(
                run_step_0b,
                "generate_reports",
                side_effect=AssertionError("verify must not rebuild"),
            ):
                run_step_0b.command_verify(args=args)


if __name__ == "__main__":
    unittest.main()
