# Step 0B Metric Alignment

Generated at UTC `2026-06-22T08:57:16.135808+00:00`.

## Shape

- Rows: 72
- Companies: {'NYSE:IBM': 24, 'NYSE:JPM': 24, 'NYSE:CAT': 24}
- Scopes: {'LATEST_COMMON_ANNUAL': 36, 'LATEST_COMMON_QUARTER': 36}
- Statuses: {'MATCH': 38, 'MISMATCH': 11, 'MISSING_SEC': 11, 'NEAR_MATCH': 3, 'COMPOSITE_REQUIRED': 6, 'AMBIGUOUS_MAPPING': 1, 'NOT_APPLICABLE': 2}

## Required Identity Checks

- `semantic_key` is shared by AV and SEC rows because it excludes `source_system`.
- `av_observation_id` and `sec_observation_id` differ because their inputs include source system and source artifact identity.

## Non-MATCH Samples

- NYSE:IBM LATEST_COMMON_ANNUAL financial.gross_profit: MISMATCH - selected GrossProfit by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_ANNUAL financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:IBM LATEST_COMMON_QUARTER financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:IBM LATEST_COMMON_ANNUAL balance.cash_and_equivalents: NEAR_MATCH - selected CashAndCashEquivalentsAtCarryingValue by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_ANNUAL balance.total_debt: COMPOSITE_REQUIRED - SEC total debt requires explicit component formula; no configured debt component formula was complete
- NYSE:IBM LATEST_COMMON_QUARTER balance.total_debt: COMPOSITE_REQUIRED - SEC total debt requires explicit component formula; no configured debt component formula was complete
- NYSE:IBM LATEST_COMMON_ANNUAL cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_QUARTER cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_ANNUAL earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins; annualEarnings quarterly duplicate excluded when detected
- NYSE:IBM LATEST_COMMON_QUARTER earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_ANNUAL financial.revenue: AMBIGUOUS_MAPPING - selected Revenues by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_QUARTER financial.revenue: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL financial.gross_profit: NOT_APPLICABLE - banking archetype does not report this metric cleanly; no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_QUARTER financial.gross_profit: NOT_APPLICABLE - banking archetype does not report this metric cleanly; no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_QUARTER financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL balance.cash_and_equivalents: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_QUARTER balance.cash_and_equivalents: MISSING_SEC - no candidate concept produced an eligible fact
- ... 16 more rows
