# Data dictionary

This repository separates legal annual status from stable research entities. `entity_id` is a project identifier and is never an official administrative division code.

## `data/processed/entities.csv`

One row per stable research entity. `verification_status` reports whether this first release changed and checked the entity or inherited it from the original snapshot.

## `data/processed/entity_names.csv`

Temporal name/status spans. Blank `name_zh` values are intentional when the research entity was not an active legal prefecture. Spans are closed intervals.

## `data/processed/legal_roster_2000_2024.csv`

One row per research entity and year. This is the first provisional legal-status layer. Records marked `inherited_unverified` have passed structural checks only and must not be described as individually source-verified.

## `data/processed/events_2000_2026.csv`

Machine-readable export of the 63 core prefecture-level change events in the source workbook. Event dates follow the workbook's approval-date convention. The source workbook remains the archival input.

## `data/processed/event_entity_links.csv`

Audit bridge between all 63 events and stable research entities. The release validator fails if an event is unmatched or ambiguous. Complex merger/split semantics are not represented as one-to-one continuity merely because the source event can be associated with an entity.

## `data/processed/sources.csv`

Source registry. Wikipedia is a secondary source and is explicitly labeled as such.

## `data/audit/wikipedia_entity_audit.csv`

Reproducible page-level audit for every entity. It records the resolved page, revision ID, canonical URL, and the category, introduction, Wikidata instance, or municipality rule used to confirm prefecture-level scope. Disambiguated pages are explicitly overridden for Baishan, Songyuan, and the former prefecture-level Chaohu.
