# Alpha Vantage Observed Schema Verification Report

## 1. Executive Summary

- Generated at UTC `2026-06-15T14:25:15.385426+00:00` from existing Alpha Vantage raw responses only.
- Planned schemas usable: `15` / `15`.
- Deferred checks: `0`.
- Calls used: demo `0` / `20`, real `0` / `6`.
- Real key available to runner: `False`.

## 2. Call Log Summary

| endpoint | status | attempts | final classification | raw |
| --- | --- | --- | --- | --- |
| overview_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/001_overview_ibm.txt |
| income_statement_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/002_income_statement_ibm.txt |
| balance_sheet_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/003_balance_sheet_ibm.txt |
| cash_flow_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/004_cash_flow_ibm.txt |
| earnings_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/005_earnings_ibm.txt |
| dividends_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/006_dividends_ibm.txt |
| insider_transactions_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/007_insider_transactions_ibm.txt |
| shares_outstanding_msft | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/008_shares_outstanding_msft.txt |
| earnings_estimates_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/009_earnings_estimates_ibm.txt |
| splits_ibm | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/010_splits_ibm.txt |
| news_sentiment_aapl_latest | observed | 2 | data_json | artifacts/alpha_vantage/raw/real/016_news_sentiment_aapl_latest.txt |
| news_sentiment_technology_latest | observed | 2 | data_json | artifacts/alpha_vantage/raw/real/017_news_sentiment_technology_latest.txt |
| earnings_call_transcript_ibm_2024q1 | observed | 1 | data_json | artifacts/alpha_vantage/raw/demo/013_earnings_call_transcript_ibm_2024q1.txt |
| listing_status | observed | 1 | data_csv | artifacts/alpha_vantage/raw/demo/014_listing_status.txt |
| earnings_calendar_ibm_12month | observed | 1 | data_csv | artifacts/alpha_vantage/raw/demo/015_earnings_calendar_ibm_12month.txt |

## 3. Observed Endpoint Schemas

### overview_ibm

- root keys: `200DayMovingAverage, 50DayMovingAverage, 52WeekHigh, 52WeekLow, Address, AnalystRatingBuy, AnalystRatingHold, AnalystRatingSell, AnalystRatingStrongBuy, AnalystRatingStrongSell, AnalystTargetPrice, AssetType, Beta, BookValue, CIK, Country, Currency, Description, DilutedEPSTTM, DividendDate, DividendPerShare, DividendYield, EBITDA, EPS, EVToEBITDA, EVToRevenue, ExDividendDate, Exchange, FiscalYearEnd, ForwardPE, GrossProfitTTM, Industry, LatestQuarter, MarketCapitalization, Name, OfficialSite, OperatingMarginTTM, PEGRatio, PERatio, PercentInsiders, PercentInstitutions, PriceToBookRatio, PriceToSalesRatioTTM, ProfitMargin, QuarterlyEarningsGrowthYOY, QuarterlyRevenueGrowthYOY, ReturnOnAssetsTTM, ReturnOnEquityTTM, RevenuePerShareTTM, RevenueTTM, Sector, SharesFloat, SharesOutstanding, Symbol, TrailingPE`
- JSON field paths observed: `56`
- sampled paths: `$, $.200DayMovingAverage, $.50DayMovingAverage, $.52WeekHigh, $.52WeekLow, $.Address, $.AnalystRatingBuy, $.AnalystRatingHold, $.AnalystRatingSell, $.AnalystRatingStrongBuy, $.AnalystRatingStrongSell, $.AnalystTargetPrice, $.AssetType, $.Beta, $.BookValue, $.CIK, $.Country, $.Currency, $.Description, $.DilutedEPSTTM`
- endpoint checks: {"required_field_presence": {"50DayMovingAverage": true, "52WeekHigh": true, "DividendYield": true, "LatestQuarter": true, "MarketCapitalization": true, "Name": true, "PERatio": true, "PercentInsiders": true, "PercentInstitutions": true, "SharesOutstanding": true, "Symbol": true}}

### income_statement_ibm

- root keys: `annualReports, quarterlyReports, symbol`
- JSON field paths observed: `58`
- sampled paths: `$, $.annualReports, $.annualReports[], $.annualReports[].comprehensiveIncomeNetOfTax, $.annualReports[].costOfRevenue, $.annualReports[].costofGoodsAndServicesSold, $.annualReports[].depreciation, $.annualReports[].depreciationAndAmortization, $.annualReports[].ebit, $.annualReports[].ebitda, $.annualReports[].fiscalDateEnding, $.annualReports[].grossProfit, $.annualReports[].incomeBeforeTax, $.annualReports[].incomeTaxExpense, $.annualReports[].interestAndDebtExpense, $.annualReports[].interestExpense, $.annualReports[].interestIncome, $.annualReports[].investmentIncomeNet, $.annualReports[].netIncome, $.annualReports[].netIncomeFromContinuingOperations`
- endpoint checks: {"annual_reports_keys_sampled": ["comprehensiveIncomeNetOfTax", "costOfRevenue", "costofGoodsAndServicesSold", "depreciation", "depreciationAndAmortization", "ebit", "ebitda", "fiscalDateEnding", "grossProfit", "incomeBeforeTax", "incomeTaxExpense", "interestAndDebtExpense", "interestExpense", "interestIncome", "investmentIncomeNet", "netIncome", "netIncomeFromContinuingOperations", "netInterestIncome", "nonInterestIncome", "operatingExpenses", "operatingIncome", "otherNonOperatingIncome", "reportedCurrency", "researchAndDevelopment", "sellingGeneralAndAdministrative", "totalRevenue"], "costOfRevenue_present": true, "costof GoodsAndServicesSold_with_space_present": false, "costofGoodsAndServicesSold_present": true, "quarterly_reports_keys_sampled": ["comprehensiveIncomeNetOfTax", "costOfRevenue", "costofGoodsAndServicesSold", "depreciation", "depreciationAndAmortization", "ebit", "ebitda", "fiscalDateEnding", "grossProfit", "incomeBeforeTax", "incomeTaxExpense", "interestAndDebtExpense

### balance_sheet_ibm

- root keys: `annualReports, quarterlyReports, symbol`
- JSON field paths observed: `82`
- sampled paths: `$, $.annualReports, $.annualReports[], $.annualReports[].accumulatedDepreciationAmortizationPPE, $.annualReports[].capitalLeaseObligations, $.annualReports[].cashAndCashEquivalentsAtCarryingValue, $.annualReports[].cashAndShortTermInvestments, $.annualReports[].commonStock, $.annualReports[].commonStockSharesOutstanding, $.annualReports[].currentAccountsPayable, $.annualReports[].currentDebt, $.annualReports[].currentLongTermDebt, $.annualReports[].currentNetReceivables, $.annualReports[].deferredRevenue, $.annualReports[].fiscalDateEnding, $.annualReports[].goodwill, $.annualReports[].intangibleAssets, $.annualReports[].intangibleAssetsExcludingGoodwill, $.annualReports[].inventory, $.annualReports[].investments`
- endpoint checks: {"commonStockSharesOutstanding_present": true, "otherNonCurrentAssets_present": true, "otherNonCurrrentAssets_present": false, "shortLongTermDebtTotal_present": true}

### cash_flow_ibm

- root keys: `annualReports, quarterlyReports, symbol`
- JSON field paths observed: `66`
- sampled paths: `$, $.annualReports, $.annualReports[], $.annualReports[].capitalExpenditures, $.annualReports[].cashflowFromFinancing, $.annualReports[].cashflowFromInvestment, $.annualReports[].changeInCashAndCashEquivalents, $.annualReports[].changeInExchangeRate, $.annualReports[].changeInInventory, $.annualReports[].changeInOperatingAssets, $.annualReports[].changeInOperatingLiabilities, $.annualReports[].changeInReceivables, $.annualReports[].depreciationDepletionAndAmortization, $.annualReports[].dividendPayout, $.annualReports[].dividendPayoutCommonStock, $.annualReports[].dividendPayoutPreferredStock, $.annualReports[].fiscalDateEnding, $.annualReports[].netIncome, $.annualReports[].operatingCashflow, $.annualReports[].paymentsForOperatingActivities`
- endpoint checks: {"field_presence": {"capitalExpenditures": true, "cashflowFromFinancing": true, "cashflowFromInvestment": true, "dividendPayout": true, "operatingCashflow": true}, "outflow_sign_examples": {"capitalExpenditures": ["non_negative_string"], "cashflowFromFinancing": ["negative_string", "non_negative_string"], "cashflowFromInvestment": ["negative_string", "non_negative_string"], "dividendPayout": ["non_negative_string"], "dividendPayoutCommonStock": ["non_negative_string"]}}

### earnings_ibm

- root keys: `annualEarnings, quarterlyEarnings, symbol`
- JSON field paths observed: `15`
- sampled paths: `$, $.annualEarnings, $.annualEarnings[], $.annualEarnings[].fiscalDateEnding, $.annualEarnings[].reportedEPS, $.quarterlyEarnings, $.quarterlyEarnings[], $.quarterlyEarnings[].estimatedEPS, $.quarterlyEarnings[].fiscalDateEnding, $.quarterlyEarnings[].reportTime, $.quarterlyEarnings[].reportedDate, $.quarterlyEarnings[].reportedEPS, $.quarterlyEarnings[].surprise, $.quarterlyEarnings[].surprisePercentage, $.symbol`
- endpoint checks: {"annual_earnings_keys_sampled": ["fiscalDateEnding", "reportedEPS"], "quarterly_earnings_keys_sampled": ["estimatedEPS", "fiscalDateEnding", "reportTime", "reportedDate", "reportedEPS", "surprise", "surprisePercentage"], "quarterly_required_presence": {"estimatedEPS": true, "reportTime": true, "reportedDate": true, "surprise": true, "surprisePercentage": true}}

### dividends_ibm

- root keys: `data, symbol`
- JSON field paths observed: `9`
- sampled paths: `$, $.data, $.data[], $.data[].amount, $.data[].declaration_date, $.data[].ex_dividend_date, $.data[].payment_date, $.data[].record_date, $.symbol`
- endpoint checks: {"data_row_keys_sampled": ["amount", "declaration_date", "ex_dividend_date", "payment_date", "record_date"], "required_row_key_presence": {"amount": true, "declaration_date": true, "ex_dividend_date": true, "payment_date": true, "record_date": true}}

### insider_transactions_ibm

- root keys: `data`
- JSON field paths observed: `11`
- sampled paths: `$, $.data, $.data[], $.data[].acquisition_or_disposal, $.data[].executive, $.data[].executive_title, $.data[].security_type, $.data[].share_price, $.data[].shares, $.data[].ticker, $.data[].transaction_date`
- endpoint checks: {"data_row_keys_sampled": ["acquisition_or_disposal", "executive", "executive_title", "security_type", "share_price", "shares", "ticker", "transaction_date"], "natural_primary_key_candidate_fields": ["executive", "shares"]}

### shares_outstanding_msft

- root keys: `data, status, symbol`
- JSON field paths observed: `8`
- sampled paths: `$, $.data, $.data[], $.data[].date, $.data[].shares_outstanding_basic, $.data[].shares_outstanding_diluted, $.status, $.symbol`
- endpoint checks: {"all_report_keys_sampled": ["date", "shares_outstanding_basic", "shares_outstanding_diluted"], "basic_share_fields": ["shares_outstanding_basic"], "date_fields": ["date"], "diluted_share_fields": ["shares_outstanding_diluted"]}

### earnings_estimates_ibm

- root keys: `estimates, symbol`
- JSON field paths observed: `22`
- sampled paths: `$, $.estimates, $.estimates[], $.estimates[].date, $.estimates[].eps_estimate_analyst_count, $.estimates[].eps_estimate_average, $.estimates[].eps_estimate_average_30_days_ago, $.estimates[].eps_estimate_average_60_days_ago, $.estimates[].eps_estimate_average_7_days_ago, $.estimates[].eps_estimate_average_90_days_ago, $.estimates[].eps_estimate_high, $.estimates[].eps_estimate_low, $.estimates[].eps_estimate_revision_down_trailing_30_days, $.estimates[].eps_estimate_revision_down_trailing_7_days, $.estimates[].eps_estimate_revision_up_trailing_30_days, $.estimates[].eps_estimate_revision_up_trailing_7_days, $.estimates[].horizon, $.estimates[].revenue_estimate_analyst_count, $.estimates[].revenue_estimate_average, $.estimates[].revenue_estimate_high`
- endpoint checks: {"analyst_count_fields": ["eps_estimate_analyst_count", "revenue_estimate_analyst_count"], "eps_fields": ["eps_estimate_analyst_count", "eps_estimate_average", "eps_estimate_average_30_days_ago", "eps_estimate_average_60_days_ago", "eps_estimate_average_7_days_ago", "eps_estimate_average_90_days_ago", "eps_estimate_high", "eps_estimate_low", "eps_estimate_revision_down_trailing_30_days", "eps_estimate_revision_down_trailing_7_days", "eps_estimate_revision_up_trailing_30_days", "eps_estimate_revision_up_trailing_7_days"], "estimate_row_keys_sampled": ["date", "eps_estimate_analyst_count", "eps_estimate_average", "eps_estimate_average_30_days_ago", "eps_estimate_average_60_days_ago", "eps_estimate_average_7_days_ago", "eps_estimate_average_90_days_ago", "eps_estimate_high", "eps_estimate_low", "eps_estimate_revision_down_trailing_30_days", "eps_estimate_revision_down_trailing_7_days", "eps_estimate_revision_up_trailing_30_days", "eps_estimate_revision_up_trailing_7_days", "horizon", "rev

### splits_ibm

- root keys: `data, symbol`
- JSON field paths observed: `6`
- sampled paths: `$, $.data, $.data[], $.data[].effective_date, $.data[].split_factor, $.symbol`
- endpoint checks: {"data_row_keys_sampled": ["effective_date", "split_factor"], "date_fields": ["effective_date"], "ratio_or_factor_fields": ["split_factor"]}

### news_sentiment_aapl_latest

- root keys: `feed, items, relevance_score_definition, sentiment_score_definition`
- JSON field paths observed: `28`
- sampled paths: `$, $.feed, $.feed[], $.feed[].authors, $.feed[].authors[], $.feed[].banner_image, $.feed[].category_within_source, $.feed[].overall_sentiment_label, $.feed[].overall_sentiment_score, $.feed[].source, $.feed[].source_domain, $.feed[].summary, $.feed[].ticker_sentiment, $.feed[].ticker_sentiment[], $.feed[].ticker_sentiment[].relevance_score, $.feed[].ticker_sentiment[].ticker, $.feed[].ticker_sentiment[].ticker_sentiment_label, $.feed[].ticker_sentiment[].ticker_sentiment_score, $.feed[].time_published, $.feed[].title`
- endpoint checks: {"actual_feed_count": 50, "duplicate_urls": {"duplicate_count": 0, "duplicate_urls": []}, "empty_array_paths": [], "feed_keys_sampled": ["authors", "banner_image", "category_within_source", "overall_sentiment_label", "overall_sentiment_score", "source", "source_domain", "summary", "ticker_sentiment", "time_published", "title", "topics", "url"], "items_value": "50", "requested_limit": "10", "root_keys": ["feed", "items", "relevance_score_definition", "sentiment_score_definition"], "sentiment_score_types": ["number"], "source_domain_comparison": {"samples": [{"parsed_domain": "ca.investing.com", "source": "Investing.com Canada", "source_domain": "Investing.com Canada"}, {"parsed_domain": "www.benzinga.com", "source": "Benzinga", "source_domain": "Benzinga"}, {"parsed_domain": "www.theglobeandmail.com", "source": "The Globe and Mail", "source_domain": "The Globe and Mail"}, {"parsed_domain": "www.theglobeandmail.com", "source": "The Globe and Mail", "source_domain": "The Globe and Mail"},

### news_sentiment_technology_latest

- root keys: `feed, items, relevance_score_definition, sentiment_score_definition`
- JSON field paths observed: `28`
- sampled paths: `$, $.feed, $.feed[], $.feed[].authors, $.feed[].authors[], $.feed[].banner_image, $.feed[].category_within_source, $.feed[].overall_sentiment_label, $.feed[].overall_sentiment_score, $.feed[].source, $.feed[].source_domain, $.feed[].summary, $.feed[].ticker_sentiment, $.feed[].ticker_sentiment[], $.feed[].ticker_sentiment[].relevance_score, $.feed[].ticker_sentiment[].ticker, $.feed[].ticker_sentiment[].ticker_sentiment_label, $.feed[].ticker_sentiment[].ticker_sentiment_score, $.feed[].time_published, $.feed[].title`
- endpoint checks: {"actual_feed_count": 50, "duplicate_urls": {"duplicate_count": 0, "duplicate_urls": []}, "empty_array_paths": [], "feed_keys_sampled": ["authors", "banner_image", "category_within_source", "overall_sentiment_label", "overall_sentiment_score", "source", "source_domain", "summary", "ticker_sentiment", "time_published", "title", "topics", "url"], "items_value": "50", "requested_limit": "10", "root_keys": ["feed", "items", "relevance_score_definition", "sentiment_score_definition"], "sentiment_score_types": ["number"], "source_domain_comparison": {"samples": [{"parsed_domain": "www.investing.com", "source": "Investing.com", "source_domain": "Investing.com"}, {"parsed_domain": "au.investing.com", "source": "Investing.com Australia", "source_domain": "Investing.com Australia"}, {"parsed_domain": "retail-systems.com", "source": "Retail Systems", "source_domain": "Retail Systems"}, {"parsed_domain": "www.benzinga.com", "source": "Benzinga", "source_domain": "Benzinga"}, {"parsed_domain": "sg.

### earnings_call_transcript_ibm_2024q1

- root keys: `quarter, symbol, transcript`
- JSON field paths observed: `9`
- sampled paths: `$, $.quarter, $.symbol, $.transcript, $.transcript[], $.transcript[].content, $.transcript[].sentiment, $.transcript[].speaker, $.transcript[].title`
- endpoint checks: {"content_fields": ["content"], "quarter_present": true, "root_keys": ["quarter", "symbol", "transcript"], "speaker_fields": ["speaker"], "symbol_present": true, "title_or_role_fields": ["title"], "transcript_row_keys_sampled": ["content", "sentiment", "speaker", "title"]}

### listing_status

- CSV columns: `symbol, name, exchange, assetType, ipoDate, delistingDate, status`
- endpoint checks: {"columns": ["symbol", "name", "exchange", "assetType", "ipoDate", "delistingDate", "status"], "expected_column_presence": {"assetType": true, "delistingDate": true, "exchange": true, "ipoDate": true, "name": true, "status": true, "symbol": true}}

### earnings_calendar_ibm_12month

- CSV columns: `symbol, name, reportDate, fiscalDateEnding, estimate, currency, timeOfTheDay`
- endpoint checks: {"columns": ["symbol", "name", "reportDate", "fiscalDateEnding", "estimate", "currency", "timeOfTheDay"], "company_name_fields": ["name"], "currency_fields": ["currency"], "estimate_fields": ["estimate"], "fiscal_date_fields": ["fiscalDateEnding"], "report_date_fields": ["reportDate"], "symbol_fields": ["symbol"]}

## 4. Key/Value Dictionary

- `$`: semantic=`object`; observed_at=`overview_ibm:$; income_statement_ibm:$; balance_sheet_ibm:$; cash_flow_ibm:$; earnings_ibm:$`; examples=`{"Symbol": "IBM", "AssetType": "Common Stock", "Name": "International Business Machines", "Description": "International Business Machines...; {"symbol": "IBM", "annualReports": [{"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD", "grossProfit": "40185000000", "totalRev...; {"symbol": "IBM", "annualReports": [{"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD", "totalAssets": "151880000000", "totalCu...`
- `200DayMovingAverage`: semantic=`numeric_string`; observed_at=`overview_ibm:$.200DayMovingAverage`; examples=`"273.07"`
- `50DayMovingAverage`: semantic=`numeric_string`; observed_at=`overview_ibm:$.50DayMovingAverage`; examples=`"249.15"`
- `52WeekHigh`: semantic=`numeric_string`; observed_at=`overview_ibm:$.52WeekHigh`; examples=`"332.46"`
- `52WeekLow`: semantic=`numeric_string`; observed_at=`overview_ibm:$.52WeekLow`; examples=`"212.34"`
- `Address`: semantic=`string`; observed_at=`overview_ibm:$.Address`; examples=`"ONE NEW ORCHARD ROAD, ARMONK, NY, UNITED STATES, 10504"`
- `AnalystRatingBuy`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystRatingBuy`; examples=`"11"`
- `AnalystRatingHold`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystRatingHold`; examples=`"7"`
- `AnalystRatingSell`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystRatingSell`; examples=`"0"`
- `AnalystRatingStrongBuy`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystRatingStrongBuy`; examples=`"1"`
- `AnalystRatingStrongSell`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystRatingStrongSell`; examples=`"2"`
- `AnalystTargetPrice`: semantic=`numeric_string`; observed_at=`overview_ibm:$.AnalystTargetPrice`; examples=`"290.89"`
- `AssetType`: semantic=`string`; observed_at=`overview_ibm:$.AssetType`; examples=`"Common Stock"`
- `Beta`: semantic=`numeric_string`; observed_at=`overview_ibm:$.Beta`; examples=`"0.665"`
- `BookValue`: semantic=`numeric_string`; observed_at=`overview_ibm:$.BookValue`; examples=`"35.08"`
- `CIK`: semantic=`numeric_string`; observed_at=`overview_ibm:$.CIK`; examples=`"51143"`
- `Country`: semantic=`string`; observed_at=`overview_ibm:$.Country`; examples=`"USA"`
- `Currency`: semantic=`string`; observed_at=`overview_ibm:$.Currency`; examples=`"USD"`
- `Description`: semantic=`string`; observed_at=`overview_ibm:$.Description`; examples=`"International Business Machines Corporation (IBM) is an American multinational technology company headquartered in Armonk, New York, wit...`
- `DilutedEPSTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.DilutedEPSTTM`; examples=`"11.3"`
- `DividendDate`: semantic=`date_yyyy_mm_dd`; observed_at=`overview_ibm:$.DividendDate`; examples=`"2026-06-10"`
- `DividendPerShare`: semantic=`numeric_string`; observed_at=`overview_ibm:$.DividendPerShare`; examples=`"6.72"`
- `DividendYield`: semantic=`numeric_string`; observed_at=`overview_ibm:$.DividendYield`; examples=`"0.0244"`
- `EBITDA`: semantic=`numeric_string`; observed_at=`overview_ibm:$.EBITDA`; examples=`"16611000000"`
- `EPS`: semantic=`numeric_string`; observed_at=`overview_ibm:$.EPS`; examples=`"11.3"`
- `EVToEBITDA`: semantic=`numeric_string`; observed_at=`overview_ibm:$.EVToEBITDA`; examples=`"17.81"`
- `EVToRevenue`: semantic=`numeric_string`; observed_at=`overview_ibm:$.EVToRevenue`; examples=`"4.555"`
- `ExDividendDate`: semantic=`date_yyyy_mm_dd`; observed_at=`overview_ibm:$.ExDividendDate`; examples=`"2026-05-08"`
- `Exchange`: semantic=`string`; observed_at=`overview_ibm:$.Exchange`; examples=`"NYSE"`
- `FiscalYearEnd`: semantic=`string`; observed_at=`overview_ibm:$.FiscalYearEnd`; examples=`"December"`
- `ForwardPE`: semantic=`numeric_string`; observed_at=`overview_ibm:$.ForwardPE`; examples=`"21.98"`
- `GrossProfitTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.GrossProfitTTM`; examples=`"40214999000"`
- `Industry`: semantic=`string`; observed_at=`overview_ibm:$.Industry`; examples=`"INFORMATION TECHNOLOGY SERVICES"`
- `LatestQuarter`: semantic=`date_yyyy_mm_dd`; observed_at=`overview_ibm:$.LatestQuarter`; examples=`"2026-03-31"`
- `MarketCapitalization`: semantic=`numeric_string`; observed_at=`overview_ibm:$.MarketCapitalization`; examples=`"255874367000"`
- `Name`: semantic=`string`; observed_at=`overview_ibm:$.Name`; examples=`"International Business Machines"`
- `OfficialSite`: semantic=`string`; observed_at=`overview_ibm:$.OfficialSite`; examples=`"https://www.ibm.com"`
- `OperatingMarginTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.OperatingMarginTTM`; examples=`"0.138"`
- `PEGRatio`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PEGRatio`; examples=`"2.542"`
- `PERatio`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PERatio`; examples=`"24.09"`
- `PercentInsiders`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PercentInsiders`; examples=`"0.117"`
- `PercentInstitutions`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PercentInstitutions`; examples=`"65.589"`
- `PriceToBookRatio`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PriceToBookRatio`; examples=`"7.76"`
- `PriceToSalesRatioTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.PriceToSalesRatioTTM`; examples=`"3.713"`
- `ProfitMargin`: semantic=`numeric_string`; observed_at=`overview_ibm:$.ProfitMargin`; examples=`"0.156"`
- `QuarterlyEarningsGrowthYOY`: semantic=`numeric_string`; observed_at=`overview_ibm:$.QuarterlyEarningsGrowthYOY`; examples=`"0.142"`
- `QuarterlyRevenueGrowthYOY`: semantic=`numeric_string`; observed_at=`overview_ibm:$.QuarterlyRevenueGrowthYOY`; examples=`"0.095"`
- `ReturnOnAssetsTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.ReturnOnAssetsTTM`; examples=`"0.0537"`
- `ReturnOnEquityTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.ReturnOnEquityTTM`; examples=`"0.358"`
- `RevenuePerShareTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.RevenuePerShareTTM`; examples=`"73.71"`
- `RevenueTTM`: semantic=`numeric_string`; observed_at=`overview_ibm:$.RevenueTTM`; examples=`"68910998000"`
- `Sector`: semantic=`string`; observed_at=`overview_ibm:$.Sector`; examples=`"TECHNOLOGY"`
- `SharesFloat`: semantic=`numeric_string`; observed_at=`overview_ibm:$.SharesFloat`; examples=`"937902000"`
- `SharesOutstanding`: semantic=`numeric_string`; observed_at=`overview_ibm:$.SharesOutstanding`; examples=`"939885000"`
- `Symbol`: semantic=`string`; observed_at=`overview_ibm:$.Symbol`; examples=`"IBM"`
- `TrailingPE`: semantic=`numeric_string`; observed_at=`overview_ibm:$.TrailingPE`; examples=`"24.09"`
- `accumulatedDepreciationAmortizationPPE`: semantic=`literal_string_none, numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].accumulatedDepreciationAmortizationPPE; balance_sheet_ibm:$.quarterlyReports[].accumulatedDepreciationAmortizationPPE`; examples=`"None"; "-14390000000"; "-23136000000"`
- `acquisition_or_disposal`: semantic=`string`; observed_at=`insider_transactions_ibm:$.data[].acquisition_or_disposal`; examples=`"D"; "A"`
- `amount`: semantic=`numeric_string`; observed_at=`dividends_ibm:$.data[].amount`; examples=`"1.69"; "1.68"; "1.67"`
- `annualEarnings`: semantic=`array, object`; observed_at=`earnings_ibm:$.annualEarnings; earnings_ibm:$.annualEarnings[]`; examples=`[{"fiscalDateEnding": "2026-03-31", "reportedEPS": "1.91"}, {"fiscalDateEnding": "2025-12-31", "reportedEPS": "11.57"}, {"fiscalDateEndin...; {"fiscalDateEnding": "2026-03-31", "reportedEPS": "1.91"}; {"fiscalDateEnding": "2025-12-31", "reportedEPS": "11.57"}`
- `annualReports`: semantic=`array, object`; observed_at=`income_statement_ibm:$.annualReports; income_statement_ibm:$.annualReports[]; balance_sheet_ibm:$.annualReports; balance_sheet_ibm:$.annualReports[]; cash_flow_ibm:$.annualReports`; examples=`[{"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD", "grossProfit": "40185000000", "totalRevenue": "67535000000", "costOfRevenu...; {"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD", "grossProfit": "40185000000", "totalRevenue": "67535000000", "costOfRevenue...; {"fiscalDateEnding": "2024-12-31", "reportedCurrency": "USD", "grossProfit": "35551000000", "totalRevenue": "62753000000", "costOfRevenue...`
- `assetType`: semantic=`string`; observed_at=`listing_status:csv.assetType`; examples=`"Stock"; "ETF"`
- `authors`: semantic=`array, string`; observed_at=`news_sentiment_aapl_latest:$.feed[].authors; news_sentiment_aapl_latest:$.feed[].authors[]; news_sentiment_technology_latest:$.feed[].authors; news_sentiment_technology_latest:$.feed[].authors[]`; examples=`["Senad Karaahmetovic"]; ["Benzinga Staff Writer"]; ["Zacks Investment Research"]`
- `banner_image`: semantic=`string, null`; observed_at=`news_sentiment_aapl_latest:$.feed[].banner_image; news_sentiment_technology_latest:$.feed[].banner_image`; examples=`"https://i-invdn-com.investing.com/news/SP500StandardandPoors500Index_800x533_L_1657544297.jpg"; "https://cdn.benzinga.com/cdn-cgi/image/width=1300,format=auto,quality=85/files/images/story/2025/07/24/article-header-background-image.png"; "https://staticx-tuner.zacks.com/images/articles/main/83/1163.jpg"`
- `capitalExpenditures`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].capitalExpenditures; cash_flow_ibm:$.quarterlyReports[].capitalExpenditures`; examples=`"1617000000"; "1685000000"; "1918000000"`
- `capitalLeaseObligations`: semantic=`numeric_string, literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].capitalLeaseObligations; balance_sheet_ibm:$.quarterlyReports[].capitalLeaseObligations`; examples=`"3347000000"; "3423000000"; "3388000000"`
- `cashAndCashEquivalentsAtCarryingValue`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].cashAndCashEquivalentsAtCarryingValue; balance_sheet_ibm:$.quarterlyReports[].cashAndCashEquivalentsAtCarryingValue`; examples=`"13641000000"; "13947000000"; "13068000000"`
- `cashAndShortTermInvestments`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].cashAndShortTermInvestments; balance_sheet_ibm:$.quarterlyReports[].cashAndShortTermInvestments`; examples=`"13641000000"; "13947000000"; "13068000000"`
- `cashflowFromFinancing`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].cashflowFromFinancing; cash_flow_ibm:$.quarterlyReports[].cashflowFromFinancing`; examples=`"-3829000000"; "-7079000000"; "-6016000000"`
- `cashflowFromInvestment`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].cashflowFromInvestment; cash_flow_ibm:$.quarterlyReports[].cashflowFromInvestment`; examples=`"-10302000000"; "-4937000000"; "-7070000000"`
- `category_within_source`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.feed[].category_within_source; news_sentiment_technology_latest:$.feed[].category_within_source`; examples=`"General"`
- `changeInCashAndCashEquivalents`: semantic=`literal_string_none, numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].changeInCashAndCashEquivalents; cash_flow_ibm:$.quarterlyReports[].changeInCashAndCashEquivalents`; examples=`"None"; "-6533000000"; "5448000000"`
- `changeInExchangeRate`: semantic=`literal_string_none, numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].changeInExchangeRate; cash_flow_ibm:$.quarterlyReports[].changeInExchangeRate`; examples=`"None"; "937000000"; "-51000000"`
- `changeInInventory`: semantic=`numeric_string, literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].changeInInventory; cash_flow_ibm:$.quarterlyReports[].changeInInventory`; examples=`"70000000"; "-166000000"; "390000000"`
- `changeInOperatingAssets`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].changeInOperatingAssets; cash_flow_ibm:$.quarterlyReports[].changeInOperatingAssets`; examples=`"None"`
- `changeInOperatingLiabilities`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].changeInOperatingLiabilities; cash_flow_ibm:$.quarterlyReports[].changeInOperatingLiabilities`; examples=`"None"`
- `changeInReceivables`: semantic=`literal_string_none, numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].changeInReceivables; cash_flow_ibm:$.quarterlyReports[].changeInReceivables`; examples=`"None"; "1372000000"; "5297000000"`
- `commonStock`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].commonStock; balance_sheet_ibm:$.quarterlyReports[].commonStock`; examples=`"63318000000"; "61380000000"; "59643000000"`
- `commonStockSharesOutstanding`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].commonStockSharesOutstanding; balance_sheet_ibm:$.quarterlyReports[].commonStockSharesOutstanding`; examples=`"948700000"; "937200000"; "922073828"`
- `comprehensiveIncomeNetOfTax`: semantic=`literal_string_none`; observed_at=`income_statement_ibm:$.annualReports[].comprehensiveIncomeNetOfTax; income_statement_ibm:$.quarterlyReports[].comprehensiveIncomeNetOfTax`; examples=`"None"`
- `content`: semantic=`string`; observed_at=`earnings_call_transcript_ibm_2024q1:$.transcript[].content`; examples=`"Thank you. I'd like to welcome you to IBM's First Quarter 2024 Earnings Presentation. I'm Olympia McNerney, and I'm here today with Arvi...; "Thank you for joining us. In the first quarter, we had solid performance across revenue and cash flow. These results are further proof o...; "Thank you, Arvind. Let me start with the details of the transaction. We have agreed to acquire HashiCorp for $6.4 billion in enterprise ...`
- `costOfRevenue`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].costOfRevenue; income_statement_ibm:$.quarterlyReports[].costOfRevenue`; examples=`"27350000000"; "27201000000"; "27560000000"`
- `costofGoodsAndServicesSold`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].costofGoodsAndServicesSold; income_statement_ibm:$.quarterlyReports[].costofGoodsAndServicesSold`; examples=`"27350000000"; "27201000000"; "27560000000"`
- `currency`: semantic=`string`; observed_at=`earnings_calendar_ibm_12month:csv.currency`; examples=`"USD"`
- `currentAccountsPayable`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].currentAccountsPayable; balance_sheet_ibm:$.quarterlyReports[].currentAccountsPayable`; examples=`"4756000000"; "4032000000"; "4132000000"`
- `currentDebt`: semantic=`literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].currentDebt; balance_sheet_ibm:$.quarterlyReports[].currentDebt`; examples=`"None"`
- `currentLongTermDebt`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].currentLongTermDebt; balance_sheet_ibm:$.quarterlyReports[].currentLongTermDebt`; examples=`"6424000000"; "5089000000"; "6426000000"`
- `currentNetReceivables`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].currentNetReceivables; balance_sheet_ibm:$.quarterlyReports[].currentNetReceivables`; examples=`"17639000000"; "14010000000"; "13956000000"`
- `data`: semantic=`array, object`; observed_at=`dividends_ibm:$.data; dividends_ibm:$.data[]; insider_transactions_ibm:$.data; insider_transactions_ibm:$.data[]; shares_outstanding_msft:$.data`; examples=`[{"ex_dividend_date": "2026-05-08", "declaration_date": "2026-04-22", "record_date": "2026-05-08", "payment_date": "2026-06-10", "amount"...; {"ex_dividend_date": "2026-05-08", "declaration_date": "2026-04-22", "record_date": "2026-05-08", "payment_date": "2026-06-10", "amount":...; {"ex_dividend_date": "2026-02-10", "declaration_date": "2026-01-28", "record_date": "2026-02-10", "payment_date": "2026-03-10", "amount":...`
- `date`: semantic=`date_yyyy_mm_dd`; observed_at=`shares_outstanding_msft:$.data[].date; earnings_estimates_ibm:$.estimates[].date`; examples=`"2026-03-31"; "2025-12-31"; "2025-09-30"`
- `declaration_date`: semantic=`date_yyyy_mm_dd`; observed_at=`dividends_ibm:$.data[].declaration_date`; examples=`"2026-04-22"; "2026-01-28"; "2025-10-22"`
- `deferredRevenue`: semantic=`literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].deferredRevenue; balance_sheet_ibm:$.quarterlyReports[].deferredRevenue`; examples=`"None"`
- `delistingDate`: semantic=`string`; observed_at=`listing_status:csv.delistingDate`; examples=`"null"`
- `depreciation`: semantic=`literal_string_none`; observed_at=`income_statement_ibm:$.annualReports[].depreciation; income_statement_ibm:$.quarterlyReports[].depreciation`; examples=`"None"`
- `depreciationAndAmortization`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].depreciationAndAmortization; income_statement_ibm:$.quarterlyReports[].depreciationAndAmortization`; examples=`"5021000000"; "4667000000"; "4395000000"`
- `depreciationDepletionAndAmortization`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].depreciationDepletionAndAmortization; cash_flow_ibm:$.quarterlyReports[].depreciationDepletionAndAmortization`; examples=`"5021000000"; "4667000000"; "4381000000"`
- `dividendPayout`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].dividendPayout; cash_flow_ibm:$.quarterlyReports[].dividendPayout`; examples=`"6255000000"; "6147000000"; "6016000000"`
- `dividendPayoutCommonStock`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].dividendPayoutCommonStock; cash_flow_ibm:$.quarterlyReports[].dividendPayoutCommonStock`; examples=`"6255000000"; "6147000000"; "6016000000"`
- `dividendPayoutPreferredStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].dividendPayoutPreferredStock; cash_flow_ibm:$.quarterlyReports[].dividendPayoutPreferredStock`; examples=`"None"`
- `ebit`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].ebit; income_statement_ibm:$.quarterlyReports[].ebit`; examples=`"12263000000"; "7509000000"; "7514000000"`
- `ebitda`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].ebitda; income_statement_ibm:$.quarterlyReports[].ebitda`; examples=`"17284000000"; "12176000000"; "7514000000"`
- `effective_date`: semantic=`date_yyyy_mm_dd`; observed_at=`splits_ibm:$.data[].effective_date`; examples=`"2021-11-04"; "1999-05-27"`
- `eps_estimate_analyst_count`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_analyst_count`; examples=`"22.0000"; "18.0000"; "19.0000"`
- `eps_estimate_average`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_average`; examples=`"13.4227"; "12.4254"; "2.9336"`
- `eps_estimate_average_30_days_ago`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_average_30_days_ago`; examples=`"13.4537"; "12.4295"; "2.9347"`
- `eps_estimate_average_60_days_ago`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_average_60_days_ago`; examples=`"13.3984"; "12.3767"; "2.9128"`
- `eps_estimate_average_7_days_ago`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_average_7_days_ago`; examples=`"13.4227"; "12.4254"; "2.9336"`
- `eps_estimate_average_90_days_ago`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_average_90_days_ago`; examples=`"13.4008"; "12.3800"; "2.9136"`
- `eps_estimate_high`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_high`; examples=`"14.0100"; "12.6900"; "3.1400"`
- `eps_estimate_low`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_low`; examples=`"12.6700"; "12.1000"; "2.7800"`
- `eps_estimate_revision_down_trailing_30_days`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_revision_down_trailing_30_days`; examples=`"0.0000"; "4.0000"; "9.0000"`
- `eps_estimate_revision_down_trailing_7_days`: semantic=`null`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_revision_down_trailing_7_days`; examples=`null`
- `eps_estimate_revision_up_trailing_30_days`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_revision_up_trailing_30_days`; examples=`"1.0000"; "17.0000"; "5.0000"`
- `eps_estimate_revision_up_trailing_7_days`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].eps_estimate_revision_up_trailing_7_days`; examples=`"0.0000"; "1.0000"; "2.0000"`
- `estimate`: semantic=`numeric_string`; observed_at=`earnings_calendar_ibm_12month:csv.estimate`; examples=`"2.95"`
- `estimatedEPS`: semantic=`numeric_string`; observed_at=`earnings_ibm:$.quarterlyEarnings[].estimatedEPS`; examples=`"1.81"; "4.29"; "2.45"`
- `estimates`: semantic=`array, object`; observed_at=`earnings_estimates_ibm:$.estimates; earnings_estimates_ibm:$.estimates[]`; examples=`[{"date": "2027-12-31", "horizon": "fiscal year", "eps_estimate_average": "13.4227", "eps_estimate_high": "14.0100", "eps_estimate_low": ...; {"date": "2027-12-31", "horizon": "fiscal year", "eps_estimate_average": "13.4227", "eps_estimate_high": "14.0100", "eps_estimate_low": "...; {"date": "2026-12-31", "horizon": "fiscal year", "eps_estimate_average": "12.4254", "eps_estimate_high": "12.6900", "eps_estimate_low": "...`
- `ex_dividend_date`: semantic=`date_yyyy_mm_dd`; observed_at=`dividends_ibm:$.data[].ex_dividend_date`; examples=`"2026-05-08"; "2026-02-10"; "2025-11-10"`
- `exchange`: semantic=`string`; observed_at=`listing_status:csv.exchange`; examples=`"NASDAQ"; "NYSE"; "BATS"`
- `executive`: semantic=`string`; observed_at=`insider_transactions_ibm:$.data[].executive`; examples=`"FEHRING, NICOLAS A."; "ZOLLAR, ALFRED W"; "BUBERL, THOMAS"`
- `executive_title`: semantic=`string`; observed_at=`insider_transactions_ibm:$.data[].executive_title`; examples=`"VP, Controller"; "Director"`
- `feed`: semantic=`array, object`; observed_at=`news_sentiment_aapl_latest:$.feed; news_sentiment_aapl_latest:$.feed[]; news_sentiment_technology_latest:$.feed; news_sentiment_technology_latest:$.feed[]`; examples=`[{"title": "Why is Traws Pharma stock tumbling today?", "url": "https://ca.investing.com/news/stock-market-news/why-is-traws-pharma-stock...; {"title": "Why is Traws Pharma stock tumbling today?", "url": "https://ca.investing.com/news/stock-market-news/why-is-traws-pharma-stock-...; {"title": "Performance Comparison: Apple And Competitors In Technology Hardware, Storage & Peripherals Industry", "url": "https://www.ben...`
- `fiscalDateEnding`: semantic=`date_yyyy_mm_dd`; observed_at=`income_statement_ibm:$.annualReports[].fiscalDateEnding; income_statement_ibm:$.quarterlyReports[].fiscalDateEnding; balance_sheet_ibm:$.annualReports[].fiscalDateEnding; balance_sheet_ibm:$.quarterlyReports[].fiscalDateEnding; cash_flow_ibm:$.annualReports[].fiscalDateEnding`; examples=`"2025-12-31"; "2024-12-31"; "2023-12-31"`
- `goodwill`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].goodwill; balance_sheet_ibm:$.quarterlyReports[].goodwill`; examples=`"67717000000"; "60706000000"; "60178000000"`
- `grossProfit`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].grossProfit; income_statement_ibm:$.quarterlyReports[].grossProfit`; examples=`"40185000000"; "35551000000"; "34300000000"`
- `horizon`: semantic=`string`; observed_at=`earnings_estimates_ibm:$.estimates[].horizon`; examples=`"fiscal year"; "fiscal quarter"`
- `incomeBeforeTax`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].incomeBeforeTax; income_statement_ibm:$.quarterlyReports[].incomeBeforeTax`; examples=`"10328000000"; "5797000000"; "8690000000"`
- `incomeTaxExpense`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].incomeTaxExpense; income_statement_ibm:$.quarterlyReports[].incomeTaxExpense`; examples=`"-242000000"; "-218000000"; "1176000000"`
- `intangibleAssets`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].intangibleAssets; balance_sheet_ibm:$.quarterlyReports[].intangibleAssets`; examples=`"11391000000"; "10661000000"; "11036000000"`
- `intangibleAssetsExcludingGoodwill`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].intangibleAssetsExcludingGoodwill; balance_sheet_ibm:$.quarterlyReports[].intangibleAssetsExcludingGoodwill`; examples=`"11391000000"; "10661000000"; "11036000000"`
- `interestAndDebtExpense`: semantic=`literal_string_none`; observed_at=`income_statement_ibm:$.annualReports[].interestAndDebtExpense; income_statement_ibm:$.quarterlyReports[].interestAndDebtExpense`; examples=`"None"`
- `interestExpense`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].interestExpense; income_statement_ibm:$.quarterlyReports[].interestExpense`; examples=`"1935000000"; "1712000000"; "1607000000"`
- `interestIncome`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].interestIncome; income_statement_ibm:$.quarterlyReports[].interestIncome`; examples=`"645000000"; "747000000"; "591000000"`
- `inventory`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].inventory; balance_sheet_ibm:$.quarterlyReports[].inventory`; examples=`"1220000000"; "1289000000"; "1161000000"`
- `investmentIncomeNet`: semantic=`literal_string_none`; observed_at=`income_statement_ibm:$.annualReports[].investmentIncomeNet; income_statement_ibm:$.quarterlyReports[].investmentIncomeNet`; examples=`"None"`
- `investments`: semantic=`literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].investments; balance_sheet_ibm:$.quarterlyReports[].investments`; examples=`"None"`
- `ipoDate`: semantic=`date_yyyy_mm_dd`; observed_at=`listing_status:csv.ipoDate`; examples=`"2023-08-30"; "1999-11-18"; "2016-10-18"`
- `items`: semantic=`numeric_string`; observed_at=`news_sentiment_aapl_latest:$.items; news_sentiment_technology_latest:$.items`; examples=`"50"`
- `longTermDebt`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].longTermDebt; balance_sheet_ibm:$.quarterlyReports[].longTermDebt`; examples=`"54836000000"; "49884000000"; "50121000000"`
- `longTermDebtNoncurrent`: semantic=`literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].longTermDebtNoncurrent; balance_sheet_ibm:$.quarterlyReports[].longTermDebtNoncurrent`; examples=`"None"`
- `longTermInvestments`: semantic=`literal_string_none, numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].longTermInvestments; balance_sheet_ibm:$.quarterlyReports[].longTermInvestments`; examples=`"None"; "1617000000"; "1823000000"`
- `name`: semantic=`string`; observed_at=`listing_status:csv.name; earnings_calendar_ibm_12month:csv.name`; examples=`"Presurance Holdings Inc"; "Agilent Technologies Inc"; "Alcoa Corp"`
- `netIncome`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].netIncome; income_statement_ibm:$.quarterlyReports[].netIncome; cash_flow_ibm:$.annualReports[].netIncome; cash_flow_ibm:$.quarterlyReports[].netIncome`; examples=`"10593000000"; "6023000000"; "7502000000"`
- `netIncomeFromContinuingOperations`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].netIncomeFromContinuingOperations; income_statement_ibm:$.quarterlyReports[].netIncomeFromContinuingOperations`; examples=`"10571000000"; "6015000000"; "7099000000"`
- `netInterestIncome`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].netInterestIncome; income_statement_ibm:$.quarterlyReports[].netInterestIncome`; examples=`"-1290000000"; "-965000000"; "-924000000"`
- `nonInterestIncome`: semantic=`literal_string_none`; observed_at=`income_statement_ibm:$.annualReports[].nonInterestIncome; income_statement_ibm:$.quarterlyReports[].nonInterestIncome`; examples=`"None"`
- `operatingCashflow`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].operatingCashflow; cash_flow_ibm:$.quarterlyReports[].operatingCashflow`; examples=`"13192000000"; "13445000000"; "13432000000"`
- `operatingExpenses`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].operatingExpenses; income_statement_ibm:$.quarterlyReports[].operatingExpenses`; examples=`"29860000000"; "25478000000"; "26786000000"`
- `operatingIncome`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].operatingIncome; income_statement_ibm:$.quarterlyReports[].operatingIncome`; examples=`"10325000000"; "10074000000"; "7514000000"`
- `otherCurrentAssets`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].otherCurrentAssets; balance_sheet_ibm:$.quarterlyReports[].otherCurrentAssets`; examples=`"2530000000"; "4592000000"; "4350000000"`
- `otherCurrentLiabilities`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].otherCurrentLiabilities; balance_sheet_ibm:$.quarterlyReports[].otherCurrentLiabilities`; examples=`"10577000000"; "7313000000"; "7023000000"`
- `otherNonCurrentAssets`: semantic=`literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].otherNonCurrentAssets; balance_sheet_ibm:$.quarterlyReports[].otherNonCurrentAssets`; examples=`"None"`
- `otherNonCurrentLiabilities`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].otherNonCurrentLiabilities; balance_sheet_ibm:$.quarterlyReports[].otherNonCurrentLiabilities`; examples=`"1068000000"; "981000000"; "1164000000"`
- `otherNonOperatingIncome`: semantic=`literal_string_none, numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].otherNonOperatingIncome; income_statement_ibm:$.quarterlyReports[].otherNonOperatingIncome`; examples=`"None"; "-873000000"; "-861000000"`
- `overall_sentiment_label`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.feed[].overall_sentiment_label; news_sentiment_technology_latest:$.feed[].overall_sentiment_label`; examples=`"Somewhat-Bearish"; "Neutral"; "Somewhat-Bullish"`
- `overall_sentiment_score`: semantic=`number`; observed_at=`news_sentiment_aapl_latest:$.feed[].overall_sentiment_score; news_sentiment_technology_latest:$.feed[].overall_sentiment_score`; examples=`-0.311872; -0.045159; 0.331742`
- `payment_date`: semantic=`date_yyyy_mm_dd`; observed_at=`dividends_ibm:$.data[].payment_date`; examples=`"2026-06-10"; "2026-03-10"; "2025-12-10"`
- `paymentsForOperatingActivities`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].paymentsForOperatingActivities; cash_flow_ibm:$.quarterlyReports[].paymentsForOperatingActivities`; examples=`"None"`
- `paymentsForRepurchaseOfCommonStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].paymentsForRepurchaseOfCommonStock; cash_flow_ibm:$.quarterlyReports[].paymentsForRepurchaseOfCommonStock`; examples=`"None"`
- `paymentsForRepurchaseOfEquity`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].paymentsForRepurchaseOfEquity; cash_flow_ibm:$.quarterlyReports[].paymentsForRepurchaseOfEquity`; examples=`"None"`
- `paymentsForRepurchaseOfPreferredStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].paymentsForRepurchaseOfPreferredStock; cash_flow_ibm:$.quarterlyReports[].paymentsForRepurchaseOfPreferredStock`; examples=`"None"`
- `proceedsFromIssuanceOfCommonStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromIssuanceOfCommonStock; cash_flow_ibm:$.quarterlyReports[].proceedsFromIssuanceOfCommonStock`; examples=`"None"`
- `proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet; cash_flow_ibm:$.quarterlyReports[].proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet`; examples=`"None"`
- `proceedsFromIssuanceOfPreferredStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromIssuanceOfPreferredStock; cash_flow_ibm:$.quarterlyReports[].proceedsFromIssuanceOfPreferredStock`; examples=`"None"`
- `proceedsFromOperatingActivities`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromOperatingActivities; cash_flow_ibm:$.quarterlyReports[].proceedsFromOperatingActivities`; examples=`"None"`
- `proceedsFromRepaymentsOfShortTermDebt`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromRepaymentsOfShortTermDebt; cash_flow_ibm:$.quarterlyReports[].proceedsFromRepaymentsOfShortTermDebt`; examples=`"None"`
- `proceedsFromRepurchaseOfEquity`: semantic=`numeric_string`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromRepurchaseOfEquity; cash_flow_ibm:$.quarterlyReports[].proceedsFromRepurchaseOfEquity`; examples=`"-1018000000"; "-651000000"; "-416000000"`
- `proceedsFromSaleOfTreasuryStock`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].proceedsFromSaleOfTreasuryStock; cash_flow_ibm:$.quarterlyReports[].proceedsFromSaleOfTreasuryStock`; examples=`"None"`
- `profitLoss`: semantic=`literal_string_none`; observed_at=`cash_flow_ibm:$.annualReports[].profitLoss; cash_flow_ibm:$.quarterlyReports[].profitLoss`; examples=`"None"`
- `propertyPlantEquipment`: semantic=`numeric_string, literal_string_none`; observed_at=`balance_sheet_ibm:$.annualReports[].propertyPlantEquipment; balance_sheet_ibm:$.quarterlyReports[].propertyPlantEquipment`; examples=`"9028000000"; "8928000000"; "8721000000"`
- `quarter`: semantic=`string`; observed_at=`earnings_call_transcript_ibm_2024q1:$.quarter`; examples=`"2024Q1"`
- `quarterlyEarnings`: semantic=`array, object`; observed_at=`earnings_ibm:$.quarterlyEarnings; earnings_ibm:$.quarterlyEarnings[]`; examples=`[{"fiscalDateEnding": "2026-03-31", "reportedDate": "2026-04-22", "reportedEPS": "1.91", "estimatedEPS": "1.81", "surprise": "0.1", "surp...; {"fiscalDateEnding": "2026-03-31", "reportedDate": "2026-04-22", "reportedEPS": "1.91", "estimatedEPS": "1.81", "surprise": "0.1", "surpr...; {"fiscalDateEnding": "2025-12-31", "reportedDate": "2026-01-28", "reportedEPS": "4.52", "estimatedEPS": "4.29", "surprise": "0.23", "surp...`
- `quarterlyReports`: semantic=`array, object`; observed_at=`income_statement_ibm:$.quarterlyReports; income_statement_ibm:$.quarterlyReports[]; balance_sheet_ibm:$.quarterlyReports; balance_sheet_ibm:$.quarterlyReports[]; cash_flow_ibm:$.quarterlyReports`; examples=`[{"fiscalDateEnding": "2026-03-31", "reportedCurrency": "USD", "grossProfit": "8950000000", "totalRevenue": "15917000000", "costOfRevenue...; {"fiscalDateEnding": "2026-03-31", "reportedCurrency": "USD", "grossProfit": "8950000000", "totalRevenue": "15917000000", "costOfRevenue"...; {"fiscalDateEnding": "2025-12-31", "reportedCurrency": "USD", "grossProfit": "12119000000", "totalRevenue": "19686000000", "costOfRevenue...`
- `record_date`: semantic=`date_yyyy_mm_dd`; observed_at=`dividends_ibm:$.data[].record_date`; examples=`"2026-05-08"; "2026-02-10"; "2025-11-10"`
- `relevance_score`: semantic=`numeric_string`; observed_at=`news_sentiment_aapl_latest:$.feed[].ticker_sentiment[].relevance_score; news_sentiment_aapl_latest:$.feed[].topics[].relevance_score; news_sentiment_technology_latest:$.feed[].ticker_sentiment[].relevance_score; news_sentiment_technology_latest:$.feed[].topics[].relevance_score`; examples=`"1.000000"; "0.606795"; "0.612517"`
- `relevance_score_definition`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.relevance_score_definition; news_sentiment_technology_latest:$.relevance_score_definition`; examples=`"0 < x <= 1, with a higher score indicating higher relevance."`
- `reportDate`: semantic=`date_yyyy_mm_dd`; observed_at=`earnings_calendar_ibm_12month:csv.reportDate`; examples=`"2026-07-22"`
- `reportTime`: semantic=`string`; observed_at=`earnings_ibm:$.quarterlyEarnings[].reportTime`; examples=`"post-market"`
- `reportedCurrency`: semantic=`string`; observed_at=`income_statement_ibm:$.annualReports[].reportedCurrency; income_statement_ibm:$.quarterlyReports[].reportedCurrency; balance_sheet_ibm:$.annualReports[].reportedCurrency; balance_sheet_ibm:$.quarterlyReports[].reportedCurrency; cash_flow_ibm:$.annualReports[].reportedCurrency`; examples=`"USD"`
- `reportedDate`: semantic=`date_yyyy_mm_dd`; observed_at=`earnings_ibm:$.quarterlyEarnings[].reportedDate`; examples=`"2026-04-22"; "2026-01-28"; "2025-10-22"`
- `reportedEPS`: semantic=`numeric_string`; observed_at=`earnings_ibm:$.annualEarnings[].reportedEPS; earnings_ibm:$.quarterlyEarnings[].reportedEPS`; examples=`"1.91"; "11.57"; "10.33"`
- `researchAndDevelopment`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].researchAndDevelopment; income_statement_ibm:$.quarterlyReports[].researchAndDevelopment`; examples=`"8320000000"; "7479000000"; "6631000000"`
- `retainedEarnings`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].retainedEarnings; balance_sheet_ibm:$.quarterlyReports[].retainedEarnings`; examples=`"155648000000"; "151163000000"; "151276000000"`
- `revenue_estimate_analyst_count`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].revenue_estimate_analyst_count`; examples=`"20.00"; "15.00"; "17.00"`
- `revenue_estimate_average`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].revenue_estimate_average`; examples=`"74636094990.00"; "71465024380.00"; "17114782670.00"`
- `revenue_estimate_high`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].revenue_estimate_high`; examples=`"76013674440.00"; "71975000000.00"; "17270000000.00"`
- `revenue_estimate_low`: semantic=`numeric_string`; observed_at=`earnings_estimates_ibm:$.estimates[].revenue_estimate_low`; examples=`"72592041360.00"; "70765466910.00"; "16934077440.00"`
- `security_type`: semantic=`string`; observed_at=`insider_transactions_ibm:$.data[].security_type`; examples=`"Common Stock"; "Promised Fee Share"`
- `sellingGeneralAndAdministrative`: semantic=`numeric_string`; observed_at=`income_statement_ibm:$.annualReports[].sellingGeneralAndAdministrative; income_statement_ibm:$.quarterlyReports[].sellingGeneralAndAdministrative`; examples=`"18285000000"; "16737000000"; "17952000000"`
- `sentiment`: semantic=`numeric_string`; observed_at=`earnings_call_transcript_ibm_2024q1:$.transcript[].sentiment`; examples=`"0.6"; "0.7"; "0.5"`
- `sentiment_score_definition`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.sentiment_score_definition; news_sentiment_technology_latest:$.sentiment_score_definition`; examples=`"x <= -0.35: Bearish; -0.35 < x <= -0.15: Somewhat-Bearish; -0.15 < x < 0.15: Neutral; 0.15 <= x < 0.35: Somewhat_Bullish; x >= 0.35: Bul...`
- `share_price`: semantic=`numeric_string`; observed_at=`insider_transactions_ibm:$.data[].share_price`; examples=`"0.0"; "242.39"`
- `shares`: semantic=`numeric_string`; observed_at=`insider_transactions_ibm:$.data[].shares`; examples=`"400.0"; "377.0"; "403.0"`
- `shares_outstanding_basic`: semantic=`numeric_string`; observed_at=`shares_outstanding_msft:$.data[].shares_outstanding_basic`; examples=`"7445000000"; "7460000000"; "7466000000"`
- `shares_outstanding_diluted`: semantic=`numeric_string`; observed_at=`shares_outstanding_msft:$.data[].shares_outstanding_diluted`; examples=`"7445000000"; "7460000000"; "7466000000"`
- `shortLongTermDebtTotal`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].shortLongTermDebtTotal; balance_sheet_ibm:$.quarterlyReports[].shortLongTermDebtTotal`; examples=`"67154000000"; "58396000000"; "59935000000"`
- `shortTermDebt`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].shortTermDebt; balance_sheet_ibm:$.quarterlyReports[].shortTermDebt`; examples=`"7224000000"; "5857000000"; "7246000000"`
- `shortTermInvestments`: semantic=`numeric_string`; observed_at=`balance_sheet_ibm:$.annualReports[].shortTermInvestments; balance_sheet_ibm:$.quarterlyReports[].shortTermInvestments`; examples=`"830000000"; "644000000"; "373000000"`
- `source`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.feed[].source; news_sentiment_technology_latest:$.feed[].source`; examples=`"Investing.com Canada"; "Benzinga"; "The Globe and Mail"`
- `source_domain`: semantic=`string`; observed_at=`news_sentiment_aapl_latest:$.feed[].source_domain; news_sentiment_technology_latest:$.feed[].source_domain`; examples=`"Investing.com Canada"; "Benzinga"; "The Globe and Mail"`
- Dictionary truncated in Markdown at 200 keys; JSON contains 229 keys.

## 5. Schema Risks

- EARNINGS_ESTIMATES 有 JSON null：$.estimates[].eps_estimate_revision_down_trailing_7_days。
- NEWS_SENTIMENT source_domain 不是 hostname；样本显示其为来源名称而不是 URL hostname。
- NEWS_SENTIMENT 请求 limit=10，但现有 raw 响应实际返回 50 条 feed/items（items=50）。
- LISTING_STATUS delistingDate 是 "null" 字符串，不是 JSON null 或空值。
- LISTING_STATUS 当前默认样本只有 Active；不要把 status 建模成单值常量。
- income_statement_ibm $.annualReports[].comprehensiveIncomeNetOfTax: missing values can appear as literal string "None".
- income_statement_ibm $.annualReports[].depreciation: missing values can appear as literal string "None".
- income_statement_ibm $.annualReports[].interestAndDebtExpense: missing values can appear as literal string "None".
- income_statement_ibm $.annualReports[].investmentIncomeNet: missing values can appear as literal string "None".
- income_statement_ibm $.annualReports[].nonInterestIncome: missing values can appear as literal string "None".
- income_statement_ibm $.annualReports[].otherNonOperatingIncome: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].comprehensiveIncomeNetOfTax: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].depreciation: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].interestAndDebtExpense: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].investmentIncomeNet: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].nonInterestIncome: missing values can appear as literal string "None".
- income_statement_ibm $.quarterlyReports[].otherNonOperatingIncome: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].accumulatedDepreciationAmortizationPPE: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].capitalLeaseObligations: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].currentDebt: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].deferredRevenue: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].investments: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].longTermDebtNoncurrent: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].longTermInvestments: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].otherNonCurrentAssets: missing values can appear as literal string "None".
- balance_sheet_ibm $.annualReports[].treasuryStock: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].accumulatedDepreciationAmortizationPPE: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].currentDebt: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].deferredRevenue: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].investments: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].longTermDebtNoncurrent: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].longTermInvestments: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].otherNonCurrentAssets: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].propertyPlantEquipment: missing values can appear as literal string "None".
- balance_sheet_ibm $.quarterlyReports[].treasuryStock: missing values can appear as literal string "None".
- cash_flow_ibm $.annualReports[].changeInCashAndCashEquivalents: missing values can appear as literal string "None".
- cash_flow_ibm $.annualReports[].changeInExchangeRate: missing values can appear as literal string "None".
- cash_flow_ibm $.annualReports[].changeInOperatingAssets: missing values can appear as literal string "None".
- cash_flow_ibm $.annualReports[].changeInOperatingLiabilities: missing values can appear as literal string "None".
- cash_flow_ibm $.annualReports[].changeInReceivables: missing values can appear as literal string "None".

## 6. Database Implications

- Persist raw response text and parsed records separately so vendor messages do not corrupt typed tables.
- Normalize literal string "None" and empty strings at ingestion boundaries before numeric/date casts.
- Model array children such as feed.ticker_sentiment, feed.topics, annualReports, and quarterlyReports as child tables.
- Keep Alpha Vantage news time_published as raw text unless a separate timezone policy is introduced.
- LISTING_STATUS and EARNINGS_CALENDAR are CSV-shaped and need a CSV ingestion path beside JSON fundamentals.

## 7. Deferred Checks

- None.

## 8. Next Run Queue

- Queue is empty.
