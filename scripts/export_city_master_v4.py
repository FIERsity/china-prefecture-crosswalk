#!/usr/bin/env python3
"""Export the V4 year-end entity master and reproducible data bundle."""

from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
AUDIT = ROOT / "data" / "audit"
OUTPUT = ROOT / "data" / "releases" / "v4.0"
FIXED_DATETIME = datetime(2026, 8, 20, tzinfo=timezone.utc)
FIXED_ZIP_TIME = (2026, 8, 20, 0, 0, 0)
CURATED_DATA_FILES = (
    "entities.csv",
    "entity_id_crosswalk.csv",
    "aliases.csv",
    "entity_names_year_end_1987_2026.csv",
    "entity_name_match_ranges_1987_2026.csv",
    "legal_roster_year_end_1987_2026.csv",
    "unified_events_1987_2026.csv",
    "prefecture_administrative_events_1983_2026.csv",
    "county_administrative_events_1983_2026.csv",
    "event_timing_reviews.csv",
    "unified_event_relations.csv",
    "major_lineage_relations.csv",
    "county_affiliation_transitions.csv",
    "ctamap_prefecture_links.csv",
    "ctamap_snapshots.csv",
    "source_registry.csv",
)


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def deterministic_zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def normalize_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as source:
        members = [(name, source.read(name)) for name in sorted(source.namelist())]
    temporary = path.with_suffix(path.suffix + ".deterministic")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, payload in members:
            if name == "docProps/core.xml":
                payload = re.sub(
                    rb"<dcterms:modified[^>]*>.*?</dcterms:modified>",
                    b'<dcterms:modified xsi:type="dcterms:W3CDTF">2026-08-20T00:00:00Z</dcterms:modified>',
                    payload,
                )
            output.writestr(deterministic_zip_info(name), payload)
    temporary.replace(path)


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
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="entities")
        writer.book.properties.created = FIXED_DATETIME
        writer.book.properties.modified = FIXED_DATETIME
    normalize_zip(xlsx_path)

    bundle_path = OUTPUT / "china_prefecture_crosswalk_research_bundle_v4.0.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in CURATED_DATA_FILES:
            path = DATA / name
            if not path.exists():
                raise FileNotFoundError(path)
            archive.writestr(deterministic_zip_info(f"data/{path.name}"), path.read_bytes())
        archive.writestr(deterministic_zip_info("CODEBOOK.md"), (ROOT / "CODEBOOK.md").read_bytes())
        archive.writestr(deterministic_zip_info("README.md"), (OUTPUT / "README.md").read_bytes())
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    (OUTPUT / "china_prefecture_crosswalk_research_bundle_v4.0.sha256").write_text(
        f"{digest}  {bundle_path.name}\n", encoding="utf-8"
    )
    print(f"rows={len(rows)} csv={csv_path} xlsx={xlsx_path} bundle={bundle_path}")


if __name__ == "__main__":
    main()
