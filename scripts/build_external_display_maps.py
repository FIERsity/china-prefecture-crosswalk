"""Build current external province/prefecture/county display layers.

These layers are deliberately outside the CNUR annual roster. Taiwan uses the
pinned geoBoundaries ADM1/ADM2 public files; Hong Kong uses the cached MIT
18-district files; Macau is represented as one county-level external display
region because a redistributable sub-district boundary source has not yet been
verified.
"""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "external_boundaries"
OUT = ROOT / "docs" / "data" / "maps" / "external"

TAIWAN_NAMES = {
    "Hsinchu County": "新竹县", "Miaoli County": "苗栗县", "Matsu Islands": "连江县",
    "Kinmen": "金门县", "Chiayi County": "嘉义县", "Yilan County": "宜兰县",
    "Nantou County": "南投县", "Changhua County": "彰化县", "Pingtung County": "屏东县",
    "Taitung County": "台东县", "Hualien County": "花莲县", "Penghu": "澎湖县",
    "Yunlin County": "云林县", "Chiayi": "嘉义市", "Hsinchu": "新竹市",
    "Keelung": "基隆市", "Taichung": "台中市", "Taoyuan": "桃园市",
    "New Taipei": "新北市", "Tainan": "台南市", "Taipei": "台北市", "Kaohsiung": "高雄市",
}

HK_NAMES = {
    "Central and Western": "中西区", "Eastern": "东区", "Southern": "南区", "Wan Chai": "湾仔区",
    "Kowloon City": "九龙城区", "Kwun Tong": "观塘区", "Sham Shui Po": "深水埗区",
    "Wong Tai Sin": "黄大仙区", "Yau Tsim Mong": "油尖旺区", "Islands": "离岛区",
    "Kwai Tsing": "葵青区", "North": "北区", "Sai Kung": "西贡区", "Sha Tin": "沙田区",
    "Tai Po": "大埔区", "Tsuen Wan": "荃湾区", "Tuen Mun": "屯门区", "Yuen Long": "元朗区",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def external_feature(feature: dict, *, name: str, level: str, group: str, source: str, county_type: str = "") -> dict:
    properties = {
        "map_level": level,
        "external_only": True,
        "display_name_zh": name,
        "source_name": name,
        "source_code": "",
        "province_name": "台湾省" if group == "taiwan" else ("香港特别行政区" if group == "hongkong" else "澳门特别行政区"),
        "province_code": f"EXTERNAL-{group.upper()}",
        "county_type": county_type,
        "prefecture_type": "外部地级对应区" if level == "prefecture" else "",
        "parent_entity_id": "",
        "link_status": "external_display_only",
        "external_group": group,
        "external_source": source,
    }
    return {
        "type": "Feature",
        "id": f"EXTERNAL-{group.upper()}-{level.upper()}-{name}",
        "properties": properties,
        "geometry": feature["geometry"],
    }


def build_taiwan() -> tuple[list[dict], list[dict]]:
    adm1 = read_json(RAW / "taiwan_geoboundaries" / "TWN-ADM1.geojson")
    adm2 = read_json(RAW / "taiwan_geoboundaries" / "TWN-ADM2.geojson")
    prefecture = []
    for feature in adm1["features"]:
        source_name = feature.get("properties", {}).get("shapeName", "")
        prefecture.append(external_feature(feature, name=TAIWAN_NAMES.get(source_name, source_name), level="prefecture", group="taiwan", source="geoBoundaries TWN ADM1", county_type=""))
    county = []
    for feature in adm2["features"]:
        source_name = feature.get("properties", {}).get("shapeName", "")
        county.append(external_feature(feature, name=source_name, level="county", group="taiwan", source="geoBoundaries TWN ADM2", county_type="县级外部展示区"))
    return prefecture, county


def build_hongkong() -> list[dict]:
    source_dir = RAW / "hongkong_github_18districts"
    features = []
    for path in sorted(source_dir.glob("*.json")):
        if path.name in {"cn.json"} or path.name == "Hong_Kong.geojson":
            continue
        payload = read_json(path)
        for feature in payload.get("features", []):
            source_name = feature.get("properties", {}).get("name", path.stem)
            features.append(external_feature(feature, name=HK_NAMES.get(source_name, source_name), level="county", group="hongkong", source="Paulkit/HKMap (MIT)", county_type="区级外部展示区"))
    return features


def build_macau() -> list[dict]:
    current = read_json(OUT / "external_current.geojson")
    feature = next(item for item in current["features"] if item["properties"].get("display_name_zh") == "澳门特别行政区")
    return [external_feature(feature, name="澳门特别行政区", level="county", group="macau", source="current Macau external display boundary", county_type="外部展示区（未拆分）")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prefecture, taiwan_county = build_taiwan()
    county = taiwan_county + build_hongkong() + build_macau()
    (OUT / "taiwan_prefecture.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": prefecture}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "external_county.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": county}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"taiwan_prefecture={len(prefecture)} external_county={len(county)}")


if __name__ == "__main__":
    main()
