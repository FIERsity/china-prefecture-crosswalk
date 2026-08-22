# Changelog

## Unreleased

- Unified the province, prefecture and county map switcher around one national
  map context. County detail now overlays the national province outline;
  switching Taiwan, Hong Kong or Macao back to prefecture/province keeps the
  same geographic focus instead of leaking the hidden county filter or showing
  an unrelated external layer. Duplicate province outlines were also removed,
  and stale asynchronous map renders can no longer overwrite the latest level.

## 4.0.2 - 2026-08-21

- Full-coverage sweep captured 10 prefecture upgrades that existed in the
  Wikipedia row archive but were never extracted: 威海/三亚 (1987), 东莞/
  中山/大庸 (1988), 莱芜 (1992), 云浮 (1994), 贵港 (1995), 泰州/宿迁
  (1996). The extractor's patterns missed "升格为地级市" and
  "设立地级X市" sentence forms. Same-name county-level → prefecture
  upgrades are now classified as upgrade (continuous). Unified events
  157 → 167, prefecture event layer 224 → 234, relations 190 → 200.

## 4.0.1 - 2026-08-21

- Filled the 1989—1991 event-layer gap (no Wikipedia annual pages exist for these years) with three reviewed events sourced from official texts: 日照 upgraded to prefecture-level (1989-06-12, 国函〔1989〕43号), 潮州 upgraded (1991-12-07, 国函〔1991〕84号), and 揭阳 established after abolishing 揭阳县 (1991-12-07, 国函〔1991〕84号). Unified events 144 → 157, prefecture event layer 211 → 224, source registry 50 → 54.
- Added the missing event layer entries for the 1993 Hebei region merges (张家口/沧州/邯郸/邢台/承德, 国函〔1993〕89号), 1994 保定 (国函〔1994〕133号), 1996 松花江 (国函〔1996〕64号), 1998 桂林 (国函〔1998〕73号), 1997 重庆 municipality upgrade, and the 1997-12 万县/涪陵/黔江 adjustment (中办厅字〔1997〕34号).
- Completed successor relations for every merge/split/abolish (沙市/郧阳/惠阳/梧州/柳州/南宁 2002/巢湖 2011/莱芜 2018) and added 2015 枞阳/寿县, 2016 简阳, 2020 公主岭 transfers to `county_affiliation_transitions.csv` (90 → 94, all references resolvable). Event relations 149 → 190.
- Renamed `from_entity_key` to `from_entity_id` in `major_lineage_relations.csv` and `county_affiliation_transitions.csv` so all relation tables share one field vocabulary.
- Fixed "柳州" alias misrouting to 来宾市 (2000—2001), the 鞍山市 substring match inside 马鞍山市 county rows, and dropped shadowed suffix-omitted aliases.
- Hardened the release chain: `docs/data` byte-consistency assertion in validate, `shasum -c` in CI, rebuilt SHA256SUMS, bare-filename analysis checksum, pages deploy repaired, version/stat numbers injected from bundle meta, and a documented `build_external_current.py` generator.

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
