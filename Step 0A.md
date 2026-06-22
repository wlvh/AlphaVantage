# Step 0A 的目标

这一阶段不是开始解析财务数据，而是先在 Databricks 中建立一个**可治理、可测试、可供后端访问的数据地基**。

完成后应当具备：

```text
company_intel_dev Catalog
├── bronze Schema
│   ├── source_artifact Table
│   └── source_artifacts Volume
├── silver Schema
│   ├── company Table
│   └── source_identifier Table
└── gold Schema
    └── company_dashboard_snapshot Table

另有：
- 一个开发 SQL Warehouse
- 一个 Alpha Vantage secret scope
- 一个 Job service principal
- 一个 Backend service principal
- 一个 Git repository / Git folder
- 一个成功运行的平台 smoke-test Job
```

Databricks 的 Unity Catalog 使用三级结构：

```text
catalog.schema.table
catalog.schema.volume
```

Catalog 包含 Schema，Schema 再包含表、View 和 Volume。非表格原始文件建议放在 Unity Catalog Volume 中，而不是 DBFS root 或个人目录。([docs.databricks.com][1])

---

# 一、开始之前先固定名称

第一阶段只建 `dev`，不要立刻创建 staging 和 production。

| 对象                        | 建议名称                                        |
| ------------------------- | ------------------------------------------- |
| Catalog                   | `company_intel_dev`                         |
| Schemas                   | `bronze`、`silver`、`gold`                    |
| Managed Volume            | `company_intel_dev.bronze.source_artifacts` |
| SQL Warehouse             | `company-intel-dev-sql`                     |
| Secret Scope              | `company-intel-dev`                         |
| Alpha Vantage secret key  | `alpha-vantage-api-key`                     |
| 管理组                       | `company-intel-admins`                      |
| 开发组                       | `company-intel-engineers`                   |
| 只读组                       | `company-intel-readers`                     |
| Job Service Principal     | `sp-company-intel-jobs-dev`                 |
| Backend Service Principal | `sp-company-intel-backend-dev`              |

所有时间统一使用 UTC。

原始文件路径约定：

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

Volume 路径只应使用 ASCII 字符。你当前的 `归档(4).zip` 上传前应重命名为：

```text
alpha_vantage_exploration.zip
```

Unity Catalog Volume 的标准路径格式是：

```text
/Volumes/<catalog>/<schema>/<volume>/<path>
```

([docs.databricks.com][2])

---

# 二、先确认哪些事情需要管理员处理

你未必拥有以下权限：

```text
CREATE CATALOG
创建 Service Principal
创建 SQL Warehouse
设置 Warehouse 权限
配置网络出口
创建或管理 Secret Scope
```

所以第一件事是给 Databricks 平台管理员发一个明确的请求。

## 可直接发送给管理员的消息

**标题：**

```text
[Databricks] Request: company-intel dev foundation setup
```

**正文：**

```text
我们正在建立一个上市公司情报系统的 Databricks 开发环境。

当前阶段范围：
1. Alpha Vantage 是主要数据源；
2. 只处理公开上市公司及公开财务数据；
3. 不处理 Broker 客户数据、保单数据或其他内部敏感数据；
4. SEC 当前只参与模型验证，暂不作为生产财务主源；
5. 前端不会直接访问 Databricks，后端只读取 Gold Snapshot。

希望建立以下对象：

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
- Auto stop approximately 10 minutes
- Min/max cluster 1/1
- Tags:
  project=company-intel
  environment=dev

Groups:
- company-intel-admins
- company-intel-engineers
- company-intel-readers

Service principals:
- sp-company-intel-jobs-dev
- sp-company-intel-backend-dev

Required network:
- Outbound HTTPS access to www.alphavantage.co
- SEC access will be requested separately later

Please confirm:
1. Unity Catalog metastore is attached to the workspace;
2. Whether the metastore or catalog has a managed storage location;
3. Who can create the catalog;
4. Service principal application IDs;
5. SQL Warehouse ID and HTTP Path;
6. Outbound HTTPS availability;
7. Git folder integration availability.
```

创建 Catalog 需要 metastore 上的 `CREATE CATALOG`；如果没有 metastore 级 managed storage，还需要管理员提供 managed storage location 或 external location。([docs.databricks.com][1])

---

# 三、团队角色怎么分

| 角色             | 应负责什么                               | 不应负责什么               |
| -------------- | ----------------------------------- | -------------------- |
| Databricks 管理员 | Unity Catalog、Group、SP、Warehouse、权限 | 业务指标设计               |
| 安全/网络团队        | API key 管理、HTTPS 出站访问               | Alpha Vantage parser |
| 你/数据工程负责人      | 表设计、Migration、Volume、Smoke test     | 云账号级 IAM             |
| Codex          | 根据明确 Ticket 编写 SQL、Notebook、测试      | 自行改变架构原则             |
| Backend 工程师    | 使用 Backend SP 查询 Gold               | 查询 Bronze/Silver     |
| Frontend 工程师   | 消费 Dashboard JSON                   | 访问 SQL、理解 AV 字段      |
| 产品/保险人员        | 后续验证 Dashboard 内容                   | 验收 Step 0A 基础设施      |

Step 0A 暂时不需要产品人员判断财务数据是否正确；他们只需要知道系统基础环境正在建立。

---

# 四、在 Databricks 中实际操作

## 第 1 步：确认 Unity Catalog

进入 Databricks Workspace。

打开：

```text
SQL → SQL Editor
```

选择一个已有 SQL Warehouse，然后运行：

```sql
SHOW CATALOGS;
```

应当能够看到：

```text
system
hive_metastore
以及若干 Unity Catalog catalogs
```

如果只能使用 `hive_metastore`，暂停开发，请管理员确认 Workspace 是否已经连接 Unity Catalog metastore。

---

## 第 2 步：创建开发 SQL Warehouse

进入：

```text
SQL Warehouses → Create SQL Warehouse
```

建议：

```text
Name: company-intel-dev-sql
Type: Serverless（若可用）
Size: 最小可用
Min clusters: 1
Max clusters: 1
Auto stop: 10 minutes
```

Databricks 当前建议可用时优先采用 Serverless SQL Warehouse；Serverless 默认自动停止时间通常为 10 分钟。([docs.databricks.com][3])

在 Warehouse 的 Permissions 页面添加：

| Principal                      | Warehouse 权限                   |
| ------------------------------ | ------------------------------ |
| `company-intel-engineers`      | Can Use / Can Monitor          |
| `sp-company-intel-backend-dev` | Can Use                        |
| `sp-company-intel-jobs-dev`    | 仅在任务需要 SQL Warehouse 时 Can Use |

同时记录：

```text
Server Hostname
HTTP Path
Warehouse ID
```

Backend 后续会使用这些值。

---

## 第 3 步：建立 Git Folder

Databricks 当前将过去的 Repos 称为 **Git folders**。Git folders 可以直接在 Workspace 内连接 GitHub、GitLab、Azure DevOps 等仓库。([docs.databricks.com][4])

在 Workspace 中创建一个 Git folder，建议仓库结构：

```text
company-intel/
├── docs/
│   ├── architecture.md
│   ├── databricks-bootstrap.md
│   └── access-matrix.md
├── sql/
│   └── migrations/
│       ├── 001_platform_bootstrap.sql
│       └── 002_permissions_template.sql
├── notebooks/
│   └── 00_platform_smoke_test.py
├── src/
├── tests/
└── config/
```

原则：

> 所有在 Databricks UI 中执行的正式 SQL，都必须同时存在于 Git 中。

不要只在 SQL Editor 中临时运行一段无人保存的 DDL。

---

# 五、执行第一份 Migration

在：

```text
sql/migrations/001_platform_bootstrap.sql
```

写入以下内容。

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
-- Raw source artifact index.
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
COMMENT 'Index of immutable raw source files stored in the source_artifacts volume';


-- ------------------------------------------------------------
-- Simplified company identity.
-- No legal-entity resolution in V1.
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
    ipo_date              DATE,

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
-- Lightweight source identifiers.
-- Not an entity-resolution system.
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
COMMENT 'Source-specific identifiers such as Alpha Vantage symbol or SEC CIK';


-- ------------------------------------------------------------
-- Stable Gold serving contract.
-- Metric tables can be finalized after the SEC/AV spike.
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

在 SQL Editor 中：

1. 选择 `company-intel-dev-sql`；
2. 粘贴并运行完整文件；
3. 打开 Catalog Explorer；
4. 确认 Catalog、三个 Schema、Volume 和四张表都已出现。

---

# 六、设置所有权和权限

Databricks 建议把对象所有权交给 Group，而不是个人。Unity Catalog 的权限可以从 Catalog 或 Schema 继承到当前和未来的子对象。([docs.databricks.com][5])

下面 SQL 中的 Service Principal 名称必须替换成管理员提供的实际 principal 名称或 application ID。

## 所有权

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

## 开发人员权限

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

## Job Service Principal 权限

Job 负责：

```text
写 Bronze
写 Silver
生成 Gold Snapshot
读写 Volume
```

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
管理权限授权
```

正式 Migration 由管理员组或 deployment identity 执行。

## Backend Service Principal 权限

Backend 只允许读 Gold：

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
```

## 人工只读用户

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

---

# 七、验证权限

管理员或负责人运行：

```sql
SHOW GRANTS ON CATALOG company_intel_dev;

SHOW GRANTS ON SCHEMA company_intel_dev.bronze;

SHOW GRANTS ON SCHEMA company_intel_dev.silver;

SHOW GRANTS ON SCHEMA company_intel_dev.gold;

SHOW GRANTS ON VOLUME
  company_intel_dev.bronze.source_artifacts;
```

重点检查：

```text
对象 owner 不是某个个人邮箱；
Backend SP 只有 Gold SELECT；
Job SP 没有 MANAGE；
普通 reader 看不到 Bronze 和 Silver。
```

---

# 八、创建 Alpha Vantage Secret

Alpha Vantage API key 不得放在：

```text
Notebook 源代码
Git
Widget 默认值
Job 参数
Volume 文件
Spark DataFrame
日志
```

Databricks Secret Scope 可以保存加密 Secret，并通过 ACL 控制访问。Secret Scope 应按应用或角色划分，而不是按个人划分。([docs.databricks.com][6])

使用 Databricks CLI：

```bash
databricks secrets create-scope company-intel-dev
```

添加 Secret：

```bash
databricks secrets put-secret \
  company-intel-dev \
  alpha-vantage-api-key
```

终端会要求输入值。

给 Job SP 读取权限：

```bash
databricks secrets put-acl \
  company-intel-dev \
  <JOB_SERVICE_PRINCIPAL_APPLICATION_ID> \
  READ
```

给管理员组管理权限：

```bash
databricks secrets put-acl \
  company-intel-dev \
  company-intel-admins \
  MANAGE
```

不要给 Backend SP Alpha Vantage key；Backend 不应直接调用 Alpha Vantage。

Notebook 中读取：

```python
api_key = dbutils.secrets.get(
    scope="company-intel-dev",
    key="alpha-vantage-api-key",
)
```

不要执行：

```python
print(api_key)
```

---

# 九、上传当前 fixture

进入：

```text
Catalog
→ company_intel_dev
→ bronze
→ source_artifacts
```

创建目录：

```text
fixtures/alphavantage
```

建议从现有归档中先上传：

```text
artifacts/alpha_vantage/raw/demo/001_overview_ibm.txt
```

目标路径：

```text
/Volumes/company_intel_dev/bronze/source_artifacts/
fixtures/alphavantage/001_overview_ibm.txt
```

也可以把整个归档重命名后上传：

```text
alpha_vantage_exploration.zip
```

Unity Catalog Volume 支持通过 Catalog Explorer 上传、下载和管理文件。([docs.databricks.com][7])

不要把 fixture 放到：

```text
/Workspace/Users/<你的邮箱>/
/FileStore/
dbfs:/
My Files
```

共享项目数据应该进入项目 Volume，而不是个人文件区域。

---

# 十、创建 Smoke Test Notebook

在 Git folder 中创建：

```text
notebooks/00_platform_smoke_test.py
```

内容如下：

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


# ------------------------------------------------------------
# 1. Write and read a file in the managed volume.
# ------------------------------------------------------------

artifact_id = str(uuid.uuid4())
now = datetime.now(timezone.utc)

smoke_dir = VOLUME_ROOT / "_smoke"
smoke_dir.mkdir(parents=True, exist_ok=True)

payload = {
    "artifact_id": artifact_id,
    "status": "ok",
    "created_at": now.isoformat(),
}

raw_bytes = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")

file_path = smoke_dir / f"{artifact_id}.json"
file_path.write_bytes(raw_bytes)

assert file_path.exists(), f"File was not created: {file_path}"
assert file_path.read_bytes() == raw_bytes

content_hash = hashlib.sha256(raw_bytes).hexdigest()


# ------------------------------------------------------------
# 2. Register the file in the Bronze artifact table.
# ------------------------------------------------------------

safe_path = str(file_path).replace("'", "''")
safe_time = now.strftime("%Y-%m-%d %H:%M:%S")

spark.sql(
    f"""
    INSERT INTO {TABLE}
    VALUES (
        '{artifact_id}',
        'INTERNAL_SMOKE_TEST',
        'API_JSON',
        NULL,
        'PLATFORM_SMOKE:{artifact_id}',
        '{{}}',
        '{safe_path}',
        '{content_hash}',
        'application/json',
        200,
        'DATA_JSON',
        NULL,
        TIMESTAMP '{safe_time}',
        'platform-smoke-v1',
        '{{}}'
    )
    """
)


# ------------------------------------------------------------
# 3. Verify that the table row and physical file agree.
# ------------------------------------------------------------

result = spark.sql(
    f"""
    SELECT
        artifact_id,
        source_system,
        storage_uri,
        content_hash,
        classification
    FROM {TABLE}
    WHERE artifact_id = '{artifact_id}'
    """
).collect()

assert len(result) == 1
assert result[0]["content_hash"] == content_hash
assert result[0]["classification"] == "DATA_JSON"

display(result)

print("STEP 0A PLATFORM SMOKE TEST PASSED")
```

这个 Notebook 验证了：

```text
Job identity 可以写 Volume
Job identity 可以读 Volume
Job identity 可以写 Bronze Delta 表
Volume 文件和 metadata hash 一致
```

---

# 十一、建立一个 Smoke Test Job

进入：

```text
Jobs & Pipelines
→ Create
→ Job
```

配置：

| 项目        | 值                                     |
| --------- | ------------------------------------- |
| Job name  | `company-intel-dev-platform-smoke`    |
| Task type | Notebook                              |
| Notebook  | `notebooks/00_platform_smoke_test.py` |
| Run as    | `sp-company-intel-jobs-dev`           |
| Compute   | Serverless jobs compute，若可用           |
| Schedule  | 无                                     |

Databricks 当前支持 Notebook、Python Script 和 Python Wheel 等任务使用 Serverless Jobs compute；创建任务时通常默认选择 Serverless。([docs.databricks.com][8])

手动运行一次。

期待结果：

```text
Job status: Succeeded
Notebook output:
STEP 0A PLATFORM SMOKE TEST PASSED
```

如果它以你的个人身份成功、以 Service Principal 身份失败，说明权限配置仍未完成。

---

# 十二、可选：做一次真实 Alpha Vantage 网络测试

这一步只运行一次，不解析到 Silver。

```python
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import requests
import uuid


api_key = dbutils.secrets.get(
    scope="company-intel-dev",
    key="alpha-vantage-api-key",
)

response = requests.get(
    "https://www.alphavantage.co/query",
    params={
        "function": "OVERVIEW",
        "symbol": "IBM",
        "apikey": api_key,
    },
    timeout=30,
)

assert response.status_code == 200
assert response.text.strip()

artifact_id = str(uuid.uuid4())
now = datetime.now(timezone.utc)

path = Path(
    "/Volumes/company_intel_dev/bronze/source_artifacts/"
    f"raw/alphavantage/overview/{now:%Y/%m/%d}/{artifact_id}.json"
)

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(response.text, encoding="utf-8")

print("Alpha Vantage connectivity test completed.")
print(f"HTTP status: {response.status_code}")
print(f"Raw artifact path: {path}")
```

不要打印完整响应，避免供应商提示中混入不必要的信息。

在 response classifier 完成之前，真实响应只能进入 Bronze，不能进入 Silver。

---

# 十三、Backend Service Principal 怎么建立

外部 Backend 不应使用个人 PAT。推荐创建单独的 Service Principal，并通过 OAuth machine-to-machine 访问 Databricks SQL。Databricks 当前支持 Service Principal OAuth M2M，Python SQL Connector 也支持这种认证方式。([docs.databricks.com][9])

管理员需要向 Backend 工程师安全地提供：

```text
DATABRICKS_HOST
DATABRICKS_HTTP_PATH
DATABRICKS_CLIENT_ID
DATABRICKS_CLIENT_SECRET
```

`CLIENT_SECRET` 应放在 Backend 所在平台的 secret manager 中，不应放进 Databricks Volume 或 Git。

Backend 验收查询：

```sql
SELECT COUNT(*)
FROM company_intel_dev.gold.company_dashboard_snapshot;
```

应成功，返回 `0` 也算成功。

负向测试：

```sql
SELECT COUNT(*)
FROM company_intel_dev.bronze.source_artifact;
```

应当被拒绝。

如果两条都成功，Backend 权限过大。

---

# 十四、Step 0A 应如何验收

## 验收表

| 编号  | 验收内容              | 负责人           | 通过标准                          |
| --- | ----------------- | ------------- | ----------------------------- |
| A01 | Unity Catalog 可用  | Admin         | `SHOW CATALOGS` 可看到项目 Catalog |
| A02 | Catalog/Schema 建立 | Data          | bronze/silver/gold 全部存在       |
| A03 | Managed Volume    | Data          | 能写入并读取 `_smoke/*.json`        |
| A04 | Delta 表           | Data          | 四张基础表全部存在                     |
| A05 | 所有权               | Admin         | Owner 是 Admin Group，不是个人      |
| A06 | Secret            | Security/Data | Job SP 可读，Backend SP 不可读      |
| A07 | Job Identity      | Data          | Job 以 Job SP 成功执行             |
| A08 | Backend 权限        | Backend       | 能读 Gold，不能读 Bronze/Silver     |
| A09 | Git               | Tech Lead     | DDL 和 Notebook 已提交            |
| A10 | Warehouse         | Admin         | 可连接、自动停止、已设置成本 Tag            |
| A11 | 网络                | Security      | Job compute 可 HTTPS 访问 AV     |
| A12 | 数据一致性             | Data          | Volume 文件 hash 与表中 hash 一致    |

## 验收时应该展示什么

不要只展示截图。应提供：

```text
1. Git commit hash
2. Migration SQL
3. SHOW GRANTS 输出
4. Smoke Job run URL
5. source_artifact 中的 smoke row
6. 对应 Volume 文件路径
7. Backend 正向和负向权限测试
8. SQL Warehouse 配置截图
```

---

# 十五、发给团队的项目说明

可以直接放入 Slack、Teams 或项目 README：

```text
我们正在建立 company-intel 的 Databricks 数据基础。

系统当前以 Alpha Vantage 作为主要公司和财务数据源。
SEC 现阶段只用于验证数据模型，后续只优先接入 AV 不具备的
filing、法律、治理、风险因素和事件证据。

Databricks 的职责：
- 保存不可变原始响应；
- 标准化公司和财务数据；
- 计算派生指标；
- 生成前端可直接消费的 Gold Dashboard Snapshot。

Backend 的职责：
- 只读取 Gold；
- 不访问 Bronze/Silver；
- 不直接调用 Alpha Vantage；
- 不向浏览器暴露 Databricks 凭据。

Frontend 的职责：
- 只渲染 Backend 返回的 sections/components；
- 不执行 SQL；
- 不理解 Alpha Vantage 字段；
- 不实现行业判断。

Step 0A 的交付不是 Dashboard，而是：
- Catalog / Schema / Volume；
- 基础 Delta 表；
- Service Principal 和权限；
- Secret；
- SQL Warehouse；
- 可重复运行的 Smoke Job；
- Git 中的 Migration。
```

---

# 十六、给 Codex 的背景和任务

把下面内容放入 Codex Ticket。

## Codex Context

```text
Project:
Public-company intelligence platform.

Primary source:
Alpha Vantage.

Future SEC usage:
SEC will initially provide only unique filing metadata, risk,
legal, governance, event and evidence content.
SEC financial reconciliation is not part of V1.

Databricks:
Databricks is the source of truth for raw artifacts,
canonical data and Gold Dashboard Snapshots.

Frontend:
Frontend never queries Databricks directly.

Backend:
Backend has SELECT access only to Gold.
```

## Codex Architecture Invariants

```text
1. Use Unity Catalog, never hive_metastore.

2. Store non-tabular raw files in:
   /Volumes/company_intel_dev/bronze/source_artifacts/

3. Store raw file metadata in:
   company_intel_dev.bronze.source_artifact

4. Never store API keys in source code or tables.

5. DDL must be idempotent:
   CREATE ... IF NOT EXISTS.

6. Do not use CREATE OR REPLACE TABLE for migrations.

7. Do not grant Backend access to Bronze or Silver.

8. Job code must run under sp-company-intel-jobs-dev.

9. Object ownership must belong to a Group, not a user.

10. Use UTC timestamps.

11. Financial numbers later use DECIMAL, never float.

12. No production Alpha Vantage response may enter Silver
    until it passes response classification.
```

## Codex 第一个 Ticket

```text
Create the Databricks Step 0A foundation.

Deliverables:
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
- all SQL is idempotent;
- smoke notebook verifies volume and Delta write;
- permissions follow the specified least-privilege matrix;
- all paths and names are parameterized for future environments.
```

当团队开始创建多个 Job 和 CI/CD 时，应把 Job 定义迁移到 Databricks **Declarative Automation Bundles**。Databricks 将 Bundles 定位为适合多人协作和 CI/CD 的基础设施即代码方式；在此之前，可以先手工创建一个 Smoke Job，验证平台和权限，再由 Codex 将其编码。([docs.databricks.com][10])

---

# 十七、常见失败及责任人

| 错误                        | 原因                            | 找谁                   |
| ------------------------- | ----------------------------- | -------------------- |
| `CREATE CATALOG` denied   | 无 metastore 权限                | Databricks admin     |
| Catalog 无 managed storage | Metastore/catalog storage 未配置 | Cloud/platform admin |
| Job 无法写 Volume            | 缺少 `WRITE VOLUME`             | Catalog owner        |
| Job 能写表但不能读 Secret        | Secret Scope ACL 缺失           | Security/admin       |
| Backend 能读 Bronze         | 权限过大                          | Catalog owner        |
| Backend 连接 Warehouse 失败   | 缺少 Can Use 或 OAuth 配置错误       | Workspace admin      |
| Alpha Vantage timeout     | 出站网络被阻止                       | Network/security     |
| Notebook 个人运行成功、Job 失败    | Job SP 权限不完整                  | Databricks admin     |
| 文件上传失败                    | 中文或特殊字符路径                     | 重命名为 ASCII           |
| SQL 成功但 Git 无记录           | 手工变更未同步                       | Tech lead            |

---

# 十八、Step 0A 暂时不要做的事情

```text
不要创建全部 production 表。

不要开始全量抓 8,000 多家公司。

不要让 Spark partitions 并行调用 Alpha Vantage。

不要把 API key 放到 Notebook widget。

不要让 Backend 查询 Silver。

不要让 Frontend 调 Databricks SQL。

不要使用个人目录保存 fixture。

不要在没有 Git Migration 的情况下手工 ALTER TABLE。

不要因为 Step 0A 完成，就认为业务数据模型已经冻结。
```

执行顺序应当是：

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
进入 AV/SEC Spike 和 Metric Schema
```

[1]: https://docs.databricks.com/aws/en/catalogs/create-catalog?utm_source=chatgpt.com "Create catalogs | Databricks on AWS"
[2]: https://docs.databricks.com/aws/en/volumes/utility-commands?utm_source=chatgpt.com "Create and manage Unity Catalog volumes"
[3]: https://docs.databricks.com/aws/en/compute/sql-warehouse/create?utm_source=chatgpt.com "Create a SQL warehouse | Databricks on AWS"
[4]: https://docs.databricks.com/aws/en/repos/?utm_source=chatgpt.com "Databricks Git folders | Databricks on AWS"
[5]: https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/?utm_source=chatgpt.com "Manage privileges in Unity Catalog | Databricks on AWS"
[6]: https://docs.databricks.com/aws/en/security/secrets/?utm_source=chatgpt.com "Secret management | Databricks on AWS"
[7]: https://docs.databricks.com/aws/en/volumes/volume-files?utm_source=chatgpt.com "Work with files in Unity Catalog volumes | Databricks on AWS"
[8]: https://docs.databricks.com/aws/en/jobs/configure-job?utm_source=chatgpt.com "Configure and edit Lakeflow Jobs | Databricks on AWS"
[9]: https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m?utm_source=chatgpt.com "Authorize service principal access to Databricks with OAuth"
[10]: https://docs.databricks.com/aws/en/dev-tools/bundles/?utm_source=chatgpt.com "What are Declarative Automation Bundles?"
