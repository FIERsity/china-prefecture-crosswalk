# Data dictionary

This repository separates year-end legal status from stable research entities. `entity_id` uses the permanent `CNUR-000001` namespace and is never an official administrative division code. Legacy identifiers remain available only through `entity_id_crosswalk.csv`.

## `data/processed/entities.csv`

One row per stable research entity. `verification_status` reports whether this first release changed and checked the entity or inherited it from the original snapshot.

## `data/processed/entity_names.csv`

Temporal name/status spans. Blank `name_zh` values are intentional when the research entity was not an active legal prefecture. Spans are closed intervals.

## Year-end status layer: 1987—2026

`legal_roster_year_end_1987_2026.csv` contains all 363 current and historical entities for every year from 1987 through 2026. Every row has `status_as_of=YYYY-12-31` and `year_basis=year_end`. Event transitions use explicit effective/implementation dates when available and otherwise retain a labelled approval-date or event-year inference. A name ending in `市` is never sufficient to establish prefecture-level status: county-level cities enter the roster only from their reviewed prefecture-level establishment year.

`entity_names_year_end_1987_2026.csv` compresses that year-end state into closed year spans. `entity_name_match_ranges_1987_2026.csv` is deliberately broader: it records names that were valid at any time during a calendar year, so a continuous rename can accept both the old and new name while returning one year-end standard name. `legal_roster_1987_2026.csv` and `entity_names_1987_2026.csv` are V4 compatibility copies with the same year-end semantics.

`event_timing_reviews.csv` provides one timing record for every unified event. `annual_effective_basis` distinguishes explicit implementation evidence from approval-date and event-year inference; `temporal_confidence` prevents an inferred year from being presented as an exact implementation date.

## `data/processed/events_2000_2026.csv`

Machine-readable export of the 63 core prefecture-level change events in the source workbook. `approval_date` follows the workbook's approval-date convention; year-end transitions are taken from `event_timing_reviews.csv`, not from the event year alone. The source workbook remains the archival input.

## CTAmap 1.30 spatial bridge

`ctamap_snapshots.csv` inventories the 2000—2024 year-start province and prefecture Shapefiles, including checksums, CRS and record counts. A snapshot labelled `S年初` is aligned to panel year `S-1`; the files do not contain feature-level effective dates.

`ctamap_prefecture_links.csv` links 8,423 counted prefecture features to CNUR entities. Ordinary prefecture types are 地级市、地区、自治州、盟; the four municipalities are treated as prefecture-equivalent, while other `不统计` directly administered county-level units remain outside the bridge. Source codes are retained as temporal attributes and never replace CNUR IDs. `docs/data/maps/prefecture/` contains per-year simplified GeoJSON for the non-commercial static visualization; the original Shapefiles are not redistributed and the derived geometry follows its own NOTICE rather than this project's CC BY 4.0 license.

## `data/processed/event_entity_links.csv`

Audit bridge between all 63 events and stable research entities. The release validator fails if an event is unmatched or ambiguous. Complex merger/split semantics are not represented as one-to-one continuity merely because the source event can be associated with an entity.

## `data/processed/sources.csv` and `data/processed/source_registry.csv`

Source registry. Each source has a type, coverage, locator, authority, and provenance status. Wikipedia is a revisioned secondary source; six 1983—1986 People's Daily summaries are preserved as contemporaneous primary-text transcriptions, while the 1983 Q4 and 1984 H1 gap periods use separately labelled secondary transcriptions from 区划地名网. The State Council Gazette archive and annual administrative-division books are registered as verification references, not silently treated as row-level evidence.

## `data/audit/wikipedia_entity_audit.csv`

Reproducible page-level audit for every entity. It records the resolved page, revision ID, canonical URL, and the category, introduction, Wikidata instance, or municipality rule used to confirm prefecture-level scope. Disambiguated pages are explicitly overridden for Baishan, Songyuan, and the former prefecture-level Chaohu.

## Wikipedia historical archive

`wikipedia_change_pages.csv` inventories every discoverable annual page and its revision ID. `wikipedia_prefecture_change_rows.csv` preserves rows found under headings explicitly containing “地级”. These records cover available pages from 1987 onward and are an evidence/search layer, not automatically accepted one-to-one entity mappings.

`wikipedia_normalized_events_1987_1999.csv` is the semantic normalization layer. Accepted rule extractions require explicit old and new prefecture names; manually reviewed links document their reasoning. Unresolved mergers, abolitions, and pre-2000 entities remain `review_required` and never imply automatic continuity.

## County-level Wikipedia supplement

`wikipedia_county_change_pages.csv` inventories the same annual pages used for the prefecture archive and records the revision checked by the fetcher. `wikipedia_county_change_rows.csv` preserves rows extracted from county-level tables, including the section, table header, cleaned row text, raw cell markup, and source URL.

`county_administrative_events_1987_2026.csv` is a display-oriented event layer derived from those rows. It preserves the source row in `description`, while `change_description` extracts the descriptive change cell when the table structure permits it. `old_county_units` and `new_county_units` are positional “before/related” and “after/destination” hints, not a completed county genealogy; the descriptive sentence is authoritative when the two hints are incomplete. `event_type` covers administrative transfer, merge, split, rename, residence change, abolition, establishment, and jurisdiction adjustment. `prefecture_entity_ids` is a loose text/entity hit against current and historical prefecture names; it is intentionally not a formal county-to-prefecture genealogy. Directly administered county-level cities and rows whose historical parent is not represented in the current entity registry remain unlinked rather than being assigned by guesswork.

The current county-level classification follows the eight ordinary county-level administrative types listed in national statistical materials: 市辖区、县级市、县、自治县、旗、自治旗、特区、林区. Historical `工农区` is retained as an additional legacy type when it appears in a source row. `开发区` is retained for provenance but marked outside the ordinary county-level scope; rows such as government-residence changes that do not expose a type are marked `untyped_county_record` rather than being silently discarded. The source archive is the annual Chinese Wikipedia change-list collection, for example the [2024 county-level change tables](https://zh.wikipedia.org/wiki/2024年中华人民共和国县级以上行政区划变更列表); the project does not claim that Wikipedia alone proves a complete official genealogy.

`county_unit_type_coverage_1987_2026.csv` is an explicit coverage audit. It lists all eight ordinary types even when a type has zero change rows in this period, so “no observed event” is not confused with “category omitted from the extractor”.

## `data/processed/county_administrative_events_1983_2026.csv`

This is the browser-facing county event layer. It combines the 1987—2026 Wikipedia-derived records with 286 records from six 1983—1986 People's Daily archive pages and two separately labelled 区划地名网 transcription pages. The early importer keeps the full descriptive sentence and only fills `old_county_units`, `new_county_units`, and `prefecture_entity_ids` as search/display hints. `source_id`, `source_locator`, and `source_confidence` make the origin visible; parsed or transcribed rows still require page-level legal review before they can be treated as a strict county genealogy.

## `data/processed/unified_events_1987_2026.csv`

The reviewed 1987—2026 prefecture event table. `prefecture_administrative_events_1983_2026.csv` is the browser/package event interface: it preserves this table and appends the 67 early descriptive records from `prefecture_events_early_1983_1986.csv`. Its `entity_ids` and `prefecture_entity_ids` fields support related-card display; early rows deliberately set `automatic_continuity=false` and retain the full source wording in `description`. The display layer uses `description` as the event record; `old_prefecture_name` and `new_prefecture_name` remain analytical hints and are not rendered as a cleaned lineage. The 1983—1986 rows are event evidence, not a reconstructed annual legal roster.

The combined event layer uses one event-type vocabulary and one provenance structure across the periods. The query window is 1983—2026; the current source records end in 2018, while the annual status layer continues through 2026.

Historical units needed for complete lineage are registered in `historical_entities.csv`. Non-1:1 outcomes are represented in `unified_event_relations.csv`; in particular, Yanbei splits to Datong and Shuozhou, while the 1996 Chongqing transition links Wanxian, Fuling, and Qianjiang without permitting automatic value conversion.

`major_lineage_relations.csv` is the reviewed material-lineage layer built from county-level composition. `county_affiliation_transitions.csv` records the county-level units supporting each relation. It focuses on changes that materially alter the main territorial composition of a prefecture entity; incidental transfers of one or two peripheral counties are normally omitted. Every relation in this layer has `automatic_mapping=false`.

`data/audit/unified_continuity_audit.csv` is generated from the complete unified model. It checks event uniqueness, entity references, historical lifespans, province continuity, annual-roster names, chronological name chains, relation references, and the prohibition on automatic mapping for complex events.
