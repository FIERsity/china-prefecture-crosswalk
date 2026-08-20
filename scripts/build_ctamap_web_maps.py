#!/usr/bin/env python3
"""Build repository-friendly, simplified per-year GeoJSON for the static map."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import shapefile
from shapely.geometry import mapping, shape as shapely_shape


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "CTAmap1.30版本_2000-2024_2025.04.25"
LINKS = ROOT / "data" / "processed" / "ctamap_prefecture_links.csv"
OUTPUT = ROOT / "docs" / "data" / "maps" / "prefecture"
TOLERANCE_DEGREES = 0.02


def main() -> None:
    with LINKS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_year: dict[int, dict[int, dict[str, str]]] = {}
    for row in rows:
        year = int(row["snapshot_year"])
        index = int(row["source_feature_id"].rsplit("-", 1)[-1])
        by_year.setdefault(year, {})[index] = row

    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for year in range(2000, 2025):
        shp = next((SOURCE / str(year) / "地级").glob("*.shp"))
        reader = shapefile.Reader(str(shp), encoding="utf-8")
        features = []
        for index, shape_record in enumerate(reader.iterShapeRecords()):
            link = by_year[year].get(index)
            if not link:
                continue
            geom = shapely_shape(shape_record.shape.__geo_interface__).simplify(TOLERANCE_DEGREES, preserve_topology=True)
            features.append({
                "type": "Feature",
                "id": link["source_feature_id"],
                "properties": {
                    "entity_id": link["entity_id"],
                    "source_name": link["source_name"],
                    "year_end_name": link["year_end_name"],
                    "source_code": link["source_code"],
                    "prefecture_type": link["source_prefecture_type"],
                    "province_name": link["province_name"],
                    "snapshot_year": year,
                    "panel_year": year - 1,
                },
                "geometry": mapping(geom),
            })
        payload = {"type": "FeatureCollection", "features": features}
        path = OUTPUT / f"{year}.geojson"
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        manifest.append({"snapshot_year": year, "panel_year": year - 1, "feature_count": len(features), "file": path.name, "size_bytes": path.stat().st_size})
    (OUTPUT.parent / "manifest.json").write_text(json.dumps({"source": "CTAmap 1.30", "snapshot_basis": "year_start", "panel_mapping": "snapshot_year - 1", "format": "simplified GeoJSON", "simplification_tolerance_degrees": TOLERANCE_DEGREES, "years": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"years={len(manifest)} features={sum(row['feature_count'] for row in manifest)} size_mb={sum(row['size_bytes'] for row in manifest)/1024/1024:.1f}")


if __name__ == "__main__":
    main()
