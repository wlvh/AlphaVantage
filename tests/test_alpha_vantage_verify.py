"""Regression tests for local Alpha Vantage response parsing.

Purpose:
    Verify CSV payloads with vendor-message keywords inside data values still
    classify as usable CSV.

Call graph:
    unittest -> ParseResponseTests -> alpha_vantage_verify.parse_response
"""

from __future__ import annotations

import unittest

from scripts import alpha_vantage_verify


class ParseResponseTests(unittest.TestCase):
    """Exercise response classification boundaries."""

    def test_csv_information_company_name_is_data_csv(self) -> None:
        """CSV rows containing Information in names remain data_csv.

        Args:
            None.

        Returns:
            None. Assertions validate classification and observed CSV columns.
        """
        raw_text = (
            "symbol,name,exchange,assetType,ipoDate,delistingDate,status\n"
            "CASS,Cass Information Systems Inc,NASDAQ,Stock,"
            "1996-01-02,null,Active\n"
        )

        # The parser must prefer table shape over text-level vendor heuristics.
        parsed = alpha_vantage_verify.parse_response(
            status=200,
            raw_text=raw_text,
        )

        self.assertEqual(first="data_csv", second=parsed["classification"])
        self.assertEqual(
            first=[
                "symbol",
                "name",
                "exchange",
                "assetType",
                "ipoDate",
                "delistingDate",
                "status",
            ],
            second=parsed["schema"]["columns"],
        )


if __name__ == "__main__":
    unittest.main()
