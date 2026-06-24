# Public Company Intelligence Dashboard

> 面向保险 Broker 的上市公司情报 Dashboard。
>
> 当前状态更新时间：2026-06-23

## 1. 项目背景

保险 Broker 在评估上市公司客户、准备续保或承保沟通时，通常需要同时理解公司的基本资料、财务趋势、盈利表现、重大事件、风险披露、治理变化和原始证据。

这些信息分散在市场数据供应商、公司公告和 SEC filing 中，数据结构、时间口径和可信度也不一致。本项目的目标是建立一条可治理、可追溯的数据链路，把不同来源的数据整理成稳定的公司 Dashboard，并通过 Backend API 提供给通用 Frontend。

第一版产品优先证明完整链路：

```text
Source → Bronze Raw → Silver Canonical Data → Gold Snapshot → Backend → Frontend
```

核心数据源战略是：

> **SEC 先参与设计，但不先主导开发；Alpha Vantage 先主导产品，但不允许主导领域模型。**

具体含义：

- Alpha Vantage 是 V1 公司目录、Company Overview、财务报表和 Earnings 的主要来源；
- SEC 从一开始参与 schema 验证，避免模型被单一供应商字段锁定；
- SEC 初期不覆盖 Alpha Vantage 财务数据；
- SEC 后续优先提供 filing metadata、8-K events、Risk Factors、Legal Proceedings、Governance、Cyber disclosures 和原文 evidence。

## 2. 开发环境约束

项目横跨外网开发环境和内网 Databricks 环境：

- 外网可以使用 Codex，加速设计、代码生成、单元测试、fixture 验证和部署包生成；
- 内网不能使用 Codex，Databricks 中的 SQL 和 Notebook 需要人工录入或从允许的 Git 工作流同步；
- 因此，外网交付必须尽量模块化、可测试，并同时生成少量、可审核、可重复执行的 Databricks 文件；
- 内网不应临时设计 schema，也不应维护一套脱离 Git 的代码分支；
- 所有正式 DDL 必须有 Git migration，所有生产凭证必须通过 Secret Scope 管理。

## 3. 当前进度总览

| 阶段 | 状态 | 当前结果 |
|---|---|---|
| Step 0：Alpha Vantage endpoint / schema 探索 | 已完成 | 已归档和检查核心及后续 endpoint 的真实响应结构，确认 V1 数据源范围并识别 response classification、missing value、Decimal 和 endpoint-specific parsing 等要求。 |
| Step 0B：AV / SEC 跨源 spike | 已完成 | 已对 IBM、JPM、CAT 的 12 个 canonical metrics 做年度和季度对照，并完成一个带 SEC 原文 evidence 的法律事项样本。 |
| Step 0A：Databricks 基础方案设计 | 已完成 | 已根据 Step 0B 结果更新平台方案；PR #1 已合并。方案明确不在 Bootstrap 阶段创建 `metric_observation`。 |
| Step 0A：Databricks 内网实施与验收 | 待完成 | 需要在 Databricks dev 环境实际创建 Catalog、Schemas、Volume、基础表、身份、Secret、Warehouse、权限和 Smoke Test Job。 |
| Step 1/2：Alpha Vantage Canonical Core | 待完成 | 计划把 Canonical Metric Foundation 与 AV Core Ingestion 合并为一个交付里程碑，但保留先冻结 schema contract、再写 Silver 的验收闸门。 |
| Step 3 及以后 | 待完成 | Gold Snapshot、Backend、Frontend、AV 内容数据、SEC 独有信息、Signals/LLM 和生产化。 |

## 4. 已完成工作

### 4.1 Step 0：Alpha Vantage 探索

已完成 Alpha Vantage endpoint 和 schema 探索，并保存真实或 demo raw artifacts。

详细记录见 [`docs/archive/step-0-alpha-vantage-exploration.md`](docs/archive/step-0-alpha-vantage-exploration.md)。该文档保留了早期 15 个 endpoint/schema scope 的验证结果，以及 missing value、NEWS_SENTIMENT、Transcript、LISTING_STATUS、调用额度和原始 artifact 等探索细节。它属于 **Step 0 历史事实与交接记录**，不再作为当前数据库 schema 或实施路线的最终依据；当前架构以本 README、`AlphaVantage.md`、`Step 0A.md` 和 Step 0B schema decision 为准。

第一版核心 endpoint 已确定为：

```text
LISTING_STATUS
OVERVIEW
INCOME_STATEMENT
BALANCE_SHEET
CASH_FLOW
EARNINGS
```

后续优先利用的 Alpha Vantage 能力包括 Transcript、News、Estimates 和 Corporate Actions。

探索阶段确认了几个重要工程事实：

- HTTP 成功不等于响应中包含业务数据；vendor message、rate-limit 和 error response 必须先分类；
- JSON 和 CSV 必须按 endpoint 校验，不能依赖宽松的通用 parser；
- 财务数字必须使用 Decimal；
- missing token 需要统一规范化；
- API fetch 和 Spark transformation 必须分离；
- Alpha Vantage 调用不能由 Spark partitions 无控制地并行执行；
- 所有响应必须先写 Bronze，再决定是否允许进入 Silver。

### 4.2 Step 0B：AV / SEC 跨源模型验证

Step 0B 选择了三种不同公司类型：

- IBM：Technology / Services；
- JPMorgan：Financial / Banking；
- Caterpillar：Asset-heavy / Industrial。

实验覆盖 12 个 canonical metrics、annual / quarterly 两种口径，共形成 72 个对照行。

结果：

| 状态 | 数量 |
|---|---:|
| MATCH | 38 |
| NEAR_MATCH | 3 |
| MISMATCH | 11 |
| MISSING_SEC | 11 |
| COMPOSITE_REQUIRED | 6 |
| NOT_APPLICABLE | 2 |
| AMBIGUOUS_MAPPING | 1 |

实验还完成了：

- 可离线重复运行的 AV / SEC 对照流程；
- mapping matrix 和 discrepancy report；
- schema decision；
- 一个带精确 SEC 原文 evidence 的法律事项样本；
- raw artifact hash 和输出 hash；
- API key 泄漏检查。

Step 0B 的 schema decision 是：

> **PASS WITH REQUIRED CHANGES**

它证明基础平台不需要推倒重建，但正式 Silver metric model 必须先增加来源观测身份、mapping lineage、applicability、period semantics 和 composite lineage。

由此确定的关键原则包括：

1. `semantic_key` 表示现实中的同一语义事实，不包含 `source_system`；
2. `observation_id` 表示某个来源的具体观测，必须包含来源身份；
3. `period_start`、`period_end` 和 `period_type` 必须保存；
4. provider metric key 与 canonical metric key 必须分离；
5. mapping rule 必须保存 ID 和版本；
6. `NOT_APPLICABLE` 与 `MISSING` 不相同；
7. composite metric 必须保存公式和输入 lineage；
8. raw value 与 normalized value 必须同时保留；
9. 公司类型可以影响 metric applicability，但不能改变 Silver schema；
10. SEC 财务暂不进入 V1 正式 Gold 数据流。

### 4.3 Step 0A：方案已更新，但尚未宣称部署完成

PR #1 已完成并合并，主要完成了：

- 把 Step 0B 的结论反馈到 `Step 0A.md`；
- 固定 Databricks dev 基础对象、权限边界和 Smoke Test；
- 保持 Bronze source model 对 Alpha Vantage 和 SEC 中立；
- 明确 Backend 只能读取 Gold；
- 明确 `metric_observation` 不属于 Bootstrap migration；
- 明确 SEC 财务只保留在 shadow mapping / validation 范围。

需要特别区分：

```text
Step 0A 方案设计：已完成
Step 0A 内网 Databricks 部署和验收：尚未完成
```

计划中的 dev 基础包括：

```text
Catalog: company_intel_dev
Schemas: bronze / silver / gold
Managed Volume: company_intel_dev.bronze.source_artifacts

Tables:
- bronze.source_artifact
- silver.company
- silver.source_identifier
- gold.company_dashboard_snapshot
```

另需建立 SQL Warehouse、Job Service Principal、Backend Service Principal、Alpha Vantage Secret Scope、Git Folder 和 Platform Smoke Test Job。

## 5. 当前尚未完成的能力

截至当前，以下内容尚不能被视为已经实现：

- Databricks Step 0A dev 环境的实际部署和权限验收；
- 正式 `silver.metric_observation` 和 `silver.earnings_event`；
- 六个 Alpha Vantage 核心 endpoint 的生产 Bronze → Silver pipeline；
- Gold Dashboard Snapshot Builder；
- Backend BFF；
- Frontend；
- Transcript、News、Estimates 和 Corporate Actions；
- SEC production ingestion；
- Signals、LLM Insight / Question；
- staging / production、CI/CD、监控、SLA、安全和 retention。

## 6. 接下来要完成的部分

### Step 0A：Databricks Dev Foundation

在内网 Databricks 中实施并验收已经批准的平台方案，包括基础对象、权限、Secret、Warehouse、Git 和 Smoke Test。

### Step 1/2：Alpha Vantage Canonical Core

把原计划的 Canonical Metric Foundation 和 Alpha Vantage Core Ingestion 合并成一个交付里程碑，以减少内网人工录入和往返部署成本。

合并不代表跳过模型设计。该里程碑仍需先确认 metric schema、identity、period、applicability、mapping version 和 lineage contract，然后才能把 Alpha Vantage Bronze 数据写入 Silver。

外网主要负责源码、测试、fixture 和 Databricks 部署包；内网主要负责执行 migration、录入或同步少量 Notebook、配置 Secret、运行 Job 和保存验收证据。

### Step 3A：Gold Snapshot Contract

定义 archetype、capability、profile、server-driven sections/components、source manifest 和 JSON Schema。

### Step 3B：Backend BFF

提供 company search、dashboard、refresh 和 refresh status API，只查询 Gold。

### Step 3C：Frontend

使用通用组件渲染 Gold Snapshot，不包含行业 if/else、Alpha Vantage 字段名或指标计算逻辑。

### Step 4：Alpha Vantage 扩展内容

先接 Transcript，再接 News，随后接 Estimates 和 Corporate Actions。

### Step 5：SEC 独有信息

先接 filing metadata，再接结构化 8-K events，最后接 Risk、Legal、Governance、Cyber 和 Evidence。

### Step 6：Signals 与 LLM

先实现可解释的规则 Signals，再实现基于正式数据和 evidence 的 LLM Insight / Question。

### Step 7：生产化

建立 staging / production、CI/CD、监控、成本控制、SLA、安全、审计和 retention。

### Step 8：SEC 财务 reconciliation

只有出现明确产品或合规需求后，才把 SEC 财务 reconciliation 提升为正式能力。

## 7. 不可违反的架构边界

- 所有外部数据先写 Bronze；
- vendor、rate-limit 和 error response 不能进入 Silver；
- `semantic_key` 不包含来源，`observation_id` 包含来源；
- 所有财务数字使用 Decimal；
- 公司类型不改变 Silver schema；
- 只有 Gold Builder 读取 company profile 配置；
- Backend 和 Frontend 不实现行业规则；
- Backend 只读 Gold，Frontend 不直接访问 Databricks；
- SEC 初期不能覆盖 Alpha Vantage 财务指标；
- SEC finding 没有 evidence 不得正式发布；
- Earnings 使用 typed table；Transcript 和 News 使用 content tables；
- 不允许 Spark partitions 并行调用 Alpha Vantage；
- 不允许在没有 Git migration 的情况下手工修改正式 schema；
- API key 不进入代码、表、Volume、日志或 Job 参数。

## 8. 主要文档和产物

- [`AlphaVantage.md`](AlphaVantage.md)：完整产品和技术路线；
- [`docs/archive/step-0-alpha-vantage-exploration.md`](docs/archive/step-0-alpha-vantage-exploration.md)：Step 0 的历史 endpoint/schema 探索与交接记录，保存 15 个 schema scope 和供应商响应细节；其中早期建库建议不代表当前正式架构；
- [`Step 0A.md`](Step%200A.md)：Databricks dev foundation 设计与验收；
- [`Step 0B.md`](Step%200B.md)：跨源 spike 执行方案；
- [`Step 0B Acceptance.md`](Step%200B%20Acceptance.md)：Step 0B 验收说明；
- [`spikes/step_0b/reports/schema_decision.md`](spikes/step_0b/reports/schema_decision.md)：schema decision；
- [`spikes/step_0b/reports/metric_alignment.md`](spikes/step_0b/reports/metric_alignment.md)：对照结果；
- [`spikes/step_0b/reports/discrepancy_report.md`](spikes/step_0b/reports/discrepancy_report.md)：差异报告；
- [`spikes/step_0b/reports/narrative_finding.md`](spikes/step_0b/reports/narrative_finding.md)：SEC evidence 样本。

## 9. 当前最近的里程碑

```text
完成 Step 0A 内网部署与验收
        ↓
交付合并后的 Step 1/2 Alpha Vantage Canonical Core
        ↓
生成第一份可验证的 Gold Dashboard Snapshot
```
