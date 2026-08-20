#!/usr/bin/env python3
"""Audit and bridge CTAmap 1.30 province/prefecture snapshots to CNUR entities."""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    import shapefile
    from shapely.geometry import shape as shapely_shape
except ImportError as exc:  # pragma: no cover - explicit optional dependency gate
    raise SystemExit("Install optional GIS dependencies with: pip install -r requirements-geo.txt") from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "CTAmap1.30版本_2000-2024_2025.04.25"
DATA = ROOT / "data" / "processed"
AUDIT = ROOT / "data" / "audit"
YEARS = range(2000, 2025)
LEGAL_PREFECTURE_TYPES = {"地级市", "地区", "自治州", "盟"}
MUNICIPALITIES = {"北京市", "天津市", "上海市", "重庆市"}
OUT_OF_SCOPE_PROVINCES = {"香港特别行政区", "澳门特别行政区", "台湾省"}
PUNCT = re.compile(r"[\s\u200b-\u200f\u2060\ufeff·•,，。.;；:：()（）\[\]【】_-]+")


def normalize(value: str) -> str:
    return PUNCT.sub("", unicodedata.normalize("NFKC", value or "").replace("巿", "市")).strip()


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fields or (list(rows[0]) if rows else [])
    if not fieldnames:
        raise AssertionError(f"no fields for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_layer(year: int, level: str) -> Path:
    paths = list((SOURCE / str(year) / level).glob("*.shp"))
    if len(paths) != 1:
        raise AssertionError(f"expected exactly one {level} shapefile for {year}, found {paths}")
    return paths[0]


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"CTAmap source directory is missing: {SOURCE}")

    entities = {row["entity_id"]: row for row in read_csv("entities.csv")}
    historical_entities = {
        row["historical_entity_id"]: {
            **row,
            "entity_id": row["historical_entity_id"],
            "province_name_zh": row["province_at_time"],
            "source_ids": row.get("source_id", ""),
        }
        for row in read_csv("historical_entities.csv")
    }
    entity_meta = {**entities, **historical_entities}
    year_end_roster = read_csv("legal_roster_year_end_1987_2026.csv")
    match_ranges = read_csv("entity_name_match_ranges_1987_2026.csv")
    aliases = read_csv("aliases.csv")

    year_end_index: dict[tuple[int, str, str], str] = {}
    active_by_year: dict[int, set[str]] = defaultdict(set)
    year_end_name_by_entity_year: dict[tuple[str, int], str] = {}
    for row in year_end_roster:
        year = int(row["year"])
        if row["status"] == "active" and row["entity_id"] in entity_meta:
            key = (year, normalize(row["province_name_zh"]), normalize(row["legal_name_zh"]))
            year_end_index[key] = row["entity_id"]
            active_by_year[year].add(row["entity_id"])
            year_end_name_by_entity_year[(row["entity_id"], year)] = row["legal_name_zh"]

    valid_name_index: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    any_name_index: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in match_ranges:
        entity = entity_meta.get(row["entity_id"])
        if not entity:
            continue
        province = normalize(entity["province_name_zh"])
        name = normalize(row["name_zh"])
        any_name_index[(province, name)].add(row["entity_id"])
        for year in range(int(row["start_year"]), int(row["end_year"]) + 1):
            valid_name_index[(year, province, name)].add(row["entity_id"])
    alias_index: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for row in aliases:
        entity = entity_meta.get(row["entity_id"])
        if not entity:
            continue
        for year in range(int(row["start_year"]), int(row["end_year"]) + 1):
            alias_index[(year, normalize(entity["province_name_zh"]), normalize(row["alias"]))].add(row["entity_id"])

    snapshots: list[dict[str, object]] = []
    links: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []

    for snapshot_year in YEARS:
        panel_year = snapshot_year - 1
        for level in ("省级", "地级"):
            shp_path = find_layer(snapshot_year, level)
            reader = shapefile.Reader(str(shp_path), encoding="utf-8")
            prj_path = shp_path.with_suffix(".prj")
            prj = prj_path.read_text(encoding="utf-8", errors="replace")
            crs_status = "wgs84" if "WGS_1984" in prj else "unexpected"
            snapshots.append({
                "source_id": "SRC-CTAMAP-1.30",
                "snapshot_year": snapshot_year,
                "snapshot_label": f"{snapshot_year}年初",
                "snapshot_precision": "year_start",
                "panel_year": panel_year,
                "administrative_level": "province" if level == "省级" else "prefecture",
                "relative_path": str(shp_path.relative_to(ROOT)),
                "record_count": len(reader),
                "shape_type": reader.shapeTypeName,
                "crs_status": crs_status,
                "shp_sha256": sha256(shp_path),
                "dbf_sha256": sha256(shp_path.with_suffix(".dbf")),
            })
            if level == "省级":
                if len(reader) != 34:
                    issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": "province_count_mismatch", "source_name": "", "source_code": "", "entity_id": "", "detail": f"expected 34 province records, found {len(reader)}"})
                continue

            seen_source_keys: set[tuple[str, str, str]] = set()
            linked_ids: set[str] = set()
            for feature_index, shape_record in enumerate(reader.iterShapeRecords()):
                record = shape_record.record.as_dict()
                source_name = str(record.get("地名", "") or "")
                source_code = str(record.get("区划码", "") or record.get("code", "") or "")
                prefecture_type = str(record.get("地级类", "") or "")
                province = str(record.get("省级", "") or "")
                source_year = str(record.get("year", "") or "")
                include = prefecture_type in LEGAL_PREFECTURE_TYPES or (prefecture_type == "不统计" and source_name in MUNICIPALITIES)
                if not include:
                    continue

                source_key = (normalize(province), normalize(source_name), source_code)
                duplicate_source_key = source_key in seen_source_keys
                seen_source_keys.add(source_key)
                if source_year != str(snapshot_year):
                    issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": "source_year_mismatch", "source_name": source_name, "source_code": source_code, "entity_id": "", "detail": f"feature year={source_year}"})

                geometry = shapely_shape(shape_record.shape.__geo_interface__)
                geometry_status = "valid"
                if geometry.is_empty:
                    geometry_status = "empty"
                elif not geometry.is_valid:
                    geometry_status = "invalid"
                if duplicate_source_key:
                    geometry_status = f"{geometry_status}|duplicate_source_key"

                province_key, name_key = normalize(province), normalize(source_name)
                entity_id = year_end_index.get((panel_year, province_key, name_key), "")
                match_method = "year_end_name" if entity_id else ""
                candidates: set[str] = set()
                if not entity_id:
                    candidates = valid_name_index.get((panel_year, province_key, name_key), set())
                    if len(candidates) == 1:
                        entity_id = next(iter(candidates)); match_method = "name_valid_during_year"
                if not entity_id:
                    candidates = alias_index.get((panel_year, province_key, name_key), set())
                    if len(candidates) == 1:
                        entity_id = next(iter(candidates)); match_method = "reviewed_alias"
                if not entity_id:
                    candidates = any_name_index.get((province_key, name_key), set())
                    if len(candidates) == 1:
                        entity_id = next(iter(candidates)); match_method = "historical_name_outside_panel_year"

                link_status = "linked" if entity_id else "ambiguous" if len(candidates) > 1 else "unmatched"
                if entity_id:
                    linked_ids.add(entity_id)
                year_end_name = year_end_name_by_entity_year.get((entity_id, panel_year), "") if entity_id else ""
                legacy_code = entity_meta.get(entity_id, {}).get("legacy_entity_id", "").removeprefix("E") if entity_id else ""
                code_status = "matches_current_legacy" if legacy_code and source_code == legacy_code else "historical_or_different" if entity_id else "not_checked"

                links.append({
                    "source_feature_id": f"CTAMAP-{snapshot_year}-PREF-{feature_index:04d}",
                    "source_id": "SRC-CTAMAP-1.30",
                    "snapshot_year": snapshot_year,
                    "snapshot_label": f"{snapshot_year}年初",
                    "panel_year": panel_year,
                    "source_name": source_name,
                    "source_code": source_code,
                    "source_prefecture_type": prefecture_type,
                    "province_name": province,
                    "entity_id": entity_id,
                    "year_end_name": year_end_name,
                    "match_method": match_method,
                    "link_status": link_status,
                    "code_status": code_status,
                    "geometry_status": geometry_status,
                    "geometry_type": geometry.geom_type,
                    "source_year_verified": str(source_year == str(snapshot_year)).lower(),
                })
                if link_status != "linked":
                    issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": f"prefecture_{link_status}", "source_name": source_name, "source_code": source_code, "entity_id": "、".join(sorted(candidates)), "detail": province})
                if geometry_status != "valid":
                    issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": "geometry_issue", "source_name": source_name, "source_code": source_code, "entity_id": entity_id, "detail": geometry_status})
                if entity_id and year_end_name and normalize(source_name) != normalize(year_end_name):
                    issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": "source_name_differs_from_year_end", "source_name": source_name, "source_code": source_code, "entity_id": entity_id, "detail": f"year_end_name={year_end_name}; match_method={match_method}"})

            for entity_id in sorted(active_by_year[panel_year] - linked_ids):
                issues.append({"snapshot_year": snapshot_year, "panel_year": panel_year, "issue_type": "year_end_entity_missing_from_snapshot", "source_name": "", "source_code": "", "entity_id": entity_id, "detail": year_end_name_by_entity_year.get((entity_id, panel_year), "")})

    write_csv(DATA / "ctamap_snapshots.csv", snapshots)
    write_csv(DATA / "ctamap_prefecture_links.csv", links)
    write_csv(
        AUDIT / "ctamap_alignment_issues.csv",
        issues,
        ["snapshot_year", "panel_year", "issue_type", "source_name", "source_code", "entity_id", "detail"],
    )
    unresolved = sum(row["link_status"] != "linked" for row in links)
    invalid = sum(row["geometry_status"] != "valid" for row in links)
    print(f"snapshots={len(snapshots)} prefecture_features={len(links)} unresolved={unresolved} geometry_issues={invalid} audit_issues={len(issues)}")


if __name__ == "__main__":
    main()
