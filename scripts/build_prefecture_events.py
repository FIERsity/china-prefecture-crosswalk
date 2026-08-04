#!/usr/bin/env python3
"""Build a prefecture-level event layer from the early county-change archive.

The 1983—1986 source material is descriptive text rather than a normalized
prefecture event table.  This script extracts rows that explicitly describe
the abolition, renaming, upgrading, establishment, or reorganization of a
prefecture-level unit.  The original wording is retained in ``description``;
the old/new columns are deliberately conservative and are not treated as an
automatic lineage map.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

FIELDS = [
    "event_id", "year", "province_name", "event_type", "entity_id", "entity_ids",
    "prefecture_names", "prefecture_entity_ids", "old_prefecture_name",
    "new_prefecture_name", "approval_date", "document_number",
    "automatic_continuity", "confidence", "review_status", "risk_flags",
    "description", "review_note", "source_url", "source_revision_id",
    "source_locator", "source_layer", "source_id", "source_type",
    "source_confidence",
]

HIGH_LEVEL_MARKERS = re.compile(
    r"(?:撤销[^。；，]*(?:地区|盟)|(?:地区|盟)更名为|(?:市)改由省直接领导|"
    r"(?:市)升为地级市|设立[^。；，]*(?:市|自治州)[（(]?地级|"
    r"恢复[^。；，]*(?:市|地区)[（(]?地级|撤销[^。；，]*(?:市|地区)[，。；]|"
    r"市管县)"
)
ABOLISHED_REGION_RE = re.compile(r"(?:撤销|撤消)\s*([一-龥]{1,12}(?:地区|盟))")
RENAMED_REGION_RE = re.compile(r"([一-龥]{1,12}(?:地区|盟))更名为")
ORIGINAL_REGION_RE = re.compile(r"原([一-龥]{1,12}(?:地区|盟))")
UPGRADED_CITY_RE = re.compile(r"([一-龥]{1,12}市)(?=升为地级市|改由省直接领导)")
ESTABLISHED_PREFECTURE_RE = re.compile(
    r"(?:设立|恢复)([一-龥]{1,20}(?:市|自治州))(?=[（(]地级)"
)
DOCUMENT_RE = re.compile(r"[（(]?\d{2}[）)]?国函(?:字)?\d+号")
DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def split_names(value: str) -> list[str]:
    return unique(re.split(r"[、,，]", value or ""))


def source_text(row: dict[str, str]) -> str:
    return (row.get("change_description") or row.get("description") or "").strip()


def related_prefecture_names(row: dict[str, str]) -> list[str]:
    return split_names(row.get("prefecture_names", ""))


def region_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern in (ABOLISHED_REGION_RE, RENAMED_REGION_RE, ORIGINAL_REGION_RE):
        names.extend(match.group(1) for match in pattern.finditer(text))
    return unique(names)


def city_names(text: str, related: list[str]) -> list[str]:
    explicit = [match.group(1) for match in UPGRADED_CITY_RE.finditer(text)]
    explicit.extend(match.group(1) for match in ESTABLISHED_PREFECTURE_RE.finditer(text))
    related_cities = [name for name in related if name.endswith(("市", "自治州"))]
    return unique(explicit + related_cities)


def event_type(text: str) -> str:
    if "更名为" in text and ("地区" in text or "盟" in text):
        return "rename"
    if "升为地级市" in text or "改由省直接领导" in text:
        return "upgrade"
    if re.search(r"(?:设立|恢复)[^。；，]*(?:市|自治州)[（(]?地级", text):
        return "establish"
    if "市管县" in text:
        return "jurisdiction_transfer"
    if re.search(r"撤销[^。；，]*(?:地区|盟)", text):
        return "jurisdiction_transfer"
    return "jurisdiction_adjustment"


def old_new_names(row: dict[str, str], text: str) -> tuple[str, str]:
    related = related_prefecture_names(row)
    old = region_names(text)
    new = city_names(text, related)

    # A pure city upgrade has no region name in the source sentence.  Keep the
    # status change explicit while leaving the full legal wording in description.
    if not old and ("升为地级市" in text or "改由省直接领导" in text):
        old = [name for name in new if name.endswith("市")]

    # For an abolished region whose target city is only stated in the county
    # transfer clause, the linked prefecture names provide a safe target list.
    if not new:
        new = [name for name in related if name.endswith(("市", "自治州"))]

    return "、".join(old), "、".join(new)


def province_name(section: str) -> str:
    return (section.split(" / ", 1)[0] if " / " in section else "").strip()


def approval_date(year: int, text: str) -> str:
    match = DATE_RE.search(text)
    if not match:
        return ""
    month, day = (int(value) for value in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def build() -> list[dict[str, str]]:
    source_rows = read_csv(PROCESSED / "county_administrative_events_1983_1986.csv")
    rows: list[dict[str, str]] = []
    for source in source_rows:
        text = source_text(source)
        if not text or not HIGH_LEVEL_MARKERS.search(text):
            continue
        ids = split_names(source.get("prefecture_entity_ids", ""))
        related = related_prefecture_names(source)
        old, new = old_new_names(source, text)
        year = int(source["year"])
        source_type = source.get("source_type", "")
        is_secondary = source_type == "secondary_transcription" or source["source_id"].startswith("SRC-XZQH-")
        rows.append({
            "event_id": f"EARLY-PREFECTURE-{source['event_id']}",
            "year": str(year),
            "province_name": province_name(source.get("section", "")),
            "event_type": event_type(text),
            "entity_id": ids[0] if ids else "",
            "entity_ids": "、".join(ids),
            "prefecture_names": "、".join(related),
            "prefecture_entity_ids": "、".join(ids),
            "old_prefecture_name": old,
            "new_prefecture_name": new,
            "approval_date": approval_date(year, text),
            "document_number": (DOCUMENT_RE.search(text).group(0) if DOCUMENT_RE.search(text) else ""),
            "automatic_continuity": "false",
            "confidence": "low" if is_secondary else "medium",
            "review_status": "early_secondary_transcription_review_required" if is_secondary else "early_source_text_parsed",
            "risk_flags": "early_year_before_roster|secondary_transcription" if is_secondary else "early_year_before_roster|source_text_parsed",
            "description": text,
            "review_note": "早期材料中的市级、地区级或盟级变化；保留原文，实体年度状态仍从1987年开始。",
            "source_url": source.get("source_url", ""),
            "source_revision_id": "",
            "source_locator": source.get("source_locator", ""),
            "source_layer": "early_secondary_city_extraction" if is_secondary else "early_people_daily_city_extraction",
            "source_id": source.get("source_id", ""),
            "source_type": source_type,
            "source_confidence": source.get("source_confidence", ""),
        })
    write_csv(PROCESSED / "prefecture_events_early_1983_1986.csv", rows)
    return rows


def build_combined(early_rows: list[dict[str, str]]) -> None:
    current = read_csv(PROCESSED / "unified_events_1987_2026.csv")
    combined: list[dict[str, str]] = []
    for row in current:
        entity_id = row.get("entity_id", "")
        related = unique([row.get("old_prefecture_name", ""), row.get("new_prefecture_name", "")])
        combined.append({
            "event_id": row.get("event_id", ""), "year": row.get("year", ""),
            "province_name": row.get("province_name", ""), "event_type": row.get("event_type", ""),
            "entity_id": entity_id, "entity_ids": entity_id,
            "prefecture_names": "、".join(related), "prefecture_entity_ids": entity_id,
            "old_prefecture_name": row.get("old_prefecture_name", ""),
            "new_prefecture_name": row.get("new_prefecture_name", ""),
            "approval_date": row.get("approval_date", ""), "document_number": row.get("document_number", ""),
            "automatic_continuity": row.get("automatic_continuity", ""), "confidence": row.get("confidence", ""),
            "review_status": row.get("review_status", ""), "risk_flags": row.get("risk_flags", ""),
            "description": row.get("description", ""), "review_note": row.get("review_note", ""),
            "source_url": row.get("source_url", ""), "source_revision_id": row.get("source_revision_id", ""),
            "source_locator": row.get("source_locator", ""), "source_layer": row.get("source_layer", ""),
            "source_id": row.get("source_id", ""), "source_type": row.get("source_type", ""),
            "source_confidence": row.get("source_confidence", ""),
        })
    combined.extend(early_rows)
    combined.sort(key=lambda row: (int(row["year"]), row["event_id"]))
    write_csv(PROCESSED / "prefecture_administrative_events_1983_2026.csv", combined)


if __name__ == "__main__":
    early = build()
    build_combined(early)
    print(f"early_prefecture_events={len(early)} combined_prefecture_events={len(read_csv(PROCESSED / 'prefecture_administrative_events_1983_2026.csv'))}")
