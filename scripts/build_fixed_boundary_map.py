#!/usr/bin/env python3
"""Build the 2020-reference-year fixed-boundary map for whole-city panel
research.

For every prefecture-level unit that exists at the 2020 year end (the
reference boundary), the map records:

1. ``fixed_boundary_reference_units_2020.csv`` — one row per 2020 unit:
   how it came to be (``formation_path``), which years its whole-city
   statistical coverage was mechanically altered (``break_years``), and a
   ``treatment_hint`` for the researcher (aggregate vs weight vs flag).

2. ``fixed_boundary_legacy_links.csv`` — every predecessor unit
   (historical or since-merged/abolished) linked to the 2020 unit it
   feeds, with the relation type and a treatment hint, so panel values
   for any 1999-2020 year can be re-expressed on the fixed 2020 boundary.

Only whole-city events are considered here (merge / split / abolish /
cross-prefecture transfer / establishment of a new city carving out
territory).  County-to-district conversions and within-city adjustments
do not change the whole-city boundary and belong to the municipal-district
layer, not this table.

Sources: year-end roster (2020 active units), unified event relations,
event timing reviews (annual effective year), entity/historical catalogs.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

# Event types that alter a unit's whole-city territorial scope.
WHOLE_CITY_EVENTS = {"merge", "split", "abolish", "jurisdiction_transfer", "major_transfer"}
# Event types that are identity-continuous (rename / 撤地设市 upgrade keep
# the same research entity; no territorial break, but the unit may enter the
# city sample of statistical yearbooks for the first time).
CONTINUOUS_EVENTS = {"rename", "upgrade", "establish_prefecture"}

FIELDS_UNITS = [
    "entity_id", "canonical_name", "province", "formation_path",
    "break_years", "sample_entry_year", "treatment_hint",
]
FIELDS_LINKS = [
    "from_entity_id", "from_name", "to_entity_id", "to_name",
    "relation_type", "year", "automatic_continuity", "mapping_quality",
    "treatment_hint", "review_note",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def treatment_hint(relation_type: str, mapping_quality: str, automatic: bool) -> str:
    if automatic:
        return "continuous_identity"
    if mapping_quality == "aggregate":
        return "aggregate_safe"
    if mapping_quality == "disaggregate":
        return "split_needs_weight"
    if relation_type == "jurisdiction_transfer":
        return "transfer_aggregate_safe"
    return "break_flag_only"


def main() -> None:
    roster = read_csv(DATA / "legal_roster_year_end_1987_2026.csv")
    entities = {row["entity_id"]: row for row in read_csv(DATA / "entities.csv")}
    historical = {row["historical_entity_id"]: row for row in read_csv(DATA / "historical_entities.csv")}
    relations = read_csv(DATA / "unified_event_relations.csv")
    timing = {row["event_id"]: row for row in read_csv(DATA / "event_timing_reviews.csv")}
    # Material county-level transfers (major lineage) also change a unit's
    # whole-city scope even though they are county-level events: e.g. 2015
    # 枞阳→铜陵, 2016 简阳→成都, 2020 公主岭→长春.
    major_lineage = read_csv(DATA / "major_lineage_relations.csv")

    name_of = {eid: row["canonical_name_zh"] for eid, row in entities.items()}
    name_of.update({eid: row["canonical_name_zh"] for eid, row in historical.items()})

    # ---- reference units: 2020 year-end active prefecture units ----
    ref = [
        row for row in roster
        if row["year"] == "2020" and row["status"] == "active" and row["entity_id"]
    ]
    ref_ids = {row["entity_id"] for row in ref}
    ref_province = {row["entity_id"]: row["province_name_zh"] for row in ref}

    # ---- collect events per reference unit ----
    # Relations point from_entity -> to_entity; a relation is "about" a unit
    # when the unit appears as from or to.
    events_by_unit: dict[str, list[dict[str, str]]] = {}
    for rel in relations:
        for unit in {rel["from_entity_id"], rel["to_entity_id"]}:
            if unit:
                events_by_unit.setdefault(unit, []).append(rel)
    # Major lineage relations: county-level carve-outs / transfers /
    # territory contributions between prefecture entities.
    for case in major_lineage:
        fid, tid = case["from_entity_id"], case["to_entity_id"]
        if not tid:
            continue
        events_by_unit.setdefault(fid, []).append({
            "event_id": case["source_event_id"],
            "relation_type": "major_transfer",
            "from_entity_id": fid, "to_entity_id": tid,
            "year": case["year"], "mapping_quality": case.get("materiality", ""),
            "automatic_mapping": "false", "review_note": f"major lineage: {case['relation_type']}",
        })
        events_by_unit.setdefault(tid, []).append({
            "event_id": case["source_event_id"],
            "relation_type": "major_transfer",
            "from_entity_id": fid, "to_entity_id": tid,
            "year": case["year"], "mapping_quality": case.get("materiality", ""),
            "automatic_mapping": "false", "review_note": f"major lineage: {case['relation_type']}",
        })

    # ---- legacy links: every non-2020 unit maps to a 2020 reference unit ----
    # Walk relations from_entity -> to_entity; resolve to the 2020 unit by
    # following successor chains (to_entity itself may be a historical unit).
    def resolve_to_ref(entity_id: str) -> str | None:
        seen = set()
        current = entity_id
        while current and current not in ref_ids:
            if current in seen:
                return None
            seen.add(current)
            next_id = None
            for rel in events_by_unit.get(current, []):
                # follow the successor edge (to_entity_id) of this unit
                if rel["from_entity_id"] == current and rel["to_entity_id"]:
                    next_id = rel["to_entity_id"]
                    break
            if next_id is None:
                return None
            current = next_id
        return current if current in ref_ids else None

    links: list[dict[str, object]] = []
    for rel in relations:
        fid, tid = rel["from_entity_id"], rel["to_entity_id"]
        if not fid:
            continue
        year = int(rel.get("year") or 0)
        # Both ends may be historical; resolve the target to a 2020 unit.
        resolved = resolve_to_ref(tid) if tid else None
        if tid and resolved is None:
            # 2020 单位自身 as target
            resolved = tid if tid in ref_ids else None
        to_ref = resolved or tid or ""
        automatic = rel.get("automatic_mapping") == "true"
        links.append({
            "from_entity_id": fid,
            "from_name": name_of.get(fid, ""),
            "to_entity_id": to_ref,
            "to_name": name_of.get(to_ref, ""),
            "relation_type": rel["relation_type"],
            "year": year,
            "automatic_continuity": rel.get("automatic_mapping", ""),
            "mapping_quality": rel.get("mapping_quality", ""),
            "treatment_hint": treatment_hint(rel["relation_type"], rel.get("mapping_quality", ""), automatic),
            "review_note": rel.get("review_note", ""),
        })

    # ---- unit table ----
    units: list[dict[str, object]] = []
    for unit_id in sorted(ref_ids):
        name = name_of.get(unit_id, "")
        province = ref_province.get(unit_id, "")
        unit_events = events_by_unit.get(unit_id, [])
        # formation path: first non-continuous relation involving the unit
        formation = "stable"
        for rel in unit_events:
            rtype = rel["relation_type"]
            if rtype in WHOLE_CITY_EVENTS:
                if rel["from_entity_id"] == unit_id and rel["to_entity_id"]:
                    formation = "split_origin" if rtype == "split" else "merged_away"
                else:
                    formation = "merge_successor" if rtype == "merge" else (
                        "split_successor" if rtype == "split" else "transfer_in")
                break
        if formation == "stable":
            for rel in unit_events:
                if rel["relation_type"] == "establish":
                    formation = "new_established"
                    break
                if rel["relation_type"] in CONTINUOUS_EVENTS:
                    formation = "continuous_upgrade"
                    break
        # break years: whole-city events effective during 1999-2020 panel
        break_years = sorted({
            int(timing[rel["event_id"]]["annual_effective_year"])
            if rel["event_id"] in timing and rel["relation_type"] != "major_transfer"
            else int(rel["year"])
            for rel in unit_events
            if rel["relation_type"] in WHOLE_CITY_EVENTS
            and 1999 <= (
                int(timing[rel["event_id"]]["annual_effective_year"])
                if rel["event_id"] in timing and rel["relation_type"] != "major_transfer"
                else int(rel["year"])
            ) <= 2020
        })
        # sample entry: first active year in the yearbook panel
        first_active = min(int(row["year"]) for row in roster if row["entity_id"] == unit_id and row["status"] == "active")
        sample_entry = first_active if first_active > 1999 else 0
        units.append({
            "entity_id": unit_id,
            "canonical_name": name,
            "province": province,
            "formation_path": formation,
            "break_years": "、".join(str(y) for y in break_years) or "",
            "sample_entry_year": sample_entry,
            "treatment_hint": "aggregate_safe" if not break_years and formation in {"stable", "continuous_upgrade"} else "break_flag_only",
        })

    write_csv(DATA / "fixed_boundary_reference_units_2020.csv", FIELDS_UNITS, units)
    write_csv(DATA / "fixed_boundary_legacy_links.csv", FIELDS_LINKS, links)
    print(f"reference_units={len(units)} legacy_links={len(links)}")


if __name__ == "__main__":
    main()
