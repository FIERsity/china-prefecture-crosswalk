#!/usr/bin/env python3
"""Apply the permanent CNUR research-entity namespace to processed data."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
AUDIT = ROOT / "data" / "audit"
CROSSWALK = DATA / "entity_id_crosswalk.csv"

FILES = {
    DATA / "entities.csv": ["entity_id"],
    DATA / "entity_names.csv": ["entity_id"],
    DATA / "legal_roster_2000_2024.csv": ["entity_id"],
    DATA / "aliases.csv": ["entity_id"],
    DATA / "event_entity_links.csv": ["entity_id"],
    DATA / "name_exclusions.csv": ["parent_entity_id"],
    DATA / "event_relations.csv": ["entity_id"],
    DATA / "wikipedia_normalized_events_1987_1999.csv": ["entity_id"],
    DATA / "unified_events_1987_2026.csv": ["entity_id"],
    DATA / "historical_entities.csv": ["historical_entity_id"],
    DATA / "unified_event_relations.csv": ["from_entity_id", "to_entity_id"],
    AUDIT / "wikipedia_entity_audit.csv": ["entity_id"],
}


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle); return list(reader.fieldnames or []), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def create_crosswalk() -> None:
    if CROSSWALK.exists(): return
    _, entities = read(DATA / "entities.csv")
    _, historical = read(DATA / "historical_entities.csv")
    rows = []
    for row in entities:
        rows.append({"entity_id": f"CNUR-{len(rows)+1:06d}", "legacy_entity_id": row["entity_id"], "canonical_name_zh": row["canonical_name_zh"], "entity_scope": "current_panel_entity", "id_status": "permanent"})
    for row in historical:
        rows.append({"entity_id": f"CNUR-{len(rows)+1:06d}", "legacy_entity_id": row["historical_entity_id"], "canonical_name_zh": row["canonical_name_zh"], "entity_scope": "historical_entity", "id_status": "permanent"})
    write(CROSSWALK, list(rows[0]), rows)


def main() -> None:
    create_crosswalk()
    _, crosswalk = read(CROSSWALK)
    mapping = {row["legacy_entity_id"]: row["entity_id"] for row in crosswalk}
    _, audit_rows = read(AUDIT / "wikipedia_entity_audit.csv")
    audited = {mapping.get(row["entity_id"], row["entity_id"]) for row in audit_rows if row["review_status"] == "verified"}
    for path, columns in FILES.items():
        fields, rows = read(path)
        for row in rows:
            for column in columns:
                if row.get(column) in mapping: row[column] = mapping[row[column]]
        if path.name == "entities.csv" and "legacy_entity_id" not in fields:
            fields.insert(1, "legacy_entity_id")
            reverse = {row["entity_id"]: row["legacy_entity_id"] for row in crosswalk}
            for row in rows: row["legacy_entity_id"] = reverse[row["entity_id"]]
        if path.name == "entities.csv":
            for row in rows:
                if row["entity_id"] in audited and row["verification_status"] == "inherited_unverified": row["verification_status"] = "wikipedia_entity_verified"
        if path.name == "historical_entities.csv" and "legacy_entity_id" not in fields:
            fields.insert(1, "legacy_entity_id")
            reverse = {row["entity_id"]: row["legacy_entity_id"] for row in crosswalk}
            for row in rows: row["legacy_entity_id"] = reverse[row["historical_entity_id"]]
        write(path, fields, rows)
    print(f"migrated={len(mapping)} namespace=CNUR")


if __name__ == "__main__": main()
