"""Evidence binding tests for Step 0B narrative output.

Purpose:
    Verify committed legal finding evidence can be recovered from its fixture and
    carries the structured fields required by the acceptance guide.

Call graph:
    unittest -> committed narrative_finding.json and fixture text
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
FINDING_PATH = REPO_DIR / "spikes" / "step_0b" / "reports" / "narrative_finding.json"


class Step0BEvidenceTest(unittest.TestCase):
    """Verify narrative evidence binding is reproducible in a clean checkout."""

    def test_evidence_offsets_recover_exact_text_from_fixture(self) -> None:
        """Check evidence_start/evidence_end bind to committed normalized text."""
        finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
        text_path = REPO_DIR / finding["normalized_text_path"]
        text = text_path.read_text(encoding="utf-8")

        self.assertEqual(
            finding["evidence_text"],
            text[finding["evidence_start"] : finding["evidence_end"]],
        )

    def test_finding_schema_contains_structured_legal_fields(self) -> None:
        """Check legal finding fields required for later extraction work."""
        finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))

        self.assertEqual("PROGRAMMATICALLY_VERIFIED", finding["validation_status"])
        self.assertEqual("NOT_REVIEWED", finding["human_review_status"])
        self.assertTrue(finding["title"])
        self.assertTrue(finding["status_text"])
        self.assertTrue(finding["affected_entity_text"])
        self.assertEqual("1300000000", finding["amount_value"])
        self.assertIn(finding["amount_text"], finding["evidence_text"])

    def test_evidence_starts_at_litigation_note(self) -> None:
        """Check evidence no longer includes unrelated guarantee text."""
        finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))

        self.assertTrue(finding["evidence_text"].startswith("Note 24"))
        self.assertNotIn("Guarantees of subsidiaries", finding["evidence_text"])


if __name__ == "__main__":
    unittest.main()
