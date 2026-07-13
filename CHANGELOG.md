# Changelog

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
