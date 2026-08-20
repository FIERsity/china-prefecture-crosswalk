#!/usr/bin/env python3
"""Build the project's source registry and attach provenance to local tables."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from import_early_county_events import SOURCES

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TODAY = "2026-08-04"
SOURCE_FIELDS = [
    "source_id", "source_type", "title", "url", "accessed_date",
    "coverage_start", "coverage_end", "source_locator", "authority", "scope",
    "provenance_status", "notes",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add_source(registry: dict[str, dict[str, str]], row: dict[str, str]) -> None:
    source_id = row["source_id"]
    if source_id not in registry:
        registry[source_id] = {field: row.get(field, "") for field in SOURCE_FIELDS}
        return
    # Existing hand-written notes remain authoritative; fill only missing
    # registry fields when the inventory gives us a more precise locator.
    for field in SOURCE_FIELDS:
        if not registry[source_id].get(field) and row.get(field):
            registry[source_id][field] = row[field]


def page_source_id(year: str, url_to_id: dict[str, str]) -> str:
    url = f"https://zh.wikipedia.org/wiki/{year}年中华人民共和国县级以上行政区划变更列表"
    return url_to_id.get(url, f"SRC-WIKI-{year}")


def build_registry() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    _, old_rows = read_csv(PROCESSED / "sources.csv")
    registry: dict[str, dict[str, str]] = {}
    url_to_id: dict[str, str] = {}
    for old in old_rows:
        row = {
            "source_id": old.get("source_id", ""),
            "source_type": old.get("source_type", ""),
            "title": old.get("title", ""),
            "url": old.get("url", ""),
            "accessed_date": old.get("accessed_date", TODAY),
            "coverage_start": "",
            "coverage_end": "",
            "source_locator": "",
            "authority": "project",
            "scope": old.get("scope", ""),
            "provenance_status": "unverified" if old.get("source_id") == "SRC-LEGACY-SNAPSHOT" else "reviewed_reference",
            "notes": old.get("notes", ""),
        }
        add_source(registry, row)
        if row["url"]:
            url_to_id[row["url"]] = row["source_id"]

    for name in ("wikipedia_change_pages.csv", "wikipedia_county_change_pages.csv"):
        _, rows = read_csv(PROCESSED / name)
        for page in rows:
            source_id = page_source_id(page["year"], url_to_id)
            add_source(registry, {
                "source_id": source_id,
                "source_type": "wikipedia",
                "title": page.get("title", ""),
                "url": page.get("page_url", ""),
                "accessed_date": page.get("checked_at_utc", TODAY)[:10],
                "coverage_start": page.get("year", ""),
                "coverage_end": page.get("year", ""),
                "source_locator": f"revision {page.get('revision_id', '')}",
                "authority": "Wikipedia community-maintained secondary source",
                "scope": "prefecture_and_county_change_archive",
                "provenance_status": "revisioned_secondary",
                "notes": "Annual page is retained with revision ID in the local archive inventory.",
            })
            url_to_id.setdefault(page.get("page_url", ""), source_id)

    for source in SOURCES:
        start, end = source["period"].split("—")
        is_xzqh = source.get("parser") == "xzqh"
        add_source(registry, {
            "source_id": source["source_id"],
            "source_type": "secondary_transcription" if is_xzqh else "people_daily_summary",
            "title": source["title"],
            "url": source["url"],
            "accessed_date": TODAY,
            "coverage_start": start,
            "coverage_end": end,
            "source_locator": source["locator"],
            "authority": "区划地名网（根据国务院批复整理）" if is_xzqh else "新华社/人民日报历史版面（转录档案）",
            "scope": "county_level_and_above_changes",
            "provenance_status": "secondary_transcription" if is_xzqh else "primary_text_transcription",
            "notes": "条目为区划地名网根据公开国务院批复整理的转录，保留原条目文字。" if is_xzqh else "The report is a contemporaneous summary of changes approved in the stated period; each imported row retains the full wording.",
        })
        url_to_id[source["url"]] = source["source_id"]

    add_source(registry, {
        "source_id": "SRC-CTAMAP-1.30",
        "source_type": "annual_vector_snapshot",
        "title": "CTAmap 1.30：2000—2024年初省市县行政区划矢量数据",
        "url": "https://github.com/ruiduobao/shengshixian.com",
        "accessed_date": "2026-08-20",
        "coverage_start": "2000",
        "coverage_end": "2024",
        "source_locator": "CTAmap1.30版本_2000-2024_2025.04.25 local snapshot",
        "authority": "CTAmap project",
        "scope": "province_and_prefecture_year_start_geometry_crosscheck",
        "provenance_status": "reviewed_external_snapshot_redistribution_pending",
        "notes": "Annual year-start Shapefiles are used for spatial alignment and cross-checking; they do not override reviewed CNUR year-end legal status.",
    })
    add_source(registry, {
        "source_id": "SRC-STATE-COUNCIL-GAZETTE-ARCHIVE",
        "source_type": "state_council_gazette_archive",
        "title": "中国政府网：国务院公报历史期号目录",
        "url": "https://www.gov.cn/gongbao/2001/issue_67/",
        "accessed_date": TODAY,
        "coverage_start": "1983",
        "coverage_end": "1986",
        "source_locator": "1983—1986 historical issue links",
        "authority": "中华人民共和国国务院",
        "scope": "official_approval_document_archive",
        "provenance_status": "official_reference_pending_ocr",
        "notes": "Official Gazette archive used to verify approval documents; some historical PDFs are image-only and still require page-level OCR/manual checking.",
    })
    add_source(registry, {
        "source_id": "SRC-ADMIN-DIVISION-BOOKS-1983-1986",
        "source_type": "annual_administrative_division_book",
        "title": "《中华人民共和国行政区划简册》1983—1986年版书目线索",
        "url": "https://ci.nii.ac.jp/ncid/BN05656093",
        "accessed_date": TODAY,
        "coverage_start": "1983",
        "coverage_end": "1986",
        "source_locator": "annual edition bibliography",
        "authority": "民政部系统年度行政区划资料（书目）",
        "scope": "annual_county_roster_and_change_verification",
        "provenance_status": "bibliographic_reference",
        "notes": "Bibliographic lead for year-end roster verification; not used as row-level evidence until the editions are obtained and checked.",
    })
    return registry, url_to_id


def attach(rows: list[dict[str, str]], url_to_id: dict[str, str], locator: str = "") -> list[dict[str, str]]:
    for row in rows:
        url = row.get("source_url") or row.get("page_url") or row.get("source_url", "")
        source_id = row.get("source_id") or url_to_id.get(url, "")
        if not source_id:
            match = re.search(r"/(?:wiki/)?((?:19|20)\d{2})年", url)
            if match:
                source_id = f"SRC-WIKI-{match.group(1)}"
        if source_id:
            row["source_id"] = source_id
        row.setdefault("source_type", "")
        row.setdefault("source_locator", locator)
        row.setdefault("source_confidence", "")
        if source_id.startswith("SRC-WIKI-"):
            row["source_type"] = "wikipedia"
            row["source_confidence"] = row["source_confidence"] or "revisioned_secondary"
        elif source_id.startswith("SRC-RMRB-"):
            row["source_type"] = "people_daily_summary"
            row["source_confidence"] = row["source_confidence"] or "primary_text"
        elif source_id.startswith("SRC-XZQH-"):
            row["source_type"] = "secondary_transcription"
            row["source_confidence"] = row["source_confidence"] or "secondary_transcription"
    return rows


def enrich_file(name: str, url_to_id: dict[str, str]) -> None:
    path = PROCESSED / name
    fields, rows = read_csv(path)
    rows = attach(rows, url_to_id)
    extra = [field for field in ("source_id", "source_type", "source_locator", "source_confidence") if field not in fields]
    write_csv(path, fields + extra, rows)


def enrich_derived(url_to_id: dict[str, str]) -> None:
    _, events = read_csv(PROCESSED / "unified_events_1987_2026.csv")
    sources_by_entity: dict[str, set[str]] = defaultdict(set)
    for event in events:
        source_id = event.get("source_id") or url_to_id.get(event.get("source_url", ""), "SRC-LEGACY-SNAPSHOT")
        if event.get("entity_id"):
            sources_by_entity[event["entity_id"]].add(source_id)

    for name, key in (
        ("entity_names_1987_2026.csv", "entity_id"),
        ("entity_names_year_end_1987_2026.csv", "entity_id"),
        ("entity_name_match_ranges_1987_2026.csv", "entity_id"),
        ("legal_roster_1987_2026.csv", "entity_id"),
        ("legal_roster_year_end_1987_2026.csv", "entity_id"),
        ("entities.csv", "entity_id"),
    ):
        path = PROCESSED / name
        if not path.exists():
            continue
        fields, rows = read_csv(path)
        for row in rows:
            ids = sorted(sources_by_entity.get(row.get(key, ""), {"SRC-LEGACY-SNAPSHOT"}))
            row["source_ids"] = row.get("source_ids") or "、".join(ids)
            row["provenance_kind"] = row.get("provenance_kind") or "derived_from_event_chain"
        write_csv(path, fields + [field for field in ("source_ids", "provenance_kind") if field not in fields], rows)


def main() -> None:
    registry, url_to_id = build_registry()
    registry_rows = sorted(registry.values(), key=lambda row: row["source_id"])
    write_csv(PROCESSED / "sources.csv", SOURCE_FIELDS, registry_rows)
    write_csv(PROCESSED / "source_registry.csv", SOURCE_FIELDS, registry_rows)
    for name in (
        "wikipedia_change_pages.csv", "wikipedia_prefecture_change_rows.csv",
        "wikipedia_county_change_pages.csv", "wikipedia_county_change_rows.csv",
        "unified_events_1987_2026.csv", "county_affiliation_transitions.csv",
        "prefecture_events_early_1983_1986.csv", "prefecture_administrative_events_1983_2026.csv",
        "county_administrative_events_1987_2026.csv", "county_administrative_events_1983_1986.csv",
        "historical_entities.csv",
    ):
        enrich_file(name, url_to_id)
    enrich_derived(url_to_id)
    print(f"sources={len(registry)} enriched_files=12")


if __name__ == "__main__":
    main()
