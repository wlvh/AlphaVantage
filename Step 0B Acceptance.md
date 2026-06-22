# Step 0B 验收书

本文用于验收 [Step 0B.md](Step%200B.md) 所定义的本地 Alpha Vantage / SEC 跨源 Spike。

验收重点不是“AV 和 SEC 的所有数字都一致”，而是确认：

```text
1. 运行过程安全、可重复、可离线复核；
2. 跨源数据没有被错误地强行对齐；
3. semantic identity 与 source observation 分离正确；
4. 期间、单位、行业适用性和来源差异都有明确记录；
5. SEC 叙事 finding 可以准确回到原文 evidence；
6. 输出足以决定正式 Silver schema 是否需要调整。
```

---

# 一、验收前需要 Codex 提交什么

代码和配置：

```text
scripts/step_0b/
spikes/step_0b/config/
tests/test_step_0b_*.py
```

报告：

```text
spikes/step_0b/reports/metric_alignment.csv
spikes/step_0b/reports/metric_alignment.md
spikes/step_0b/reports/discrepancy_report.md
spikes/step_0b/reports/schema_decision.md
spikes/step_0b/reports/narrative_finding.json
spikes/step_0b/reports/narrative_finding.md
spikes/step_0b/reports/run_summary.json
```

Codex 还应提供：

```text
执行命令
Python 版本
commit SHA
是否在线运行过
AV 实际调用次数
SEC 实际调用次数
warnings / unresolved mappings
```

Raw 工作文件可以只保存在本地：

```text
spikes/step_0b/work/
```

不要求把大型 raw 文件提交到 Git，但本机验收时必须存在。

---

# 二、验收结论等级

最终结论只能是以下三种之一。

## PASS

```text
所有 Blocking 项通过；
非 Blocking 项没有阻止正式 schema 决策；
可以依据 schema_decision.md 进入 AV V1 开发。
```

## PASS WITH REQUIRED CHANGES

```text
Spike 本身可信，但报告发现正式 Silver schema 必须先修改；
列出必须修改的字段、mapping 或 period 规则；
修改完成后不必重新抓全部数据，但应离线重跑分析。
```

## FAIL

出现任一情况：

```text
API key 泄露
raw 未先保存
离线无法重跑
72 行矩阵不完整且没有合理原因
source 被放进 semantic key
期间明显错配
SEC evidence 无法回到原文
报告为了追求匹配而强行选择概念
```

---

# 三、Blocking 验收清单

以下项目任一失败，Step 0B 不得通过。

## A. 安全与仓库卫生

```text
[ ] 没有 Databricks / PySpark / Delta 依赖
[ ] 没有真实 Alpha Vantage API key
[ ] 没有把 SEC User-Agent 中的私密信息写进不必要的公开报告
[ ] 日志和 manifest 中的 Alpha Vantage URL 使用 REDACTED
[ ] spikes/step_0b/work/ 已被 gitignore
[ ] 没有意外提交大型 SEC companyfacts / filing HTML
[ ] 原有 fixture 和 verifier 没有被无关重写
```

建议命令：

```bash
git status --short
git diff --stat main...HEAD

git grep -n "ALPHAVANTAGE_API_KEY"
git grep -n "apikey="
git grep -nE "pyspark|databricks|delta\.tables"
```

注意：

```text
代码中出现环境变量名 ALPHAVANTAGE_API_KEY 是正常的；
出现具体 key 值或未去密 URL 才是失败。
```

如果怀疑 secret 曾经进入历史：

```bash
git log -p --all -- . | grep -i "apikey="
```

不要把真实 key 复制进 grep 命令。

## B. 测试与离线可重跑

```text
[ ] 原有测试继续通过
[ ] 新增 Step 0B 测试全部通过
[ ] analyze 不需要 API key
[ ] verify --offline 不会联网
[ ] offline 重跑能够重新生成同语义的报告
```

执行：

```bash
python -m unittest discover -s tests -p 'test*.py'
python scripts/step_0b/run_step_0b.py verify --offline
```

验收时可以临时清空环境变量，确认离线命令仍工作：

```bash
unset ALPHAVANTAGE_API_KEY
unset SEC_USER_AGENT
python scripts/step_0b/run_step_0b.py verify --offline
```

如果离线命令尝试网络连接或要求 key，直接 FAIL。

## C. Raw-first 和调用预算

检查 `run_summary.json` 和 manifest：

```text
[ ] IBM 使用已有 fixture，默认没有重新请求
[ ] JPM 五个 AV endpoint 成功或有明确错误记录
[ ] CAT 五个 AV endpoint 成功或有明确错误记录
[ ] 默认 AV live call count <= 10
[ ] 每个成功网络调用都有 raw body、hash、status 和 fetched_at
[ ] 解析错误不会删除 raw
[ ] 重跑默认复用已成功 raw
```

如果 Codex 因 API 错误重试导致调用超过 10，应提供逐次调用说明；无说明视为失败。

## D. 财务对齐矩阵完整性

`metric_alignment.csv` 必须满足：

```text
[ ] 72 条业务行
[ ] 3 家公司
[ ] 12 个 canonical metrics
[ ] 每个 metric 同时有 annual 和 quarterly scope
[ ] 缺失、不适用、歧义行没有被删除
[ ] 每行都有 comparison_status
[ ] 每个非 MATCH 行都有 rationale
```

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

快速检查：

```bash
python - <<'PY'
import csv
from collections import Counter
from pathlib import Path

path = Path('spikes/step_0b/reports/metric_alignment.csv')
rows = list(csv.DictReader(path.open(encoding='utf-8')))

print('rows:', len(rows))
print('companies:', Counter(r['company_key'] for r in rows))
print('scopes:', Counter(r['comparison_scope'] for r in rows))
print('statuses:', Counter(r['comparison_status'] for r in rows))

assert len(rows) == 72
assert len({r['company_key'] for r in rows}) == 3
assert all(r['comparison_status'] for r in rows)
assert all(
    r['comparison_status'] == 'MATCH' or r['rationale'].strip()
    for r in rows
)
PY
```

## E. Semantic key 与 observation ID

抽查至少五组可比较记录：

```text
IBM annual revenue
IBM quarterly net income
CAT annual total assets
CAT quarterly operating cash flow
JPM annual total equity
```

每组必须满足：

```text
[ ] AV 和 SEC semantic_key 相同
[ ] AV 和 SEC observation_id 不同
[ ] semantic key 的输入中没有 source_system
[ ] observation ID 的输入中有 source_system
[ ] period、metric 和 dimensions 相同才共享 semantic key
```

再检查一组不可比记录：

```text
JPM gross profit 或 operating income
```

如果口径不适用或无法映射，应标为 `NOT_APPLICABLE` / `AMBIGUOUS_MAPPING`，不能为了生成相同 semantic key 而伪造值。

## F. 期间选择正确

重点验收：

```text
[ ] Annual AV 值来自 annualReports / 合法 annualEarnings
[ ] Quarterly AV 值来自 quarterlyReports / quarterlyEarnings
[ ] IBM 伪 annual EPS 被排除
[ ] SEC annual 使用 10-K
[ ] SEC quarterly 使用 10-Q
[ ] YTD 没有被静默当单季度
[ ] amendment / restatement 的选择有记录
[ ] 每个 SEC fact 保存 start/end/form/filed/accn
```

必须手工查看以下行：

```text
IBM annual diluted EPS
IBM quarterly diluted EPS
IBM quarterly revenue
CAT quarterly Capex
```

IBM 已知异常：最新 `annualEarnings` 项可能与季度项同日同值。如果该记录出现在 annual comparison，直接 FAIL。

## G. 映射没有被强行简化

检查 JPM：

```text
[ ] Gross Profit 没有被强行映射为一个不等价 concept
[ ] Operating Income 缺失或口径不同有明确状态
[ ] Revenue 映射解释了金融公司口径
[ ] Total Debt 若需要组合，保留所有组件和公式
[ ] Equity 明确说明是否包含 noncontrolling interest
```

验收标准不是 JPM 全部 MATCH，而是边界被诚实记录。

如果 JPM 12 个指标全部显示 MATCH，反而应高度怀疑映射是否被强行处理。

## H. Narrative evidence

打开：

```text
spikes/step_0b/reports/narrative_finding.json
```

检查：

```text
[ ] filing accession、form、filing date、source URL 完整
[ ] finding_type 为 LEGAL_MATTER 或明确的监管事项类型
[ ] evidence_text 是原始 normalized filing text 的精确子串
[ ] evidence_start / evidence_end 能恢复相同文本
[ ] summary 没有增加 evidence 中不存在的事实
[ ] 未披露金额时 amount 为 null
[ ] amount 非 null 时 amount_text 原样存在于 evidence_text
[ ] validation_status = VERIFIED 只用于通过上述验证的 finding
```

执行程序验证：

```bash
python - <<'PY'
import json
from pathlib import Path

finding = json.loads(
    Path('spikes/step_0b/reports/narrative_finding.json')
    .read_text(encoding='utf-8')
)

text_path = Path(finding['normalized_text_path'])
text = text_path.read_text(encoding='utf-8')
start = finding['evidence_start']
end = finding['evidence_end']

assert text[start:end] == finding['evidence_text']
if finding.get('amount_text'):
    assert finding['amount_text'] in finding['evidence_text']
assert finding['validation_status'] == 'VERIFIED'
print('evidence verified')
PY
```

如果实现没有在 finding 中保存 `normalized_text_path`，Codex 必须提供等价的可复核位置；否则无法独立验收。

---

# 四、数据手工抽查

自动测试通过后，至少手工追踪以下五条记录到 raw source。

## 1. IBM Annual Revenue

检查：

```text
AV 是否来自 INCOME_STATEMENT.totalRevenue
期间是否为合法 annual report
SEC concept 和 accession 是否明确
单位是否相同
差异是否与报告一致
```

## 2. IBM Quarterly EPS

检查：

```text
AV 是否来自 quarterlyEarnings.reportedEPS
SEC 是否使用 EarningsPerShareDiluted
是否没有误用 annualEarnings 重复项
```

## 3. CAT Quarterly Capex

检查：

```text
AV capitalExpenditures 的符号
SEC PaymentsToAcquire... concept 的符号
是否只在报告层解释符号，而没有改写原始值
```

## 4. JPM Annual Equity

检查：

```text
SEC 选择 StockholdersEquity 还是含 NCI 的 concept
选择理由
与 AV totalShareholderEquity 的语义是否相当
```

## 5. JPM Gross Profit

预期通常是：

```text
NOT_APPLICABLE
MISSING_SEC
或 AMBIGUOUS_MAPPING
```

如果是 MATCH，要求 Codex 出示非常明确的依据。

---

# 五、报告内容验收

## `discrepancy_report.md`

必须明确回答：

```text
[ ] 哪些指标跨三家公司可直接映射
[ ] 哪些指标需要 composite formula
[ ] 哪些指标有行业适用性限制
[ ] 哪些差异来自期间口径
[ ] 哪些差异来自 amendment / restatement
[ ] 哪些差异可能来自 Alpha Vantage 不透明标准化
[ ] 哪些问题仍需正式 SEC pipeline 才能解决
```

不接受只列数值、没有归因的报告。

## `schema_decision.md`

必须明确写出：

```text
[ ] 推荐 semantic key 的字段
[ ] 推荐 observation identity 的字段
[ ] source_system 不进入 semantic key
[ ] period_start 是否必须
[ ] dimensions / reporting scope 如何表达
[ ] 是否需要 mapping_rule_id
[ ] applicability 如何表达
[ ] composite metric 如何保存 lineage
[ ] 正式 Silver schema 需要哪些修改
[ ] 哪些问题明确推迟到 SEC 财务阶段
```

`schema_decision.md` 应给出决定，不应只是重复“需要进一步研究”。允许有少量 unresolved items，但必须标明负责人和下一步。

## `run_summary.json`

必须包含：

```text
[ ] run ID
[ ] online / offline
[ ] 开始和结束时间
[ ] AV call count
[ ] SEC call count
[ ] raw / fixture hashes
[ ] 输出文件 hashes
[ ] warnings
[ ] unresolved mappings
[ ] key redaction check
```

---

# 六、非 Blocking 但必须记录的问题

以下不必导致失败，但必须进入 discrepancy 或 schema decision：

```text
某个 SEC concept 在一家企业不存在
季度只有 YTD 值
AV 与 SEC 差异超过阈值
Total Debt 无法证明等价
银行 Revenue 定义不统一
某个 filing 没有量化法律金额
SEC amendment 改写了历史值
```

正确做法是分类和记录，不是隐藏。

---

# 七、验收时不应该要求什么

不要把以下内容作为 Step 0B 通过条件：

```text
所有 72 行都 MATCH
自动解析所有 SEC filings
自动提取所有法律事项
生产级 SEC client
数据库或 Databricks 写入
前端页面
LLM 自动抽取
银行专用指标
```

Step 0B 是模型验证 Spike，不是生产数据平台。

---

# 八、最终验收记录模板

复制并填写：

```text
Step 0B Acceptance Record

Repository:
Branch / Commit:
Reviewer:
Review Date:

1. Security and secret scan: PASS / FAIL
Notes:

2. Existing + new unit tests: PASS / FAIL
Command / output:

3. Offline reproducibility: PASS / FAIL
Notes:

4. AV call budget and raw-first: PASS / FAIL
AV calls:
SEC calls:

5. 72-row alignment matrix: PASS / FAIL
Row count:
Status distribution:

6. Semantic / observation identity: PASS / FAIL
Notes:

7. Period handling: PASS / FAIL
Notes:

8. JPM applicability and mapping boundaries: PASS / FAIL
Notes:

9. Narrative evidence binding: PASS / FAIL
Filing:
Finding:
Evidence verified:

10. Reports and schema decision: PASS / FAIL
Required schema changes:

Final Decision:
PASS / PASS WITH REQUIRED CHANGES / FAIL

Required actions before Step 1:
- ...
- ...
```

---

# 九、通过后的下一步

## 如果 PASS

```text
依据 schema_decision.md 创建正式 metric_observation DDL；
进入 Alpha Vantage V1 ingestion；
SEC 只保留 spike 代码和报告，不进入生产财务流。
```

## 如果 PASS WITH REQUIRED CHANGES

```text
先修改正式 schema 设计；
用已有 raw 完全离线重跑；
确认 schema_decision 和报告已更新；
不需要重复消耗 API，除非 raw 确实缺失。
```

## 如果 FAIL

```text
停止冻结 Silver schema；
修复失败项；
优先复用已保存 raw；
只有数据缺失时才重新发网络请求。
```
