# Changelog

## 2.0.0 - 2026-07-12

- Migrated 345 current and historical entities to permanent `CNUR-000001` identifiers.
- Published the unified V2.0 city entity master table in CSV and Excel formats.
- Unified 144 historical change events and 149 entity relations across 1987—2026 source coverage.
- Extended the web app, Python matcher, and CLI runtime coverage from 2000—2024 to 1987—2026.
- Added a 13,800-row annual status layer for all 345 entities and 501 compressed temporal-name spans.
- Added 1,138 automated continuity checks with zero unresolved entity references.
- Added an online database browser and V2.0 downloads to the Streamlit application.
- Added the `cnur` command-line interface for single, batch, entity, and event queries.
- Added a county-composition audit with 70 county-unit transitions and 18 material lineage relations, including the two-way Nanning Prefecture and three-way Huiyang Prefecture successions.

## 0.1.0 - 2026-07-11

- Added machine-readable entity, temporal-name, annual legal-status, event, and source tables.
- Corrected ten high-risk entities identified by the initial audit.
- Distinguished Wikipedia-verified corrections from inherited, unverified snapshot records.
- Added deterministic build and validation scripts.
- Added a reproducible Chinese Wikipedia page and administrative-level audit for all 340 entities.
- Resolved ambiguous titles for Baishan, Songyuan, and the former prefecture-level Chaohu.
