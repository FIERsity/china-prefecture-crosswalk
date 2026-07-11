#!/usr/bin/env python3
"""Audit temporal and relational continuity across the unified event model."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTPUT = ROOT / "data" / "audit" / "unified_continuity_audit.csv"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    events = read("unified_events_1987_2026.csv")
    relations = read("unified_event_relations.csv")
    current = {row["entity_id"]: row for row in read("entities.csv")}
    historical = {row["historical_entity_id"]: row for row in read("historical_entities.csv")}
    roster = {(row["entity_id"], int(row["year"])): row for row in read("legal_roster_1987_2026.csv")}
    event_ids = {row["event_id"] for row in events}
    entity_ids = set(current) | set(historical)
    findings: list[dict[str, str]] = []

    def add(check: str, status: str, subject: str, detail: str) -> None:
        findings.append({"check": check, "status": status, "subject": subject, "detail": detail})

    duplicate_ids = len(events) - len(event_ids)
    add("unique_event_id", "pass" if not duplicate_ids else "error", "all_events", f"duplicates={duplicate_ids}")
    signatures = [(r["year"], r["event_type"], r["old_prefecture_name"], r["new_prefecture_name"]) for r in events]
    add("unique_event_signature", "pass" if len(signatures) == len(set(signatures)) else "error", "all_events", f"events={len(events)}")

    for event in events:
        eid, year = event["entity_id"], int(event["year"])
        add("entity_reference", "pass" if eid in entity_ids else "error", event["event_id"], eid)
        automatic_allowed = event["event_type"] in {"rename", "upgrade"} and bool(event["old_prefecture_name"] and event["new_prefecture_name"])
        actual = event["automatic_continuity"] == "true"
        add("automatic_continuity", "pass" if actual == automatic_allowed else "error", event["event_id"], f"type={event['event_type']} automatic={actual}")
        if eid in historical:
            start, end = int(historical[eid]["start_year"]), int(historical[eid]["end_year"])
            add("historical_lifespan", "pass" if start <= year <= end else "error", event["event_id"], f"event={year} lifespan={start}-{end}")
        if eid in current and event["province_name"] != current[eid]["province_name_zh"]:
            allowed = "historical_province_differs_from_current_entity" in event["risk_flags"]
            add("province_continuity", "pass" if allowed else "error", event["event_id"], f"event={event['province_name']} entity={current[eid]['province_name_zh']}")
        if 1987 <= year <= 2026:
            annual = roster[(eid, year)]
            if event["event_type"] in {"rename", "upgrade", "establish"} and event["new_prefecture_name"]:
                add("event_roster_name", "pass" if annual["legal_name_zh"] == event["new_prefecture_name"] else "error", event["event_id"], f"event={event['new_prefecture_name']} roster={annual['legal_name_zh']}")

    by_entity: dict[str, list[dict[str, str]]] = {}
    for event in events: by_entity.setdefault(event["entity_id"], []).append(event)
    for eid, timeline in by_entity.items():
        timeline.sort(key=lambda row: (int(row["year"]), row["event_id"]))
        for previous, current_event in zip(timeline, timeline[1:]):
            if previous["new_prefecture_name"] and current_event["old_prefecture_name"] and previous["automatic_continuity"] == "true" and current_event["automatic_continuity"] == "true":
                matches = previous["new_prefecture_name"] == current_event["old_prefecture_name"]
                add("name_chain", "pass" if matches else "error", eid, f"{previous['event_id']}:{previous['new_prefecture_name']} -> {current_event['event_id']}:{current_event['old_prefecture_name']}")
        years = [int(row["year"]) for row in timeline]
        add("chronological_order", "pass" if years == sorted(years) else "error", eid, ",".join(map(str, years)))

    for relation in relations:
        add("relation_event_reference", "pass" if relation["event_id"] in event_ids else "error", relation["event_id"], relation["relation_type"])
        add("relation_from_entity", "pass" if relation["from_entity_id"] in entity_ids else "error", relation["event_id"], relation["from_entity_id"])
        if relation["to_entity_id"]:
            add("relation_to_entity", "pass" if relation["to_entity_id"] in entity_ids else "error", relation["event_id"], relation["to_entity_id"])
        safe = relation["relation_type"] not in {"merge", "split", "abolish", "jurisdiction_transfer"} or relation["automatic_mapping"] == "false"
        add("complex_relation_mapping", "pass" if safe else "error", relation["event_id"], f"{relation['relation_type']} automatic={relation['automatic_mapping']}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(findings[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(findings)
    errors = [row for row in findings if row["status"] == "error"]
    print(f"checks={len(findings)} pass={len(findings)-len(errors)} errors={len(errors)}")
    for row in errors: print(row)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
