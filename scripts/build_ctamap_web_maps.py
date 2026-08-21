#!/usr/bin/env python3
"""Build simplified province, prefecture, and county GeoJSON for the static map."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import shapefile
from pyproj import Transformer
from shapely.geometry import mapping, shape as shapely_shape
from shapely.ops import transform as shapely_transform


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "CTAmap1.30版本_2000-2024_2025.04.25"
LINKS = ROOT / "data" / "processed" / "ctamap_prefecture_links.csv"
OUTPUT = ROOT / "docs" / "data" / "maps"
TOLERANCE = {"province": 0.03, "prefecture": 0.02, "county": 0.01}
COORDINATE_PRECISION = 5
LEVEL_DIR = {"province": "省级", "prefecture": "地级", "county": "县级"}


def round_coordinates(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, COORDINATE_PRECISION)
    if isinstance(value, (list, tuple)):
        return [round_coordinates(item) for item in value]
    return value


def layer_transformer(path: Path) -> Transformer | None:
    projection = path.with_suffix(".prj").read_text(encoding="utf-8", errors="replace")
    if "Web_Mercator" in projection or "Pseudo_Mercator" in projection:
        return Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    if "GCS_WGS_1984" in projection or "WGS_1984" in projection:
        return None
    raise AssertionError(f"unsupported projection: {path.with_suffix('.prj')}")


def simplified_geometry(shape_record: Any, level: str, transformer: Transformer | None) -> dict[str, Any]:
    geometry = shapely_shape(shape_record.shape.__geo_interface__)
    if transformer is not None:
        geometry = shapely_transform(transformer.transform, geometry)
    geometry = geometry.simplify(TOLERANCE[level], preserve_topology=True)
    result = mapping(geometry)
    result["coordinates"] = round_coordinates(result["coordinates"])
    return result


def find_layer(year: int, level: str) -> Path:
    paths = list((SOURCE / str(year) / LEVEL_DIR[level]).glob("*.shp"))
    if len(paths) != 1:
        raise AssertionError(f"expected one {level} Shapefile for {year}: {paths}")
    return paths[0]


def write_geojson(path: Path, features: list[dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"file": str(path.relative_to(OUTPUT)), "feature_count": len(features), "size_bytes": path.stat().st_size}


def load_prefecture_links() -> tuple[dict[int, dict[int, dict[str, str]]], dict[int, dict[str, dict[str, str]]], dict[int, dict[tuple[str, str], dict[str, str]]]]:
    with LINKS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_index: dict[int, dict[int, dict[str, str]]] = defaultdict(dict)
    by_code: dict[int, dict[str, dict[str, str]]] = defaultdict(dict)
    by_name: dict[int, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    for row in rows:
        year = int(row["snapshot_year"])
        index = int(row["source_feature_id"].rsplit("-", 1)[-1])
        by_index[year][index] = row
        by_code[year][row["source_code"]] = row
        by_name[year][(row["province_name"], row["source_name"])] = row
    return by_index, by_code, by_name


def province_features(year: int, provinces: dict[str, str]) -> list[dict[str, Any]]:
    path = find_layer(year, "province")
    reader = shapefile.Reader(str(path), encoding="utf-8")
    transformer = layer_transformer(path)
    features = []
    for index, shape_record in enumerate(reader.iterShapeRecords()):
        row = shape_record.record.as_dict()
        code = str(row.get("省级码", "") or row.get("FIRST_GID", "") or "")
        name = str(row.get("省", "") or "")
        provinces[code] = name
        features.append({
            "type": "Feature", "id": f"CTAMAP-{year}-PROV-{index:03d}",
            "properties": {"map_level": "province", "source_name": name, "source_code": code, "province_name": name, "province_code": code, "province_type": str(row.get("省类型", "") or ""), "snapshot_year": year, "panel_year": year - 1, "link_status": "province_context"},
            "geometry": simplified_geometry(shape_record, "province", transformer),
        })
    return features


def prefecture_features(year: int, links_by_index: dict[int, dict[str, str]]) -> tuple[list[dict[str, Any]], int, int]:
    path = find_layer(year, "prefecture")
    reader = shapefile.Reader(str(path), encoding="utf-8")
    transformer = layer_transformer(path)
    features = []
    linked_count = context_count = 0
    for index, shape_record in enumerate(reader.iterShapeRecords()):
        row = shape_record.record.as_dict()
        link = links_by_index.get(index)
        source_name = str(row.get("地名", "") or "")
        source_code = str(row.get("区划码", "") or row.get("code", "") or "")
        province_name = str(row.get("省级", "") or "")
        province_code = str(row.get("省级码", "") or "")
        if link:
            linked_count += 1
            feature_id = link["source_feature_id"]
            properties = {"map_level": "prefecture", "entity_id": link["entity_id"], "source_name": link["source_name"], "year_end_name": link["year_end_name"], "source_code": link["source_code"], "prefecture_type": link["source_prefecture_type"], "province_name": link["province_name"], "province_code": province_code, "snapshot_year": year, "panel_year": year - 1, "link_status": "linked", "context_kind": "prefecture_or_municipality"}
        else:
            context_count += 1
            feature_id = f"CTAMAP-{year}-CONTEXT-{index:04d}"
            properties = {"map_level": "prefecture", "entity_id": "", "source_name": source_name, "year_end_name": "", "source_code": source_code, "prefecture_type": str(row.get("地级类", "") or "不统计"), "province_name": province_name, "province_code": province_code, "snapshot_year": year, "panel_year": year - 1, "link_status": "context_only", "context_kind": "out_of_scope_province" if province_name in {"香港特别行政区", "澳门特别行政区", "台湾省"} else "source_non_prefecture_context"}
        features.append({"type": "Feature", "id": feature_id, "properties": properties, "geometry": simplified_geometry(shape_record, "prefecture", transformer)})
    return features, linked_count, context_count


def county_features(year: int, links_by_code: dict[str, dict[str, str]], links_by_name: dict[tuple[str, str], dict[str, str]], province_codes_by_name: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    path = find_layer(year, "county")
    reader = shapefile.Reader(str(path), encoding="utf-8")
    transformer = layer_transformer(path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, shape_record in enumerate(reader.iterShapeRecords()):
        row = shape_record.record.as_dict()
        province_name = str(row.get("省级", "") or "")
        province_code = province_codes_by_name.get(province_name, str(row.get("省级码", "") or ""))
        prefecture_name = str(row.get("地级", "") or "")
        prefecture_code = str(row.get("地级码", "") or "")
        parent = links_by_code.get(prefecture_code) or links_by_name.get((province_name, prefecture_name))
        if not parent and province_name in {"北京市", "天津市", "上海市", "重庆市"}:
            parent = links_by_name.get((province_name, province_name))
        properties = {
            "map_level": "county", "source_name": str(row.get("地名", "") or row.get("县级", "") or ""), "source_code": str(row.get("区划码", "") or row.get("县级码", "") or ""), "county_type": str(row.get("县级类", "") or ""),
            "prefecture_name": prefecture_name, "prefecture_code": prefecture_code, "prefecture_type": str(row.get("地级类", "") or ""), "parent_entity_id": parent["entity_id"] if parent else "", "parent_year_end_name": parent["year_end_name"] if parent else "",
            "province_name": province_name, "province_code": province_code, "snapshot_year": year, "panel_year": year - 1, "link_status": "parent_linked" if parent else "province_direct_or_out_of_scope", "former_name": str(row.get("曾用名", "") or ""), "note": str(row.get("备注", "") or ""),
        }
        grouped[province_code].append({"type": "Feature", "id": f"CTAMAP-{year}-COUNTY-{index:04d}", "properties": properties, "geometry": simplified_geometry(shape_record, "county", transformer)})
    return grouped


def main() -> None:
    links_by_index, links_by_code, links_by_name = load_prefecture_links()
    provinces: dict[str, str] = {}
    level_manifest: dict[str, Any] = {"province": {"mode": "national", "years": []}, "prefecture": {"mode": "national", "years": []}, "county": {"mode": "province_partition", "years": []}}

    for year in range(2000, 2025):
        province_path = OUTPUT / "province" / f"{year}.geojson"
        province_entry = write_geojson(province_path, province_features(year, provinces))
        province_entry.update({"snapshot_year": year, "panel_year": year - 1})
        level_manifest["province"]["years"].append(province_entry)

        prefectures, linked_count, context_count = prefecture_features(year, links_by_index[year])
        prefecture_entry = write_geojson(OUTPUT / "prefecture" / f"{year}.geojson", prefectures)
        prefecture_entry.update({"snapshot_year": year, "panel_year": year - 1, "linked_feature_count": linked_count, "context_feature_count": context_count})
        level_manifest["prefecture"]["years"].append(prefecture_entry)

        county_groups = county_features(year, links_by_code[year], links_by_name[year], {name: code for code, name in provinces.items()})
        county_files = []
        county_output = OUTPUT / "county" / str(year)
        for province_code, features in sorted(county_groups.items()):
            entry = write_geojson(county_output / f"{province_code}.geojson", features)
            entry.update({"province_code": province_code, "province_name": provinces.get(province_code, "")})
            county_files.append(entry)
        expected_files = {f"{code}.geojson" for code in county_groups}
        for stale in county_output.glob("*.geojson"):
            if stale.name not in expected_files:
                stale.unlink()
        level_manifest["county"]["years"].append({"snapshot_year": year, "panel_year": year - 1, "feature_count": sum(row["feature_count"] for row in county_files), "province_count": len(county_files), "files": county_files})

    manifest = {
        "source": "CTAmap 1.30", "snapshot_basis": "year_start", "panel_mapping": "snapshot_year - 1", "format": "simplified GeoJSON", "coordinate_precision": COORDINATE_PRECISION, "simplification_tolerance_degrees": TOLERANCE,
        "provinces": [{"province_code": code, "province_name": name} for code, name in sorted(provinces.items())], "levels": level_manifest,
        "years": level_manifest["prefecture"]["years"],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total_size = sum(path.stat().st_size for path in OUTPUT.rglob("*.geojson"))
    print(f"province={sum(row['feature_count'] for row in level_manifest['province']['years'])} prefecture={sum(row['feature_count'] for row in level_manifest['prefecture']['years'])} county={sum(row['feature_count'] for row in level_manifest['county']['years'])} size_mb={total_size/1024/1024:.1f}")


if __name__ == "__main__":
    main()
