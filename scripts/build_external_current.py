#!/usr/bin/env python3
"""Generate the province-level external display boundary file
``docs/data/maps/external/external_current.geojson`` from repo-local raw
sources, so the website build chain is reproducible.

Sources (all committed under ``data/raw/external_boundaries/``):
- Hong Kong:  bmkor/hk_osm_map ``Hong_Kong.geojson`` (repository license
  review required upstream)
- Taiwan:     geoBoundaries gbOpen TWN ADM0 ``TWN-ADM0.geojson``
- Macau:      ``macau_github_2017/China_Macau_U.shp`` — local no-license
  candidate.  NOTE: the committed website snapshot uses Natural Earth 10m
  (public domain) for Macau; regenerating this file swaps in the 2017
  candidate geometry.  Keep the committed snapshot unless the swap is
  intentional.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "external_boundaries"
OUT = ROOT / "docs" / "data" / "maps" / "external"
OUTPUT = OUT / "external_current.geojson"

FEATURES = [
    {
        "id": "EXTERNAL-HKG",
        "properties": {
            "map_level": "province", "external_only": True, "region_code": "HK",
            "display_name_zh": "香港特别行政区", "source_name_original": "Hong Kong S.A.R.",
            "prefecture_name": "", "entity_id": "",
            "source": "bmkor/hk_osm_map",
            "source_url": "https://github.com/bmkor/hk_osm_map",
            "license_status": "repository_license_review_required",
        },
        "source": RAW / "hongkong_github_18districts" / "Hong_Kong.geojson",
        "feature_index": 0,
    },
    {
        "id": "EXTERNAL-TWN",
        "properties": {
            "map_level": "province", "external_only": True, "region_code": "TW",
            "display_name_zh": "台湾省", "source_name_original": "Republic Of China",
            "prefecture_name": "", "entity_id": "",
            "source": "geoBoundaries gbOpen TWN ADM0",
            "source_url": "https://www.geoboundaries.org/api/current/gbOpen/TWN/ADM0/",
            "license_status": "CC-BY-4.0_or_ODbL_upstream",
        },
        "source": RAW / "taiwan_geoboundaries" / "TWN-ADM0.geojson",
        "feature_index": 0,
    },
    {
        "id": "EXTERNAL-MAC",
        "properties": {
            "map_level": "province", "external_only": True, "region_code": "MO",
            "display_name_zh": "澳门特别行政区", "source_name_original": "Macao S.A.R.",
            "prefecture_name": "", "entity_id": "",
            "source": "macau_github_2017 (local candidate; committed snapshot uses Natural Earth 10m)",
            "source_url": "https://github.com/ruiduobao/shengshixian.com",
            "license_status": "no_license_declared_review_only",
        },
        "shapefile": RAW / "macau_github_2017" / "China_Macau_U.shp",
    },
]


def as_multipolygon(geometry: dict) -> dict:
    if geometry.get("type") == "Polygon":
        return {"type": "MultiPolygon", "coordinates": [geometry["coordinates"]]}
    return geometry


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    features = []
    for spec in FEATURES:
        if "shapefile" in spec:
            try:
                import shapefile  # pyshp
            except ImportError:
                sys.exit("pyshp required: pip install -r requirements-geo.txt")
            if not spec["shapefile"].exists():
                sys.exit(f"missing raw shapefile: {spec['shapefile']}")
            reader = shapefile.Reader(str(spec["shapefile"]))
            shape = reader.shape(0)
            points = shape.points
            parts = list(shape.parts) + [len(points)]
            rings = [points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
            geometry = {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
        else:
            payload = json.loads(spec["source"].read_text(encoding="utf-8"))
            feature = payload["features"][spec["feature_index"]]
            geometry = as_multipolygon(feature["geometry"])
        features.append({
            "type": "Feature", "id": spec["id"],
            "properties": spec["properties"], "geometry": geometry,
        })
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"external_current written: {len(features)} features -> {OUTPUT}")


if __name__ == "__main__":
    main()
