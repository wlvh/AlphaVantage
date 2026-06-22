# Step 0B Discrepancy Report

Generated at UTC `2026-06-22T08:57:16.135939+00:00`.

## Direct Mapping Candidates

These metrics produced at least one `MATCH` or `NEAR_MATCH` row and can enter AV V1 with source-specific observation metadata:

- balance.cash_and_equivalents
- balance.total_assets
- balance.total_equity
- balance.total_liabilities
- cashflow.operating_cash_flow
- earnings.diluted_eps
- financial.gross_profit
- financial.net_income
- financial.operating_income
- financial.revenue

## Composite Formula Required

Total debt cannot be treated as a single SEC concept. The Silver schema must store formula components, concept lineage, accession, unit, value, and artifact hash.

- balance.total_debt

## Industry Applicability Limits

JPM confirms that generic industrial metrics do not always apply to banking statements. Gross profit is not forced into a fake match, and revenue / operating income remain mapping-sensitive.

- financial.gross_profit
- financial.revenue

## Period and Filing Effects

Annual rows use 10-K facts and annual AV reports or valid annual earnings. Quarter rows use 10-Q facts and quarterly AV reports. YTD-only SEC facts are reported as not comparable instead of being silently treated as single-quarter values.

- None

## Amendment and Restatement

Selection prefers latest filed facts for the same form, period end, duration, and unit. The selected SEC accession and filed date are kept in every matrix row so amendments and restatements remain auditable.

## Alpha Vantage Opaque Standardization

AV fields such as `totalRevenue`, `grossProfit`, `operatingIncome`, `shortLongTermDebtTotal`, and `reportedEPS` are vendor-normalized labels. The raw response does not prove their complete accounting definition, so source observation identity is preserved rather than overwriting SEC facts.

## Mismatch Samples

- NYSE:IBM LATEST_COMMON_ANNUAL financial.gross_profit: MISMATCH - selected GrossProfit by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_ANNUAL cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_QUARTER cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:IBM LATEST_COMMON_ANNUAL earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins; annualEarnings quarterly duplicate excluded when detected
- NYSE:IBM LATEST_COMMON_QUARTER earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_ANNUAL cashflow.operating_cash_flow: MISMATCH - selected NetCashProvidedByUsedInOperatingActivities by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_ANNUAL earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins; annualEarnings quarterly duplicate excluded when detected
- NYSE:CAT LATEST_COMMON_ANNUAL cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:CAT LATEST_COMMON_QUARTER cashflow.capital_expenditure: MISMATCH - selected PaymentsToAcquirePropertyPlantAndEquipment by form/end/duration/unit; latest filed observation wins
- NYSE:CAT LATEST_COMMON_ANNUAL earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins; annualEarnings quarterly duplicate excluded when detected
- NYSE:CAT LATEST_COMMON_QUARTER earnings.diluted_eps: MISMATCH - selected EarningsPerShareDiluted by form/end/duration/unit; latest filed observation wins

## JPM Boundary Rows

- NYSE:JPM LATEST_COMMON_ANNUAL financial.revenue: AMBIGUOUS_MAPPING - selected Revenues by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_QUARTER financial.revenue: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL financial.gross_profit: NOT_APPLICABLE - banking archetype does not report this metric cleanly; no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_QUARTER financial.gross_profit: NOT_APPLICABLE - banking archetype does not report this metric cleanly; no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_QUARTER financial.operating_income: MISSING_SEC - no candidate concept produced an eligible fact
- NYSE:JPM LATEST_COMMON_ANNUAL balance.total_equity: MATCH - selected StockholdersEquity by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_QUARTER balance.total_equity: MATCH - selected StockholdersEquity by form/end/duration/unit; latest filed observation wins
- NYSE:JPM LATEST_COMMON_ANNUAL balance.total_debt: COMPOSITE_REQUIRED - SEC total debt requires explicit component formula; no configured debt component formula was complete
- NYSE:JPM LATEST_COMMON_QUARTER balance.total_debt: COMPOSITE_REQUIRED - SEC total debt requires explicit component formula; no configured debt component formula was complete

## Requires Formal SEC Pipeline Later

- Automated concept discovery across all statement roles and dimensional facts.
- Quarter derivation from YTD facts when the filing has enough prior-period context.
- Production-grade amendment policy and industry-specific metric families.
