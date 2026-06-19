# 最终路线

> **SEC 先参与设计，但不先主导开发；Alpha Vantage 先主导产品，但不允许主导领域模型。**

```text
设计阶段：
用少量 SEC 数据压测数据模型，确认模型不会被 Alpha Vantage 锁死。

第一版产品：
主要使用 Alpha Vantage，快速完成 Databricks → Backend → Frontend 全链路。

后续扩展：
优先接 SEC 独有的 filing、事件、法律、治理、风险因素和原文证据。

暂不做：
用 SEC 财务数字替换 Alpha Vantage 财务数字。
```

Alpha Vantage 当前已经提供公司概览、损益表、资产负债表、现金流、Earnings、上市状态和 earnings-call transcript 等接口；你的归档也已经验证了其中多个真实响应结构。

SEC 则提供无 API key 的 submissions 和 XBRL API；但 Company Facts 只聚合非自定义 taxonomy、并且适用于整个申报主体的事实，公司扩展标签、分部和复杂披露仍需要解析具体 filing。因此，SEC 财务标准化是另一类工程，不应该拖慢第一版。

---

# 一、最终产品边界

## 第一版主要数据源：Alpha Vantage

第一版正式生产接入：

```text
LISTING_STATUS
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

第二批 Alpha Vantage 数据：

```text
EARNINGS_CALL_TRANSCRIPT
NEWS_SENTIMENT
EARNINGS_ESTIMATES
DIVIDENDS
SPLITS
SHARES_OUTSTANDING
INSIDER_TRANSACTIONS
```

## SEC 第一阶段只负责其独有信息

正式产品中的 SEC 初期范围：

```text
Filing Metadata
- 最近的 10-K / 10-Q / 8-K / DEF 14A
- filing date
- accession number
- form type
- report date
- 原始 filing 链接

Event Signals
- 8-K 重大事件
- 高管和董事变动
- 审计师变动
- 并购、重大合同和减值事件

Narrative / Evidence
- Risk Factors
- Legal Proceedings
- Cybersecurity disclosures
- Governance disclosures
- 精确原文证据
```

初期不把 SEC 财务数据正式写入产品指标：

```text
不使用 SEC Revenue 替换 AV Revenue
不使用 SEC Net Income 替换 AV Net Income
不在 Gold 层做 AV / SEC 数值竞争
```

SEC 财务只在前置 spike 中用于验证数据模型。

---

# 二、整体架构

```text
                  Alpha Vantage
                        │
                        ▼
              Bronze Source Artifacts
                        │
                        ▼
             Silver Canonical Metrics
                        │
                        ├──────────────┐
                        │              │
                        ▼              ▼
                 Derived Metrics   AV Transcript
                 Financial Rules   / News Features
                        │              │
                        └──────┬───────┘
                               ▼
                      Gold Dashboard Snapshot
                               │
                               ▼
                        Backend BFF API
                               │
                               ▼
                         React Frontend


随后增加：

                       SEC EDGAR
                           │
                           ▼
              Filing / Event / Evidence Tables
                           │
                           ▼
                   Gold Dashboard Snapshot
```

核心特点：

```text
Alpha Vantage 和 SEC 不直接连接前端。

前端只读取 Gold Snapshot。

公司类型只在 Gold Builder 中发挥作用。

Silver 不按行业拆表。

SEC 独有数据作为新的内容维度加入，
而不是强行塞进 financial metric 表。
```

Databricks 官方推荐 Bronze、Silver、Gold 分层，使用 Unity Catalog managed tables 保存结构化数据，并使用 managed volumes 保存原始和非结构化内容。([docs.databricks.com][3])

---

# 三、Databricks 数据库应当第一时间建立

不要先写完所有 Python parser，再临时决定怎么落库。数据库和代码应该从第一周就一起发展。

建议环境：

```text
company_intel_dev
company_intel_staging
company_intel_prod
```

每个 Catalog 包含：

```text
bronze
silver
gold
```

并建立原始文件 Volume：

```text
/Volumes/company_intel_dev/bronze/source_artifacts/
```

## 第一批立即创建的表

```text
bronze.source_artifact
silver.company
silver.source_identifier
silver.metric_observation
silver.earnings_event
gold.company_dashboard_snapshot
```

## SEC 正式接入时再增加

```text
silver.filing
silver.evidence_span
silver.filing_finding
```

## AV transcript / news 接入时增加

```text
silver.content_item
silver.content_company_signal
```

---

# 四、核心数据模型

## 1. `bronze.source_artifact`

不要建成 `av_raw_response`，而应该从第一天就是来源中立的：

```sql
CREATE TABLE bronze.source_artifact (
    artifact_id          STRING NOT NULL,

    source_system        STRING NOT NULL,
    artifact_type        STRING NOT NULL,

    company_id           STRING,
    provider_key         STRING,
    request_params_json  STRING,

    storage_uri          STRING NOT NULL,
    content_hash         STRING NOT NULL,
    content_type         STRING,

    http_status          INT,
    classification       STRING NOT NULL,

    source_published_at  TIMESTAMP,
    fetched_at           TIMESTAMP NOT NULL,

    parser_version       STRING,
    metadata_json        STRING
)
USING DELTA;
```

### `source_system`

```text
ALPHA_VANTAGE
SEC_EDGAR
```

### `artifact_type`

```text
API_JSON
API_CSV
FILING_HTML
FILING_XBRL
EXHIBIT
```

### 为什么原始内容放 Volume

Alpha Vantage JSON 和 CSV 体积较小，但 SEC filing HTML、Inline XBRL 和 exhibits 可能更大。

因此：

```text
Volume：
保存完整原始文件

source_artifact：
保存地址、哈希、时间和分类结果
```

原则：

```text
Raw append-only
同一个 provider key 内容改变 → 新 artifact
永远不覆盖原始内容
```

---

## 2. `silver.company`

当前不做复杂实体解析，但仍使用内部 `company_id`。

```sql
CREATE TABLE silver.company (
    company_id           STRING NOT NULL,
    company_key          STRING NOT NULL,

    symbol               STRING NOT NULL,
    exchange             STRING NOT NULL,
    name                 STRING NOT NULL,

    canonical_asset_type STRING,
    listing_status       STRING,
    ipo_date             DATE,

    country              STRING,
    currency             STRING,

    sector_raw           STRING,
    industry_raw         STRING,
    archetype            STRING,

    description          STRING,
    official_site        STRING,
    fiscal_year_end      STRING,
    latest_quarter       DATE,

    created_at           TIMESTAMP NOT NULL,
    updated_at           TIMESTAMP NOT NULL
)
USING DELTA;
```

### `company_key`

保持可读：

```text
NYSE:IBM
NASDAQ:MSFT
NYSE:JPM
```

### `company_id`

使用生成的 UUID。

不要使用 ticker 作为事实表的永久外键：

```text
company_id：事实表 FK
company_key：人类可读的查询 key
```

当前不解决 ticker 变更、双重上市或复杂证券关系，但不会让所有历史事实直接绑死在 ticker 字符串上。

---

## 3. `silver.source_identifier`

这是一个非常轻量的映射，不是实体解析系统。

```sql
CREATE TABLE silver.source_identifier (
    company_id          STRING NOT NULL,
    source_system       STRING NOT NULL,
    identifier_type     STRING NOT NULL,
    identifier_value    STRING NOT NULL,

    verification_status STRING NOT NULL,
    observed_at         TIMESTAMP NOT NULL
)
USING DELTA;
```

示例：

```text
company_id = cmp_001
ALPHA_VANTAGE / SYMBOL / IBM

company_id = cmp_001
SEC_EDGAR / CIK / 0000051143
```

CIK 可以直接从 Alpha Vantage `OVERVIEW.CIK` 获得。

规则：

```text
CIK 合法且唯一：
→ 允许启用 SEC capability

CIK 缺失或冲突：
→ 该公司暂不启用 SEC
→ 不做名称模糊匹配
```

这符合“先简化、不做实体解析”的要求。

---

## 4. `silver.metric_observation`

这里只保存标准化后的标量指标：

```text
OVERVIEW 数值
Income Statement 数值
Balance Sheet 数值
Cash Flow 数值
派生指标
```

```sql
CREATE TABLE silver.metric_observation (
    observation_id         STRING NOT NULL,
    semantic_key           STRING NOT NULL,

    company_id             STRING NOT NULL,

    metric_key             STRING NOT NULL,
    provider_metric_key    STRING NOT NULL,

    source_system          STRING NOT NULL,
    source_artifact_id     STRING NOT NULL,

    period_type            STRING NOT NULL,
    period_start           DATE,
    period_end             DATE,

    dimensions_json        STRING NOT NULL,

    value_decimal          DECIMAL(38, 10),
    value_text             STRING,

    unit                   STRING,
    currency               STRING,

    source_published_at    TIMESTAMP,
    fetched_at             TIMESTAMP NOT NULL,

    derivation_type        STRING NOT NULL,
    input_observation_ids  ARRAY<STRING>,

    quality_status         STRING NOT NULL
)
USING DELTA;
```

## Semantic key 不包含来源

```text
semantic_key =
company_id
+ metric_key
+ period_type
+ period_start
+ period_end
+ canonical dimensions
```

例如：

```text
IBM
financial.revenue
QUARTERLY
2025-01-01
2025-03-31
{}
```

未来 AV 和 SEC 的观测可以具有相同的 semantic key：

```text
semantic_key: ABC123
    ├── Alpha Vantage observation
    ├── SEC original filing observation
    └── SEC amended filing observation
```

来源属于 observation，不属于现实事实的语义身份。

## `dimensions_json`

AV 第一版通常是：

```json
{}
```

未来 SEC 可以变成：

```json
{
  "scope": "CONSOLIDATED",
  "segment": "CLOUD"
}
```

这样不需要现在预先焊死几十个 SEC 专用列。

---

## 5. `silver.earnings_event`

Earnings 不要拆成多条 metric observation。

```sql
CREATE TABLE silver.earnings_event (
    earnings_id            STRING NOT NULL,
    company_id             STRING NOT NULL,

    source_system          STRING NOT NULL,
    source_artifact_id     STRING NOT NULL,

    source_bucket          STRING NOT NULL,
    canonical_period_type  STRING NOT NULL,

    fiscal_date_ending     DATE NOT NULL,
    reported_date          DATE,
    report_time            STRING,

    reported_eps           DECIMAL(38, 10),
    estimated_eps          DECIMAL(38, 10),
    surprise               DECIMAL(38, 10),
    surprise_percentage    DECIMAL(38, 10),

    exclude_from_trend     BOOLEAN NOT NULL,

    fetched_at             TIMESTAMP NOT NULL,
    quality_status         STRING NOT NULL
)
USING DELTA;
```

根据现有归档，IBM 的 `annualEarnings` 第一条和季度数组中的最新值重复，并不是真正完整年度值。

因此：

```text
annual bucket 中日期不是 fiscal year end
且与 quarterly bucket 同日同值
→ QUARTERLY_DUPLICATE
→ exclude_from_trend = true
```

---

## 6. `silver.filing`

SEC 正式接入后创建：

```sql
CREATE TABLE silver.filing (
    filing_id            STRING NOT NULL,
    company_id           STRING NOT NULL,

    cik                  STRING NOT NULL,
    accession_number     STRING NOT NULL,

    form_type            STRING NOT NULL,
    filing_date          DATE,
    report_date          DATE,
    accepted_at          TIMESTAMP,

    primary_document     STRING,
    filing_items         ARRAY<STRING>,

    source_artifact_id   STRING NOT NULL
)
USING DELTA;
```

它负责：

```text
Recent Activity
10-K / 10-Q / 8-K feed
原始 filing 跳转
```

SEC submissions API 本身包含 CIK 对应的 filing 历史、公司名称、ticker、交易所和申报元数据；API 无需 key，并随 filings 实时更新。([美国证券交易委员会][2])

---

## 7. `silver.evidence_span`

```sql
CREATE TABLE silver.evidence_span (
    evidence_id          STRING NOT NULL,

    filing_id            STRING NOT NULL,
    source_artifact_id   STRING NOT NULL,

    section_key          STRING,
    item_key             STRING,

    character_start      BIGINT,
    character_end        BIGINT,
    html_anchor          STRING,

    excerpt              STRING NOT NULL,
    excerpt_hash         STRING NOT NULL,

    extraction_version   STRING NOT NULL
)
USING DELTA;
```

证据至少要能回答：

```text
来自哪份 filing？
哪个 section / item？
原文是什么？
原文在文档中的位置在哪里？
```

---

## 8. `silver.filing_finding`

不要为法律、风险、治理分别建十几张表，第一版使用 typed finding：

```sql
CREATE TABLE silver.filing_finding (
    finding_id           STRING NOT NULL,

    company_id           STRING NOT NULL,
    filing_id            STRING NOT NULL,

    finding_type         STRING NOT NULL,
    event_date           DATE,

    title                STRING NOT NULL,
    summary              STRING,
    structured_payload   STRING,

    evidence_ids         ARRAY<STRING>,

    extraction_method    STRING NOT NULL,
    confidence           DOUBLE,
    validation_status    STRING NOT NULL,

    generated_at         TIMESTAMP NOT NULL
)
USING DELTA;
```

`finding_type`：

```text
EXECUTIVE_CHANGE
AUDITOR_CHANGE
MATERIAL_AGREEMENT
LEGAL_MATTER
RISK_FACTOR_CHANGE
CYBER_DISCLOSURE
GOVERNANCE_DISCLOSURE
```

---

## 9. `gold.company_dashboard_snapshot`

Frontend 主要只读取这一张表。

```sql
CREATE TABLE gold.company_dashboard_snapshot (
    snapshot_id          STRING NOT NULL,
    company_id           STRING NOT NULL,

    archetype            STRING NOT NULL,

    capabilities_json    STRING NOT NULL,
    payload_json         STRING NOT NULL,

    schema_version       STRING NOT NULL,
    config_version       STRING NOT NULL,

    source_manifest_json STRING NOT NULL,

    data_as_of           TIMESTAMP NOT NULL,
    generated_at         TIMESTAMP NOT NULL,

    status               STRING NOT NULL
)
USING DELTA;
```

每次刷新：

```text
插入新 Snapshot
不覆盖旧 Snapshot
```

`source_manifest_json` 保存这次页面使用了哪些：

```text
metric observation
earnings event
filing
filing finding
evidence span
source artifact
```

---

# 五、配置文件

公司类型和指标规则放在 Git 中，而不是数据库。

```text
config/
  metric_catalog.yaml
  archetype_rules.yaml
  company_profiles.yaml
  signal_rules.yaml
  sec_finding_schemas.yaml
  sec_concept_spike_map.yaml
```

## `metric_catalog.yaml`

定义：

```text
canonical metric
AV provider field
单位
期间
显示格式
派生公式
```

示例：

```yaml
metrics:
  financial.revenue:
    label: Revenue
    unit: currency
    format: compact_currency
    sources:
      - source_system: ALPHA_VANTAGE
        function: INCOME_STATEMENT
        field: totalRevenue

  profitability.gross_margin:
    label: Gross Margin
    unit: ratio
    format: percent_1
    formula:
      operation: divide
      numerator: financial.gross_profit
      denominator: financial.revenue

  cashflow.free_cash_flow:
    label: Free Cash Flow
    unit: currency
    format: compact_currency
    formula:
      operation: subtract
      left: cashflow.operating_cash_flow
      right:
        metric: cashflow.capital_expenditure
        normalization: absolute
```

## `archetype_rules.yaml`

```yaml
industry_overrides:
  "BANKS - REGIONAL": FINANCIAL
  "SOFTWARE - APPLICATION": TECHNOLOGY
  "BIOTECHNOLOGY": HEALTHCARE
  "REIT - INDUSTRIAL": REAL_ESTATE

sector_map:
  TECHNOLOGY: TECHNOLOGY
  FINANCE: FINANCIAL
  HEALTHCARE: HEALTHCARE
  REAL ESTATE: REAL_ESTATE
  CONSUMER CYCLICAL: CONSUMER
  CONSUMER DEFENSIVE: CONSUMER
  INDUSTRIALS: ASSET_HEAVY
  ENERGY: ASSET_HEAVY
  MATERIALS: ASSET_HEAVY
  UTILITIES: ASSET_HEAVY

fallback: GENERAL
```

## `company_profiles.yaml`

只决定：

```text
哪些 section
指标顺序
组件类型
```

不负责数据计算。

---

# 六、分阶段实施方案

# Step 0A：立即建立 Databricks 基础

这一步和 SEC spike 可以并行。

## 需要做什么

1. 创建三个环境 Catalog。
2. 创建 `bronze`、`silver`、`gold` schemas。
3. 创建 raw Volume。
4. 创建以下表：

   * `bronze.source_artifact`
   * `silver.company`
   * `silver.source_identifier`
5. 创建 SQL migrations 目录。
6. 建立 Backend 使用的 Databricks service principal。
7. 建立一个最小 SQL Warehouse。

Backend 推荐通过 Databricks SQL Connector 查询 Gold，使用参数化 SQL和 OAuth M2M 的 service principal，而不是把 token 放进浏览器或使用个人凭据。Databricks SQL Connector 目前支持原生参数化查询以及 OAuth M2M。([docs.databricks.com][4])

## 完成标准

```text
Codex 能运行 migration
Raw fixture 能写进 Volume
source_artifact 中能看到 raw 元数据
Backend service principal 能执行 SELECT
```

---

# Step 0B：在冻结 Metric Schema 前做跨源 Spike

这不是生产 SEC pipeline。

## 选择三家公司

推荐：

```text
IBM：Technology / Services
JPMorgan：Financial
Caterpillar：Asset Heavy / Industrial
```

银行必须保留，因为它最容易暴露通用 canonical metric 的边界：

```text
Gross Profit 可能不适用
Operating Income 口径不同
Revenue 定义不同
Debt 组成不同
```

## 比较 12 个指标

```text
Revenue
Gross Profit
Operating Income
Net Income
Total Assets
Cash
Total Liabilities
Total Equity
Total Debt
Operating Cash Flow
Capital Expenditure
Diluted EPS
```

## 获取的数据

Alpha Vantage：

```text
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

SEC：

```text
Submissions
Company Facts
最近一份 10-K
最近一份 10-Q
```

## 输出一张映射矩阵

```text
canonical metric
AV field
SEC candidate concepts
最终选择的 concept
是否需要计算
期间语义
是否适用于该公司类型
两边是否一致
差异原因
```

重点不是追求全部一致，而是回答：

```text
一个 canonical metric 是否对所有行业都成立？
哪些指标只适用于部分 Archetype？
哪些 SEC 指标需要多个 concepts 组合？
dimensions_json 是否足够？
period_start 是否必须保存？
```

## 同时做一个困难的 SEC 叙事实验

不要只测试最简单的 8-K 高管变动。

选择一份有实际法律或或有事项披露的 10-Q：

```text
找到 Legal Proceedings 或 Contingencies
抽取一个法律事项
抽取：
- 事项名称
- 金额
- 当前状态
- 可能影响
- 原文 evidence span
```

目标不是建立通用 parser，而是确认：

```text
filing
evidence_span
filing_finding
```

这三个模型足够表达真正困难的叙事内容。

## 完成标准

```text
形成 metric mapping matrix
形成 discrepancy report
形成 schema ADR
形成一个带精确 evidence 的 legal finding
```

ADR 是 Architecture Decision Record，即记录为什么最终选择某种 schema 的短文档。

---

# Step 1：修复 Alpha Vantage 离线解析层

基于现有[Alpha Vantage 探索归档](sandbox:/mnt/data/归档%284%29.zip)实施。

## 必须先修的分类器问题

现有代码：

```text
先判断 CSV shape
后判断 vendor message
```

而未知 CSV 的 fallback 太宽松，可能把带逗号和换行的供应商提示误判为数据。

应该改为：

```text
JSON：
先解析 JSON
再按 endpoint 校验预期结构

CSV：
只允许已知 CSV endpoint
必须严格匹配 endpoint-specific header
必须验证每行结构
没有 generic CSV fallback

其他响应：
再识别 rate limit / premium / information / error
```

## 实现六个 typed parser

```text
LISTING_STATUS
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

## Missing normalization

统一：

```text
"None"
"null"
"NULL"
""
"NaN"
JSON null
→ None / SQL NULL
```

财务数字使用 `Decimal`。

## Alpha Vantage 特殊规则

必须实现：

```text
costOfRevenue 和 costofGoodsAndServicesSold
→ first_non_null
→ 不相加

annualEarnings 中的季度重复值
→ exclude_from_trend

LISTING_STATUS.Stock
和 OVERVIEW.Common Stock
→ canonical_asset_type = EQUITY
```

## 完成标准

```text
所有保存的 fixture 都能安全分类
vendor response 不进入 Silver
六个核心 parser 全部有测试
重复 ingestion 不产生重复结果
```

---

# Step 2：完成 Alpha Vantage Core Pipeline

## Pipeline 顺序

```text
LISTING_STATUS
    ↓
company universe

用户选择公司
    ↓
OVERVIEW
    ↓
company + source_identifier + archetype

INCOME / BALANCE / CASH FLOW
    ↓
metric_observation

EARNINGS
    ↓
earnings_event

derived metrics
    ↓
signals

profile + capability
    ↓
dashboard snapshot
```

## 第一版派生指标

控制在约 20 个：

```text
Revenue YoY Growth
Net Income YoY Growth
Gross Margin
Operating Margin
Net Margin
R&D / Revenue
Debt / Equity
Debt / Assets
Cash / Debt
Asset Growth
Inventory Growth
Free Cash Flow
FCF Margin
OCF / Net Income
Capex / OCF
EPS Surprise
Consecutive EPS Beat / Miss
```

## 完成标准

```text
IBM 可以完全离线生成 Snapshot
JPM 和 CAT 可以使用同一 pipeline
银行缺少 Gross Margin 时不会显示 0
不同 Archetype 使用不同指标顺序
Silver schema 完全相同
```

---

# Step 3：Backend 和 Frontend

## Backend API

第一版：

```http
GET /v1/companies/search?q=ibm

GET /v1/companies/{companyId}/dashboard

POST /v1/companies/{companyId}/refresh

GET /v1/refresh/{runId}
```

SEC 接入后增加：

```http
GET /v1/evidence/{evidenceId}

GET /v1/companies/{companyId}/filings
```

## Dashboard 逻辑

```text
新鲜 Snapshot
→ 返回 200

存在旧 Snapshot
→ 返回旧数据
→ 后台触发 refresh

没有 Snapshot
→ 返回 202 BUILDING
```

## Frontend 通用组件

```text
metric_grid
trend_chart
earnings_table
content_feed
filing_feed
finding_cards
insight_cards
question_list
evidence_drawer
```

前端不能包含：

```javascript
if (company.archetype === "FINANCIAL") {
  renderFinancialPage();
}
```

而是：

```javascript
for (const section of dashboard.sections) {
  renderSection(section);
}
```

## 完成标准

```text
同一个 React 页面渲染所有 Archetype
Frontend 不出现 Alpha Vantage 字段名
Frontend 不计算 YoY、Margin 或 FCF
Frontend 不知道数据来自 AV 还是 SEC
```

---

# Step 4：Alpha Vantage 行为和前瞻信息

由于数据源优先 Alpha Vantage，完成 Core 后先继续利用 AV 已经提供的独有能力。

## 第一批

```text
EARNINGS_CALL_TRANSCRIPT
NEWS_SENTIMENT
```

新增：

```text
silver.content_item
silver.content_company_signal
```

可以计算：

```text
Management sentiment
Analyst Q&A sentiment
关键词频次变化
首次出现的风险词
季度间措辞变化
Ticker-weighted news sentiment
```

Transcript API 当前提供指定季度的逐轮发言，并带 turn-level sentiment。([Alpha Vantage][1])

## 第二批

```text
EARNINGS_ESTIMATES
DIVIDENDS
SPLITS
SHARES_OUTSTANDING
INSIDER_TRANSACTIONS
```

## 完成标准

```text
Behavioral Insights 不依赖 SEC
Transcript 保持 sequence order
News 使用 ticker-level relevance/sentiment
Insider 不因 share_price=0 计算错误交易金额
```

---

# Step 5：SEC Filing Metadata

这一步是 SEC 正式生产接入的起点，但仍不使用 SEC 财务数字。

## 需要做什么

1. 从 `source_identifier` 获取 CIK。
2. 调用 SEC Submissions。
3. 写入 raw artifact。
4. 标准化到 `silver.filing`。
5. 只保留产品需要的表单：

   * 10-K
   * 10-Q
   * 8-K
   * DEF 14A
6. 在 Dashboard 增加 Recent Filings / Recent Activity。

## 完成标准

```text
公司页面能显示最近 filing
每个 filing 可打开原始文档
没有 CIK 的公司继续正常使用 AV 页面
SEC 失败不会影响 AV Dashboard
```

---

# Step 6：SEC 独有的事件和证据

建议按难度和价值逐步接入。

## 第一批：8-K 事件

```text
Item 5.02：高管和董事变动
Auditor change
Material agreement
Acquisition / disposition
Impairment
Cyber incident
```

## 第二批：Risk Factors

```text
提取 10-K Item 1A
比较前后两期
识别新增、删除和显著改变的风险段落
```

## 第三批：Legal

```text
Legal Proceedings
Contingencies
诉讼、调查、和解和准备金
```

## 第四批：Governance

```text
DEF 14A
董事会结构
委员会
高管薪酬和激励
股东治理事项
```

## 抽取流程

```text
先确定 section
    ↓
切分 evidence spans
    ↓
规则 / LLM 提取 JSON
    ↓
验证数字和实体是否出现在原文
    ↓
生成 filing finding
    ↓
进入 Gold Snapshot
```

LLM 不直接面对整份 filing。

## Validation status

```text
PROVISIONAL
VERIFIED
REJECTED
```

没有 evidence span 的 finding 不允许出现在正式 Dashboard。

---

# Step 7：Insight 和 Broker Questions

## 第一阶段：规则生成

```text
Financial metrics
+ Earnings
+ Transcript features
+ SEC findings
        ↓
Signals
```

示例：

```text
Revenue growth deceleration
Margin compression
Free cash flow deterioration
Debt rising faster than revenue
Consecutive EPS misses
New legal proceeding
Executive departure
New risk factor
Negative management tone shift
```

## 第二阶段：LLM 综合

LLM 输入必须是：

```json
{
  "companyArchetype": "TECHNOLOGY",
  "metrics": [],
  "signals": [],
  "filingFindings": [],
  "evidenceIds": []
}
```

LLM 只负责：

```text
总结
去重
优先级
自然语言问题
```

不得创造新数字或无证据事实。

---

# Step 8：SEC 财务仅在出现明确需求后再做

触发条件：

```text
需要审计 AV 数字
需要 SEC custom KPI
需要 segment financials
AV 某些字段质量明显不足
用户明确要求 filing-level 财务证据
```

这时才正式增加：

```text
SEC XBRL raw facts
SEC concept mapping
Amendment / restatement
Source preference
Conflict detection
```

来源选择按 metric 配置：

```yaml
financial.revenue:
  preferred_sources:
    - SEC
    - ALPHA_VANTAGE

valuation.pe_ttm:
  preferred_sources:
    - ALPHA_VANTAGE
```

不是简单规定：

```text
SEC 永远优先
```

---

# 七、给 Codex 的项目背景

以下内容应直接放进仓库的：

```text
docs/architecture.md
```

## Project Goal

构建上市公司情报 Dashboard：

```text
Alpha Vantage 是通用公司和财务数据主源。

SEC 只提供 Alpha Vantage 不具备的 filing、
法律、治理、风险因素、8-K 事件和证据。

前端通过 Gold Snapshot 获取 server-driven 页面。
```

## Current Verified Alpha Vantage Facts

现有归档已验证 15 个 schema scope。

V1 typed ingestion 只实现：

```text
LISTING_STATUS
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

已知风险：

```text
缺失值有多种表达
财务数字是字符串
Earnings annual bucket 存在季度重复
未知 CSV fallback 不安全
costOfRevenue 有别名字段
Stock 和 Common Stock 词表不同
```

## Architecture Invariants

Codex 不得违反：

```text
1. 所有源数据先写 Bronze。

2. Vendor / rate-limit message 不得进入 Silver。

3. semantic_key 不含 source_system。

4. observation 必须包含 source_system。

5. Silver 使用 canonical metric key，
   不把 Alpha Vantage 字段名暴露给前端。

6. 公司类型不改变 Silver schema。

7. 只有 Gold Builder 读取 company profile 配置。

8. Backend 和 Frontend 不实现行业判断。

9. Frontend 只读取 Gold Snapshot。

10. SEC 初期不得覆盖 AV 财务指标。

11. SEC finding 没有 evidence 不得发布。

12. 所有财务数字使用 Decimal，不使用 float。
```

## Repository Layout

```text
src/
  connectors/
    alphavantage/
      client.py
      classifier.py
      parsers/
        listing_status.py
        overview.py
        income_statement.py
        balance_sheet.py
        cash_flow.py
        earnings.py

    sec/
      client.py
      submissions.py
      filing_fetcher.py
      section_parser.py
      finding_extractors/

  domain/
    metrics.py
    earnings.py
    filings.py
    findings.py
    snapshots.py

  pipelines/
    ingest_av_core.py
    build_metrics.py
    build_dashboard.py
    ingest_sec_filings.py
    extract_sec_findings.py

  quality/
    response_validation.py
    metric_validation.py
    evidence_validation.py

  api/
    companies.py
    dashboards.py
    refresh.py
    evidence.py

config/
  metric_catalog.yaml
  archetype_rules.yaml
  company_profiles.yaml
  signal_rules.yaml
  sec_finding_schemas.yaml

sql/
  migrations/
    001_create_schemas.sql
    002_create_source_artifact.sql
    003_create_company.sql
    004_create_metric_observation.sql
    005_create_earnings.sql
    006_create_dashboard_snapshot.sql
    007_create_sec_tables.sql

tests/
  fixtures/
    alphavantage/
    sec/
  unit/
  integration/
  snapshot/

spikes/
  av_sec_metric_alignment/
  sec_legal_evidence/
```

## Definition of Done

每个 parser 或 pipeline PR 必须包含：

```text
Raw fixture
Parser unit test
Missing-value test
Malformed-response test
Idempotency test
Expected Silver rows
Data-quality result
```

每个 Gold Snapshot 变更必须包含：

```text
JSON schema validation
Frontend component compatibility test
Snapshot regression test
```

---

# 八、实际开始顺序

第一批 Codex tickets 应按这个顺序建立：

```text
Ticket 1
创建 Databricks Catalog、schemas、Volume 和 migration framework。

Ticket 2
创建 source_artifact、company、source_identifier。

Ticket 3
将现有 Alpha Vantage raw fixtures 复制到测试目录。

Ticket 4
重写 response classifier，删除 unknown CSV fallback。

Ticket 5
实现统一 missing / Decimal normalization。

Ticket 6
实现六个 Core endpoint parsers。

Ticket 7
运行 3 公司 × 12 metric 的 AV / SEC spike。

Ticket 8
根据 spike 结果冻结 metric_observation schema。

Ticket 9
创建 earnings_event 和 dashboard_snapshot。

Ticket 10
实现 Archetype、Capability 和 Profile Builder。

Ticket 11
实现 Backend Dashboard API。

Ticket 12
实现 server-driven React 页面。

Ticket 13
接入 AV transcript / news。

Ticket 14
接入 SEC filing metadata。

Ticket 15
实现 SEC evidence 和第一类 filing finding。
```

这里最关键的执行顺序是：

```text
Databricks Raw Foundation
        ↓
Parser Correctness
        ↓
SEC Spike
        ↓
Canonical Schema Freeze
        ↓
AV Product
        ↓
SEC Unique Content
```

而不是：

```text
先写 UI
→ 再补数据库
→ 再发现模型被 AV 锁死
```

最终形态是：

> **Alpha Vantage 提供广度、速度和通用财务；SEC 提供 filings、事件、风险、治理、法律与可验证证据；Databricks 负责统一计算和页面快照；Backend 提供稳定契约；Frontend 不感知公司类型或数据来源。**
