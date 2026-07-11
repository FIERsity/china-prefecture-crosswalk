#!/usr/bin/env python3
"""Combine all normalized prefecture events into one 1987-2026 schema."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTPUT = DATA / "unified_events_1987_2026.csv"
RELATIONS_OUTPUT = DATA / "unified_event_relations.csv"
TYPE_MAP = {
    "地区改设地级市": "upgrade", "盟改设地级市": "upgrade",
    "县级市升格为地级市": "upgrade", "地级市更名": "rename",
    "以县新设地级市": "establish", "撤销办事处并新设地级市": "establish",
    "撤销地区并将辖区划归自治州": "abolish", "撤销地级市并分拆辖区": "split",
    "撤销地级市并整体并入另一地级市": "merge",
}


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    historical = read("wikipedia_normalized_events_1987_1999.csv")
    current = read("events_2000_2026.csv")
    links = {row["event_id"]: row["entity_id"] for row in read("event_entity_links.csv")}
    entities = {row["entity_id"]: row for row in read("entities.csv")}
    historical_entities = {row["historical_entity_id"]: row for row in read("historical_entities.csv")}
    rows = []
    for row in historical:
        rows.append({
            "event_id": row["event_id"], "year": row["year"], "province_name": row["province_name"],
            "event_type": row["event_type"], "entity_id": row["entity_id"],
            "old_prefecture_name": row["old_prefecture_name"], "new_prefecture_name": row["new_prefecture_name"],
            "approval_date": row["approval_date"], "document_number": row["document_number"],
            "automatic_continuity": row["automatic_continuity"], "confidence": row["confidence"],
            "review_status": row["normalization_status"], "risk_flags": row["risk_flags"],
            "description": row["description"], "review_note": row["review_note"],
            "source_url": row["source_url"], "source_revision_id": row["revision_id"],
            "source_locator": f"row:{row['source_row_number']}", "source_layer": "wikipedia_semantic_normalization",
        })
    for row in current:
        entity_id = links[row["事件ID"]]
        relation_type = TYPE_MAP[row["事件类型"]]
        risks = []
        if relation_type in {"merge", "split"}: risks.append(f"{relation_type}_event")
        if row["年份"] == "2018" and row["事件ID"] == "PL-2018-001": risks.append("publication_year_differs")
        rows.append({
            "event_id": row["事件ID"], "year": row["年份"], "province_name": row["省级单位"],
            "event_type": relation_type, "entity_id": entity_id,
            "old_prefecture_name": row["原单位"], "new_prefecture_name": row["新单位"],
            "approval_date": row["批准日期"], "document_number": row["批复文号"],
            "automatic_continuity": "true" if relation_type in {"rename", "upgrade"} else "false",
            "confidence": "high" if row["置信度"] == "高" else "medium",
            "review_status": "accepted_reviewed", "risk_flags": "|".join(risks),
            "description": row["处理凭证（释义）"], "review_note": row["判定备注"],
            "source_url": row["来源URL"], "source_revision_id": "",
            "source_locator": row["网页行号凭证"], "source_layer": "reviewed_event_workbook",
        })
    rows.sort(key=lambda item: (int(item["year"]), item["event_id"]))
    # Reconcile province from the linked entity, preserving explicit historical scope in notes.
    for row in rows:
        if row["entity_id"] and row["entity_id"] in entities:
            expected = entities[row["entity_id"]]["province_name_zh"]
            if row["province_name"] and row["province_name"] != expected:
                row["risk_flags"] = "|".join(filter(None, [row["risk_flags"], "historical_province_differs_from_current_entity"]));
            elif not row["province_name"]:
                row["province_name"] = expected
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    relations = []
    for row in rows:
        if row["entity_id"]:
            relations.append({"event_id": row["event_id"], "from_entity_id": row["entity_id"], "to_entity_id": row["entity_id"] if row["automatic_continuity"] == "true" else "", "relation_type": row["event_type"], "mapping_quality": "exact" if row["automatic_continuity"] == "true" else "event_only", "automatic_mapping": row["automatic_continuity"], "review_note": row["review_note"]})
    # Explicit non-1:1 relationships found during final network review.
    relations.extend([
        {"event_id": "WIKI-1993-029", "from_entity_id": "HIST-SX-YANBEI", "to_entity_id": "E140200", "relation_type": "split", "mapping_quality": "disaggregate", "automatic_mapping": "false", "review_note": "seven former Yanbei counties transferred to Datong"},
        {"event_id": "WIKI-1993-029", "from_entity_id": "HIST-SX-YANBEI", "to_entity_id": "E140600", "relation_type": "split", "mapping_quality": "disaggregate", "automatic_mapping": "false", "review_note": "Huairen, Youyu, and Ying counties transferred to Shuozhou"},
        {"event_id": "WIKI-1996-056", "from_entity_id": "HIST-CQ-WANXIAN", "to_entity_id": "E500100", "relation_type": "jurisdiction_transfer", "mapping_quality": "aggregate", "automatic_mapping": "false", "review_note": "entrusted to Chongqing administration in 1996"},
        {"event_id": "WIKI-1996-056", "from_entity_id": "HIST-CQ-FULING", "to_entity_id": "E500100", "relation_type": "jurisdiction_transfer", "mapping_quality": "aggregate", "automatic_mapping": "false", "review_note": "entrusted to Chongqing administration in 1996"},
        {"event_id": "WIKI-1996-056", "from_entity_id": "HIST-CQ-QIANJIANG", "to_entity_id": "E500100", "relation_type": "jurisdiction_transfer", "mapping_quality": "aggregate", "automatic_mapping": "false", "review_note": "entrusted to Chongqing administration in 1996"},
    ])
    with RELATIONS_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(relations[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(relations)
    print(f"events={len(rows)} years={rows[0]['year']}-{rows[-1]['year']}")


if __name__ == "__main__":
    main()
