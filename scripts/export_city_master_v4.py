#!/usr/bin/env python3
"""Export the V4 year-end entity master and reproducible data bundle."""

from __future__ import annotations

import csv
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
AUDIT = ROOT / "data" / "audit"
OUTPUT = ROOT / "data" / "releases" / "v4.0"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    crosswalk = read("entity_id_crosswalk.csv")
    entities = {row["entity_id"]: row for row in read("entities.csv")}
    province_short = {row["province_name_zh"]: row["province_short_zh"] for row in entities.values()}
    historical = {row["historical_entity_id"]: row for row in read("historical_entities.csv")}
    names: dict[str, list[dict[str, str]]] = defaultdict(list)
    roster: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read("entity_names_year_end_1987_2026.csv"):
        names[row["entity_id"]].append(row)
    for row in read("legal_roster_year_end_1987_2026.csv"):
        roster[row["entity_id"]].append(row)
    event_counts = Counter(row["entity_id"] for row in read("unified_events_1987_2026.csv"))

    rows: list[dict[str, object]] = []
    for item in crosswalk:
        entity_id = item["entity_id"]
        annual = sorted(roster[entity_id], key=lambda row: int(row["year"]))
        active = [row for row in annual if row["status"] == "active"]
        spans = sorted(names[entity_id], key=lambda row: int(row["start_year"]))
        history = "; ".join(
            f"{row['start_year']}-{row['end_year']} {row['name_zh'] or '[' + row['legal_status'] + ']'}"
            for row in spans
        )
        if entity_id in entities:
            entity = entities[entity_id]
            scope = "research_entity"
            province = entity["province_name_zh"]
            entity_type = entity["entity_level"]
            verification = entity["verification_status"]
            successor = ""
            source_url = ""
        else:
            entity = historical[entity_id]
            scope = "historical_entity"
            province = entity["province_at_time"]
            entity_type = entity["entity_type"]
            verification = entity["review_status"]
            successor = entity["successor_summary"]
            source_url = entity["source_url"]
        rows.append({
            "entity_id": entity_id,
            "legacy_entity_id": item["legacy_entity_id"],
            "canonical_name_zh": entity["canonical_name_zh"],
            "entity_scope": scope,
            "province_name_zh": province,
            "province_short_zh": province_short.get(province, province.removesuffix("省")),
            "entity_type": entity_type,
            "first_active_year_end": min(int(row["year"]) for row in active) if active else "",
            "last_active_year_end": max(int(row["year"]) for row in active) if active else "",
            "status_at_2026_year_end": annual[-1]["status"],
            "name_at_2026_year_end": annual[-1]["legal_name_zh"],
            "year_basis": "year_end",
            "verification_status": verification,
            "name_history_year_end": history,
            "event_count": event_counts[entity_id],
            "successor_summary": successor,
            "primary_source_url": source_url,
        })

    OUTPUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT / "china_city_entity_master_V4.0.csv"
    xlsx_path = OUTPUT / "china_city_entity_master_V4.0.xlsx"
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(rows).to_excel(xlsx_path, index=False, sheet_name="entities")

    bundle_path = OUTPUT / "china_prefecture_crosswalk_data_v4.0.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(DATA.glob("*.csv")):
            archive.write(path, path.name)
        for name in ("year_end_roster_diff_v3_v4.csv", "ctamap_alignment_issues.csv", "unified_continuity_audit.csv"):
            path = AUDIT / name
            if path.exists():
                archive.write(path, f"audit/{path.name}")
    print(f"rows={len(rows)} csv={csv_path} xlsx={xlsx_path} bundle={bundle_path}")


if __name__ == "__main__":
    main()
