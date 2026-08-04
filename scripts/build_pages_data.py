"""Build the small, browser-friendly data bundle used by GitHub Pages."""

from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "urban_crosswalk" / "data"
OUTPUT = ROOT / "docs" / "data"
PUNCT = re.compile(r"[\s\u200b-\u200f\u2060\ufeff·•,，。.;；:：()（）\[\]【】_-]+")


def read_csv(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").replace("巿", "市")
    return PUNCT.sub("", text).strip()


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entities = {row["entity_id"]: row for row in read_csv("entities.csv")}
    for row in read_csv("historical_entities.csv"):
        entity_id = row.get("historical_entity_id", "")
        if entity_id:
            entities.setdefault(entity_id, {
                "entity_id": entity_id,
                "legacy_entity_id": "",
                "canonical_name_zh": row.get("canonical_name_zh", ""),
                "province_name_zh": row.get("province_at_time", ""),
                "province_short_zh": "",
                "entity_level": "prefecture_historical_entity",
                "id_namespace": "project_stable_id_not_official_code",
                "verification_status": row.get("verification_status", ""),
            })

    names: list[dict[str, str | int]] = []
    for row in read_csv("entity_names_1987_2026.csv"):
        if row.get("name_zh") and row.get("legal_status") == "active":
            names.append({
                "normalized": normalize_name(row["name_zh"]),
                "name": row["name_zh"],
                "entity_id": row["entity_id"],
                "method": "official_or_historical",
                "start": int(row["start_year"]),
                "end": int(row["end_year"]),
            })
    for row in read_csv("aliases.csv"):
        if row.get("alias") and row.get("entity_id"):
            names.append({
                "normalized": normalize_name(row["alias"]),
                "name": row["alias"],
                "entity_id": row["entity_id"],
                "method": row.get("alias_type", "alias"),
                "start": int(row["start_year"]),
                "end": int(row["end_year"]),
            })

    roster_status: dict[str, dict[str, str]] = {}
    for row in read_csv("legal_roster_1987_2026.csv"):
        roster_status.setdefault(row["entity_id"], {})[row["year"]] = row["status"]
    event_fields = (
        "event_id", "year", "province_name", "event_type", "entity_id",
        "old_prefecture_name", "new_prefecture_name", "approval_date",
        "document_number", "review_status", "source_url",
    )
    events = [{key: row.get(key, "") for key in event_fields} for row in read_csv("unified_events_1987_2026.csv")]

    payload = {
        "meta": {
            "version": "3.0.0",
            "ruleVersion": "2026.07.1",
            "coverage": "1987—2026",
            "entityCount": len(entities),
            "note": "CNUR 是项目研究编号，不是官方行政区划代码。",
        },
        "entities": entities,
        "names": names,
        "rosterStatus": roster_status,
        "events": events,
        "relations": read_csv("event_relations.csv"),
    }
    (OUTPUT / "crosswalk.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    for filename in (
        "entities.csv",
        "entity_names_1987_2026.csv",
        "legal_roster_1987_2026.csv",
        "unified_events_1987_2026.csv",
    ):
        shutil.copyfile(SOURCE / filename, OUTPUT / filename)


if __name__ == "__main__":
    build()
