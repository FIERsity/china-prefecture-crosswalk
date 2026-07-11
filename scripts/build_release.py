#!/usr/bin/env python3
"""Build the first machine-readable release from the repository snapshots."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
YEARS = range(2000, 2025)

# Corrections verified against the linked Chinese Wikipedia annual change lists.
# Empty years mean that the research entity was not an active legal prefecture.
CORRECTIONS = {
    "E533400": [(2000, 2024, "迪庆藏族自治州", "active")],
    "E341400": [(2000, 2010, "巢湖市", "active"), (2011, 2024, "", "abolished")],
    "E371200": [(2000, 2018, "莱芜市", "active"), (2019, 2024, "", "abolished")],
    "E654100": [(2000, 2000, "伊犁地区", "active"), (2001, 2024, "", "abolished")],
    "E460300": [(2000, 2011, "", "not_established"), (2012, 2024, "三沙市", "active")],
    "E460400": [(2000, 2014, "", "not_prefecture_level"), (2015, 2024, "儋州市", "active")],
    "E640500": [(2000, 2002, "", "not_established"), (2003, 2024, "中卫市", "active")],
    "E540300": [(2000, 2013, "昌都地区", "active"), (2014, 2024, "昌都市", "active")],
    "E530800": [(2000, 2002, "思茅地区", "active"), (2003, 2006, "思茅市", "active"), (2007, 2024, "普洱市", "active")],
    "E530900": [(2000, 2002, "临沧地区", "active"), (2003, 2024, "临沧市", "active")],
}

SOURCE_BY_ENTITY = {
    "E654100": "SRC-WIKI-2001",
    "E530800": "SRC-WIKI-2003",
    "E530900": "SRC-WIKI-2003",
    "E640500": "SRC-WIKI-2003",
    "E341400": "SRC-WIKI-2011",
    "E460300": "SRC-WIKI-2012",
    "E540300": "SRC-WIKI-2014",
    "E460400": "SRC-WIKI-2015",
    "E371200": "SRC-WIKI-2019",
    "E533400": "SRC-WIKI-DIQING",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def corrected_value(entity_id: str, year: int, fallback: str) -> tuple[str, str, str]:
    if entity_id not in CORRECTIONS:
        return fallback, "active", "inherited_unverified"
    for start, end, name, status in CORRECTIONS[entity_id]:
        if start <= year <= end:
            return name, status, "wikipedia_verified"
    raise AssertionError((entity_id, year))


def main() -> None:
    panel = read_csv(RAW / "prefecture_master_wide_2000_2024.csv")
    events = read_csv(PROCESSED / "events_2000_2026.csv")
    names_by_entity = {
        row["entity_id"]: {value for key, value in row.items() if key.startswith("name_") and value}
        for row in panel
    }
    event_links: list[dict[str, object]] = []
    crosschecked_entities: set[str] = set()
    for event in events:
        old_name, new_name = event["原单位"], event["新单位"]
        old_matches = [entity_id for entity_id, names in names_by_entity.items() if old_name and old_name in names]
        new_matches = [entity_id for entity_id, names in names_by_entity.items() if new_name and new_name in names]
        # Prefer the disappearing entity for abolitions/mergers; otherwise the new entity.
        matches = old_matches if "撤销" in event["事件类型"] and old_matches else new_matches or old_matches
        match_status = "unique" if len(matches) == 1 else "ambiguous" if matches else "unmatched"
        entity_id = matches[0] if len(matches) == 1 else ""
        if entity_id:
            crosschecked_entities.add(entity_id)
        event_links.append({
            "event_id": event["事件ID"],
            "entity_id": entity_id,
            "match_status": match_status,
            "match_basis": "old_name" if matches is old_matches else "new_name",
            "manual_review_required": "false" if match_status == "unique" else "true",
        })
    legal_rows: list[dict[str, object]] = []
    name_rows: list[dict[str, object]] = []
    entity_rows: list[dict[str, object]] = []

    for row in panel:
        entity_id = row["entity_id"]
        timeline = []
        for year in YEARS:
            name, status, verification = corrected_value(entity_id, year, row[f"name_{year}"])
            if verification == "inherited_unverified" and entity_id in crosschecked_entities:
                verification = "event_crosschecked"
            timeline.append((year, name, status, verification))
            legal_rows.append({
                "entity_id": entity_id,
                "year": year,
                "legal_name_zh": name,
                "legal_level": "prefecture" if status == "active" else "none",
                "status": status,
                "verification_status": verification,
                "source_id": SOURCE_BY_ENTITY.get(entity_id, "SRC-LEGACY-SNAPSHOT"),
            })

        start_year, prev_name, prev_status, prev_verification = timeline[0]
        for year, name, status, verification in timeline[1:] + [(2025, None, None, None)]:
            if (name, status, verification) != (prev_name, prev_status, prev_verification):
                name_rows.append({
                    "entity_id": entity_id,
                    "name_zh": prev_name or "",
                    "start_year": start_year,
                    "end_year": year - 1,
                    "legal_status": prev_status,
                    "verification_status": prev_verification,
                    "source_id": SOURCE_BY_ENTITY.get(entity_id, "SRC-LEGACY-SNAPSHOT"),
                })
                start_year, prev_name, prev_status, prev_verification = year, name, status, verification

        active_names = [name for _, name, status, _ in timeline if status == "active" and name]
        entity_rows.append({
            "entity_id": entity_id,
            "canonical_name_zh": active_names[-1],
            "entity_level": "prefecture_research_entity",
            "id_namespace": "project_stable_id_not_official_code",
            "verification_status": "wikipedia_verified" if entity_id in CORRECTIONS else "event_crosschecked" if entity_id in crosschecked_entities else "inherited_unverified",
        })

    write_csv(PROCESSED / "entities.csv", list(entity_rows[0]), entity_rows)
    write_csv(PROCESSED / "entity_names.csv", list(name_rows[0]), name_rows)
    write_csv(PROCESSED / "legal_roster_2000_2024.csv", list(legal_rows[0]), legal_rows)
    write_csv(PROCESSED / "event_entity_links.csv", list(event_links[0]), event_links)


if __name__ == "__main__":
    main()
