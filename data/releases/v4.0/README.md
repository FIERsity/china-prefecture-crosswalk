# V4.0 研究者下载包

这是面向研究者的精简数据包，不包含网页构建产物、原始抓取表、年度页面索引、兼容副本或内部审计差异文件。

## 推荐下载

- `china_city_entity_master_V4.0.csv`：一行一个跨期研究实体，适合直接并入城市面板。
- `china_city_entity_master_V4.0.xlsx`：同一主表的人工核查版本。
- `china_prefecture_crosswalk_research_bundle_v4.0.zip`：研究所需的核心 CSV、代码本、名称映射、年末状态、地级/县级事件、事件时间口径、关系和地图桥接。
- `china_prefecture_crosswalk_research_bundle_v4.0.sha256`：研究包校验值。

地图精度分析包单独位于 [`../maps/`](../maps/)，因为它体积较大且属于第三方 CTAmap 派生空间数据。

## 包内数据

包内 `data/` 目录只保留以下研究用途明确的内容：实体主表、旧编号映射、名称和别名、1987—2026 年末状态、1983—2026 地级/县级事件、时间口径、实体关系、县级构成关系、CTAmap 地级桥接、快照清单和来源登记。字段定义见包内 `CODEBOOK.md`。

## 不再作为研究下载提供的内容

Wikipedia 原始表格行、年度页面索引、早期解析中间表、V4 兼容副本、内部审计差异和构建缓存仍保留在仓库的 `data/processed/` 或 `data/audit/`，用于复现和质量控制，但不放入研究下载包。
