#!/usr/bin/env python3
"""Build the municipal-district-layer fixed-boundary map.

County-to-district conversions (撤县设区 / 撤市设区) do not change a
city's whole-city boundary, but they mechanically inflate the
municipal-district statistics (area, population, GDP) of the host city
and remove the annexed county from county-level panels. This module
extracts every district-scope event from the county event layer and
emits:

1. ``fixed_boundary_district_events_1987_2026.csv`` — one row per event
   with the category, the old/new units, the unit scope, and a treatment
   hint.

2. ``fixed_boundary_district_breaks_1999_2020.csv`` — city x panel-year
   counts of district-scope jumps, for direct merge into a panel.

Categories:
- ``county_to_district``: 撤销县/县级市设立市辖区 (scope jump + county
  panel break)
- ``district_merge``: 市辖区合并 (aggregate-safe for the merged district)
- ``district_transfer``: 部分乡镇/街道跨区划转 (minor adjustment)
- ``district_other``: 其他市辖区级撤并 (e.g. 区级合并伴更名)

Sources: county_administrative_events_1983_2026.csv.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
EVENTS = DATA / "county_administrative_events_1983_2026.csv"

PANEL_START, PANEL_END = 1999, 2020

FIELDS_EVENTS = [
    "event_id", "year", "prefecture_entity_id", "prefecture_name",
    "old_county_units", "new_district_units", "event_category",
    "unit_scope", "treatment_hint", "source_url",
]
FIELDS_BREAKS = [
    "prefecture_entity_id", "prefecture_name", "year",
    "county_to_district_count", "district_merge_count", "break_flag",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def classify(row: dict[str, str]) -> str | None:
    et, t = row["event_type"], row["county_unit_types"]
    old, new = row.get("old_county_units", ""), row.get("new_county_units", "")
    # County-to-district conversion is a semantic property: Wikipedia records
    # some of them as transfer/rename/split, so judge on the structured
    # unit fields, not on the event type.  Excludes 撤县设市 (new = 市).
    if "市辖区" in t and "县" in t and new and "区" in new and ("县" in old or "市" in old):
        return "county_to_district"
    if et == "merge" and "市辖区" in t:
        return "district_merge"
    if et == "abolish_or_merge" and "市辖区" in t and "县" not in t:
        return "district_other"
    if et in ("jurisdiction_transfer", "jurisdiction_adjustment") and "市辖区" in t:
        return "district_transfer"
    return None


def unit_scope(row: dict[str, str], category: str) -> str:
    if category == "county_to_district":
        return "whole_county"
    if "部分" in row.get("change_description", "") or "划归" in row.get("change_description", ""):
        return "partial"
    return "whole"


def treatment_hint(category: str, scope: str) -> str:
    if category == "county_to_district":
        return "district_scope_jump_county_panel_break"
    if category == "district_merge":
        return "district_merge_aggregate_safe"
    if category == "district_transfer":
        return "district_internal_adjust"
    return "district_scope_jump"


def main() -> None:
    events = read_csv(EVENTS)
    name_of_entity: dict[str, str] = {}
    for row in read_csv(DATA / "entities.csv"):
        name_of_entity[row["entity_id"]] = row["canonical_name_zh"]
    for row in read_csv(DATA / "historical_entities.csv"):
        name_of_entity[row["historical_entity_id"]] = row["canonical_name_zh"]

    rows: list[dict[str, object]] = []
    for event in events:
        category = classify(event)
        if category is None:
            continue
        # one row per affected prefecture entity (some events span two)
        prefectures = [pid for pid in event["prefecture_entity_ids"].split("、") if pid]
        if not prefectures:
            continue
        prefecture_name = name_of_entity.get(prefectures[0], event.get("prefecture_names", "").split("、")[0] if event.get("prefecture_names") else "")
        for pid in prefectures:
            scope = unit_scope(event, category)
            rows.append({
                "event_id": event["event_id"],
                "year": int(event["year"]),
                "prefecture_entity_id": pid,
                "prefecture_name": name_of_entity.get(pid, prefecture_name),
                "old_county_units": event.get("old_county_units", ""),
                "new_district_units": event.get("new_county_units", ""),
                "event_category": category,
                "unit_scope": scope,
                "treatment_hint": treatment_hint(category, scope),
                "source_url": event.get("source_url", ""),
            })

    rows.sort(key=lambda r: (r["year"], r["prefecture_entity_id"], r["event_id"]))
    write_csv(DATA / "fixed_boundary_district_events_1987_2026.csv", FIELDS_EVENTS, rows)

    # city x panel-year summary
    by_key: dict[tuple[str, int], list[dict[str, object]]] = {}
    for r in rows:
        if not (PANEL_START <= r["year"] <= PANEL_END):
            continue
        by_key.setdefault((r["prefecture_entity_id"], r["year"]), []).append(r)

    breaks: list[dict[str, object]] = []
    for (pid, year), group in sorted(by_key.items()):
        c2d = sum(1 for g in group if g["event_category"] == "county_to_district")
        dm = sum(1 for g in group if g["event_category"] == "district_merge")
        breaks.append({
            "prefecture_entity_id": pid,
            "prefecture_name": name_of_entity.get(pid, ""),
            "year": year,
            "county_to_district_count": c2d,
            "district_merge_count": dm,
            "break_flag": "1" if c2d else "",
        })
    write_csv(DATA / "fixed_boundary_district_breaks_1999_2020.csv", FIELDS_BREAKS, breaks)
    print(f"district_events={len(rows)} breaks={len(breaks)}")


if __name__ == "__main__":
    main()
