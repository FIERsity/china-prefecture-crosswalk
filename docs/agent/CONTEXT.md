# 项目上下文

> 稳定项目地图。最后复核：2026-08-22。动态近况见 [`STATUS.md`](STATUS.md)。字段级定义以 [`../../CODEBOOK.md`](../../CODEBOOK.md) 为准。

## 一句话定位

这是一个面向中国城市面板研究的地级行政实体数据库、行政区划事件库、历史地图桥接和名称匹配工具。它用永久 `CNUR-*` 研究编号连接跨期名称和实体，同时保留复杂区划变更的不确定性，不替研究者擅自分配历史统计值。

## 当前公开范围

| 层 | 当前口径 |
|---|---|
| 地级、县级事件查询 | 1983—2026；现有地级事件记录到 2018 |
| 年末法定状态与年末规范名 | 1987—2026，每年 12 月 31 日 |
| 历史地图 | 2000—2024 年初快照，对应 1999—2023 面板年 |
| 固定边界研究产品 | 2020 参考边界；事件旗标面板为 1999—2020 |
| 港澳台 | 当前外部展示层；无 CNUR、无逐年面板、无名称匹配 |

`1983`、`1987` 和 `2026` 是项目覆盖边界，不是名称的自然生效或终止日期。直辖市按地级等价单位处理。

## 系统组成

| 位置 | 角色 | 修改提示 |
|---|---|---|
| `data/raw/` | 原始快照、人工覆盖表、外部边界审计缓存 | 尽量保留来源、版本、许可和校验值；不要“清洗后覆盖原件” |
| `data/processed/` | 版本控制中的规范机器可读层 | 既包含构建输入，也包含派生表；先查脚本读写关系再编辑 |
| `data/audit/` | 连续性、年份、地图和实体审计结果 | 通常由审计脚本生成，错误必须解释或修复上游 |
| `urban_crosswalk/` | Python API、CLI 和随包发布的数据镜像 | `urban_crosswalk/data/` 由 `sync_package_data.py` 同步 |
| `docs/` | 无后端 GitHub Pages 应用 | `docs/data/` 和地图文件由构建脚本生成；浏览器本地查询 |
| `app.py` | 本地 Streamlit 入口 | 与 Python 匹配规则和公开口径保持一致 |
| `data/releases/` | 版本化 CSV/XLSX、研究包和地图包 | 发布资产；数据变化时同步版本、校验值和说明 |
| `scripts/` | 抓取、规范化、构建、审计、同步和导出 | CI 中的顺序是可复现构建的主参考 |
| `tests/` | 匹配器、CLI、Streamlit 和解析器回归 | 结构/口径修复应补语义回归，避免只按行号或 ID 断言 |

## 数据流

```text
原始快照 / 人工覆盖 / 已登记来源
  -> 基础实体与 2000—2024 发布层
  -> 维基历史记录规范化 + 统一事件与关系
  -> CNUR 迁移 + 1987—2026 年末名册
  -> 连续性、县级、地级、来源与固定边界产品
  -> Python 包数据镜像
  -> 港澳台外部展示层 + 地图/网页数据 + 研究发布包
  -> 校验、测试、GitHub Pages
```

重要区别：

- `data/processed/` 是规范层，但并非其中每张表都能由单一命令从 `data/raw/` 完整重建。抓取归档和人工审核结果也会作为后续构建输入。
- `urban_crosswalk/data/` 和大部分 `docs/data/` 是消费副本，不应成为上游事实源。
- `docs/data/maps/` 是已提交的简化网页几何；约 2.5 GB 的 CTAmap 原始 Shapefile 只在本地可选路径中使用。

## 完整可复现构建顺序

下列顺序与 `.github/workflows/validate.yml` 对齐。改变构建链时，应同时修改 CI 和本节。

```bash
python scripts/build_release.py
python scripts/normalize_wikipedia_history.py
python scripts/build_unified_events.py
python scripts/build_major_lineage_audit.py
python scripts/migrate_cnur_ids.py
python scripts/build_extended_roster.py
python scripts/audit_unified_continuity.py
python scripts/build_county_events.py
python scripts/build_prefecture_events.py
python scripts/build_source_registry.py
python scripts/build_fixed_boundary_map.py
python scripts/build_fixed_boundary_district.py
python scripts/build_event_flag_panel.py
python scripts/sync_package_data.py
python scripts/build_external_display_maps.py
python scripts/build_map_release.py
python scripts/build_pages_data.py
python scripts/export_city_master_v4.py
```

随后验证：

```bash
git diff --exit-code  # 只适用于期望完整重建后无漂移的场景
python scripts/validate_data.py
pytest -q
cnur match "思茅市" --year 2005 --province 云南省
```

本地环境的推荐安装方式见 `README.md`。仅改文档时不必运行整条数据链，但至少检查链接、命令和 Git diff。

## 核心数据契约

### 实体、名称和时间

- `CNUR-*` 是项目永久研究编号。官方区划码和 CTAmap 源码都是随时间变化的属性或桥接键。
- `legal_roster_year_end_1987_2026.csv` 是显式年末名册；无 `_year_end_` 的 V4 兼容表必须保持相同年末语义。
- `entity_name_match_ranges_1987_2026.csv` 比年末名称层更宽：连续改名当年可接受旧名和新名，但输出仍返回统一年末名。
- 县级同名不能仅凭“市”后缀冒充地级实体；省份、年份、层级和设立状态参与复核。

### 事件和关系

- 事件层回答“发生了什么”，关系层回答“实体之间如何连接”。
- `automatic_continuity=true` 只适用于同一实体延续，如改名或普通升格。
- `automatic_mapping=false` 用于合并、拆分、撤销、代管和重要跨地级划转；存在关系不代表可以自动搬运统计值。
- `event_timing_reviews.csv` 决定年末状态采用哪个年份，并明确区分批准、公布、实施和推定依据。

### 来源和地图

- 每条重要数据应保留 `source_id`、URL/定位、修订或版次、可信度与核验状态。
- 维基年度页是固定修订的证据档案，不等于官方原件级核验。
- CTAmap 与港澳台外部边界是不同来源、许可、坐标和语义层，不能静默混合。
- 香港 18 区、台湾 ADM1/ADM2、澳门当前未拆分区域仅用于展示；名称可转换为简体，但要保留原名和来源元数据。

## 公开消费面与同步点

一次数据或规则变化可能需要同步：

- `README.md`、`CODEBOOK.md`、`CHANGELOG.md`；
- `pyproject.toml`、`CITATION.cff`、CLI、匹配器和网页元数据中的版本号；
- `data/processed/`、`urban_crosswalk/data/`、`docs/data/`；
- V4 CSV/XLSX、研究 ZIP、地图 ZIP 与 SHA256；
- GitHub Release 的说明与资产。

不要仅凭全局搜索机械替换数量或版本；优先从构建产物的真实行数和元数据计算。

## 自动化与发布

- 所有 push 和 PR 触发 `validate-data`：完整重建、检查无生成漂移、数据校验、校验和、pytest、Streamlit 和 CLI 冒烟。
- push 到 `main` 触发 `deploy-pages`：重建浏览器/地图数据，上传 `docs/` 并发布 GitHub Pages。
- 线上入口：<https://fiersity.github.io/china-prefecture-crosswalk/>。
- 远程仓库：<https://github.com/FIERsity/china-prefecture-crosswalk>。

## 常见改动的最小检查

| 改动 | 至少检查 |
|---|---|
| 名称、事件、关系或时间口径 | 完整相关构建、`validate_data.py`、pytest、消费副本 diff |
| 网页查询 | 构建网页数据、真实浏览器检查空/早期/改名/越界年份、控制台错误 |
| 地图 | manifest、要素数/许可/坐标系、不同层级加载、地图发布包校验值 |
| Python 匹配或 CLI | pytest、单条和批量样例、退出码/审计输出 |
| 版本发布 | 所有版本面、CHANGELOG、CITATION、发布资产和 SHA256 |
| 纯 Agent 文档 | 链接、命令、日期、Git/GitHub 事实；不需重建数据 |
