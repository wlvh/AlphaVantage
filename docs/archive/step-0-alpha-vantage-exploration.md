# Alpha Vantage 基本面 + 新闻情绪数据库项目交接文档

## 文档目的

本项目目标是为一个小股票池构建本地数据库，数据源为 Alpha Vantage free API。数据库覆盖两类信息：

1. 公司基本面：公司画像、估值快照、财报三表、EPS、分红、内部交易、股本、盈利预期、拆股、上市状态、财报日历、财报电话会逐字稿。
2. 新闻与情绪：新闻文章、文章主题、文章对各 ticker 的相关性与情绪分值。

当前阶段已经完成 **Alpha Vantage endpoint/schema 验证**。下一阶段不再验证 endpoint 是否存在，而是进入 **数据库 schema 与 ingestion harness** 的实现。

---

# 1. 当前项目状态

## 1.1 验证阶段结论

当前 schema verification 阶段已经完成。

核心结论：

```text
15 / 15 schema scopes usable
deferred checks = 0
next_run_queue = []
```

当前不应继续消耗 Alpha Vantage API 额度去确认 endpoint 是否存在，也不应重复验证已经保存 raw response 的 endpoint。

## 1.2 API 调用与安全状态

验证阶段使用过：

```text
demo calls: 15
real calls: 2
```

两次真实 key 调用均用于 `NEWS_SENTIMENT`，原因是 demo key 对 NEWS_SENTIMENT 返回供应商提示，无法获得可用 schema。

最近一次修复运行是本地 no-API reparse：

```text
network_calls_made = 0
api_key_used = false
usable_schema_count = 15
```

未发现明文 Alpha Vantage API key 泄露。日志和报告中 API key 应保持 redacted。

项目运行预算按 free API 的 **25 requests/day** 处理。工程实现中应设置更保守的软上限，例如每日最多 20 次，保留 5 次人工排错缓冲。

---

# 2. 已验证 endpoint / schema scope

下面 15 个 schema scope 已经获得 raw response 和 schema artifact。

| # | Scope | 标的 / 参数 | 返回格式 | 状态 |
|---:|---|---|---|---|
| 1 | `OVERVIEW` | IBM | JSON | usable |
| 2 | `INCOME_STATEMENT` | IBM | JSON | usable |
| 3 | `BALANCE_SHEET` | IBM | JSON | usable |
| 4 | `CASH_FLOW` | IBM | JSON | usable |
| 5 | `EARNINGS` | IBM | JSON | usable |
| 6 | `DIVIDENDS` | IBM | JSON | usable |
| 7 | `INSIDER_TRANSACTIONS` | IBM | JSON | usable |
| 8 | `SHARES_OUTSTANDING` | MSFT | JSON | usable |
| 9 | `EARNINGS_ESTIMATES` | IBM | JSON | usable |
| 10 | `SPLITS` | IBM | JSON | usable |
| 11 | `NEWS_SENTIMENT` | `tickers=AAPL` | JSON | usable |
| 12 | `NEWS_SENTIMENT` | `topics=technology` | JSON | usable |
| 13 | `EARNINGS_CALL_TRANSCRIPT` | IBM 2024Q1 | JSON | usable |
| 14 | `LISTING_STATUS` | default | CSV | usable |
| 15 | `EARNINGS_CALENDAR` | IBM 12month | CSV | usable |

`NEWS_SENTIMENT` 有两个 schema scope，因为 ticker 查询和 topic 查询是两种不同的生产使用模式。

---

# 3. 数据事实与建库规则

本节是下一阶段建库与 ETL 的事实基础。

## 3.1 raw response 是最高事实源

事实优先级如下：

```text
1. artifacts/alpha_vantage/raw/ 里的原始响应
2. artifacts/alpha_vantage/schema/*.json 的 per-endpoint schema
3. reports/alpha_vantage_observed_schema.json 的聚合 schema
4. reports/alpha_vantage_observed_schema.md 的人读摘要
5. 本交接文档
```

监督 Codex 或做技术评审时，应优先用 raw response 核对报告结论，不要只看 Markdown report。

## 3.2 缺失值规则

Alpha Vantage 的缺失值不是单一形式。ETL 必须统一处理：

| 来源 | 缺失值形式 | 入库规则 |
|---|---|---|
| 财报三表 | 字符串 `"None"` | SQL NULL |
| 多数 JSON 数值字段 | 空字符串 `""` 或字符串数字 | 空字符串转 SQL NULL，字符串数字转 Decimal/NUMERIC |
| `EARNINGS_ESTIMATES` | 真 JSON `null` | SQL NULL |
| CSV endpoint | 字符串 `"null"` | 对 nullable date/numeric/text 字段按 SQL NULL 处理 |
| 其他异常空值 | `"NULL"`, `"NaN"`, `"nan"` | SQL NULL |

推荐 normalization 规则：

```python
MISSING_STRINGS = {"", "None", "none", "NULL", "null", "NaN", "nan"}

def normalize_missing(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip() in MISSING_STRINGS:
        return None
    return value
```

数值字段建议用 `Decimal`，不要用 `float` 作为入库前标准类型。

## 3.3 不要用 report 里的 None 清单决定 NOT NULL

`reports/alpha_vantage_observed_schema.md` 中的 `"None"` 字段清单只能作为样本提示，不能作为数据库约束依据。

原因：

```text
1. schema extractor 对数组只检查有限样本。
2. report 的 schema_risks 有显示数量截断。
3. 单个 ticker 的空值分布不能泛化到所有公司。
4. 字段是否为空取决于 field × company × period × source。
```

建表规则：

```text
所有 Alpha Vantage 财报三表和估算类数值字段都必须 nullable。
不要根据 observed None 清单给数值字段添加 NOT NULL。
```

## 3.4 财报三表结构

以下 endpoint 一次返回 annual 与 quarterly 两个数组：

```text
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
```

天然主键：

```text
(symbol, fiscal_date_ending, period_type)
```

其中：

```text
period_type ∈ {"annual", "quarterly"}
```

推荐第一版数据库使用长表结构：

```text
financial_statement_report
financial_statement_line_item
```

原因：

```text
1. 不同公司和行业字段稀疏。
2. 不同会计期间可能缺项。
3. 新增字段不需要 ALTER TABLE。
4. raw_json 可被长期保留并重新解析。
```

如果后续分析需要宽表，可以用 view 或 materialized view 从长表派生。

## 3.5 精确字段名注意事项

已经验证过的字段名：

```text
costofGoodsAndServicesSold
otherNonCurrentAssets
```

注意：

```text
costofGoodsAndServicesSold:
  "of" 小写，无空格。

otherNonCurrentAssets:
  IBM 样本中是正常拼写，不是 otherNonCurrrentAssets。
```

ETL parser 可以兼容历史拼写风险，但 typed schema 里应使用规范字段名。

## 3.6 OVERVIEW 是估值快照，不是历史序列

`OVERVIEW` 混合了静态字段与动态估值字段。

静态字段示例：

```text
Symbol
Name
CIK
Exchange
Currency
Country
Sector
Industry
FiscalYearEnd
```

动态字段示例：

```text
MarketCapitalization
PERatio
ForwardPE
AnalystTargetPrice
52WeekHigh
52WeekLow
SharesOutstanding
PercentInstitutions
```

建库规则：

```text
company:
  存相对静态公司信息。

company_overview_snapshot:
  按 snapshot_date 存动态估值快照。
```

`OVERVIEW` 自身不提供历史，历史估值序列必须由本地每日快照累积。

## 3.7 EARNINGS 与 PIT

`fiscalDateEnding` 是财报期末，不等于市场当时可看到数据的日期。

`EARNINGS.quarterlyEarnings[].reportedDate` 是实际公布日，可作为 point-in-time 对齐锚点。

建库规则：

```text
每张 typed table 都应有 ingested_at。
涉及回测或历史信号时，不能只用 fiscalDateEnding 当作可得日期。
```

## 3.8 NEWS_SENTIMENT 事实

NEWS_SENTIMENT 必须按多对多结构建模。

文章本体：

```text
news_article
```

文章与 ticker 的联结表：

```text
news_article_ticker_sentiment
```

文章与 topic 的联结表：

```text
news_article_topic
```

作者建议单独拆表：

```text
news_article_author
```

已验证事实：

```text
overall_sentiment_score:
  JSON number

ticker_sentiment[].ticker_sentiment_score:
  numeric string

ticker_sentiment[].relevance_score:
  numeric string

topics[].relevance_score:
  numeric string

source_domain:
  不是 URL hostname，更像来源显示名，常与 source 相同。

time_published:
  原始格式类似 YYYYMMDDTHHMMSS，入库应保留 raw 字符串，并单独解析时间字段。
```

建库规则：

```text
source:
  保存 API 原始 source。

source_domain_raw:
  保存 API 原始 source_domain。

url_hostname:
  从 url 自行解析出的 hostname。
```

不要把 `source_domain` 当作真实域名。

## 3.9 NEWS_SENTIMENT 查询语义与额度策略

已验证生产注意事项：

```text
tickers=AAPL,MSFT 不是 OR 查询。
它表示同时提到 AAPL 与 MSFT 的文章。
```

因此不能用多 ticker 参数来节省额度覆盖多个公司。

省额度策略：

```text
1. 对单一重点公司使用 tickers=<symbol>。
2. 对集中行业股票池使用 topics=<topic>。
3. 取回 topic 新闻后，在客户端根据 ticker_sentiment 数组过滤 watchlist。
```

本次观察到：

```text
请求 limit=10，但两个 NEWS response 实际返回 50 条 feed。
```

工程规则：

```text
不要假设 requested limit 等于实际 feed length。
永远按实际 feed 数组长度处理。
```

## 3.10 LISTING_STATUS 事实

已验证：

```text
返回格式:
  CSV

columns:
  symbol
  name
  exchange
  assetType
  ipoDate
  delistingDate
  status
```

默认调用样本：

```text
status 全部为 Active
delistingDate 为字符串 "null"
```

建库规则：

```text
listing_status 表必须能容纳 Active 与 Delisted。
delistingDate 要按 nullable date 处理。
```

无幸存者偏差股票池需要单独 ingestion delisted universe。默认 active-only 样本不能代表退市股票池已经完成。

## 3.11 EARNINGS_ESTIMATES 事实

已验证：

```text
返回 JSON。
存在真正 JSON null。
字段包含 EPS estimates、revenue estimates、analyst count、estimate revision。
```

建库规则：

```text
EARNINGS_ESTIMATES parser 必须同时支持 numeric string 与 JSON null。
```

## 3.12 EARNINGS_CALL_TRANSCRIPT 事实

已验证结构：

```text
symbol
quarter
transcript[]
```

transcript item 包括：

```text
speaker
title
content
sentiment
```

建库规则：

```text
earnings_call_transcript:
  存 call 级元数据。

earnings_call_transcript_line:
  存 speaker/title/content/sentiment。
```

此 endpoint 是情绪分析的重要原始文本来源。

---

# 4. 已修复问题与仍需修复问题

## 4.1 已修复：LISTING_STATUS 被误判为 vendor_information

历史问题：

```text
LISTING_STATUS 是合法 CSV。
CSV 正文里有公司名包含 Information。
旧分类器对整段文本裸搜 "information"。
导致整张 CSV 被误判为 vendor_information。
```

当前状态：

```text
LISTING_STATUS 已正确分类为 data_csv。
listing_status_demo.json 已生成。
next_run_queue 已清空。
```

## 4.2 仍需修复：CSV endpoint 的 vendor/rate-limit 边界

现有分类器仍需加强，才能作为正式 ingestion gateway 使用。

风险场景：

```text
CSV endpoint 在限流或供应商提示时，可能返回类似 CSV 的短文本或带表头的异常响应。
如果分类器只看表格形状，可能把供应商提示误判成 data_csv。
```

修复要求：

```text
1. 不允许使用单词 information/note 的裸子串匹配判断大型 CSV。
2. 允许使用多词 vendor phrase 检测短文本或异常响应。
3. vendor phrase 检测应覆盖：
   - thank you for using alpha vantage
   - standard api rate limit
   - call frequency
   - please visit
   - premium
   - api call frequency
   - our standard api rate limit
4. 真正大型 CSV 中出现 Information 或 Note 公司名时，必须仍判 data_csv。
5. 异常短响应或供应商提示必须在写 typed table 前被拦截。
```

需要新增 regression tests。

---

# 5. 下一阶段 Codex 工作指令

下一阶段目标：

```text
基于已有 raw response 和 observed schema，
实现本地数据库 schema 与 offline ingestion harness。
```

这不是 endpoint verification 任务。

## 5.1 硬约束

Codex 必须遵守：

```text
1. 不调用 Alpha Vantage。
2. 不发任何网络请求。
3. 不读取或使用 ALPHAVANTAGE_API_KEY。
4. 不修改已有 raw response。
5. 不继续验证 endpoint 是否存在。
6. 不根据 sampled None 清单添加 NOT NULL。
7. 所有财报/估算类数值字段必须 nullable。
8. 先写 raw layer，再写 typed tables。
9. 所有 parser 必须使用 artifacts/alpha_vantage/raw/ 下的 fixtures 离线测试。
```

## 5.2 交付物

Codex 应交付：

```text
docs/alpha_vantage_ingestion_design.md
sql/001_alpha_vantage_schema.sql
src/alpha_vantage_ingest/__init__.py
src/alpha_vantage_ingest/normalize.py
src/alpha_vantage_ingest/url_utils.py
src/alpha_vantage_ingest/classify.py
src/alpha_vantage_ingest/parsers.py
src/alpha_vantage_ingest/loaders.py
src/alpha_vantage_ingest/models.py
tests/test_alpha_vantage_normalize.py
tests/test_alpha_vantage_classify.py
tests/test_alpha_vantage_parsers.py
tests/test_alpha_vantage_offline_ingestion.py
reports/alpha_vantage_ingestion_harness_report.md
```

## 5.3 数据库 schema 要求

必须包含 raw layer：

```text
av_raw_response
```

推荐字段：

```text
id
endpoint
scope
symbol
request_params_json
response_format
classification
raw_text
raw_json
raw_hash
fetched_at
ingested_at
source_path
```

必须包含 typed tables：

```text
company
company_overview_snapshot

financial_statement_report
financial_statement_line_item

earnings
dividends
insider_transactions
shares_outstanding
earnings_estimates
splits

earnings_calendar
listing_status

earnings_call_transcript
earnings_call_transcript_line

news_article
news_article_author
news_article_topic
news_article_ticker_sentiment
```

建议不在第一版使用财报三表宽表作为主存储。若需要，可以额外生成 analytical views。

## 5.4 Parser 要求

必须实现：

```text
normalize_missing(value)
to_decimal(value)
to_int(value)
to_date(value)
parse_av_news_time_raw(value)
parse_url_hostname(url)
classify_response(raw_text, content_type)
parse_json_endpoint(endpoint, raw_json)
parse_csv_endpoint(endpoint, raw_text)
```

必须支持：

```text
"None" → None
"null" → None
"" → None
JSON null → None
numeric string → Decimal
JSON number → Decimal
CSV date string → date
malformed date → None + warning
```

## 5.5 Offline ingestion tests

测试必须使用已有 raw fixtures，不得联网。

测试至少覆盖：

```text
1. 财报三表 "None" 字符串转 SQL NULL。
2. EARNINGS_ESTIMATES JSON null 转 SQL NULL。
3. LISTING_STATUS CSV "null" 转 SQL NULL。
4. NEWS source_domain_raw 与 url_hostname 分离。
5. NEWS ticker_sentiment 多对多解析。
6. NEWS topic 多对多解析。
7. NEWS limit 不作为 feed 长度断言。
8. CSV 中公司名包含 Information 时仍分类为 data_csv。
9. 短文本 vendor/rate-limit message 不分类为 data_csv。
10. 所有 15 个 raw scopes 都能离线解析成 typed records。
```

验收命令：

```bash
python -m pytest -q
```

## 5.6 产出报告要求

`reports/alpha_vantage_ingestion_harness_report.md` 必须包含：

```text
1. 没有网络调用的声明。
2. 没有 API key 使用的声明。
3. 已解析 raw fixture 数量。
4. 每个 endpoint 解析出的 typed records 数量。
5. rejected/vendor/error response 数量。
6. 数据库表清单。
7. 每张表的主键 / unique key。
8. NULL normalization 策略。
9. NEWS 多对多落表说明。
10. LISTING_STATUS active/delisted 后续生产策略。
11. 生产 backfill 前仍需用户提供 target ticker list。
```

---

# 6. 后续真实回填策略

真实回填必须等以下条件满足：

```text
1. offline ingestion harness 通过测试。
2. 数据库 schema 已评审。
3. 用户提供 target ticker list。
4. daily quota guard 已实现。
5. raw-first 写入已实现。
```

回填原则：

```text
每一次真实 API 调用都必须立即写入 av_raw_response。
不得做一次性丢弃验证调用。
```

回填建议顺序：

```text
1. LISTING_STATUS active universe。
2. LISTING_STATUS delisted universe。
3. target tickers 的 OVERVIEW。
4. target tickers 的三张财报。
5. target tickers 的 EARNINGS。
6. target tickers 的 DIVIDENDS / SPLITS / SHARES_OUTSTANDING。
7. target tickers 的 EARNINGS_ESTIMATES。
8. NEWS_SENTIMENT:
   - 重点 ticker 用 tickers=<symbol>
   - 行业池用 topics=<topic> 后本地过滤
9. EARNINGS_CALL_TRANSCRIPT:
   - 先按最近季度或重点事件回填，不要无界回填。
```

预算原则：

```text
daily hard limit = 25
recommended soft limit = 20
reserve = 5
```

脚本必须在达到 soft limit 后停止并写 next_run_queue，不得继续尝试。

---

# 7. 文件夹说明

## 7.1 顶层文件

| 路径 | 说明 | 重点 |
|---|---|---|
| `alpha_vantage_codex_single_goal_no_claude.txt` | schema verification 阶段给 Codex 的执行规范 | 了解验证阶段被要求做什么。下一阶段不再直接复用为 ingestion 指令。 |
| `alpha_vantage_next_run_queue_corrected.json` | 历史修正辅助文件 | 当前权威队列是 `reports/alpha_vantage_next_run_queue.json`。 |

忽略：

```text
__MACOSX/
.DS_Store
.pytest_cache/
__pycache__/
```

## 7.2 `reports/`

| 路径 | 说明 | 重点 |
|---|---|---|
| `reports/alpha_vantage_observed_schema.md` | 人读版 schema verification 报告 | 读 endpoint 状态和 high-level risks；不要把 None 清单当完整约束。 |
| `reports/alpha_vantage_observed_schema.json` | 机器读版聚合 schema | 下一阶段 Codex 应主要读取此文件。 |
| `reports/alpha_vantage_next_run_queue.json` | 未完成队列 | 当前应为 `[]`。 |

## 7.3 `artifacts/alpha_vantage/raw/`

这是最高事实源。

### `artifacts/alpha_vantage/raw/demo/`

| 文件 | Endpoint / scope | 重点 |
|---|---|---|
| `001_overview_ibm.txt` | `OVERVIEW IBM` | 公司画像与估值快照。 |
| `002_income_statement_ibm.txt` | `INCOME_STATEMENT IBM` | 利润表 annual/quarterly；numeric string；`"None"`。 |
| `003_balance_sheet_ibm.txt` | `BALANCE_SHEET IBM` | 资产负债表；`otherNonCurrentAssets`。 |
| `004_cash_flow_ibm.txt` | `CASH_FLOW IBM` | 现金流；正负号；`"None"`。 |
| `005_earnings_ibm.txt` | `EARNINGS IBM` | EPS、surprise、reportedDate、reportTime。 |
| `006_dividends_ibm.txt` | `DIVIDENDS IBM` | 分红日期和金额。 |
| `007_insider_transactions_ibm.txt` | `INSIDER_TRANSACTIONS IBM` | 内部交易；无天然主键。 |
| `008_shares_outstanding_msft.txt` | `SHARES_OUTSTANDING MSFT` | basic/diluted shares outstanding。 |
| `009_earnings_estimates_ibm.txt` | `EARNINGS_ESTIMATES IBM` | 前瞻估算；JSON null。 |
| `010_splits_ibm.txt` | `SPLITS IBM` | 拆股事件。 |
| `011_news_sentiment_aapl_latest.txt` | demo NEWS ticker response | demo 返回 vendor message；不作为 NEWS schema 事实源。 |
| `012_news_sentiment_technology_latest.txt` | demo NEWS topic response | demo 返回 vendor message；不作为 NEWS schema 事实源。 |
| `013_earnings_call_transcript_ibm_2024q1.txt` | `EARNINGS_CALL_TRANSCRIPT IBM 2024Q1` | speaker/title/content/sentiment。 |
| `014_listing_status.txt` | `LISTING_STATUS` | 13,909 rows；CSV schema；active-only 样本。 |
| `015_earnings_calendar_ibm_12month.txt` | `EARNINGS_CALENDAR IBM 12month` | CSV schema；reportDate/fiscalDateEnding/timeOfTheDay。 |
| `*_headers.json` | HTTP headers | 审计用，通常不进入 typed tables。 |

### `artifacts/alpha_vantage/raw/real/`

| 文件 | Endpoint / scope | 重点 |
|---|---|---|
| `016_news_sentiment_aapl_latest.txt` | `NEWS_SENTIMENT tickers=AAPL` | 真实 NEWS ticker schema；feed 实际 50。 |
| `017_news_sentiment_technology_latest.txt` | `NEWS_SENTIMENT topics=technology` | topic 路线验证；可用于省额度策略。 |
| `*_headers.json` | HTTP headers | 审计用。 |

## 7.4 `artifacts/alpha_vantage/schema/`

每个文件是对应 endpoint 的 schema artifact，适合程序读取。

| 文件 | 对应 scope |
|---|---|
| `overview_ibm_demo.json` | `OVERVIEW IBM` |
| `income_statement_ibm_demo.json` | `INCOME_STATEMENT IBM` |
| `balance_sheet_ibm_demo.json` | `BALANCE_SHEET IBM` |
| `cash_flow_ibm_demo.json` | `CASH_FLOW IBM` |
| `earnings_ibm_demo.json` | `EARNINGS IBM` |
| `dividends_ibm_demo.json` | `DIVIDENDS IBM` |
| `insider_transactions_ibm_demo.json` | `INSIDER_TRANSACTIONS IBM` |
| `shares_outstanding_msft_demo.json` | `SHARES_OUTSTANDING MSFT` |
| `earnings_estimates_ibm_demo.json` | `EARNINGS_ESTIMATES IBM` |
| `splits_ibm_demo.json` | `SPLITS IBM` |
| `earnings_call_transcript_ibm_2024q1_demo.json` | `EARNINGS_CALL_TRANSCRIPT IBM 2024Q1` |
| `listing_status_demo.json` | `LISTING_STATUS` |
| `earnings_calendar_ibm_12month_demo.json` | `EARNINGS_CALENDAR IBM 12month` |
| `news_sentiment_aapl_latest_real.json` | `NEWS_SENTIMENT tickers=AAPL` |
| `news_sentiment_technology_latest_real.json` | `NEWS_SENTIMENT topics=technology` |

## 7.5 `artifacts/alpha_vantage/` 状态与日志文件

| 文件 | 说明 | 重点 |
|---|---|---|
| `call_log.jsonl` | 原始网络调用日志 | 记录最初 15 demo + 2 real 调用。历史记录中可能保留旧分类，不代表最终状态。 |
| `state.json` | 原始网络运行状态 | 记录原始 run，不代表最近一次 no-API 修复状态。 |
| `reparse_log.jsonl` | 本地 no-API 重解析日志 | 当前修复状态的日志。 |
| `reparse_state.json` | 本地 no-API 重解析状态 | 当前修复状态的权威文件。应显示 network_calls_made=0。 |

## 7.6 `scripts/`

| 文件 | 说明 | 重点 |
|---|---|---|
| `scripts/alpha_vantage_verify.py` | schema verification harness | 可复用 classification 与 schema extraction 思路，但必须修好 CSV vendor/rate-limit 边界后才能作为 production ingestion gateway。 |

重点看：

```text
parse_response
csv_has_usable_shape
vendor_classification_from_text
schema_risks
```

## 7.7 `tests/`

如果归档中包含 tests 目录，重点看：

```text
tests/test_alpha_vantage_verify.py
```

当前测试覆盖过核心 bug：

```text
CSV 中公司名包含 Information 时仍应分类为 data_csv。
```

下一阶段需要新增更多 tests，覆盖 vendor/rate-limit 边界与各 endpoint parser。

---

# 8. 监督下一阶段 Codex 的检查清单

监督者应逐项检查：

```text
[ ] Codex 没有联网。
[ ] Codex 没有读取或输出 API key。
[ ] Codex 没有调用 Alpha Vantage。
[ ] Codex 没有修改 raw fixtures。
[ ] SQL schema 中有 av_raw_response。
[ ] 财报/估算类数值字段均 nullable。
[ ] normalize_missing 同时处理 "None" / JSON null / "" / "null"。
[ ] NEWS 被拆成 article / author / topic / ticker_sentiment。
[ ] source_domain_raw 与 url_hostname 分开。
[ ] CSV endpoint 有独立 parser。
[ ] vendor/rate-limit response 被拦截，不写 typed tables。
[ ] 所有 15 个 raw scopes 都有 offline parser 测试。
[ ] pytest 通过。
[ ] ingestion report 说明 typed record counts 和 rejected counts。
```

如果以上任意一项不满足，不应进入真实 API 回填。

---

# 9. 术语表

| 术语 | 含义 |
|---|---|
| raw response | Alpha Vantage 返回的原始文本或 JSON，是最高事实源。 |
| schema artifact | 从 raw response 中抽取的字段名、类型、样例、路径信息。 |
| schema scope | 一个 endpoint 或同 endpoint 的一种查询模式，例如 `NEWS_SENTIMENT tickers=AAPL` 与 `NEWS_SENTIMENT topics=technology` 是两个 scope。 |
| raw layer | 数据库中保存原始响应的层，例如 `av_raw_response`。 |
| typed table | 解析后按业务语义落表的结构化表。 |
| PIT | point-in-time，历史某一时点实际可见的信息状态。 |
| snapshot | 对当下动态字段定期保存，形成自建历史序列。 |
| ingestion harness | 从 raw response 到 typed table 的解析、清洗、写入程序。 |
| vendor message | API 返回的供应商提示、错误、限流、premium 提示等非数据响应。 |
| watchlist | 用户实际要覆盖的 ticker 列表。 |

---

# 10. 最短交接摘要

```text
Alpha Vantage endpoint/schema verification 已完成。已保存 15 个 schema scope 的 raw response 与 schema artifact；最终状态为 15/15 usable，next_run_queue=[]，最近一次修复无新增 API 调用。不要继续花 API 额度验证 endpoint 是否存在。下一阶段应离线实现数据库 schema 与 ingestion harness。建库时所有财报/估算类数值字段必须 nullable，并统一处理 "None"、JSON null、空字符串和 CSV "null"。NEWS 必须多对多建模；source_domain 不可当 hostname；LISTING_STATUS 默认样本 active-only，后续生产回填还需覆盖 delisted universe。
```
