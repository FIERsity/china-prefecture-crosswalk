#!/usr/bin/env python3
"""Conservatively normalize pre-2000 prefecture events from Wikipedia rows."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "wikipedia_prefecture_change_rows.csv"
OUTPUT = ROOT / "data" / "processed" / "wikipedia_normalized_events_1987_1999.csv"
ENTITIES = ROOT / "data" / "processed" / "entities.csv"
NAMES = ROOT / "data" / "processed" / "entity_names.csv"
PROVINCE_RE = re.compile(r"(?:colspan=\"?\d+\"?\|)?(北京市|天津市|上海市|重庆市|[^|]{2,12}(?:省|自治区))$")
DOC_RE = re.compile(r"(?:国函|民行批|民批|中发|中办厅字)〔?\d{4}〕?\d+号")
DATE_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日")
MANUAL_ENTITY_LINKS = {
    "WIKI-1988-016": ("CNUR-000348", "安庆地区与既有安庆市合并并析设池州地区"),
    "WIKI-1988-017": ("E341700", "池州地区 later continued as the Chizhou research entity"),
    "WIKI-1988-018": ("E350700", "建阳地区 renamed 南平地区 and later became 南平市"),
    "WIKI-1992-021": ("CNUR-000349", "宜昌地区 merged into the existing 宜昌市"),
    "WIKI-1992-023": ("E371600", "惠民地区 renamed 滨州地区 and later became 滨州市"),
    "WIKI-1993-028": ("CNUR-000350", "石家庄地区 merged into 石家庄市"),
    "WIKI-1994-041": ("CNUR-000357", "郧阳地区 merged into 十堰市"),
    "WIKI-1994-042": ("CNUR-000358", "荆州地区 and 沙市市 merged into the new 荆沙市"),
    "WIKI-1997-065": ("E511400", "眉山地区 later became 眉山市"),
    "WIKI-1998-072": ("E512000", "资阳地区 later became 资阳市"),
}
MANUAL_ACCEPT_EVENTS = {
    "WIKI-1988-007": "朔州市 was explicitly established as a prefecture-level city",
    "WIKI-1988-011": "汕尾市 was explicitly established as a prefecture-level city",
    "WIKI-1988-012": "河源市 was explicitly established as a prefecture-level city",
    "WIKI-1988-014": "阳江市 was explicitly established as a prefecture-level city",
    "WIKI-1988-015": "清远市 was explicitly established as a prefecture-level city",
    "WIKI-1988-016": "安庆地区 and the existing city were merged into the unified 安庆市",
    "WIKI-1992-022": "松原市 was explicitly established as a prefecture-level city",
    "WIKI-1993-026": "孝感市 was explicitly established as a prefecture-level city",
    "WIKI-1993-030": "防城港市 was explicitly established as a prefecture-level city",
    "WIKI-1994-038": "郴州市 was explicitly established as a prefecture-level city",
}
MANUAL_HISTORICAL_LINKS = {
    "WIKI-1987-003": ("HIST-HN-LMZ", "abolished historical autonomous prefecture; former counties moved to direct Hainan Administrative Region control"),
    "WIKI-1992-020": ("HIST-CQ-WANXIAN", "Wanxian Prefecture continued as the historical prefecture-level Wanxian City until 1997"),
    "WIKI-1993-029": ("HIST-SX-YANBEI", "Yanbei was abolished and split between Datong and Shuozhou"),
    "WIKI-1995-048": ("HIST-CQ-FULING", "Fuling Prefecture continued as historical prefecture-level Fuling City until 1997"),
    "WIKI-1996-056": ("HIST-CQ-QIANJIANG", "multi-entity transition: Wanxian City, Fuling City, and Qianjiang Prefecture were entrusted to Chongqing administration"),
}
MANUAL_SPLIT_EVENTS = {
    "WIKI-1988-010": ("CNUR-000347", "惠阳地区撤销并形成惠州、汕尾、河源三个主要后继实体"),
    "WIKI-1997-064": ("CNUR-000363", "梧州地区主要分为贺州地区并将三县市划归既有梧州市"),
}
MANUAL_MERGE_EVENTS = {
    "WIKI-1994-042": ("CNUR-000358", "荆州地区与原地级沙市市共同组建新的荆沙市"),
}


def read() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def event_type(section: str, text: str) -> str:
    if "更名" in section and "更名" in text:
        return "rename"
    if "撤销" in text and re.search(r"(?:地区|盟).{0,20}设立.{0,12}(?:地级|市（地级）)", text):
        return "upgrade"
    if ("合并" in section or "地市合并" in text) and "合并" in text:
        return "merge"
    if "撤销地级市" in text and "设立市辖区" in text:
        return "abolish"
    if re.search(r"(?:升为|设立).{0,12}(?:地级市|市（地级）)", text):
        return "establish"
    if "撤销" in text and re.search(r"(?:自治州|地区|地级市)", text):
        return "abolish"
    if "地区的增设" in section and "设立" in text and "地区" in text:
        return "establish_prefecture"
    if "驻地" in section and ("迁" in text or "更名" in text):
        return "seat_or_name_change"
    if "代管" in section and "代管" in text:
        return "jurisdiction_transfer"
    return ""


def extract_names(kind: str, text: str) -> tuple[str, str]:
    old = new = ""
    if kind == "rename":
        match = re.search(r"([\u4e00-\u9fff·]{2,20}(?:地区|盟|自治州|市))更名为([\u4e00-\u9fff·]{2,20}(?:地区|盟|自治州|市))", text)
        if match: old, new = match.groups()
    else:
        match = re.search(r"撤销(?:[^，|]{0,8}?省)?([\u4e00-\u9fff·]{2,16}(?:地区|盟|自治州|地级市))", text)
        if match: old = match.group(1).removeprefix("地级")
        match = re.search(r"设立(?:地级)?([\u4e00-\u9fff·]{2,12}市)(?:（地级）)?", text)
        if match: new = match.group(1)
        if kind == "establish_prefecture":
            match = re.search(r"设立([\u4e00-\u9fff·]{2,16}地区)", text)
            if match: new = match.group(1)
    return old, new


def main() -> None:
    with ENTITIES.open(encoding="utf-8", newline="") as handle:
        entities = {row["entity_id"]: row for row in csv.DictReader(handle)}
    name_to_entities: dict[str, set[str]] = {}
    with NAMES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["name_zh"]:
                name_to_entities.setdefault(row["name_zh"], set()).add(row["entity_id"])
    for entity_id, entity in entities.items():
        name_to_entities.setdefault(entity["canonical_name_zh"], set()).add(entity_id)
    output, province_by_year = [], {}
    for row in read():
        year = int(row["year"])
        if year >= 2000:
            continue
        text, section = row["row_text"], row["section"]
        province_match = PROVINCE_RE.search(text)
        if province_match and "撤销" not in text and "设立" not in text:
            province_by_year[year] = province_match.group(1)
            continue
        kind = event_type(section, text)
        if not kind:
            continue
        old_name, new_name = extract_names(kind, text)
        old_name = old_name.removeprefix("将")
        new_name = new_name.removeprefix("新的")
        province = province_by_year.get(year, "")
        if province and old_name.startswith(province): old_name = old_name[len(province):]
        if province and new_name.startswith(province): new_name = new_name[len(province):]
        if old_name and new_name and kind in {"establish", "abolish"} and old_name.endswith(("地区", "盟")):
            kind = "upgrade"
        # Require a prefecture-level semantic payload, not a subordinate county row.
        if not (old_name or new_name or kind in {"seat_or_name_change", "jurisdiction_transfer"}) or (kind == "abolish" and not old_name):
            continue
        date_match = DATE_RE.search(text)
        date_text = ""
        if date_match:
            date_text = f"{date_match.group(1) or year}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        doc = DOC_RE.search(text)
        entity_candidates = name_to_entities.get(new_name, set()) | name_to_entities.get(old_name, set())
        entity_id = next(iter(entity_candidates)) if len(entity_candidates) == 1 else ""
        if entity_id:
            if entity_id in entities: province = entities[entity_id]["province_name_zh"]
        risks = []
        if doc:
            doc_year = re.search(r"\d{4}", doc.group(0))
            if doc_year and int(doc_year.group(0)) != year:
                risks.append("document_year_differs_from_page_year")
        if not entity_id: risks.append("entity_unresolved")
        automatic = kind in {"rename", "upgrade"} and bool(old_name and new_name)
        event_id = f"WIKI-{year}-{len(output)+1:03d}"
        review_note = ""
        if event_id in MANUAL_ENTITY_LINKS:
            entity_id, review_note = MANUAL_ENTITY_LINKS[event_id]
            if entity_id in entities: province = entities[entity_id]["province_name_zh"]
            risks = [risk for risk in risks if risk != "entity_unresolved"]
        if event_id in MANUAL_ACCEPT_EVENTS:
            review_note = MANUAL_ACCEPT_EVENTS[event_id]
        if event_id in MANUAL_HISTORICAL_LINKS:
            entity_id, review_note = MANUAL_HISTORICAL_LINKS[event_id]
            risks = [risk for risk in risks if risk != "entity_unresolved"]
            if event_id in {"WIKI-1993-029", "WIKI-1996-056"}: risks.append("multi_entity_relation")
        if event_id in MANUAL_SPLIT_EVENTS:
            entity_id, review_note = MANUAL_SPLIT_EVENTS[event_id]
            kind, automatic = "split", False
            risks = [risk for risk in risks if risk != "entity_unresolved"] + ["multi_entity_relation"]
        if event_id in MANUAL_MERGE_EVENTS:
            entity_id, review_note = MANUAL_MERGE_EVENTS[event_id]
            kind, automatic = "merge", False
            risks = [risk for risk in risks if risk != "entity_unresolved"] + ["multi_entity_relation"]
        status = "accepted_manual_review" if review_note else "accepted_rule_extraction" if entity_id and old_name and new_name and kind in {"rename", "upgrade"} else "review_required"
        output.append({
            "event_id": event_id, "year": year,
            "province_name": province, "event_type": kind, "entity_id": entity_id,
            "old_prefecture_name": old_name, "new_prefecture_name": new_name,
            "approval_date": date_text, "document_number": doc.group(0) if doc else "",
            "automatic_continuity": str(automatic).lower(),
            "confidence": "high" if old_name and new_name and kind in {"rename", "upgrade"} else "medium",
            "normalization_status": status, "review_note": review_note,
            "risk_flags": "|".join(risks),
            "description": text, "source_section": section, "source_url": row["source_url"],
            "revision_id": row["revision_id"], "source_row_number": row["row_number"],
        })
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    print(f"normalized={len(output)} years={min(r['year'] for r in output)}-{max(r['year'] for r in output)}")


if __name__ == "__main__":
    main()
