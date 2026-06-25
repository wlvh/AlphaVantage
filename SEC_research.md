# Alpha Vantage 与 SEC 财务数据一致性调研

## 一、本次任务
覆盖团队最初关心的五类问题：

1. 七个通用财务指标在公司内跨年、同行间是否保持同一含义；
2. Alpha Vantage 当前历史值更接近 SEC 最早披露还是后续重列；
3. gap 的频率、幅度、集中度和危险度；
4. 同一 SEC SIC 行业中，同名指标是否真正可比；
5. Alpha Vantage 的基础财务接口是否覆盖行业或公司特有 KPI；
6. 另外用 total debt 检验复杂派生指标能否套用一个固定公式。

本报告使用 7 家公司、FY2019–FY2024、7 个通用指标，形成 294 个预先定义的研究单元；其中 290 个能取得完整的产品定义 SEC reference，并生成了 720 条 SEC 历史版本记录、126 条同行比较记录和 13 条特有 KPI 探索记录。


---

## 二、研究对象、指标定义和数据方法

### 2.1 样本与同行组

研究对象：MSFT、ORCL、XOM、CVX、F、GM、IBM。

研究期：FY2019–FY2024。每家公司使用自己的 fiscal year end；例如 Microsoft 与 Oracle 的财年结束日不同，因此同行比较是按 fiscal-year label 与精确 period end 共同解释，而不是假装它们是同一日历期间。

SEC 四位 SIC 同行组：

- 软件：MSFT / ORCL，SIC 7372；
- 石油炼制：XOM / CVX，SIC 2911；
- 汽车制造：F / GM，SIC 3711；
- IBM，SIC 3570，单独用于历史重列、公司内定义漂移和特殊 KPI 案例。

### 2.2 七个通用指标的详细定义


| 指标 | 本研究的产品定义 | 主要 SEC concept | 期间类型 |
|---|---|---|---|
| Total assets | 合并主体在期末确认的全部资产账面金额 | `Assets` | Instant，期末时点 |
| Total liabilities | 合并主体在期末确认的全部负债账面金额 | `Liabilities`；缺失时允许同 accession 下由资产减含 NCI 权益推导 | Instant |
| Shareholders’ equity | 归属于母公司股东的权益，**不含 NCI** | `StockholdersEquity` | Instant |
| Cash and cash equivalents | 非受限现金、活期存款及极高流动性且接近到期的现金等价物，**不含 restricted cash** | `CashAndCashEquivalentsAtCarryingValue` | Instant |
| Revenue | 合并层面的 broad top-line revenue，即利润表最高层级、覆盖公司全部收入活动的总收入行 | 通常为 `Revenues`，但逐 company-year 核对主利润表 | Duration，完整财年 |
| Net income | 归属于母公司的净利润，不是扣除优先股等项目后的 available-to-common | `NetIncomeLoss` | Duration |
| Operating cash flow | 完整财年经营活动产生/使用的净现金流 | `NetCashProvidedByUsedInOperatingActivities` | Duration |

#### 2.2.1 什么是 restricted cash，为什么本研究排除它

`CashAndCashEquivalentsAtCarryingValue` 包括手头现金、银行活期存款，以及可随时转换为已知现金金额、利率风险极低的短期高流动性投资。

**Restricted cash（受限现金）**仍然是公司的现金，但其使用受到合同、法律、监管或担保安排限制。现金流量表通常会把“现金、现金等价物及受限现金”一起做期初—期末勾稽，但这不表示资产负债表上的普通 cash balance 应自动包含受限现金。

#### 2.2.2 什么是 broad consolidated revenue

本研究的 Revenue 指标不是“任何带 revenue 字样的数字”，而是：

> 合并集团在完整财年利润表上最高层级的总收入行，覆盖该公司作为收入列示的全部业务来源。

在 SEC taxonomy 中，`Revenues` 是较宽的概念；`RevenueFromContractWithCustomerExcludingAssessedTax` 更聚焦于与客户合同产生、且扣除代政府收取税款的收入。对石油公司，后者往往接近 sales/customer revenue，却可能不包含公司在 broad revenue 行中列示的其他收入组成。

本研究选择 broad consolidated revenue 的理由不是“SEC 规定它永远更正确”，而是一个明确的产品设计决定：

1. Alpha Vantage 字段叫 `totalRevenue`，普通用户自然会把它理解为公司总收入，而不是仅某一种销售收入；
2. broad top-line 更容易跨行业形成一个共同的“公司总收入”概念；
3. 它能揭示供应商是否在某些年份静默改取较窄 sales line；
4. 该定义能与合并利润表最高层级勾稽，而不是把收入的一部分当作全部。

但 narrow sales/customer revenue 本身不是错误指标。若产品真正想展示“sales excluding other revenue”，完全可以采用窄口径；关键是必须独立命名，并在所有公司和年份保持同一口径。本研究检验的是：AV 的 `totalRevenue` 是否稳定满足事先声明的 broad contract。

### 2.3 SEC 数据源分别是什么，JSON 结构如何使用

#### 2.3.1 Submissions API

研究使用的 company submissions JSON，可以理解为公司的“申报目录和元数据索引”。核心内容包括：

- 公司 CIK、名称、ticker、SIC 和 SIC description；
- 最近 filing 的数组字段，例如：
  - `accessionNumber`
  - `filingDate`
  - `reportDate`
  - `form`
  - `primaryDocument`
- 更老 filing 可能通过额外 JSON 文件引用。

本研究用它来：

1. 确认 SEC SIC；
2. 找出目标 10-K / 10-K/A；
3. 定位 filing 的 accession 和 primary HTML document；
4. 判断某一历史期间之后是否还有更晚年报存在。

Submissions API **不直接提供全部财务数值**；它主要告诉我们有哪些申报、何时申报、对应哪个文件。

#### 2.3.2 Company Facts API

Company Facts JSON 是 SEC 从 XBRL filings 中提取和聚合的结构化事实。其层级大致为：

```text
facts
  └── taxonomy namespace，例如 us-gaap
        └── concept，例如 Assets、Revenues
              ├── label
              ├── description
              └── units
                    └── USD / shares / USD-per-share 等
                          └── fact records
```

每条 fact record 常见字段包括：

- `val`：数值；
- `start` / `end`：期间起止；instant fact 通常只有 `end`；
- `accn`：该事实来自哪一份 filing；
- `filed`：申报日期；
- `form`：10-K、10-Q 等；
- `fy` / `fp`：filing 标示的财年与 fiscal period；
- `frame`：SEC 计算的标准化时间框架，若存在。

本研究用 Company Facts 来建立：

- 同一 company–metric–fiscal-year 在不同 filing 中的版本时间线；
- exact standard concept 的数值；
- 同期不同概念的候选匹配，例如 parent equity 与 equity incl. NCI。

Company Facts 不是完整 filing 的替代品。它对 custom tags、维度化事实、表格上下文和文字 KPI 的覆盖有限，因此 revenue scope、特殊 KPI 和复杂 debt 仍需回到 filing HTML / Inline XBRL。

#### 2.3.3 10-K HTML 与 Inline XBRL

Inline XBRL 是同一个文件中同时保留：

- 人可以阅读的财务报表、表格和文字；
- 机器可以读取的 concept、context、unit 和 value。

本研究用 filing HTML / Inline XBRL 来：

- 确认利润表可见行名称；
- 判断 revenue 数字是 broad total revenue 还是 narrow sales；
- 检查行业 KPI 所在表格或文字；
- 保存实际 source filing，而不是只给一个泛化的公司页面。

#### 2.3.4 Alpha Vantage 数据

检查的四个 fundamentals endpoints：

- `BALANCE_SHEET`
- `INCOME_STATEMENT`
- `CASH_FLOW`
- `OVERVIEW`

本研究使用的是抓取时刻的 AV 当前历史快照。它不能还原“AV 在 2020 年当日曾经返回什么”，只能回答“AV 今天对 FY2020 返回什么”。

### 2.4 关键术语

#### XBRL concept / tag

XBRL concept 是一个标准化语义标识，例如 `Assets`。通俗说，**tag** 是附在 filing 中某个可见数字上的机器标签。一个数字叫“现金”，并不代表其 tag 一定是本研究想要的 cash concept，因此仍需看标签、上下文和 scope。

#### Direct tag

**Direct tag** 表示 filing 直接报告了目标 concept 的 fact。例如资产负债表直接存在 `Liabilities = 131.7B`。

它与 derived value 不同。若 filing 没有 direct `Liabilities`，但同一份 filing 存在：

```text
Assets − StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest
```

则可以利用资产负债表恒等式推导 liabilities。这个结果可能数值完全正确，但 provenance 必须显示“derived”，不能说 filing 直接披露了该行。

#### NCI 与 equity incl. NCI

NCI（noncontrolling interest，非控股权益）是：合并报表中已经纳入集团资产、负债和利润，但由母公司之外的其他股东持有的子公司权益。

- `StockholdersEquity`：只包括归属于母公司股东的权益；
- `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`：母公司权益 + NCI。

若 AV 某年取后者、下一年取前者，字段名不变，但时间序列 scope 已改变。具体例子看后续介绍。

#### Accession number

Accession number 是 EDGAR 为一份电子 submission 分配的唯一标识，例如：

```text
0000950170-24-075605
```

它用于精确指向“哪一次提交的哪一份 filing”，而不是只指向某家公司或某个财年。格式大体包含提交者 CIK、年份和序号。

#### 为什么强调 same accession

“同一 accession”表示一个公式中的所有组件来自同一份 SEC submission。

例如不能用 2024 年报中的 Assets，减去 2025 年报对 2024 年重列后的 equity，然后声称结果来自一个可审计的 2024 filing。跨 accession 混合可能把不同版本、不同 scope 或不同修订状态拼到一起。

因此，本研究对 derived liabilities 和 debt reconciliation 要求：组件必须同期间、同单位、同 accession。

### 2.5 294 个 eligible cells 如何计算

**Eligible cell** 是研究设计中预先要求评价的最小单元：

```text
一个公司 × 一个 fiscal year × 一个核心指标
```

它不要求 AV 或 SEC 一定有值；只要在研究范围内，就算 eligible。这样可以避免因为缺失数据而悄悄缩小分母。

计算为：

```text
7 家公司 × 6 个 fiscal years × 7 个指标 = 294
```

之后再逐层区分：

- endpoint available：AV endpoint 是否成功；
- SEC-verifiable：产品定义能否由 SEC 证据支持；
- comparable：AV 值与产品定义 SEC reference 都存在；
- flagged：是否需要警告、复核或判为高风险。

本研究 294 个 eligible cells 中，290 个具有完整产品定义 SEC reference。其余 4 个为：2 个 CVX cash exact reference 缺失，以及 Ford FY2019/FY2020 只找到 available-to-common net income，未找到独立 parent fact。

### 2.6 720 条 version timeline 如何产生

`version_timeline.csv` 的一行不是一个新指标，而是：

> 同一个 company–metric–fiscal-year 在某一份具体 10-K / 10-K/A 中被再次展示的一次版本记录。

为什么一项历史数字会有多行？因为后续年报会展示比较期：

- 资产负债表常展示两个期末；
- 利润表和现金流量表常展示三个年度；
- 因此 FY2019 revenue 可能在 FY2019、FY2020 和 FY2021 filing 中出现。

290 个有 SEC timeline 的 cells，其版本数分布为：

- 4 个 cells 只有 1 次展示；
- 143 个 cells 有 2 次展示；
- 142 个 cells 有 3 次展示；
- 1 个 cell 有 4 次展示。

所以：

```text
4×1 + 143×2 + 142×3 + 1×4 = 720
```

这 720 条记录不是 720 个独立统计样本，而是 290 个指标单元的版本轨迹。

---

## 三、七个通用指标的审计结论

| 指标 | 样本结果 | 主要风险 | 最终判断 |
|---|---:|---|---|
| Total assets | 42/42 匹配产品定义；41 exact、1 rounding | 极低 | 最适合 AV fast path |
| Total liabilities | 41/42 匹配 latest-known；21/42 需推导 | direct tag 缺失、版本选择 | 可用，但必须标注 direct/derived |
| Parent equity | 37/42 匹配；5/42 实际匹配含 NCI equity | scope 跨公司/跨年漂移 | 必须逐 company-year reconciliation |
| Cash | 40 个可验证 cells 中 39 匹配、1 使用旧版本；另 2 个不可验证 | restricted cash 与历史版本 | exact tag 可 fast path，否则不可猜 |
| Revenue | 30/42 匹配 broad；11/42 匹配较窄收入；1/42 使用旧版本 | scope 与版本漂移最集中 | 不能仅凭 `totalRevenue` 使用 |
| Parent net income | 40 个可验证 cells 中 39 匹配、1 匹配 common；另 2 个只找到 common concept | parent vs common | 需 reconciliation |
| Operating cash flow | 40/42 exact/rounding；1 个小额差异；1 个重大未解释差异 | 舍入、供应商映射 | 整体稳定但需异常监控 |

### 3.1 Total assets

42/42 均匹配产品定义。IBM FY2020 的 AV 值与 SEC 相差 1M，相对于约 156B 资产属于展示精度差异。

资产是本样本中最稳定的指标，但它不能代表所有标准指标，因为 revenue、equity 和 net income 存在 scope 选择问题。

### 3.2 Total liabilities：数字能对上，不等于 filing 有 direct tag

**具体例子：ORCL FY2024。**

该期 Company Facts 中没有 direct `Liabilities`，但同一 accession `0000950170-24-075605` 中存在：

```text
Assets                                      140.976B
− Equity including NCI                        9.239B
= Derived total liabilities                 131.737B
```

Alpha Vantage `totalLiabilities` 也是 131.737B。

结论：AV 数字可通过推测重现，但它不是 direct SEC fact；产品 source 面板应写“Derived: Assets − equity incl. NCI”，并显示组件 accession。否则用户在资产负债表中找不到一条同名 131.737B 的 direct line，会误以为 source link 对不上。

### 3.3 Shareholders’ equity：IBM 证明同字段可在公司内跨年变义

IBM AV `totalShareholderEquity`：

| IBM FY | AV | Parent equity | Equity incl. NCI | AV 实际口径 |
|---|---:|---:|---:|---|
| 2019 | 20.985B | 20.841B | 20.985B | 含 NCI |
| 2020 | 20.725B | 20.597B | 20.727B | 含 NCI，2M rounding |
| 2021 | 18.996B | 18.901B | 18.996B | 含 NCI |
| 2022 | 21.944B | 21.944B | 22.021B | Parent |
| 2023 | 22.533B | 22.533B | 22.613B | Parent |
| 2024 | 27.307B | 27.307B | 27.393B | Parent |

FY2022 是切换点。字段名没有变化，但 FY2019–FY2021 包含第三方持有的子公司权益，FY2022 起不包含。这会把一个会计 scope 变化混进时间序列趋势。

CVX FY2021 和 GM FY2024 也出现 AV 匹配 equity incl. NCI，而非本研究定义的 parent equity。

### 3.4 Cash：IBM FY2020 显示的是版本风险

IBM FY2020：

- 最早披露 cash：13.212B；
- 后续 filing 的 latest-known：13.188B；
- AV 当前历史值：13.212B。

AV 匹配最早版本，而不是后续版本，差 24M。这个数看起来正常，不会像 missing 一样提醒用户，因此属于静默历史版本风险。

另外，CVX FY2019 与 FY2024 缺少本研究要求的 exact `CashAndCashEquivalentsAtCarryingValue` reference；虽然 filing 可能有 cash-plus-restricted-cash 数据，但不能把它自动当作普通 cash。正确状态是不可验证，而不是猜测拆分。

### 3.5 Revenue：XOM 与 CVX 显示字段含义可在公司间和年份间漂移

本研究把 revenue 定义为 broad consolidated top-line。XOM 的 AV `totalRevenue` 六年持续匹配较窄的 “Sales and other operating revenue”，而不是 broad revenue：

| XOM FY | AV / narrow sales | Broad revenue | 差异 |
|---|---:|---:|---:|
| 2019 | 255.583B | 264.938B | 9.355B |
| 2020 | 178.574B | 181.502B | 2.928B |
| 2021 | 276.692B | 285.640B | 8.948B |
| 2022 | 398.675B | 413.680B | 15.005B |
| 2023 | 334.697B | 344.582B | 9.885B |
| 2024 | 339.247B | 349.585B | 10.338B |

这些不是无法解释的算术错误，而是 AV 取了另一条可见报表行。

CVX 更危险：FY2019–FY2021 取 narrow，FY2022 突然取 broad，FY2023–FY2024 又回到 narrow。即使用户只看一家公司，AV `totalRevenue` 的年度趋势也不是同一语义口径。

IBM FY2020 还展示了版本问题：AV 为 73.621B，更接近 earliest 73.620B，而 latest-known 已重列为 55.179B。

### 3.6 Net income：概念不同有时数值相同，有时会真实影响图表

GM FY2023：

```text
AV netIncome                                  10.022B
NetIncomeLoss attributable to parent          10.127B
Available to common                           10.022B
```

AV 匹配 available-to-common，而不是 parent net income，少 105M。原因是 available-to-common 还扣除了优先股、参与证券等属于普通股股东之前的项目。

Ford FY2019/FY2020 只找到 available-to-common concept，AV 与其一致；由于没有独立 parent fact，不能证明 parent 值不同。因此 Ford 是“概念不同、当前观察值没有证实差异”的低风险定义警告，不能与 GM 的真实数值差异混为一类。

### 3.7 Operating cash flow：整体稳定，但仍有一个未解释重大差异

42 个 cells 中 40 个 exact/rounding。

CVX FY2019–FY2022 的 AV 值呈现 0.1B 粗粒度舍入，例如 FY2020 AV 10.600B、SEC 10.577B，差 23M，更符合一致的供应商舍入模式，而不是独立经济口径变化。

IBM FY2023：

```text
AV operatingCashflow          13.432B
SEC operating cash flow       13.931B
差异                           0.499B（约 3.58%）
```

在已检查的 concept、期间和版本中没有找到另一条可解释的 SEC line，因此它是本研究保留的唯一重大、尚未解释的纯数值差异。

---

## 四、SEC 最早披露值与后续重列

### 4.1 “表示方式改变”不等于“数值被修改”

程序原始时间线曾把 24 个 cells 归为后续呈现发生变化，但其中包含：

- concept 变了、数值相同；
- direct fact 改成 derived representation；
- scope/标签变化但数值未变。

人工审计后，真正数值变化的是 6 个 cells；另外 18 个只是表示方式或 concept 变化。

| Company / FY / Metric | Earliest | Latest | 当前 AV | AV 更接近 |
|---|---:|---:|---:|---|
| IBM 2019 revenue | 77.147B | 57.714B | 57.714B | Latest |
| IBM 2020 revenue | 73.620B | 55.179B | 73.621B | Earliest |
| IBM 2020 cash | 13.212B | 13.188B | 13.212B | Earliest |
| GM 2022 liabilities（derived） | 191.752B | 192.110B | 191.753B | Earliest |
| GM 2023 liabilities（derived） | 204.757B | 204.875B | 204.757B | Earliest |
| IBM 2019 liabilities（derived） | 131.202B | 131.201B | 131.201B | Latest |

在这 6 个真实变化 cells 中：

- AV 更接近 earliest：4/6；
- AV 匹配 latest：2/6；
- neither：0/6。

样本太小，不能估计 AV 全市场历史回填策略；但足以证明它不是统一“全部回填 latest”或“全部保留 earliest”。

### 4.2 IBM FY2019 具体发生了什么

IBM FY2019 revenue：

1. FY2019 filing 首次披露 77.147B；
2. FY2020 10-K 仍展示 77.147B；
3. FY2021 10-K 将 FY2019 revenue 重列为 57.714B；
4. 更晚 filing 不再展示 FY2019 revenue；
5. AV 当前 FY2019 revenue 为 57.714B，匹配 latest-known。

IBM FY2019 net income 在观察到的后续重复展示中没有变化。更晚 filing 未再次展示时，只能写“未重新展示”，不能写“以后没有修改”。

---

## 五、Gap 的定义、频率、幅度、集中度和危险度

### 5.1 什么是“静默语义或历史版本差异”

本报告中的 **silent semantic or version difference** 必须同时具备：

1. AV 返回了一个非空、数量级合理的数字；
2. 数字不会主动提醒用户有问题；
3. 但它对应的并不是产品定义的 SEC concept/scope，或者使用了另一历史版本；
4. 用户点击产品所声称的 source filing / line 时，不能按产品定义直接重现该数字；
5. 该差异对数值产生了用户可见影响。

例子：

- IBM equity 含 NCI，而产品定义排除 NCI；
- CVX revenue 某年取 broad、其他年取 narrow；
- GM net income 取 available-to-common 而非 parent；
- IBM FY2020 revenue 使用 earliest，而 latest-known 已被重列。

它比 missing 更危险，因为数字“看起来正常”。

### 5.2 “warning/error cells”到底是什么


**flagged review cells：需要警告、解释、复核或阻断的研究单元。**

定义为 danger level 不是 `NONE` 的 eligible cell。审计后共 34 个：

- D1：2 个可见缺口；CVX 某年度 cash。AV 有 cash 数值但没有找到满足口径的 exact SEC cash fact
- D2：11 个低影响定义/舍入警告；定义不同但当前数值相同，或者差异很小，暂时不影响趋势。Ford FY2019 net income，AV 匹配 available-to-common net income：47M。SEC希望的是 parent net income。但该期没有找到独立 parent fact 来证明两者数值不同
- D3：1 个重大但尚未解释的数值差异；例子：IBM FY2023 operating cash flow。
- D4：20 个静默语义或版本差异。例如：
  * IBM FY2019 equity：AV 包含 NCI，SEC定义不包含；
  * ICVX FY2024 revenue：AV 是较窄的 customer/sales revenue，而SEC定义是 broad revenue；
  * IGM FY2023 net income：AV 是 available-to-common 10.022B，parent net income 是 10.127B；
  * IIBM FY2020 revenue：AV 使用了较早历史版本，而后续 filing 已经重列。

因此 34 并不等于“34 个 AV 错误”。其中包含：

- 供应商可能的语义选择问题；
- SEC exact reference 缺失；
- 合理舍入；
- 历史版本选择；
- 真正未解释的数值差异。

### 5.3 频率

294 个 eligible cells 中：

- AV endpoint 和字段可用：294/294；
- 产品定义可由 SEC 完整验证：290/294；
- 产品契约匹配：268/290（92.4%）；
- 有数值影响的静默语义或历史版本差异：20/290（6.9%）；
- 尚未被语义或版本解释的数值差异：2/290（0.7%）；
- 完整产品定义不可验证：4/294。

其中 2 个未解释差异分别为 CVX FY2020 OCF 的 23M 舍入型差异，以及 IBM FY2023 OCF 的 499M 重大差异。

### 5.4 幅度

20 个静默语义/版本差异：

- 绝对差中位数：3.482B；
- p90：10.338B；
- 最大：18.442B（IBM FY2020 revenue 版本差）；
- 相对差中位数约 2.44%；
- 最大相对差约 33.42%。

这说明主要风险不是小数点误差，而是另一条报表行或另一历史版本。

### 5.5 集中度

34 个 flagged review cells 中，revenue 贡献 13 个；equity、net income、operating cash flow 各 5 个。

20 个 D4 中：

- Revenue：12/20；
- Equity：5/20；
- Net income、cash、liabilities：各 1/20。

Revenue + equity 合计 17/20，即 85%。问题明显集中在 scope-sensitive 指标，而不是均匀分布在所有字段。

### 5.6 危险等级

- **D1 — Visible gap**：SEC product reference 缺失或明显不可验证，用户通常能看到缺口；
- **D2 — Low-impact definition/rounding warning**：概念不同但当前值相同、或仅小额舍入；
- **D3 — Material unexplained numeric difference**：重大数值差，尚无已确认语义或版本解释；
- **D4 — Silent semantic/version difference**：数字存在且合理，但 scope、concept 或版本不满足产品定义，并造成用户可见数值影响。

D4 典型案例：IBM equity 跨年 NCI 切换、CVX revenue FY2022 口径反转、XOM 六年取 narrow sales、GM FY2023 common-vs-parent net income、IBM FY2020 revenue/cash 使用 earliest。

---

## 六、同行业同指标是否可比

### 6.1 MSFT / ORCL（SIC 7372）

核心财务指标总体最干净。ORCL liabilities 经常需要由资产负债表恒等式推导，因此数值可比，但 source presentation 不相同；图表或 API metadata 应标记 direct/derived。

Revenue 的 exact concept 可能不同，需确认是否都表示 consolidated top-line。RPO 与 cloud revenue 不应因为名称相似就直接混画：MSFT cloud revenue 披露绝对金额，ORCL 某期披露为总收入占比，单位和表达方式不同。

### 6.2 XOM / CVX（SIC 2911）

资产负债表指标大多可比。Revenue 不可直接使用 AV `totalRevenue`：XOM 六年为 narrow sales，CVX 五年 narrow、一年 broad。

Production volume 可换算成 boe/day 后比较，但还需确认净额/总额、权益法范围和产品组合；proved reserves 单位可统一，但地理范围、权益口径和油气构成仍需脚注。

### 6.3 F / GM（SIC 3711）

核心指标总体可比，但 GM FY2023 net income 与 GM FY2024 equity 存在 scope 问题。Ford FY2019/FY2020 没有独立 parent net-income fact，只能把 available-to-common 作为替代证据。

Wholesales、retail sales、deliveries、total vehicle sales 不是天然同义词；汽车金融子公司还会影响资产、负债、收入和 debt 的合并范围。

---

## 七、行业或公司特有 KPI：候选如何产生，AV 是否覆盖

### 7.1 这些 KPI 是 SEC 自动提示的吗

**不是。** 本研究采用的是“假设驱动的定向探索”，不是让 SEC 自动生成 KPI 清单。

候选来源有两部分：

1. 最初任务要求探索行业/公司特有 KPI；
2. 研究者基于业务模式预先提出候选 family：
   - 软件：RPO、cloud revenue；Remaining Performance Obligations
   - 石油：production volume、proved reserves；
   - 汽车：wholesales、retail sales/deliveries；
   - IBM：RPO。

随后才用 SEC filing 验证这些 KPI 是否真实存在、在哪里披露、是否结构化。

其中 RPO 有标准 `us-gaap:RevenueRemainingPerformanceObligation` concept，因此可直接在 Company Facts 中发现；cloud revenue、产量、储量和车辆销量主要通过最新两份 10-K 的表格/文字关键词和公司特定抽取规则找到。

因此，13 条记录代表“预先选定的 7 个 KPI family 在对应公司上的验证”，不是对 filing 中所有特殊 KPI 的穷尽式发现。报告应把它称为 targeted exploration，不能声称已经枚举全部公司 KPI。

### 7.2 实际调查结果

13 条 KPI 探索记录中：

- SEC 找到可量化披露：12/13；
- SEC 未找到可比总量：1/13（Ford retail-sales total）；
- AV 四个 fundamentals endpoints 中找到同语义字段：0/12；
- 找到有意义 proxy：0/12。

SEC 披露结构：

- Standard XBRL：3 条（MSFT、ORCL、IBM 的 RPO）；
- Filing tables：6 条；
- Filing text：3 条；
- Not found：1 条。

示例：

- MSFT RPO 375B、ORCL RPO 638B、IBM RPO 71B；
- MSFT cloud revenue 168.9B，ORCL cloud revenue 披露为总收入的 51%；
- XOM production 4.736M boe/day、proved reserves 19.311B boe；
- CVX production 3.7M barrels/day、reserves 10.591B boe；
- Ford wholesales 4.395M units、GM wholesales 3.799M units；
- GM total vehicle sales 6.184M units，但定义包括 retail、fleet 和部分 dealer-use，不等于 Ford retail sales。

普通 `RevenueTTM` 不是 cloud revenue、产量、储量或车辆销量的 proxy，因为业务对象、单位和分析用途不同。

结论：在本次定向测试的 AV fundamentals endpoints 中，特殊 KPI 同语义覆盖为 0/12。该结论不能外推到 AV 全部产品线，但足以证明当前四个基础接口无法满足这一需求。

---

## 八、Total debt 派生指标：哪些是 SEC 事实，哪些是研究者推断

### 8.1 不是 SEC 提供了一套“通用公式”

SEC 提供的是标准 concepts、每个 concept 的定义和公司实际申报的 facts。例如：

- `DebtCurrent`：短期债务、长期债务当期到期部分及某些租赁义务的 current total；
- `LongTermDebt`：长期债务 carrying amount，taxonomy 定义排除 capital/finance lease；
- `LongTermDebtNoncurrent`：长期债务非流动部分；
- `LongTermDebtAndCapitalLeaseObligations`：非流动长期债务与租赁义务的合并 parent；
- `FinanceLeaseLiability`：融资租赁付款义务的现值；
- `OperatingLeaseLiability`：经营租赁付款义务的现值；
- `DebtLongtermAndShorttermCombinedAmount`：长期债务（含当期到期部分）与短期债务的 aggregate。

这些 concept 名称、定义和 fact 数值来自 SEC/XBRL。

### 8.2 哪些部分是本研究自己定义和推导的

以下内容是**研究者定义的产品口径和 resolution paths**，不是 SEC 官方给出的 universal total-debt formula：

1. 产品选择是否包含 finance lease、是否排除 operating lease；
2. 当 direct combined debt tag 缺失时，尝试哪些 parent/component 组合；
3. 什么时候可以从 inclusive debt 中减去 finance lease；
4. 什么时候只能标记 candidate 或 partial；
5. 同值 fact 是否触发 overlap red flag；
6. 必须同 accession、同期间、同单位才能相加减。

换言之：

> SEC 提供原材料和语义定义；本研究提出指标契约与推导假设，再用 SEC facts 进行证伪和 reconciliation。

### 8.3 为什么使用 broad current debt、debt-and-capital-lease parent 等路径

这些路径不是凭空猜测，而是利用 taxonomy concept 的明确定义构建的候选恒等关系。例如：

```text
DebtCurrent
+ LongTermDebtAndCapitalLeaseObligations
```

在语义上尝试覆盖 current debt 与 noncurrent debt-and-lease；若要得到 ex-finance-lease 指标，再减去同一 accession 的 finance lease liability。

但该公式只有在以下条件成立时才可接受：

- parent/component scope 明确；
- components 不重叠；
- 同一 accession；
- 同一 period 和 unit；
- finance lease 可独立解析；
- 数学 reconciliation 成立。

若缺乏这些证据，就必须返回 candidate、partial 或 unresolved。

### 8.4 为什么不能说这些推导就是 ground truth

本研究没有为全部债务案例逐项人工阅读 debt footnote 并确认发行人的自定义标签、金融子公司维度和 measurement basis。因此 “fully resolved” 更准确地说是：

> **resolved under standard-tag semantics and same-accession reconciliation。**

它不是对所有 filing 经济实质的绝对认证。

债务实验 24 个 metric rows 中：

- fully resolved：8；
- candidate：4；
- partial：6；
- unresolved：6。

这证明固定三标签公式不通用，但也不等于 SEC 永远无法构造 debt；正确做法是按 metric contract、标签族和 evidence level 分层。

---

## 九、产品与架构建议

### Tier 1：AV fast path + provenance

- Total assets；
- 有 direct fact 或可清楚解释 derived provenance 的 liabilities；
- exact cash concept 可验证的 company-year；
- 未触发异常的 operating cash flow。

即使 Tier 1，也应保存 fiscal period、AV field、SEC concept、accession 和 retrieval timestamp。

### Tier 2：AV 候选值 + SEC reconciliation

- Revenue；
- Parent equity；
- Parent net income；
- historical restatement-sensitive metrics；
- derived liabilities。

验证粒度必须是 company × fiscal year，而不是按公司配置一次后永久复用。

### Tier 3：SEC filing / custom KPI track

- RPO、cloud revenue、production、reserves、vehicle volume；
- 其他公司特有 KPI；
- custom XBRL、filing tables 和 filing text；
- total debt 等复杂派生指标。

不必一开始全量解析所有 SEC filings。更合理的是按 metric family 分层：标准 headline 指标 fast path，scope-sensitive 指标后台 reconciliation，特殊 KPI 和复杂 debt 才进入 filing track。

### Source link 规则

- Direct fact：链接实际提供该 fact 的 accession；
- Derived value：展示公式、组件和同 accession；
- AV 匹配另一 concept：不能链接产品契约 concept 并声称可重现；
- 历史值：明确标注 as-reported 或 latest-known；
- 无法证明语义：返回 unavailable，不猜测。

---

## 十、最终结论

1. Alpha Vantage 不是整体不可用。Total assets 等简单 headline facts 在本样本中表现很好。
2. 主要风险不是频繁算错，而是同字段名的语义、scope 或历史版本不稳定。
3. IBM equity 与 CVX revenue 证明同一个 AV 字段可在同一家公司跨年度改变含义。
4. 在 290 个完整可比较 cells 中，268 个匹配产品定义；20 个存在有数值影响的静默语义/版本差异；2 个为尚未完全解释的数值差异。
5. AV 历史回填策略不统一：6 个真实数值变化 cells 中，4 个更接近 earliest，2 个匹配 latest。
6. 本次定向探索的 SEC 特殊 KPI 中，AV 四个 fundamentals endpoints 同语义覆盖为 0/12。
7. 同行可比性必须基于 metric contract 和 SEC scope，而不是 API 字段名。
8. Total debt 的公式是研究者提出并由 SEC facts 验证的候选推导，不是 SEC 官方通用定义；证据不足时必须 abstain。


---

## 十一、证据文件

- `output_v4/av_sec_cell_analysis.csv`
- `output_v4/company_year_metric_mapping.csv`
- `output_v4/version_timeline.csv`
- `output_v4/peer_metric_comparison.csv`
- `output_v4/special_kpi_analysis.csv`
- `output_v2/debt_resolution.csv`
- `output_v2/vendor_contract.csv`
- `data_v3/raw/sec/*_companyfacts.json`
- `data_v3/raw/sec/*_submissions.json`
- `data_v3/raw/sec/*_10-K HTML`
- `data_v3/raw/alphavantage/*`

