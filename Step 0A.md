# Step 0A：Databricks 数据地基

## 目标

Step 0A 不负责解析完整财务数据，也不负责完成 Dashboard。它只在 Databricks 中建立一个**可治理、可测试、可供后端访问、并能承载多来源数据的基础平台**。

完成后应具备：

```text
company_intel_dev Catalog
├── bronze
│   ├── source_artifact Table
│   └── source_artifacts Volume
├── silver
│   ├── company Table
│   └── source_identifier Table
└── gold
    └── company_dashboard_snapshot Table

另有：
- 一个开发 SQL Warehouse
- 一个 Alpha Vantage Secret Scope
- 一个 Job Service Principal
- 一个 Backend Service Principal
- 一个连接 GitHub 的 Git Folder
- 一个成功运行的平台 Smoke Test Job
```

Databricks Unity Catalog 使用：

```text
catalog.schema.table
catalog.schema.volume
```

非表格原始文件应放入 Unity Catalog Volume，不放入个人目录、DBFS root 或 FileStore。([docs.databricks.com][1])

---

# Step 0B 对 Step 0A 的影响

Step 0B 使用 IBM、JPM 和 CAT，对 12 个 canonical metrics 的年度与季度数据进行了 Alpha Vantage / SEC 对照，并验证了一个带 SEC 原文证据的法律事项样本。

Step 0B 的结论是：

```text
PASS WITH REQUIRED CHANGES
```

它确认了以下架构原则：

```text
1. semantic_key 表示现实中的同一语义事实，不包含 source_system。
2. observation_id 表示某个来源的具体观测，必须包含 source identity。
3. period_start、period_end 和 period_type 不能丢失。
4. provider metric 与 canonical metric 必须分离。
5. mapping 规则必须版本化。
6. metric applicability 与数据缺失是不同概念。
7. composite metric 必须保留公式和输入 lineage。
8. SEC 财务暂不进入 V1 正式数据流。
9. SEC 后续优先提供 filing、法律、治理、风险、事件和 evidence。
```

因此，Step 0A 的基础表不需要推倒重建；但 Step 0A **不得提前创建或冻结 `metric_observation`**。正式指标模型应在下一份 migration 中，根据 Step 0B 的 schema decision 创建。

推荐顺序：

```text
Step 0A：平台、权限、Raw、公司、Gold 契约
Step 0B：本地跨源模型验证
Step 1：Canonical Metric Foundation
Step 2：Alpha Vantage Core Ingestion
Step 3：Gold Builder / Backend / Frontend
Step 4：AV Transcript / News / Estimates
Step 5：SEC 独有 Filing / Event / Evidence
```

---

# 一、范围

## Step 0A 现在做

```text
Unity Catalog
bronze / silver / gold Schemas
Managed Volume
source_artifact
company
source_identifier
company_dashboard_snapshot
SQL Warehouse
Service Principals
Secret
权限
Git Folder
Smoke Test
```

## Step 0A 现在不做

```text
财务 parser
metric_observation
SEC 财务 ingestion
行业专表
实体解析
全量抓取上市公司
Frontend
LLM
```

当前数据源策略：

```text
Alpha Vantage：
V1 公司、财务、Earnings 和后续 Transcript/News 的主要来源。

SEC：
当前只参与设计验证；
后续优先接入 AV 不具备的 filing、事件、法律、治理、
风险因素和可验证原文证据。

SEC 财务：
暂时保留在 shadow / mapping 实验中，不进入 V1 Gold。
```

---

# 二、固定名称

第一阶段只创建 `dev`，不要同时建立 staging 和 production。

| 对象 | 名称 |
|---|---|
| Catalog | `company_intel_dev` |
| Schemas | `bronze`、`silver`、`gold` |
| Managed Volume | `company_intel_dev.bronze.source_artifacts` |
| SQL Warehouse | `company-intel-dev-sql` |
| Secret Scope | `company-intel-dev` |
| Alpha Vantage secret | `alpha-vantage-api-key` |
| Admin Group | `company-intel-admins` |
| Engineer Group | `company-intel-engineers` |
| Reader Group | `company-intel-readers` |
| Job Service Principal | `sp-company-intel-jobs-dev` |
| Backend Service Principal | `sp-company-intel-backend-dev` |

所有时间使用 UTC。

Volume 目录：

```text
/Volumes/company_intel_dev/bronze/source_artifacts/
├── fixtures/
│   └── alphavantage/
├── raw/
│   ├── alphavantage/
│   └── sec/
├── quarantine/
└── _smoke/
```

Volume 路径只使用 ASCII 字符。现有归档上传前重命名为：

```text
alpha_vantage_exploration.zip
```

标准路径格式：

```text
/Volumes/<catalog>/<schema>/<volume>/<path>
```

([docs.databricks.com][2])

---

# 三、管理员请求

可能需要管理员完成：

```text
CREATE CATALOG
Unity Catalog managed storage
SQL Warehouse
Service Principals
Secret Scope / ACL
Warehouse 权限
网络出口
```

可直接发送：

```text
Subject:
[Databricks] Request: company-intel dev foundation setup

We are building a public-company intelligence platform.

Current scope:
1. Alpha Vantage is the primary V1 company and financial source.
2. SEC currently participates in model validation only.
3. SEC financial reconciliation is not a V1 production dependency.
4. Future SEC usage will focus on filing metadata, legal, governance,
   risk factors, events and evidence.
5. No broker customer, policy or private submission data is in scope.
6. Frontend will not access Databricks directly.
7. Backend will have read-only access to Gold.

Please create or confirm:

Catalog:
- company_intel_dev

Schemas:
- company_intel_dev.bronze
- company_intel_dev.silver
- company_intel_dev.gold

Managed Volume:
- company_intel_dev.bronze.source_artifacts

SQL Warehouse:
- company-intel-dev-sql
- Serverless if available
- Smallest available size
- Auto stop around 10 minutes
- Min/max cluster 1/1
- Tags:
  project=company-intel
  environment=dev

Groups:
- company-intel-admins
- company-intel-engineers
- company-intel-readers

Service Principals:
- sp-company-intel-jobs-dev
- sp-company-intel-backend-dev

Required network:
- outbound HTTPS to www.alphavantage.co
- SEC network access will be enabled when filing ingestion begins

Please provide:
- metastore / managed storage status
- principal application IDs
- warehouse ID and HTTP Path
- outbound HTTPS status
- Git Folder availability
```

创建 Catalog 需要 metastore 上的 `CREATE CATALOG`；若没有 managed storage，需要管理员提供 managed storage 或 external location。([docs.databricks.com][1])

---

# 四、团队职责

| 角色 | 负责 | 不负责 |
|---|---|---|
| Databricks 管理员 | Catalog、Group、SP、Warehouse、权限 | 业务指标语义 |
| 安全/网络 | Secret、HTTPS 出站 | Parser |
| 数据工程负责人 | DDL、Migration、Volume、Pipeline、测试 | 云账号级 IAM |
| Codex | 按 Ticket 写 SQL、Notebook、代码和测试 | 自行改变架构原则 |
| Backend | 使用 Backend SP 查询 Gold | 查询 Bronze/Silver |
| Frontend | 渲染 Dashboard JSON | SQL、AV 字段和行业逻辑 |
| 产品/保险人员 | 后续验证页面与 Insight | Step 0A 平台验收 |

Step 0A 验收不判断财务数字是否正确。

---

# 五、Git 仓库结构

```text
company-intel/
├── docs/
│   ├── architecture.md
│   ├── databricks-bootstrap.md
│   ├── access-matrix.md
│   └── step-0b-schema-decision.md
├── sql/
│   └── migrations/
│       ├── 001_platform_bootstrap.sql
│       ├── 002_permissions_template.sql
│       └── 003_metric_model.sql
├── notebooks/
│   └── 00_platform_smoke_test.py
├── src/
├── tests/
└── config/
```

原则：

> 所有在 Databricks UI 中执行的正式 SQL，都必须在 Git 中有对应 Migration。

不要在 SQL Editor 中执行无 Git 记录的正式 DDL。

---

# 六、Migration 001：平台 Bootstrap

文件：

```text
sql/migrations/001_platform_bootstrap.sql
```

```sql
-- ============================================================
-- company-intel development platform bootstrap
-- Environment: dev
-- ============================================================

CREATE CATALOG IF NOT EXISTS company_intel_dev
COMMENT 'Development catalog for the public-company intelligence platform';

CREATE SCHEMA IF NOT EXISTS company_intel_dev.bronze
COMMENT 'Immutable source artifacts and raw ingestion metadata';

CREATE SCHEMA IF NOT EXISTS company_intel_dev.silver
COMMENT 'Canonical normalized company data';

CREATE SCHEMA IF NOT EXISTS company_intel_dev.gold
COMMENT 'Frontend-ready dashboard snapshots and serving data';

CREATE VOLUME IF NOT EXISTS
  company_intel_dev.bronze.source_artifacts;


-- ------------------------------------------------------------
-- Immutable raw artifact index.
-- Full files live in the Unity Catalog Volume.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS
  company_intel_dev.bronze.source_artifact
(
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
USING DELTA
COMMENT 'Index of immutable source files stored in the source_artifacts volume';


-- ------------------------------------------------------------
-- Simplified V1 company profile.
-- Not a legal-entity-resolution model.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS
  company_intel_dev.silver.company
(
    company_id            STRING NOT NULL,
    company_key           STRING NOT NULL,

    symbol                STRING NOT NULL,
    exchange              STRING NOT NULL,
    name                  STRING NOT NULL,

    canonical_asset_type  STRING,
    listing_status        STRING,
    ipo_date               DATE,

    country               STRING,
    currency              STRING,

    sector_raw            STRING,
    industry_raw          STRING,
    archetype             STRING,

    description           STRING,
    official_site         STRING,
    fiscal_year_end       STRING,
    latest_quarter        DATE,

    created_at            TIMESTAMP NOT NULL,
    updated_at            TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Current simplified company profile used by the dashboard';


-- ------------------------------------------------------------
-- Lightweight source identifier bridge.
-- This is not fuzzy entity resolution.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS
  company_intel_dev.silver.source_identifier
(
    company_id            STRING NOT NULL,
    source_system         STRING NOT NULL,

    identifier_type       STRING NOT NULL,
    identifier_value      STRING NOT NULL,

    verification_status   STRING NOT NULL,
    observed_at           TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Source identifiers such as Alpha Vantage symbol and SEC CIK';


-- ------------------------------------------------------------
-- Stable frontend serving contract.
-- Detailed metric tables are created after Step 0B.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS
  company_intel_dev.gold.company_dashboard_snapshot
(
    snapshot_id           STRING NOT NULL,
    company_id            STRING NOT NULL,

    archetype             STRING NOT NULL,

    capabilities_json     STRING NOT NULL,
    payload_json          STRING NOT NULL,

    schema_version        STRING NOT NULL,
    config_version        STRING NOT NULL,

    source_manifest_json  STRING NOT NULL,

    data_as_of            TIMESTAMP NOT NULL,
    generated_at          TIMESTAMP NOT NULL,

    status                STRING NOT NULL
)
USING DELTA
COMMENT 'Immutable frontend-ready dashboard snapshot';
```

运行后确认：

```text
Catalog
3 Schemas
Managed Volume
4 tables
```

---

# 七、Metric Model 不属于 Migration 001

Step 0B 已经证明正式指标表必须支持：

```text
semantic_key
observation_id
source_system
source_artifact_id / hash
provider_metric_key
canonical metric_key
mapping_rule_id / mapping_version
period_start / period_end / period_type
canonical dimensions
raw value / normalized value
applicability_status
quality_status
composite lineage
```

因此：

```text
Migration 001 不创建 metric_observation。
Migration 003 在 Step 0B schema decision 被接受后创建。
```

正式模型中的语义约束：

```text
semantic_key：
company_id + metric_key + period fields + canonical dimensions
不包含 source_system
不包含“latest”之类查询上下文

observation_id：
source_system + semantic_key + provider metric +
source artifact + source record + revision/value identity
```

`MATCH / MISMATCH / NEAR_MATCH` 属于跨源 reconciliation，不属于单条 observation。

---

# 八、所有权和权限

对象所有权交给 Group，不交给个人。Unity Catalog 权限可从 Catalog / Schema 向下继承。([docs.databricks.com][5])

## Owner

```sql
ALTER CATALOG company_intel_dev
OWNER TO `company-intel-admins`;

ALTER SCHEMA company_intel_dev.bronze
OWNER TO `company-intel-admins`;

ALTER SCHEMA company_intel_dev.silver
OWNER TO `company-intel-admins`;

ALTER SCHEMA company_intel_dev.gold
OWNER TO `company-intel-admins`;

ALTER VOLUME company_intel_dev.bronze.source_artifacts
OWNER TO `company-intel-admins`;

ALTER TABLE company_intel_dev.bronze.source_artifact
OWNER TO `company-intel-admins`;

ALTER TABLE company_intel_dev.silver.company
OWNER TO `company-intel-admins`;

ALTER TABLE company_intel_dev.silver.source_identifier
OWNER TO `company-intel-admins`;

ALTER TABLE company_intel_dev.gold.company_dashboard_snapshot
OWNER TO `company-intel-admins`;
```

## Engineers

```sql
GRANT USE CATALOG
ON CATALOG company_intel_dev
TO `company-intel-engineers`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY,
  CREATE TABLE,
  CREATE VOLUME,
  READ VOLUME,
  WRITE VOLUME
ON SCHEMA company_intel_dev.bronze
TO `company-intel-engineers`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY,
  CREATE TABLE
ON SCHEMA company_intel_dev.silver
TO `company-intel-engineers`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY,
  CREATE TABLE
ON SCHEMA company_intel_dev.gold
TO `company-intel-engineers`;
```

## Job Service Principal

```sql
GRANT USE CATALOG
ON CATALOG company_intel_dev
TO `sp-company-intel-jobs-dev`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY,
  READ VOLUME,
  WRITE VOLUME
ON SCHEMA company_intel_dev.bronze
TO `sp-company-intel-jobs-dev`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY
ON SCHEMA company_intel_dev.silver
TO `sp-company-intel-jobs-dev`;

GRANT
  USE SCHEMA,
  SELECT,
  MODIFY
ON SCHEMA company_intel_dev.gold
TO `sp-company-intel-jobs-dev`;
```

Job SP 不需要：

```text
MANAGE
CREATE CATALOG
权限管理
```

## Backend Service Principal

Backend 只读 Gold：

```sql
GRANT USE CATALOG
ON CATALOG company_intel_dev
TO `sp-company-intel-backend-dev`;

GRANT
  USE SCHEMA,
  SELECT
ON SCHEMA company_intel_dev.gold
TO `sp-company-intel-backend-dev`;
```

不要给 Backend：

```text
Bronze SELECT
Silver SELECT
MODIFY
WRITE VOLUME
Alpha Vantage Secret
```

## Readers

```sql
GRANT USE CATALOG
ON CATALOG company_intel_dev
TO `company-intel-readers`;

GRANT
  USE SCHEMA,
  SELECT
ON SCHEMA company_intel_dev.gold
TO `company-intel-readers`;
```

权限验收：

```sql
SHOW GRANTS ON CATALOG company_intel_dev;
SHOW GRANTS ON SCHEMA company_intel_dev.bronze;
SHOW GRANTS ON SCHEMA company_intel_dev.silver;
SHOW GRANTS ON SCHEMA company_intel_dev.gold;
SHOW GRANTS ON VOLUME company_intel_dev.bronze.source_artifacts;
```

---

# 九、Alpha Vantage Secret

API key 不得进入：

```text
Notebook 源码
Git
Widget 默认值
Job 参数
Volume
Delta 表
日志
```

创建：

```bash
databricks secrets create-scope company-intel-dev

databricks secrets put-secret \
  company-intel-dev \
  alpha-vantage-api-key
```

授权：

```bash
databricks secrets put-acl \
  company-intel-dev \
  <JOB_SERVICE_PRINCIPAL_APPLICATION_ID> \
  READ

databricks secrets put-acl \
  company-intel-dev \
  company-intel-admins \
  MANAGE
```

Notebook 读取：

```python
api_key = dbutils.secrets.get(
    scope="company-intel-dev",
    key="alpha-vantage-api-key",
)
```

禁止：

```python
print(api_key)
```

Secret Scope 应按应用或角色划分。([docs.databricks.com][6])

---

# 十、上传本地 Fixture

至少上传：

```text
artifacts/alpha_vantage/raw/demo/001_overview_ibm.txt
```

目标：

```text
/Volumes/company_intel_dev/bronze/source_artifacts/
fixtures/alphavantage/001_overview_ibm.txt
```

也可以上传整个：

```text
alpha_vantage_exploration.zip
```

共享数据必须进入项目 Volume，不进入个人 Workspace 路径。([docs.databricks.com][7])

---

# 十一、Smoke Test

Smoke Test 应验证：

```text
1. Job identity 能写 / 读 Volume。
2. Job identity 能写 Bronze Delta。
3. 文件 hash 与 metadata 一致。
4. source_artifact 可以同时表达 Alpha Vantage 与 SEC artifact，
   但 Step 0A 不进行 SEC 网络抓取。
```

文件：

```text
notebooks/00_platform_smoke_test.py
```

建议内容：

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import uuid


CATALOG = "company_intel_dev"
TABLE = f"{CATALOG}.bronze.source_artifact"
VOLUME_ROOT = Path(
    f"/Volumes/{CATALOG}/bronze/source_artifacts"
)

now = datetime.now(timezone.utc)
smoke_dir = VOLUME_ROOT / "_smoke"
smoke_dir.mkdir(parents=True, exist_ok=True)

samples = [
    {
        "source_system": "ALPHA_VANTAGE",
        "artifact_type": "API_JSON",
        "content_type": "application/json",
        "payload": {
            "symbol": "IBM",
            "source": "smoke",
        },
    },
    {
        "source_system": "SEC_EDGAR",
        "artifact_type": "FILING_HTML",
        "content_type": "text/html",
        "payload": "<html><body>SEC smoke artifact</body></html>",
    },
]

inserted_ids = []

for sample in samples:
    artifact_id = str(uuid.uuid4())
    inserted_ids.append(artifact_id)

    if isinstance(sample["payload"], str):
        raw_bytes = sample["payload"].encode("utf-8")
        suffix = "html"
    else:
        raw_bytes = json.dumps(
            sample["payload"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        suffix = "json"

    file_path = smoke_dir / f"{artifact_id}.{suffix}"
    file_path.write_bytes(raw_bytes)

    assert file_path.exists()
    assert file_path.read_bytes() == raw_bytes

    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    safe_path = str(file_path).replace("'", "''")
    safe_time = now.strftime("%Y-%m-%d %H:%M:%S")

    spark.sql(
        f"""
        INSERT INTO {TABLE}
        VALUES (
            '{artifact_id}',
            '{sample["source_system"]}',
            '{sample["artifact_type"]}',
            NULL,
            'PLATFORM_SMOKE:{artifact_id}',
            '{{}}',
            '{safe_path}',
            '{content_hash}',
            '{sample["content_type"]}',
            200,
            'DATA',
            NULL,
            TIMESTAMP '{safe_time}',
            'platform-smoke-v2',
            '{{}}'
        )
        """
    )

result = spark.sql(
    f"""
    SELECT
        artifact_id,
        source_system,
        artifact_type,
        storage_uri,
        content_hash
    FROM {TABLE}
    WHERE artifact_id IN ({",".join(repr(item) for item in inserted_ids)})
    ORDER BY source_system
    """
).collect()

assert len(result) == 2
assert {row["source_system"] for row in result} == {
    "ALPHA_VANTAGE",
    "SEC_EDGAR",
}

display(result)
print("STEP 0A PLATFORM SMOKE TEST PASSED")
```

这里的 `SEC_EDGAR` 是本地 smoke artifact，不是生产 SEC ingestion。

---

# 十二、Smoke Test Job

创建 Job：

| 配置 | 值 |
|---|---|
| Name | `company-intel-dev-platform-smoke` |
| Task | Notebook |
| Notebook | `notebooks/00_platform_smoke_test.py` |
| Run as | `sp-company-intel-jobs-dev` |
| Compute | Serverless Jobs compute，若可用 |
| Schedule | 无 |

预期：

```text
Job status: Succeeded
STEP 0A PLATFORM SMOKE TEST PASSED
```

如果个人身份成功、Job SP 失败，说明权限仍不完整。

---

# 十三、可选网络测试

可以进行一次 Alpha Vantage `OVERVIEW` 请求，但在 response classifier 完成前：

```text
只能写 Bronze
不能进入 Silver
```

网络测试必须：

```text
从 Secret Scope 读取 key
不打印 key
不打印完整请求 URL
先保存 raw，再做任何解析
```

不要在 Step 0A 接入 SEC 网络。

---

# 十四、Backend 访问

外部 Backend 不使用个人 PAT。推荐使用 Backend Service Principal，通过 OAuth M2M 查询 Databricks SQL。([docs.databricks.com][9])

安全提供：

```text
DATABRICKS_HOST
DATABRICKS_HTTP_PATH
DATABRICKS_CLIENT_ID
DATABRICKS_CLIENT_SECRET
```

Backend 正向测试：

```sql
SELECT COUNT(*)
FROM company_intel_dev.gold.company_dashboard_snapshot;
```

返回 `0` 也算成功。

负向测试：

```sql
SELECT COUNT(*)
FROM company_intel_dev.bronze.source_artifact;
```

必须被拒绝。

---

# 十五、Step 0A 验收

| 编号 | 验收内容 | 通过标准 |
|---|---|---|
| A01 | Unity Catalog | 项目 Catalog 可见 |
| A02 | Catalog / Schema | bronze、silver、gold 存在 |
| A03 | Volume | 能写入并读取 `_smoke` 文件 |
| A04 | Tables | 四张基础表存在 |
| A05 | Ownership | Owner 是 Admin Group |
| A06 | Secret | Job SP 可读；Backend SP 不可读 |
| A07 | Job Identity | Job SP 成功执行 Smoke Test |
| A08 | Backend 权限 | 能读 Gold；不能读 Bronze/Silver |
| A09 | Git | DDL、Notebook 和文档已提交 |
| A10 | Warehouse | 可连接、自动停止、成本 Tag |
| A11 | 网络 | Job compute 可访问 Alpha Vantage |
| A12 | Hash | Volume 文件 hash 与表中 hash 一致 |
| A13 | Source neutrality | Smoke Test 可登记 AV 和 SEC 两种 artifact |
| A14 | Metric boundary | 001 中没有创建 `metric_observation` |

验收材料：

```text
Git commit hash
Migration SQL
SHOW GRANTS 输出
Smoke Job URL
source_artifact smoke rows
Volume 路径与 hash
Backend 正向 / 负向权限测试
Warehouse 配置
```

---

# 十六、给 Codex 的约束

```text
1. 使用 Unity Catalog，不使用 hive_metastore。
2. 原始非表格文件进入 Managed Volume。
3. Raw metadata 进入 bronze.source_artifact。
4. API key 不进入代码、参数、表或日志。
5. DDL 使用 CREATE ... IF NOT EXISTS。
6. Migration 不使用 CREATE OR REPLACE TABLE。
7. Backend 只能读取 Gold。
8. Job 使用 sp-company-intel-jobs-dev。
9. Owner 属于 Group，不属于个人。
10. 时间使用 UTC。
11. 财务数字后续使用 DECIMAL，不使用 float。
12. 未通过 response classification 的响应不得进入 Silver。
13. Step 0A 不创建 metric_observation。
14. semantic_key 将来不包含 source_system。
15. observation_id 将来必须包含 source identity。
16. SEC 财务不属于 AV V1 生产流。
```

Codex 第一个 Ticket：

```text
Create the Databricks Step 0A foundation.

Deliver:
1. sql/migrations/001_platform_bootstrap.sql
2. sql/migrations/002_permissions_template.sql
3. notebooks/00_platform_smoke_test.py
4. docs/databricks-bootstrap.md
5. docs/access-matrix.md
6. tests/acceptance/step_0a_checklist.md

Do not:
- add parser logic;
- add SEC ingestion;
- add financial metric tables;
- create frontend code;
- store credentials;
- use personal workspace paths.

Acceptance:
- migrations are idempotent;
- smoke notebook verifies Volume and Delta writes;
- smoke notebook registers both AV and SEC artifact types;
- permissions follow least privilege;
- names and paths are parameterized for future environments.
```

---

# 十七、Step 0A 之后

Step 0A 完成后：

```text
1. 接受 Step 0B schema decision。
2. 创建下一份 metric-model migration。
3. 实现 Alpha Vantage 六个核心端点的 Bronze → Silver。
4. 建立 metric catalog、archetype applicability 和 lineage。
5. 生成第一个 Gold Dashboard Snapshot。
6. 接 Backend 和 server-driven Frontend。
7. 再接 AV Transcript / News。
8. 最后接 SEC 独有 Filing / Event / Evidence。
```

不要因为 Step 0A 完成就认为业务数据模型已冻结。

---

# 十八、团队说明

```text
我们正在建立 company-intel 的 Databricks 数据地基。

Alpha Vantage 是 V1 公司与财务数据主源；SEC 当前不参与正式财务取数，
后续优先用于 filing、法律、治理、风险因素、事件和原文证据。

Step 0B 已经验证：系统必须把“同一个现实指标”与“不同来源的观测”
分开建模，并保留期间、mapping、适用性和组合指标 lineage。
因此 Step 0A 只搭平台、Raw、公司标识和 Gold 契约，
正式 metric_observation 会在下一阶段按验证结果创建。

Frontend 不直接访问 Databricks；Backend 只读取 Gold Snapshot。
```

---

# 十九、暂时不要做

```text
不要创建全部 production 表。
不要全量抓取数千家公司。
不要让 Spark partitions 并行调用 Alpha Vantage。
不要把 API key 放进 Widget、Job 参数或 Volume。
不要让 Backend 查询 Silver。
不要让 Frontend 查询 Databricks SQL。
不要在没有 Git Migration 的情况下手工 ALTER TABLE。
不要在 Step 0A 创建或冻结 metric_observation。
不要在 V1 用 SEC 财务覆盖 Alpha Vantage。
```

执行顺序：

```text
管理员确认 Unity Catalog 和身份
        ↓
建立 SQL Warehouse
        ↓
建立 Git Folder
        ↓
执行 Bootstrap Migration
        ↓
设置 Owner 和 Grants
        ↓
创建 Secret
        ↓
上传 Fixture
        ↓
运行 Job SP Smoke Test
        ↓
Backend Gold-only 权限测试
        ↓
Step 0A 验收
        ↓
创建 Canonical Metric Foundation
```

[1]: https://docs.databricks.com/aws/en/catalogs/create-catalog "Create catalogs | Databricks on AWS"
[2]: https://docs.databricks.com/aws/en/volumes/utility-commands "Create and manage Unity Catalog volumes"
[3]: https://docs.databricks.com/aws/en/compute/sql-warehouse/create "Create a SQL warehouse | Databricks on AWS"
[4]: https://docs.databricks.com/aws/en/repos/ "Databricks Git folders | Databricks on AWS"
[5]: https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/ "Manage privileges in Unity Catalog"
[6]: https://docs.databricks.com/aws/en/security/secrets/ "Secret management | Databricks on AWS"
[7]: https://docs.databricks.com/aws/en/volumes/volume-files "Work with files in Unity Catalog volumes"
[8]: https://docs.databricks.com/aws/en/jobs/configure-job "Configure and edit Lakeflow Jobs"
[9]: https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m "Authorize service principal access with OAuth"
[10]: https://docs.databricks.com/aws/en/dev-tools/bundles/ "Declarative Automation Bundles"
