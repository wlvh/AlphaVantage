# Step 0B：Alpha Vantage / SEC 本地跨源 Spike 指导书

## 0. 任务定位

本阶段只在本地 `AlphaVantage` 仓库中运行，不接触 Databricks，不创建生产数据库，也不把 SEC 接入正式产品。

本阶段的目标只有两个：

1. 用真实的 Alpha Vantage 和 SEC 数据压测产品的 canonical metric 模型，确认它不会被 Alpha Vantage 的数据形状锁死；
2. 用一份真实 SEC filing 做一个带精确 evidence span 的法律/监管事项样本，确认未来的 `filing → evidence → finding` 模型能够表达真正的叙事信息。

本阶段完成后，应回答：

```text
1. 同一个 canonical metric 能否容纳 Alpha Vantage 和 SEC 两种观测？
2. 哪些指标可以直接映射，哪些需要组合、按行业区分或标记为不适用？
3. period / dimensions / source metadata 需要保留哪些字段？
4. SEC 的叙事 finding 能否准确回到原始 filing 的具体文本？
5. 正式 Silver schema 在进入 Step 1 前需要做哪些调整？
```

本阶段**不以“所有数值一致”为成功标准**。发现不一致、不可比或不适用，且能解释原因，本身就是有效产出。

---

# 1. 开始前先读这些文件

Codex 开始编码前必须先阅读：

```text
readme.md
AlphaVantage.md
Step 0A.md
scripts/alpha_vantage_verify.py
tests/test_alpha_vantage_verify.py
reports/alpha_vantage_observed_schema.md
```

事实优先级：

```text
1. artifacts/alpha_vantage/raw/ 中的 raw response
2. artifacts/alpha_vantage/schema/ 中的 per-endpoint schema
3. reports/alpha_vantage_observed_schema.json
4. reports/alpha_vantage_observed_schema.md
5. README / 架构文档
```

现有 IBM fixture 已经覆盖：

```text
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

IBM 默认使用已有 fixture，不重复消耗 Alpha Vantage 请求额度。

---

# 2. 不可违反的约束

```text
1. 不导入 pyspark、databricks、delta 或任何 Databricks SDK。
2. 不修改 Step 0A 的 Databricks DDL。
3. 不建立正式 SEC ingestion pipeline。
4. 不让 SEC 财务数字覆盖 Alpha Vantage 财务数字。
5. 不把 API key 写入代码、日志、URL、报告或 Git 历史。
6. 所有网络响应必须先原样保存，再做解析。
7. financial value 使用 Decimal，不使用 float 作为标准类型。
8. semantic_key 不包含 source_system。
9. observation_id 必须包含 source_system 和来源记录信息。
10. 不为了让两边“看起来一致”而静默改变期间、单位或概念。
11. 不要求所有 canonical metric 对所有公司适用。
12. 不修改现有 Alpha Vantage verifier 的行为，除非修改内容与本 spike 无关且有独立测试；本阶段优先写隔离代码。
```

---

# 3. 本地环境与 Secret

用户会单独提供 Alpha Vantage API key。只从环境变量读取：

```bash
export ALPHAVANTAGE_API_KEY='由用户提供'
```

SEC 不需要 API key，但请求必须有可识别的 User-Agent：

```bash
export SEC_USER_AGENT='company-intel-step0b/0.1 your-email@example.com'
```

不得：

```text
创建包含真实 key 的已提交 .env
在 request URL 日志中输出 apikey
把 shell history、截图或错误堆栈中的 key 复制进报告
```

如果需要本地 `.env`，必须加入 `.gitignore`，并只提交 `.env.example`：

```text
ALPHAVANTAGE_API_KEY=
SEC_USER_AGENT=
```

建议使用 Python 3.11+。优先使用标准库；如果 HTML 解析确实需要依赖，可新增仅供 spike 使用的 `requirements-step0b.txt`，但不要引入 Web framework、ORM 或数据库依赖。

---

# 4. Spike 样本

## 4.1 财务对齐样本

固定三家公司：

| 公司 | Symbol | Exchange | CIK | 目的 |
|---|---|---|---|---|
| IBM | IBM | NYSE | `0000051143` | 技术/服务公司，已有 AV fixtures |
| JPMorgan Chase | JPM | NYSE | `0000019617` | 金融公司，故意压测通用财务指标边界 |
| Caterpillar | CAT | NYSE | `0000018230` | 工业/重资产公司，压测库存、债务和 Capex |

本地可读 key：

```text
NYSE:IBM
NYSE:JPM
NYSE:CAT
```

CIK 必须同时满足：

```text
配置值为 10 位数字字符串
Alpha Vantage OVERVIEW.CIK 与配置一致（前导零规范化后）
SEC submissions 返回的主体名称合理匹配
```

任一检查失败，不允许自动按名称模糊匹配；应停止该公司 SEC 对齐并写入报告。

## 4.2 叙事证据样本

优先使用 3M：

```text
Company: 3M Company
Symbol: MMM
CIK: 0000066740
Preferred filing: 最新 10-Q
Fallback: 最新 10-K
```

原因：该公司通常存在较丰富的 Legal Proceedings / Contingencies 披露，适合压测法律事项和 evidence span。

如果最新 10-Q 没有适合的法律事项，可按以下顺序回退：

```text
1. 3M 最新 10-K
2. JPM 最新 10-Q
3. JPM 最新 10-K
```

必须在报告中记录最终用了哪份 filing 以及为何回退。

---

# 5. 要比较的 12 个 canonical metrics

每家公司都必须输出以下 12 个 metric 的记录，即使状态是 `NOT_APPLICABLE`、`MISSING` 或 `AMBIGUOUS`。

| Canonical metric | Alpha Vantage 来源 | SEC 初始候选 concept / 规则 |
|---|---|---|
| `financial.revenue` | `INCOME_STATEMENT.totalRevenue` | `Revenues`、`RevenueFromContractWithCustomerExcludingAssessedTax`、`SalesRevenueNet` 等候选；金融公司允许歧义 |
| `financial.gross_profit` | `INCOME_STATEMENT.grossProfit` | `GrossProfit`；银行通常可能不适用 |
| `financial.operating_income` | `INCOME_STATEMENT.operatingIncome` | `OperatingIncomeLoss`；银行可能缺失或口径不等价 |
| `financial.net_income` | `INCOME_STATEMENT.netIncome` | `NetIncomeLoss`，必要时检查 `ProfitLoss` |
| `balance.total_assets` | `BALANCE_SHEET.totalAssets` | `Assets` |
| `balance.cash_and_equivalents` | `BALANCE_SHEET.cashAndCashEquivalentsAtCarryingValue` | `CashAndCashEquivalentsAtCarryingValue`；其他 cash concept 只能作为显式候选，不能静默替代 |
| `balance.total_liabilities` | `BALANCE_SHEET.totalLiabilities` | `Liabilities` |
| `balance.total_equity` | `BALANCE_SHEET.totalShareholderEquity` | `StockholdersEquity`、`StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| `balance.total_debt` | `BALANCE_SHEET.shortLongTermDebtTotal` | 通常需要组合 current debt、long-term debt、short-term borrowings；必须记录公式 |
| `cashflow.operating_cash_flow` | `CASH_FLOW.operatingCashflow` | `NetCashProvidedByUsedInOperatingActivities` |
| `cashflow.capital_expenditure` | `CASH_FLOW.capitalExpenditures` | `PaymentsToAcquirePropertyPlantAndEquipment` 等候选；保留符号归一化说明 |
| `earnings.diluted_eps` | `EARNINGS.reportedEPS` | `EarningsPerShareDiluted` |

这些 SEC concept 只是搜索起点，不是硬编码真理。Codex 必须实际扫描每家公司 `companyfacts` 中存在的 concepts，并在报告中列出：

```text
候选 concepts
最终选择
选择理由
是否需要组合
是否不适用
```

尤其注意 JPM：

```text
Revenue、Gross Profit、Operating Income、Total Debt 很可能不能直接按普通工业公司口径比较。
不允许为了凑齐 12 个 MATCH 而强行映射。
```

---

# 6. 比较期间

每个公司、每个 metric 必须生成两个 comparison scope：

```text
LATEST_COMMON_ANNUAL
LATEST_COMMON_QUARTER
```

因此财务对齐矩阵的目标行数为：

```text
3 companies × 12 metrics × 2 periods = 72 rows
```

没有可比值时仍保留该行，并给出状态和原因。

## 6.1 Annual 选择规则

Alpha Vantage：

```text
三表使用 annualReports
EPS 使用 annualEarnings，但必须排除已经被证明是季度重复的伪年度记录
```

SEC：

```text
form = 10-K
period end 与 AV fiscalDateEnding 一致
Duration metric 通常应覆盖约一个完整财政年度
Instant metric 使用 period end
同一期间有多个 filing / amendment 时，选择 filed date 最新的 observation，并保留所有候选 accession
```

## 6.2 Quarterly 选择规则

Alpha Vantage：

```text
三表使用 quarterlyReports
EPS 使用 quarterlyEarnings
```

SEC：

```text
form = 10-Q
period end 与 AV fiscalDateEnding 一致
Duration metric 必须优先选择单季度时长，不能把 YTD 值当单季值
如果只能找到 YTD、无法确定单季度值：NOT_COMPARABLE_PERIOD
Instant metric按 quarter end 比较
```

Duration 粗略检查：

```text
单季度通常约 70–110 天
年度通常约 300–400 天
```

这只是候选筛选，不是唯一判据。最终必须记录 SEC fact 的 `start`、`end`、`form`、`filed`、`accn`、`fp`、`fy`。

## 6.3 不得静默推导

Step 0B 默认不从 SEC YTD 自动相减得到单季度值。若 Codex认为必须测试该能力，应：

```text
单独标记 derivation_type = CALCULATED_FROM_YTD
保留两个输入 fact
在原始比较结果中同时保留 NOT_COMPARABLE_PERIOD 行
不得让推导值冒充直接报告值
```

---

# 7. Semantic identity 与 observation identity

必须生成两个不同的 ID。

## 7.1 Semantic key

表示现实中的同一条语义事实，不包含来源：

```text
company_id
canonical_metric_key
comparison period type
period_start
period_end
canonical dimensions
```

建议将 canonical JSON 做 key sorting 后 SHA-256：

```json
{
  "company_id": "本地稳定 ID",
  "metric_key": "financial.revenue",
  "period_type": "QUARTERLY",
  "period_start": "2026-01-01",
  "period_end": "2026-03-31",
  "dimensions": {}
}
```

同一事实的 AV 和 SEC observation 必须产生相同 semantic key。

## 7.2 Observation ID

表示某个来源给出的具体观测，必须包含：

```text
semantic_key
source_system
provider_metric_key / SEC concept
source record reference
accession / source response hash
normalized value
```

因此同一 semantic key 下：

```text
AV observation_id != SEC observation_id
```

本 spike 不要求最终确定未来生产 schema 的所有列，但必须用输出证明这两个身份层次可行。

---

# 8. 网络调用与 raw-first 规则

## 8.1 Alpha Vantage 调用预算

默认：

```text
IBM：复用仓库已有 5 个 fixtures，0 次实时调用
JPM：5 个 endpoints，5 次实时调用
CAT：5 个 endpoints，5 次实时调用
合计：10 次实时 Alpha Vantage 调用
```

只有显式传入 `--refresh-ibm` 才能重新请求 IBM；默认命令不允许刷新 IBM。

请求 endpoints：

```text
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

## 8.2 SEC 调用

每个财务样本：

```text
https://data.sec.gov/submissions/CIK##########.json
https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
```

叙事样本：

```text
先获取 submissions
选择 filing
再下载 filing primary HTML
```

SEC 请求必须携带 `SEC_USER_AGENT`。保守限速为不超过 5 requests/second；对 429 / 503 使用指数退避。

SEC 官方资料：

```text
https://www.sec.gov/search-filings/edgar-application-programming-interfaces
https://www.sec.gov/about/developer-resources
```

## 8.3 Raw-first

每次网络调用顺序必须是：

```text
HTTP response
→ 立刻保存原始 body
→ 保存去密后的 request metadata、status、headers、hash
→ 再开始解析
```

不得先解析成功才保存。

任何 URL 或 metadata 中的 Alpha Vantage key 必须写成：

```text
REDACTED
```

---

# 9. 建议目录结构

在现有仓库中新增：

```text
scripts/step_0b/
├── __init__.py
├── run_step_0b.py
├── av_source.py
├── sec_source.py
├── raw_store.py
├── normalize_av.py
├── select_sec_facts.py
├── compare_metrics.py
├── narrative_evidence.py
└── report_writer.py

spikes/step_0b/
├── README.md
├── config/
│   ├── companies.json
│   └── metrics.json
├── reports/
│   ├── metric_alignment.csv
│   ├── metric_alignment.md
│   ├── discrepancy_report.md
│   ├── schema_decision.md
│   ├── narrative_finding.json
│   ├── narrative_finding.md
│   └── run_summary.json
└── work/
    ├── raw/
    ├── normalized/
    └── manifests/

tests/
├── test_step_0b_av_normalization.py
├── test_step_0b_sec_selection.py
├── test_step_0b_identity.py
├── test_step_0b_comparison.py
└── test_step_0b_evidence.py
```

`spikes/step_0b/work/` 默认加入 `.gitignore`。Raw 文件可能很大，不要求提交 Git；报告、代码、配置和测试需要提交。

不要复制现有 IBM fixtures。通过配置引用：

```text
artifacts/alpha_vantage/raw/demo/001_overview_ibm.txt
artifacts/alpha_vantage/raw/demo/002_income_statement_ibm.txt
artifacts/alpha_vantage/raw/demo/003_balance_sheet_ibm.txt
artifacts/alpha_vantage/raw/demo/004_cash_flow_ibm.txt
artifacts/alpha_vantage/raw/demo/005_earnings_ibm.txt
```

---

# 10. CLI 契约

Codex 可以调整内部模块，但必须提供以下等价命令：

```bash
# 在线抓取缺失的 JPM / CAT Alpha Vantage 数据和全部 SEC 数据
python scripts/step_0b/run_step_0b.py fetch

# 基于已保存 raw 文件离线分析和生成报告
python scripts/step_0b/run_step_0b.py analyze

# fetch + analyze
python scripts/step_0b/run_step_0b.py all

# 完全禁用网络，只验证 raw、输出和不变量
python scripts/step_0b/run_step_0b.py verify --offline
```

可选参数：

```text
--refresh-ibm
--company IBM|JPM|CAT
--force-refetch
--output-dir
```

`analyze` 和 `verify --offline` 运行时不得要求 API key，也不得进行任何网络连接。

---

# 11. AV 解析要求

## 11.1 Vendor response

Alpha Vantage 经常在 HTTP 200 下返回 Information / Note / Error Message。

对 JSON endpoints，只有根结构与 endpoint 预期一致才视为数据：

```text
OVERVIEW：包含 Symbol / Name 等预期字段
INCOME_STATEMENT：包含 annualReports / quarterlyReports
BALANCE_SHEET：包含 annualReports / quarterlyReports
CASH_FLOW：包含 annualReports / quarterlyReports
EARNINGS：包含 annualEarnings / quarterlyEarnings
```

以下根 key 必须视为非数据：

```text
Information
Note
Error Message
```

本 spike 不需要使用 CSV endpoint，不要借机修改现有 CSV 分类器。

## 11.2 Missing 与 Decimal

统一缺失值：

```text
"None"
"none"
"null"
"NULL"
""
"NaN"
"nan"
JSON null
→ None
```

数值使用：

```python
Decimal(str(value))
```

输出 JSON 时 Decimal 转成字符串；CSV 可输出规范 decimal string。

## 11.3 Earnings 伪年度记录

现有 IBM fixture 已证明 `annualEarnings[0]` 与最新季度值重复。

必须：

```text
保留原始 source bucket
识别 fiscal year end
同日同 EPS 的 annual/quarterly 重复标记为 QUARTERLY_DUPLICATE
不允许其进入 annual comparison
```

---

# 12. SEC fact 选择要求

`companyfacts` 中一个 concept 可以包含多个 unit，每个 unit 又有多条 fact。

Codex 必须保留候选层，不得只返回一个裸值。

每个候选至少保留：

```text
taxonomy
concept
unit
value
start
end
form
fy
fp
filed
accn
frame
```

选择逻辑必须输出：

```text
selected candidate
rejected candidates
rejection reason
```

可能的 rejection reason：

```text
WRONG_FORM
WRONG_PERIOD_END
YTD_NOT_QUARTER
WRONG_UNIT
OLDER_AMENDMENT
DIMENSION_OR_SCOPE_UNCLEAR
NOT_EQUIVALENT_CONCEPT
```

对于 composite metric，如 total debt，输出必须包含：

```json
{
  "operation": "sum",
  "components": [
    {"concept": "...", "value": "..."},
    {"concept": "...", "value": "..."}
  ]
}
```

如果无法证明组合口径与 Alpha Vantage `shortLongTermDebtTotal` 等价，状态应是 `COMPOSITE_REQUIRED` 或 `AMBIGUOUS_MAPPING`，而不是强行比较。

---

# 13. 比较状态与容忍度

允许状态：

```text
MATCH
NEAR_MATCH
MISMATCH
MISSING_AV
MISSING_SEC
NOT_APPLICABLE
NOT_COMPARABLE_PERIOD
COMPOSITE_REQUIRED
AMBIGUOUS_MAPPING
IDENTIFIER_MISMATCH
```

建议数值规则：

普通财务数值：

```text
MATCH：relative difference <= 0.1%
NEAR_MATCH：0.1% < relative difference <= 2%
MISMATCH：relative difference > 2%
```

EPS：

```text
MATCH：absolute difference <= 0.01
NEAR_MATCH：0.01 < absolute difference <= 0.05
MISMATCH：absolute difference > 0.05
```

这些阈值只是 spike 分类规则，不是生产质量标准。报告必须同时保存：

```text
absolute_difference
relative_difference
comparison_rule
```

若任一侧口径不等价，不得使用数值阈值，应直接标记不可比或歧义。

---

# 14. 财务对齐矩阵格式

`metric_alignment.csv` 至少包含：

```text
company_key
company_name
cik
metric_key
comparison_scope
semantic_key
av_observation_id
sec_observation_id
av_provider_field
av_period_start
av_period_end
av_value
sec_candidate_concepts
sec_selected_concept
sec_formula
sec_period_start
sec_period_end
sec_value
sec_unit
sec_form
sec_filed
sec_accession
absolute_difference
relative_difference
comparison_status
applicability
rationale
```

必须有完整 72 行。不得因为缺失或不适用而删除行。

---

# 15. 叙事 evidence Spike

## 15.1 目标

从一份真实 SEC filing 中输出一个结构化法律/监管事项，并证明 evidence 是原文的精确子串。

## 15.2 处理步骤

```text
1. 根据 submissions 找到目标 filing。
2. 下载并保存 primary HTML。
3. 将 HTML 转成保留顺序的 normalized text。
4. 搜索 Legal Proceedings / Contingencies / Litigation / Regulatory Matters 等候选章节。
5. 保存候选文本块。
6. 人工或确定性地选择一个 matter；本阶段不要求通用自动抽取器。
7. 写入 narrative_finding.json。
8. 验证 evidence_text == normalized_text[start:end]。
```

可以手工审阅并填充最终 finding；关键是 schema 和证据绑定，而不是自动化率。

## 15.3 Finding 格式

```json
{
  "finding_id": "稳定 ID",
  "company_key": "NYSE:MMM",
  "cik": "0000066740",
  "filing_accession": "...",
  "form_type": "10-Q",
  "filing_date": "YYYY-MM-DD",
  "section_title": "...",
  "finding_type": "LEGAL_MATTER",
  "title": "...",
  "summary": "...",
  "amount_text": null,
  "amount_value": null,
  "currency": null,
  "status_text": "...",
  "affected_entity_text": "...",
  "evidence_text": "原文精确片段",
  "evidence_start": 12345,
  "evidence_end": 13000,
  "source_url": "SEC filing URL",
  "extraction_method": "MANUAL_REVIEWED_SPIKE",
  "validation_status": "VERIFIED"
}
```

如果原文没有量化金额，金额字段可以为 null，但报告必须明确“未披露”，不能生成金额。

若金额字段非 null，则 `amount_text` 必须逐字出现在 `evidence_text` 中。

---

# 16. 必须生成的报告

## `metric_alignment.csv`

72 行机器可读比较结果。

## `metric_alignment.md`

按公司和指标展示的可读表格。

## `discrepancy_report.md`

至少回答：

```text
哪些指标三家公司都能直接对齐？
哪些指标需要多个 SEC concepts 组合？
哪些指标对金融公司不适用或语义不同？
哪些差异来自 period / YTD / amendment？
哪些差异可能来自 AV 的不透明标准化？
```

## `schema_decision.md`

至少给出：

```text
推荐 semantic key 字段
推荐 observation identity 字段
是否需要 period_start
如何表示 dimensions / scope
是否需要 source mapping 层
哪些 metric 应有 applicability rule
正式 Silver schema 在 Step 1 前需要修改什么
```

## `narrative_finding.json` / `.md`

结构化 finding 和人读说明。

## `run_summary.json`

至少包含：

```text
run_id
started_at / finished_at
online / offline
AV live call count
SEC call count
使用的 fixture / raw file hashes
公司和 CIK
输出文件及 hash
错误和 warnings
API key redaction check result
```

---

# 17. 测试要求

继续使用仓库当前的 `unittest` 风格，不要求引入 pytest。

至少增加：

## AV normalization

```text
None / null / 空字符串 / NaN → None
numeric string → Decimal
vendor JSON 不被当成财务数据
IBM annualEarnings 季度重复被排除
```

## SEC fact selection

使用小型本地 synthetic fixtures 测试：

```text
10-K annual fact 选择
10-Q 单季度和 YTD 区分
同期间 amendment 选择
错误单位拒绝
composite metric 保留组件
```

## Identity

```text
同一事实 AV / SEC semantic_key 相同
AV / SEC observation_id 不同
source 不进入 semantic key
```

## Comparison

```text
MATCH / NEAR_MATCH / MISMATCH
NOT_APPLICABLE
NOT_COMPARABLE_PERIOD
AMBIGUOUS_MAPPING
```

## Evidence

```text
evidence_text == normalized_text[start:end]
金额非空时 amount_text 必须在 evidence 中
不存在 evidence 时不得 VERIFIED
```

现有测试也必须继续通过：

```bash
python -m unittest discover -s tests -p 'test*.py'
```

---

# 18. 运行顺序

推荐实际执行：

```bash
# 1. 先运行原有测试
python -m unittest discover -s tests -p 'test*.py'

# 2. 设置环境变量
export ALPHAVANTAGE_API_KEY='...'
export SEC_USER_AGENT='company-intel-step0b/0.1 your-email@example.com'

# 3. 在线抓取
python scripts/step_0b/run_step_0b.py fetch

# 4. 立即检查 run manifest 中 AV call count 默认是否为 10

# 5. 离线分析
python scripts/step_0b/run_step_0b.py analyze

# 6. 离线验真
python scripts/step_0b/run_step_0b.py verify --offline

# 7. 再运行全部测试
python -m unittest discover -s tests -p 'test*.py'
```

如在线抓取中途失败：

```text
已保存的成功 raw 不得删除
重跑默认复用已成功的 raw
只有 --force-refetch 才重新请求
```

---

# 19. Definition of Done

Step 0B 只有同时满足以下条件才完成：

```text
[ ] 未接触 Databricks，未引入相关依赖
[ ] API key 未进入代码、日志、报告或 Git 历史
[ ] IBM 复用现有 fixture，默认 AV 实时调用不超过 10 次
[ ] 所有网络结果 raw-first 保存
[ ] 在线完成 JPM / CAT 五端点抓取
[ ] 在线完成三家公司 submissions / companyfacts 抓取
[ ] 完成一个真实 SEC legal/regulatory finding 和精确 evidence span
[ ] metric_alignment.csv 恰有 72 条业务行
[ ] 每一行都有 comparison status
[ ] 非 MATCH 行有 rationale
[ ] AV / SEC 相同事实的 semantic_key 相同
[ ] AV / SEC observation_id 不同
[ ] discrepancy_report.md 完整
[ ] schema_decision.md 对正式 Silver schema 给出明确建议
[ ] analyze 和 verify 可以完全离线重跑
[ ] 全部 unit tests 通过
[ ] Git diff 中没有 raw 大文件和 secret
```

完成后停止，不要继续把 SEC 财务数据接入正式产品。下一步由用户依据验收结果决定是否调整正式 `metric_observation` schema。
