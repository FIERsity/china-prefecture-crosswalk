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
    "historical_entities.csv", "unified_event_relations.csv", "entity_id_crosswalk.csv",
    "entity_names_1987_2026.csv", "legal_roster_1987_2026.csv",
    "major_lineage_relations.csv", "county_affiliation_transitions.csv",
]

DEST.mkdir(parents=True, exist_ok=True)
for name in FILES: shutil.copyfile(SOURCE / name, DEST / name)
print(f"synced={len(FILES)} package_data={DEST}")
