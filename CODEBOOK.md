# Data dictionary

This repository separates legal annual status from stable research entities. `entity_id` uses the permanent `CNUR-000001` namespace and is never an official administrative division code. Legacy identifiers remain available only through `entity_id_crosswalk.csv`.

## `data/processed/entities.csv`

One row per stable research entity. `verification_status` reports whether this first release changed and checked the entity or inherited it from the original snapshot.

## `data/processed/entity_names.csv`

Temporal name/status spans. Blank `name_zh` values are intentional when the research entity was not an active legal prefecture. Spans are closed intervals.

## `data/processed/legal_roster_2000_2024.csv`

One row per research entity and year. This is the first provisional legal-status layer. Records marked `inherited_unverified` have passed structural checks only and must not be described as individually source-verified.

## Unified 1987-2026 temporal layer

`legal_roster_1987_2026.csv` contains all 345 current and historical entities for every year from 1987 through 2026. Existing 2000-2024 legal-status records take precedence; earlier and later years are reconstructed from reviewed event chains or explicitly marked `inferred`. `entity_names_1987_2026.csv` compresses the same annual state into closed temporal spans. These two files are the runtime source for the website, Python API, and CLI.

## `data/processed/events_2000_2026.csv`

Machine-readable export of the 63 core prefecture-level change events in the source workbook. Event dates follow the workbook's approval-date convention. The source workbook remains the archival input.

## `data/processed/event_entity_links.csv`

Audit bridge between all 63 events and stable research entities. The release validator fails if an event is unmatched or ambiguous. Complex merger/split semantics are not represented as one-to-one continuity merely because the source event can be associated with an entity.

## `data/processed/sources.csv`

Source registry. Wikipedia is a secondary source and is explicitly labeled as such.

## `data/audit/wikipedia_entity_audit.csv`

Reproducible page-level audit for every entity. It records the resolved page, revision ID, canonical URL, and the category, introduction, Wikidata instance, or municipality rule used to confirm prefecture-level scope. Disambiguated pages are explicitly overridden for Baishan, Songyuan, and the former prefecture-level Chaohu.

## Wikipedia historical archive

`wikipedia_change_pages.csv` inventories every discoverable annual page and its revision ID. `wikipedia_prefecture_change_rows.csv` preserves rows found under headings explicitly containing “地级”. These records cover available pages from 1987 onward and are an evidence/search layer, not automatically accepted one-to-one entity mappings.

`wikipedia_normalized_events_1987_1999.csv` is the semantic normalization layer. Accepted rule extractions require explicit old and new prefecture names; manually reviewed links document their reasoning. Unresolved mergers, abolitions, and pre-2000 entities remain `review_required` and never imply automatic continuity.

## `data/processed/unified_events_1987_2026.csv`

The single public event interface. It combines all normalized events into one schema and one review-status vocabulary. There is no methodological split at 2000; older and newer events share the same event types, continuity rules, entity links, risk flags, and source requirements.

Historical units absent from the 2000—2024 research panel are registered in `historical_entities.csv`. Non-1:1 outcomes are represented in `unified_event_relations.csv`; in particular, Yanbei splits to Datong and Shuozhou, while the 1996 Chongqing transition links Wanxian, Fuling, and Qianjiang without permitting automatic value conversion.

`data/audit/unified_continuity_audit.csv` is generated from the complete unified model. It checks event uniqueness, entity references, historical lifespans, province continuity, annual-roster names, chronological name chains, relation references, and the prohibition on automatic mapping for complex events.
