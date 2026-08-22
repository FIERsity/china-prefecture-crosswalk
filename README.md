# China Urban Research Entity Crosswalk

[![Data validation](https://github.com/FIERsity/china-prefecture-crosswalk/actions/workflows/validate.yml/badge.svg)](https://github.com/FIERsity/china-prefecture-crosswalk/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/FIERsity/china-prefecture-crosswalk?sort=semver&label=release)](https://github.com/FIERsity/china-prefecture-crosswalk/releases)
[![License: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue.svg)](LICENSE-DATA)

[![Web app](https://img.shields.io/badge/use-GitHub_Pages-1F6E5A?logo=github&logoColor=white)](https://fiersity.github.io/china-prefecture-crosswalk/)
[![Download CSV](https://img.shields.io/badge/download-V4.0_CSV-2F81F7?logo=files&logoColor=white)](data/releases/v4.0/china_city_entity_master_V4.0.csv)
[![Download Excel](https://img.shields.io/badge/download-V4.0_Excel-217346?logo=microsoftexcel&logoColor=white)](data/releases/v4.0/china_city_entity_master_V4.0.xlsx)
[![Download Research bundle](https://img.shields.io/badge/download-V4.0_Research_bundle-888?logo=zip&logoColor=white)](data/releases/v4.0/china_prefecture_crosswalk_research_bundle_v4.0.zip)
[![Python and CLI](https://img.shields.io/badge/use-Python_%26_CLI-3776AB?logo=python&logoColor=white)](#快速开始)

面向中国城市面板研究的地级行政实体数据库与名称匹配工具。

项目提供稳定研究实体编号、12 月 31 日年末名称与状态、行政区划变更事件、CTAmap 历史地图桥接和可解释的批量匹配工具，面向需要处理统计年鉴、城市面板、OCR 资料和跨期名称变化的研究者。

> `CNUR-000001` 等 CNUR 编号是本项目的永久研究编号，不是民政部、国家统计局或任何年份的官方行政区划代码。

## 在线工具
**[打开 China Urban Research Crosswalk](https://fiersity.github.io/china-prefecture-crosswalk/)**

静态网页提供四个入口：

- 单个名称和可选省份查询；
- 1983—2026 地级行政单位变更检索，1983—2026 县级变更记录；
- 1999—2023 面板年份对应的 2000—2024 年初省、地、县三级历史地图，可按名称、代码和 CNUR 查询；
- 机器可读数据下载。

网页查询在浏览器本地完成，不需要 Python 服务器，也不会上传用户输入。完整的 CSV/XLSX 批量匹配仍可使用 Python API、CLI 或本地 Streamlit 入口。

网页数据由 GitHub Actions 从仓库数据自动构建并发布到 GitHub Pages；页面版本和规则版本会显示在页脚，避免网页与数据版本脱节。

V4.0 将年度状态统一定义为每年 12 月 31 日。连续改名发生当年，新旧名称都可匹配同一 CNUR，输出统一返回年末名称；复杂合并、拆分和撤销仍禁止自动映射后继实体。CTAmap 1.30 的 2000—2024 年初快照已完成审计。仓库保留约 146 MB 简化网页几何：省级和地级按年份加载，县级按“年份 × 省份”分片加载。2.5 GB 原始 Shapefile 不重新发布。

时间口径说明：网页事件查询覆盖 **1983—2026**，年末法定状态和“年末规范名沿革”覆盖 **1987—2026**。网页中的名称区间是项目在覆盖期内整理出的年末标签，不等同于名称完整、逐日的历史有效期；事件会分别显示批准、公布、实施日期，以及年末状态采用的年份和依据。**1983 与 2026 只是本项目的数据覆盖边界，不表示名称在这两个年份自然生效或终止。**


## 快速开始
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
crosswalk_year_end_name
crosswalk_year_basis
crosswalk_name_validity
crosswalk_transition_event_ids
```

### 完整本地网页（Streamlit）

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


## 数据概览
| 内容 | 数量/范围 |
|---|---:|
| 永久 CNUR 实体 | 363 |
| 持续追踪研究实体 | 340 |
| 历史实体 | 23 |
| 实体—年度状态 | 14,520（1987—2026） |
| 统一地级变更事件 | 167 |
| 地级行政单位事件层 | 234 条（查询窗口 1983—2026，现有记录到 2018），其中 67 条来自早期材料 |
| 事件关系 | 190 |
| 维基地级原始记录 | 988 |
| 连续性审计 | 1,506 项，0 错误 |
| 县级变更原始表格行 | 1,158（1987—2026） |
| 县级变更事件记录 | 1,431（1983—2026），其中 286 条来自早期补录 |
| 县级事件宽松关联 | 1983—2026 统一进入网页展示层 |
| CTAmap 地级快照桥接 | 8,423 个地级要素，25 个年初快照 |
| 网页地图背景区域 | 776 个跨年要素，用于补绘省直辖县级和范围外区域 |
| 省级网页地图 | 850 个跨年要素（34 × 25） |
| 县级网页地图 | 71,610 个跨年要素，按年份和省份分片 |
| 来源登记 | 54 条，含页面修订号、版次定位和来源状态 |
| 固定边界基准单位（2020 参考年） | 337，含形成路径与口径跳变年份 |
| 固定边界历史链接 | 190 条，含处理建议（可加总/需权重/断点旗标） |
| 固定边界区级事件 | 439 条（1987—2026，其中撤县设区 230 条） |
| 市辖区口径跳变（城市×年） | 223 行（1999—2020 面板期） |
| 事件旗标面板（城市×年） | 7,414 行（337 城市 × 22 年，可直接 merge） |

直辖市在研究实体体系中按地级等价单位处理。363个实体是跨期实体总数，不代表任一年度同时存在363个法定地级单位。变更前同时存在的地区与地级市始终使用不同编号；普通撤地设市仅在法定主体连续时沿用编号。

`ctamap_prefecture_links.csv` 是地图桥接表，不是地图几何：每行把某个 CTAmap 年份快照中的地级多边形、来源名称和区划码对应到一个 CNUR 研究实体及该年末名称。它用于把地图点击结果连接到研究实体，不能单独替代 GeoJSON 地图资源。


## 下载

下载区只列面向研究者的成果文件。构建缓存、原始抓取行、年度页面索引、兼容副本和内部审计文件不作为研究下载提供。

| 文件 | 用途 |
|---|---|
| [`china_city_entity_master_V4.0.csv`](data/releases/v4.0/china_city_entity_master_V4.0.csv) | 机器读取、R/Python合并 |
| [`china_city_entity_master_V4.0.xlsx`](data/releases/v4.0/china_city_entity_master_V4.0.xlsx) | 人工浏览、筛选和核查 |
| [`china_prefecture_crosswalk_research_bundle_v4.0.zip`](data/releases/v4.0/china_prefecture_crosswalk_research_bundle_v4.0.zip) | 精简研究包：主表、名称、年末状态、地级/县级事件、时间口径、关系、地图桥接和来源登记 |
| [`china_prefecture_crosswalk_research_bundle_v4.0.sha256`](data/releases/v4.0/china_prefecture_crosswalk_research_bundle_v4.0.sha256) | 精简研究包 SHA256 校验值 |
| [`data/releases/v4.0/README.md`](data/releases/v4.0/README.md) | 研究包目录和用途说明 |
| [`ctamap_county_analysis_2000_2024_t002.zip`](data/releases/maps/ctamap_county_analysis_2000_2024_t002.zip) | 县级精度分析包：2000—2024 年初 WGS84 分片数据 |
| [`china_prefecture_crosswalk_web_maps_v4.0.zip`](data/releases/maps/china_prefecture_crosswalk_web_maps_v4.0.zip) | 全部网页地图资源：省级、地级、县级 25 年分片、港澳台图层、manifest 和许可说明 |
| [`china_prefecture_crosswalk_web_maps_v4.0.sha256`](data/releases/maps/china_prefecture_crosswalk_web_maps_v4.0.sha256) | 全部网页地图资源校验值 |
| [`docs/data/maps/manifest.json`](docs/data/maps/manifest.json) | 网页地图文件清单和构建参数 |
| [`docs/data/maps/NOTICE.md`](docs/data/maps/NOTICE.md) | 地图来源、引用和许可说明 |

完整字段说明见 [`CODEBOOK.md`](CODEBOOK.md)，版本变化见 [`CHANGELOG.md`](CHANGELOG.md)。

## 开发与部署

安装运行时、测试和可选 GIS 依赖：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-geo.txt pytest
.venv/bin/pip install -e . --no-deps
```

运行数据校验和测试：

```bash
.venv/bin/python scripts/validate_data.py
.venv/bin/pytest -q
```

如本地存在 `data/raw/CTAmap1.30版本_2000-2024_2025.04.25/`，可重新审计和生成网页地图：

```bash
.venv/bin/python scripts/audit_ctamap_prefecture.py
.venv/bin/python scripts/build_ctamap_web_maps.py
```

本地预览静态网站：

```bash
python3 -m http.server 8765 --directory docs
```

推送 `main` 会触发 `.github/workflows/validate.yml` 和 `.github/workflows/pages.yml`；前者重建并验证数据，后者发布 `docs/` 到 GitHub Pages。原始 CTAmap Shapefile 被精确忽略，CI 使用仓库中已提交的简化 GeoJSON。


## 匹配原则
匹配按以下顺序执行：

1. Unicode NFKC、繁简、全半角、不可见字符和标点标准化；
2. 年末正式名称和自然年内曾有效名称精确匹配；
3. 常用简称和已审核别名；
4. 用户补充映射；
5. 有限OCR候选；
6. RapidFuzz模糊候选；
7. 省份、年末状态、法定层级、设立和撤销状态复核。

只有全国唯一、年份有效且层级一致的确定性结果会自动接受。部分名称会列出全部对应实体；县级名称会关联到相关地级实体；编辑距离模糊匹配最多显示3个候选。香格里拉市等县级同名冲突会返回上级地级实体和风险提示，不会直接替用户修改。


## 数据模型
本项目严格区分：

- **研究实体**：稳定CNUR编号，用于跨期追踪；
- **年末状态**：某实体截至1987—2026各年12月31日是否存在、名称、层级及推导依据；1987 是当前年末状态层的证据起点，2026 是当前覆盖终点；
- **年内名称匹配**：某自然年内曾正式使用的名称，与该年年末标准名称分开维护；
- **行政区划事件**：改名、撤地设市、新设、撤销、合并、拆分和代管；事件查询窗口扩展至1983—2026，但1983—1986主要是事件证据层，不构成完整年末名册；
- **事件关系**：事件主实体（`from_entity_id`）与目标实体（`to_entity_id`）的映射，以及是否允许自动映射（`automatic_mapping`）；复杂事件（合并、拆分、撤销、划转）禁止自动映射，需要研究者按研究问题决定处理方式；
- **历史实体**：覆盖期内已撤销、合并，或为解释跨期关系所必需的地级实体。

例如雁北地区撤销后分别关联大同和朔州，因此被记录为一对多 `split`，不能自动把历史统计值分配给任一城市。


## 质量控制
每次提交都会在 GitHub Actions 中自动执行：

- processed 数据可重复构建；
- 363个CNUR编号唯一且连续；
- 名称长表可还原年度面板；
- 167条事件无重复签名；
- 当前和历史实体引用完整；
- 改名链与撤地设市链连续；
- 合并、拆分、撤销和代管禁止自动映射；
- 1,506项统一连续性审计；
- 25 年省、地、县三级网页地图完整，8,423 个地级桥接要素无未匹配或无效几何；
- Python匹配回归测试与Streamlit启动测试。

审计结果见 [`data/audit/unified_continuity_audit.csv`](data/audit/unified_continuity_audit.csv)。


## 信源与限制
- 1987 年以后县级层主要使用中文维基百科年度行政区划变更页面，并保存页面 URL 和修订号；
- 1983—1986 年早期补录以人民日报历史版面的行政区划变更摘要为主，并用区划地名网按国务院批复整理的 1983 年第四季度、1984 年上半年条目补齐时段，分别保存版次或页面定位、原文和访问链接；
- 国务院公报历史目录和《中华人民共和国行政区划简册》书目已登记为核验来源，公报扫描件仍需逐页 OCR 或人工复核后，才能替代摘要层；
- 部分事件同时记录国务院、民政部或地方政府批文号；
- 维基可枚举的同名年度页面覆盖1987—1988、1992—2026；1989—1991 没有同类年度表，该三年的事件（日照升格 1989、潮州升格与揭阳设市 1991）已通过国务院批复原文（维基文库、政府网站转发件）补充收录；
- V4.0不声称已经为每条记录完成官方批复原件级核验；仅有批准日而无实施日的事件以推定口径并标注时间置信度；
- CTAmap 简化的省、地、县 GeoJSON 按上游非商业条件和独立 NOTICE 提供，不属于本项目 CC BY 4.0 数据；网页展示版县级容差为 `0.005°`，精度分析包另提供 `0.002°` 版本；
- CTAmap 原始 Shapefile 约 2.5 GB，不直接复制入仓库；仓库保留上游下载入口、派生分析包、SHA256 校验值和可复现构建脚本；
- 县级地图 2000—2010 年原始坐标为 Web Mercator，构建时转换为 WGS84；2011—2024 年原始坐标为 WGS84；
- 历史地图覆盖 2000—2024 年初，对应 1999—2023 经济面板年份；县级地图按省份加载，县级要素只连接其上级地级 CNUR，不冒充地级研究实体；
- 实体总表是跨期研究实体全集，不等同于任何单一年度的法定地级单位名单；逐年状态应以年度状态表为准；
- 对高要求历史或法律研究，应结合官方批复和本项目的 `verification_status`、`confidence`、`risk_flags` 使用。


### 港澳台公开地图资源线索

本项目当前只把港澳台作为地图背景，不纳入 CNUR 地级研究实体。后续若需要补充独立边界图层，可优先核验以下公开入口：

- 香港：[DATA.GOV.HK CKAN API](https://data.gov.hk/en/help/ckan-api-development-guide)、[CSDI 地理空间数据门户](https://portal.csdi.gov.hk/geoportal/)、[GeoInfo Map Service](https://www.hkmapservice.gov.hk/OneStopSystemMap/)。前两个是公开数据/目录入口，但具体行政边界图层需要按数据集和授权逐项确认。
- 澳门：[地理空间信息入口网站](https://www.gis.gov.mo/geoportal/)、[澳门网上地图](https://webmap.gis.gov.mo/)。目前确认有官方公开地图入口，但尚未确认可直接重新分发的行政边界 Shapefile/GeoJSON 许可。
- 台湾：[政府资料开放平台的直辖市、县市界线数据集](https://data.gov.tw/dataset/7442)，页面明确提供 TWD97 经纬度边界资料、SHP 下载和资料授权链接；另可参考 [geoBoundaries TW ADM2](https://www.geoboundaries.org/api/current/gbOpen/TWN/ADM2/)，但仍需按当前版本许可和字段核对后再导入。

这些资源不能直接与 CTAmap 混合：坐标系、行政层级、政治/法律口径和许可证不同。导入前必须保留原始来源、版本日期、坐标系和许可字段。

已抓取的 GitHub 来源缓存位于 [`data/raw/external_boundaries/`](data/raw/external_boundaries/)，当前仅供审计，不进入运行时地图：香港保留 MIT 抓取脚本，澳门保留无 License 的 2017 候选 Shapefile，台湾保留带政府来源许可记录的官方边界 RAR。清单和 SHA256 见该目录的 `manifest.json` 与 [`data/SHA256SUMS`](data/SHA256SUMS)。

当前网站外部展示层按层级处理港澳台：省级使用三份当前背景面；地级层追加台湾 geoBoundaries ADM1（22 个外部地级对应区）；县级层追加台湾 ADM2（368 个）、香港 18 区和澳门 1 个未拆分外部展示区。三级共用同一张全国地图，县级细节叠加在全国省界底图上，切换层级时保留同一省份焦点。显示名称统一以台湾省、香港特别行政区、澳门特别行政区为省级名称；香港、澳门不设置地级父节点，三者都不分配 CNUR，也不参与历史面板。

## Agent 协作

仓库用 [`AGENTS.md`](AGENTS.md) 作为跨会话 Agent 入口，并将稳定项目地图、动态近况和长期决定分别维护在 [`docs/agent/`](docs/agent/) 中。Agent 文档用于快速定位和交接；代码、数据、Git 历史和 GitHub 实时状态仍是最终事实源。

## 引用
建议引用 GitHub Release 或具体提交，并注明使用的数据版本：

```text
China Urban Research Entity Crosswalk, Version 4.0.2.
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
docs/              GitHub Pages 静态公共工具
docs/data/maps/     25 年省、地、县三级网页展示 GeoJSON、地图清单和 CTAmap NOTICE
data/releases/maps/ 县级精度分析包、校验值和来源说明
urban_crosswalk/   独立Python匹配模块
scripts/           构建、迁移、抓取和验证脚本
scripts/build_pages_data.py  生成浏览器端数据包
scripts/build_ctamap_web_maps.py  从本地 CTAmap Shapefile 重建网页地图
tests/             回归与网页测试
app.py             Streamlit网页入口
AGENTS.md           Agent 启动、验证与交接规则
docs/agent/         稳定上下文、动态近况与长期决定
```
