#!/usr/bin/env python3
"""Copy runtime CSVs into the installable Python package."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed"
DEST = ROOT / "urban_crosswalk" / "data"
FILES = [
    "entities.csv", "entity_names.csv", "legal_roster_2000_2024.csv", "aliases.csv",
    "name_exclusions.csv", "events_2000_2026.csv", "event_entity_links.csv",
    "event_relations.csv", "wikipedia_change_pages.csv", "wikipedia_prefecture_change_rows.csv",
    "wikipedia_normalized_events_1987_1999.csv", "unified_events_1987_2026.csv",
    "prefecture_events_early_1983_1986.csv", "prefecture_administrative_events_1983_2026.csv",
    "historical_entities.csv", "unified_event_relations.csv", "entity_id_crosswalk.csv",
    "entity_names_1987_2026.csv", "legal_roster_1987_2026.csv",
    "entity_names_year_end_1987_2026.csv", "entity_name_match_ranges_1987_2026.csv",
    "legal_roster_year_end_1987_2026.csv", "event_timing_reviews.csv",
    "ctamap_snapshots.csv", "ctamap_prefecture_links.csv",
    "major_lineage_relations.csv", "county_affiliation_transitions.csv",
    "wikipedia_county_change_pages.csv", "wikipedia_county_change_rows.csv",
    "county_administrative_events_1987_2026.csv", "county_administrative_events_1983_1986.csv",
    "county_administrative_events_1983_2026.csv", "county_unit_type_coverage_1987_2026.csv",
    "source_registry.csv",
    "fixed_boundary_reference_units_2020.csv",
    "fixed_boundary_legacy_links.csv",
    "fixed_boundary_district_events_1987_2026.csv",
    "fixed_boundary_district_breaks_1999_2020.csv",
    "fixed_boundary_event_flags_1999_2020.csv",
]

DEST.mkdir(parents=True, exist_ok=True)
for name in FILES: shutil.copyfile(SOURCE / name, DEST / name)
print(f"synced={len(FILES)} package_data={DEST}")
