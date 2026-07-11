#!/usr/bin/env python3
"""Build the unified 1987-2026 annual entity/name status layer."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
YEARS = range(1987, 2027)


def read(name):
    with (DATA / name).open(encoding="utf-8", newline="") as handle: return list(csv.DictReader(handle))


def write(name, rows):
    with (DATA / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)


def main():
    entities = {r["entity_id"]: r for r in read("entities.csv")}
    historical = {r["historical_entity_id"]: r for r in read("historical_entities.csv")}
    events = defaultdict(list)
    for row in read("unified_events_1987_2026.csv"): events[row["entity_id"]].append(row)
    existing = {(r["entity_id"], int(r["year"])): r for r in read("legal_roster_2000_2024.csv")}
    roster = []
    for entity_id in [*entities, *historical]:
        timeline = sorted(events[entity_id], key=lambda r: (int(r["year"]), r["event_id"]))
        if entity_id in historical:
            meta = historical[entity_id]; start, end = int(meta["start_year"]), int(meta["end_year"])
            default_name, province = meta["canonical_name_zh"], meta["province_at_time"]
            terminating = [e for e in timeline if e["event_type"] in {"abolish", "merge", "split"}]
            if terminating: end = min(end, int(terminating[0]["year"]) - 1)
        else:
            meta = entities[entity_id]; start, end = 1987, 2026
            default_name, province = meta["canonical_name_zh"], meta["province_name_zh"]
            establishing = [e for e in timeline if e["event_type"] in {"establish", "establish_prefecture"}]
            if establishing: start = int(establishing[0]["year"])
        for year in YEARS:
            name, status, basis = default_name, "active", "event_chain_inference"
            if year < start: name, status, basis = "", "not_established", "event_chain_inference"
            elif year > end: name, status, basis = "", "abolished", "event_chain_inference"
            else:
                for event in reversed(timeline):
                    event_year = int(event["year"])
                    if event["automatic_continuity"] == "true":
                        if year < event_year and event["old_prefecture_name"]: name = event["old_prefecture_name"]
                        elif year >= event_year and event["new_prefecture_name"]: name = event["new_prefecture_name"]; break
                    # Some merge events are attached to the surviving stable entity
                    # (for example 石家庄地区 -> 石家庄市).  Only terminate a current
                    # entity when the event's old name is that entity's canonical name.
                    elif (event["event_type"] in {"abolish", "merge", "split"}
                          and year >= event_year
                          and (entity_id in historical or event["old_prefecture_name"] == default_name)):
                        name, status = "", "abolished"
                basis = "reviewed_event_chain"
            if (entity_id, year) in existing:
                old = existing[(entity_id, year)]
                name, status, basis = old["legal_name_zh"], old["status"], "existing_2000_2024_roster"
            roster.append({"entity_id": entity_id, "year": year, "legal_name_zh": name, "province_name_zh": province, "legal_level": "prefecture" if status == "active" else "none", "status": status, "verification_status": "reviewed" if basis != "event_chain_inference" else "inferred", "derivation_basis": basis})

    spans = []
    for entity_id in [*entities, *historical]:
        rows = [r for r in roster if r["entity_id"] == entity_id]
        start = rows[0]["year"]; previous = rows[0]
        for row in rows[1:] + [None]:
            if row is None or (row["legal_name_zh"], row["status"], row["verification_status"]) != (previous["legal_name_zh"], previous["status"], previous["verification_status"]):
                spans.append({"entity_id": entity_id, "name_zh": previous["legal_name_zh"], "start_year": start, "end_year": (row["year"] - 1 if row else 2026), "legal_status": previous["status"], "verification_status": previous["verification_status"], "derivation_basis": previous["derivation_basis"]})
                if row: start, previous = row["year"], row
    write("legal_roster_1987_2026.csv", roster)
    write("entity_names_1987_2026.csv", spans)
    print(f"entities={len(entities)+len(historical)} entity_years={len(roster)} spans={len(spans)} years=1987-2026")


if __name__ == "__main__": main()
