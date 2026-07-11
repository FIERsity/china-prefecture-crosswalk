# China Urban Research Entity Crosswalk

[![Data validation](https://github.com/FIERsity/china-prefecture-crosswalk/actions/workflows/validate.yml/badge.svg)](https://github.com/FIERsity/china-prefecture-crosswalk/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue.svg)](LICENSE-DATA)
[![Version](https://img.shields.io/badge/data-v2.0-1f6e5a.svg)](data/releases/v2.0)

面向中国城市面板研究的地级行政实体数据库与名称匹配工具。

项目提供稳定研究实体编号、历史名称区间、年度法定状态、行政区划变更事件和可解释的批量匹配工具，帮助研究者处理统计年鉴、城市面板、OCR资料和跨期名称变化。

> `CNUR-000001` 等 CNUR 编号是本项目的永久研究编号，不是民政部、国家统计局或任何年份的官方行政区划代码。

## 在线工具

**[打开 China Urban Research Crosswalk](https://china-prefecture-crosswalk.onrender.com)**

网页提供四个入口：

- 数据库浏览与 V2.0 CSV/Excel 下载；
- 上传 CSV/XLSX 批量匹配城市名称；
- 单个名称、年份和省份查询；
- 1987—2026 行政区划事件与维基原始证据检索。

上传文件只在当前会话内存中处理，不持久化。OCR和模糊结果必须人工确认；合并、拆分和代管关系不会自动重算研究变量。

## V2.0 数据概览

| 内容 | 数量/范围 |
|---|---:|
| 永久 CNUR 实体 | 347 |
| 2000—2024 面板实体 | 340 |
| 补充历史实体 | 5 |
| 实体—年度状态 | 13,880（1987—2026） |
| 统一地级变更事件 | 144 |
| 事件关系 | 149 |
| 维基地级原始记录 | 988 |
| 连续性审计 | 1,208 项，0 错误 |

直辖市在研究实体体系中按地级等价单位处理。347个实体是跨期实体总数，不代表任一年度同时存在347个法定地级单位。

## 推荐下载

| 文件 | 用途 |
|---|---|
| [`china_city_entity_master_V2.0.csv`](data/releases/v2.0/china_city_entity_master_V2.0.csv) | 机器读取、R/Python合并 |
| [`china_city_entity_master_V2.0.xlsx`](data/releases/v2.0/china_city_entity_master_V2.0.xlsx) | 人工浏览、筛选和核查 |
| [`entity_id_crosswalk.csv`](data/processed/entity_id_crosswalk.csv) | CNUR编号与旧编号兼容映射 |
| [`entity_names_1987_2026.csv`](data/processed/entity_names_1987_2026.csv) | 1987—2026正式名和历史名有效区间 |
| [`legal_roster_1987_2026.csv`](data/processed/legal_roster_1987_2026.csv) | 347实体 × 40年的年度状态长表 |
| [`unified_events_1987_2026.csv`](data/processed/unified_events_1987_2026.csv) | 统一行政区划事件主表 |
| [`major_lineage_relations.csv`](data/processed/major_lineage_relations.csv) | 按县级构成审核的重大拆分、析设和多来源关系 |
| [`county_affiliation_transitions.csv`](data/processed/county_affiliation_transitions.csv) | 支撑重大实体关系的县级单位去向底表 |
| [`unified_event_relations.csv`](data/processed/unified_event_relations.csv) | 改名、升格、合并、拆分和代管关系 |

完整字段说明见 [`CODEBOOK.md`](CODEBOOK.md)，版本变化见 [`CHANGELOG.md`](CHANGELOG.md)。

## 快速使用

### Python

```python
import pandas as pd
from urban_crosswalk import match_name, match_dataframe

# 单个历史名称
result = match_name("思茅市", year=2005, province="云南省")
print(result.entity_id)       # CNUR-000272
print(result.match_status)    # auto_matched

# 城市面板批量匹配
panel = pd.read_csv("examples/sample_panel.csv")
matched, details = match_dataframe(panel, "城市", "年份", "省份")
matched.to_csv("matched.csv", index=False)
```

批量结果保留全部原始列，并追加：

```text
crosswalk_entity_id
crosswalk_canonical_name
crosswalk_normalized_input
crosswalk_match_status
crosswalk_match_method
crosswalk_confidence
crosswalk_year_status
crosswalk_level_status
crosswalk_risk_codes
crosswalk_candidate_count
crosswalk_rule_version
```

### 本地网页

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

### CLI 命令行

安装当前仓库后会提供 `cnur` 命令：

```bash
.venv/bin/pip install -e .
```

单个名称匹配：

```bash
cnur match "思茅市" --year 2005 --province 云南省
```

批量处理CSV或Excel：

```bash
cnur batch panel.csv \
  --name-col 城市 \
  --year-col 年份 \
  --province-col 省份 \
  --output matched.csv \
  --issues-output issues.csv \
  --audit-output audit.json
```

实体与事件查询：

```bash
cnur entity CNUR-000272
cnur events --entity-id CNUR-000110
cnur events --year 1993 --type split --output events.csv
```

默认情况下，命令成功执行即返回退出码0；加上 `--fail-on-review` 后，只要存在非自动接受记录就返回退出码2，便于接入数据流水线。

## 匹配原则

匹配按以下顺序执行：

1. Unicode NFKC、繁简、全半角、不可见字符和标点标准化；
2. 正式名称与历史名称精确匹配；
3. 常用简称和已审核别名；
4. 用户补充映射；
5. 有限OCR候选；
6. RapidFuzz模糊候选；
7. 省份、年份、法定层级、设立和撤销状态复核。

只有全国唯一、年份有效且层级一致的确定性结果会自动接受。OCR与模糊匹配只提供最多3个候选。香格里拉市等县级同名冲突会返回上级地级实体和风险提示，不会直接替用户修改。

## 数据模型

本项目严格区分：

- **研究实体**：稳定CNUR编号，用于跨期追踪；
- **年度状态**：某实体在1987—2026各年是否存在、名称、层级及推导依据；
- **行政区划事件**：改名、撤地设市、新设、撤销、合并、拆分和代管；
- **事件关系**：事件来源和目标实体，以及是否允许自动连续；
- **历史实体**：2000年前已经撤销、但对历史事件连续性必要的实体。

例如雁北地区撤销后分别关联大同和朔州，因此被记录为一对多 `split`，不能自动把历史统计值分配给任一城市。

## 质量控制

每次提交都会在 GitHub Actions 中自动执行：

- processed 数据可重复构建；
- 347个CNUR编号唯一且连续；
- 名称长表可还原年度面板；
- 144条事件无重复签名；
- 当前和历史实体引用完整；
- 改名链与撤地设市链连续；
- 合并、拆分、撤销和代管禁止自动映射；
- 1,208项统一连续性审计；
- Python匹配回归测试与Streamlit启动测试。

审计结果见 [`data/audit/unified_continuity_audit.csv`](data/audit/unified_continuity_audit.csv)。

## 信源与限制

- 当前主要二手信源为中文维基百科年度行政区划变更页面，并保存页面URL和修订号；
- 部分事件同时记录国务院、民政部或地方政府批文号；
- 维基可枚举的同名年度页面覆盖1987—1988、1992—2026，1989—1991和更早年份没有同类年度表；
- V2.0不声称已经为每条记录完成官方批复原件级核验；
- 原始340实体宽表是研究平衡面板，不是逐年法定地级单位名单；
- 对高要求历史或法律研究，应结合官方批复和本项目的 `verification_status`、`confidence`、`risk_flags` 使用。

## 引用

建议引用 GitHub Release 或具体提交，并注明使用的数据版本：

```text
China Urban Research Entity Crosswalk, Version 2.0.
https://github.com/FIERsity/china-prefecture-crosswalk
```

仓库包含 [`CITATION.cff`](CITATION.cff)，GitHub页面右侧可直接导出引用格式。

## 许可与贡献

- 代码：MIT License；
- processed与release数据：CC BY 4.0；
- 第三方来源内容仍受原来源条款约束。

欢迎通过 GitHub Issues 提交别名、OCR错误、年份冲突和来源补充。涉及新别名或历史修订时，请同时提供名称、年份、省份、预期实体和来源链接。

## 仓库结构

```text
data/raw/          原始输入快照
data/processed/    可复现生成的数据层
data/releases/     面向研究者的版本化发布文件
data/audit/        实体与连续性审计结果
urban_crosswalk/   独立Python匹配模块
scripts/           构建、迁移、抓取和验证脚本
tests/             回归与网页测试
app.py             Streamlit网页入口
```
