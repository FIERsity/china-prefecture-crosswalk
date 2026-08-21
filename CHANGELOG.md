# Changelog

## 4.0.0 - 2026-08-20

- Unified every annual entity/name status on a December 31 year-end basis and added an explicit `status_as_of`/`year_basis` contract.
- Added 144 event timing reviews with implementation/effective-date overrides for cross-year cases; 2017 year-end now retains 那曲地区 and 2018 year-end uses 那曲市.
- Corrected premature prefecture status for 亳州、随州 and 儋州, restored early 临沧地区/昌都地区 names, and removed stale names from abolished rows.
- Added calendar-year name ranges so old and new names in a continuous within-year rename both match the same CNUR while returning the year-end name.
- Added four public match columns: year-end name, year basis, name validity, and transition event IDs.
- Audited CTAmap 1.30 province/prefecture Shapefiles for 2000—2024: 50 layer snapshots and 8,423 counted prefecture features, with zero unresolved entity links and zero invalid linked geometries.
- Added CTAmap snapshot/link tables and retained two explicit cross-source timing differences for 那曲 and 莱芜; original third-party geometry is not redistributed.
- Added a GitHub Pages historical-map tab backed by 25 lazy-loaded, simplified prefecture GeoJSON files (about 40 MB total), with panel-year selection, CNUR details, and upstream source links.
- Filled former map holes with 776 context features across the 25 snapshots (province-direct county-level units plus Hong Kong, Macao and Taiwan background), styled separately and never assigned CNUR IDs.
- Added map search by current or historical name, six-digit source code and CNUR ID; linked map details now show year-end name history and open related event queries.
- Added 25 annual province maps (850 features) and 25 years of county maps (71,610 features) partitioned by province for lazy loading; 2000—2010 county Web Mercator sources are normalized to WGS84 before simplification.
- Added province/prefecture/county level selection, county province selection, county type and parent-prefecture CNUR display, and related county-event lookup in the historical map UI.
- Added a non-runtime external-boundary acquisition cache: Hong Kong GitHub scraper and source metadata, Macau 2017 review-only Shapefile candidate, and Taiwan official-boundary RAR with government source-license record; all files are checksum-tracked and excluded from CTAmap/CNUR data.
- Published V4.0 CSV, Excel, and full data bundle outputs and switched Python, CLI, Streamlit, and GitHub Pages metadata to the year-end rule.

## 3.4.1 - 2026-08-05

- 修复 Wikipedia 县级变更年度表格 `rowspan` 解析错误：原实现多延续一行，导致部分县级记录被错误串入相邻地级单位（如茂港区被错误归入上海市）。
- 重新抓取并重建县级事件层：110 条县级记录纠正地级关联，移除 4 条误识别的省份标记事件；新增回归测试覆盖 rowspan 延续逻辑。
- 发布 v3.4.1 release：打包最新全量 `data/processed` 数据（29 个 CSV）为 ZIP 快照，连同 master 实体 CSV/XLSX 作为发布资产；master 实体表内容与 V3.0 一致。
- 网页、Streamlit 下载入口与 README 下载徽章同步指向 v3.4.1。

## 3.4.0 - 2026-08-04

- Unified the public query window at 1983—2026 across the web app, Streamlit entry, CLI audit report, and repository descriptions.
- Combined canonical-name history and prefecture-level administrative-unit changes in the single-name result view.
- Changed event display to preserve the source `description`; derived old/new fields remain available for analysis but are not presented as cleaned facts.

## 3.3.0 - 2026-08-04

- Added a 211-row prefecture event interface covering the 1983—2026 query window, including 67 early city, prefecture, and league changes extracted from preserved source text.
- Added the early event layer to the website, Python matcher, CLI, package data, downloads, source registry, and validation workflow.
- Marked 1983—1986 matches as `early_event_only`: event evidence is available, while the annual legal roster still begins in 1987.

## 3.1.0 - 2026-08-04

- Re-collected county-level administrative-change tables from 37 Chinese Wikipedia annual pages.
- Added 1,158 source rows and 1,149 display-oriented county administrative events for 1987—2026.
- Added loose links from 1,128 county records to current or historical prefecture research entities.
- Added descriptive event fields for before/related units, after/destination units, change text, county-level type, and scope.
- Classified the eight ordinary county-level types, retained historical 工农区, and excluded 开发区 from the ordinary county-level result panel.
- Displayed related county-level change records beneath single-city lookup results, with source links and an explicit non-genealogical caveat.

## 3.0.0 - 2026-07-13

- Promoted the complete 1987—2026 entity-year database to the sole current public scope.
- Published a unified 363-entity V3.0 master table with 340 continuously tracked research entities and 23 historical entities.
- Aligned the website, Python package, CLI, audit metadata, documentation, and default downloads on V3.0.
- Removed the former panel-window wording from current public documentation and interfaces.

## 2.0.0 - 2026-07-12

- Migrated 363 current and historical entities to permanent `CNUR-000001` identifiers.
- Published the second-generation unified city entity master table in CSV and Excel formats.
- Unified 144 historical change events and 149 entity relations across 1987—2026 source coverage.
- Extended the web app, Python matcher, and CLI runtime coverage to 1987—2026.
- Added a 14,520-row annual status layer for all 363 entities.
- Added 1,285 automated continuity checks with zero unresolved entity references.
- Added an online database browser and versioned downloads to the Streamlit application.
- Added the `cnur` command-line interface for single, batch, entity, and event queries.
- Added a county-composition audit with 70 county-unit transitions and 18 material lineage relations, including the two-way Nanning Prefecture and three-way Huiyang Prefecture successions.
- Separated 16 additional historical prefectures/prefecture-level cities that coexisted with their merger targets; expanded the reviewed lineage layer to 37 relations and 90 county-unit transitions.
- Corrected prefecture-level establishment years for Dongguan, Zhongshan, Zhangjiajie, Rizhao, Chaozhou, Jieyang, Yunfu, and Guigang; their earlier county-level city years are not treated as prefecture entities.

## 0.1.0 - 2026-07-11

- Added machine-readable entity, temporal-name, annual legal-status, event, and source tables.
- Corrected ten high-risk entities identified by the initial audit.
- Distinguished Wikipedia-verified corrections from inherited, unverified snapshot records.
- Added deterministic build and validation scripts.
- Added a reproducible Chinese Wikipedia page and administrative-level audit for all 340 entities.
- Resolved ambiguous titles for Baishan, Songyuan, and the former prefecture-level Chaohu.
