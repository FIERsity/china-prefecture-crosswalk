#!/usr/bin/env python3
"""Export the 345-row CNUR city research entity master table V2.0."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DEST = Path("/Volumes/DataHub/SourceData/admin/china")
OUTPUT = DEST / "china_city_entity_master_V2.0.csv"


def read(name):
    with (DATA / name).open(encoding="utf-8", newline="") as handle: return list(csv.DictReader(handle))


def main():
    crosswalk = read("entity_id_crosswalk.csv")
    entities = {r["entity_id"]: r for r in read("entities.csv")}
    historical = {r["historical_entity_id"]: r for r in read("historical_entities.csv")}
    names = defaultdict(list)
    for r in read("entity_names_1987_2026.csv"): names[r["entity_id"]].append(r)
    roster = defaultdict(list)
    for r in read("legal_roster_1987_2026.csv"): roster[r["entity_id"]].append(r)
    events = Counter(r["entity_id"] for r in read("unified_events_1987_2026.csv"))
    rows = []
    for item in crosswalk:
        eid = item["entity_id"]
        if eid in entities:
            e = entities[eid]; active = [r for r in roster[eid] if r["status"] == "active"]
            first, last = min(int(r["year"]) for r in active), max(int(r["year"]) for r in active)
            final = sorted(roster[eid], key=lambda r: int(r["year"]))[-1]
            spans = sorted(names[eid], key=lambda r: int(r["start_year"]))
            history = "; ".join(f"{r['start_year']}-{r['end_year']} {r['name_zh'] or '['+r['legal_status']+']'}" for r in spans)
            rows.append({"entity_id": eid, "legacy_entity_id": item["legacy_entity_id"], "canonical_name_zh": e["canonical_name_zh"], "entity_scope": "current_panel_entity", "province_name_zh": e["province_name_zh"], "province_short_zh": e["province_short_zh"], "entity_type": e["entity_level"], "first_active_year": first, "last_active_year": last, "status_in_2026": final["status"], "verification_status": e["verification_status"], "name_history": history, "event_count": events[eid], "successor_summary": "", "primary_source_url": ""})
        else:
            h = historical[eid]
            rows.append({"entity_id": eid, "legacy_entity_id": item["legacy_entity_id"], "canonical_name_zh": h["canonical_name_zh"], "entity_scope": "historical_entity", "province_name_zh": h["province_at_time"], "province_short_zh": h["province_at_time"].removesuffix("省"), "entity_type": h["entity_type"], "first_active_year": h["start_year"], "last_active_year": h["end_year"], "status_in_2026": "abolished", "verification_status": h["review_status"], "name_history": f"{h['start_year']}-{h['end_year']} {h['canonical_name_zh']}", "event_count": events[eid], "successor_summary": h["successor_summary"], "primary_source_url": h["source_url"]})
    DEST.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    print(f"{OUTPUT} rows={len(rows)}")


if __name__ == "__main__": main()
