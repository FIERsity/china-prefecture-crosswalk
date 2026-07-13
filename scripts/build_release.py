#!/usr/bin/env python3
"""Build the first machine-readable release from the repository snapshots."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
YEARS = range(2000, 2025)
RULE_VERSION = "2026.07.1"
PROVINCES = {
    "11": ("北京市", "北京"), "12": ("天津市", "天津"), "13": ("河北省", "河北"),
    "14": ("山西省", "山西"), "15": ("内蒙古自治区", "内蒙古"), "21": ("辽宁省", "辽宁"),
    "22": ("吉林省", "吉林"), "23": ("黑龙江省", "黑龙江"), "31": ("上海市", "上海"),
    "32": ("江苏省", "江苏"), "33": ("浙江省", "浙江"), "34": ("安徽省", "安徽"),
    "35": ("福建省", "福建"), "36": ("江西省", "江西"), "37": ("山东省", "山东"),
    "41": ("河南省", "河南"), "42": ("湖北省", "湖北"), "43": ("湖南省", "湖南"),
    "44": ("广东省", "广东"), "45": ("广西壮族自治区", "广西"), "46": ("海南省", "海南"),
    "50": ("重庆市", "重庆"), "51": ("四川省", "四川"), "52": ("贵州省", "贵州"),
    "53": ("云南省", "云南"), "54": ("西藏自治区", "西藏"), "61": ("陕西省", "陕西"),
    "62": ("甘肃省", "甘肃"), "63": ("青海省", "青海"), "64": ("宁夏回族自治区", "宁夏"),
    "65": ("新疆维吾尔自治区", "新疆"),
}

# Corrections verified against the linked Chinese Wikipedia annual change lists.
# Empty years mean that the research entity was not an active legal prefecture.
CORRECTIONS = {
    "E533400": [(2000, 2024, "迪庆藏族自治州", "active")],
    "E341400": [(2000, 2010, "巢湖市", "active"), (2011, 2024, "", "abolished")],
    "E371200": [(2000, 2018, "莱芜市", "active"), (2019, 2024, "", "abolished")],
    "E654100": [(2000, 2000, "伊犁地区", "active"), (2001, 2024, "", "abolished")],
    "E460300": [(2000, 2011, "", "not_established"), (2012, 2024, "三沙市", "active")],
    "E460400": [(2000, 2014, "", "not_prefecture_level"), (2015, 2024, "儋州市", "active")],
    "E640500": [(2000, 2002, "", "not_established"), (2003, 2024, "中卫市", "active")],
    "E540300": [(2000, 2013, "昌都地区", "active"), (2014, 2024, "昌都市", "active")],
    "E530800": [(2000, 2002, "思茅地区", "active"), (2003, 2006, "思茅市", "active"), (2007, 2024, "普洱市", "active")],
    "E530900": [(2000, 2002, "临沧地区", "active"), (2003, 2024, "临沧市", "active")],
    "E451400": [(2000, 2001, "", "not_established"), (2002, 2024, "崇左市", "active")],
}

SOURCE_BY_ENTITY = {
    "E654100": "SRC-WIKI-2001",
    "E530800": "SRC-WIKI-2003",
    "E530900": "SRC-WIKI-2003",
    "E640500": "SRC-WIKI-2003",
    "E341400": "SRC-WIKI-2011",
    "E460300": "SRC-WIKI-2012",
    "E540300": "SRC-WIKI-2014",
    "E460400": "SRC-WIKI-2015",
    "E371200": "SRC-WIKI-2019",
    "E533400": "SRC-WIKI-DIQING",
    "E451400": "SRC-WIKI-2002",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def corrected_value(entity_id: str, year: int, fallback: str) -> tuple[str, str, str]:
    if entity_id not in CORRECTIONS:
        return fallback, "active", "inherited_unverified"
    for start, end, name, status in CORRECTIONS[entity_id]:
        if start <= year <= end:
            return name, status, "wikipedia_verified"
    raise AssertionError((entity_id, year))


def main() -> None:
    panel = read_csv(RAW / "prefecture_master_wide_2000_2024.csv")
    audit_path = ROOT / "data" / "audit" / "wikipedia_entity_audit.csv"
    audited_entities = {
        row["entity_id"] for row in read_csv(audit_path) if row["review_status"] == "verified"
    } if audit_path.exists() else set()
    events = read_csv(PROCESSED / "events_2000_2026.csv")
    names_by_entity = {
        row["entity_id"]: {value for key, value in row.items() if key.startswith("name_") and value}
        for row in panel
    }
    event_links: list[dict[str, object]] = []
    crosschecked_entities: set[str] = set()
    for event in events:
        old_name, new_name = event["原单位"], event["新单位"]
        old_matches = [entity_id for entity_id, names in names_by_entity.items() if old_name and old_name in names]
        new_matches = [entity_id for entity_id, names in names_by_entity.items() if new_name and new_name in names]
        # Prefer the disappearing entity for abolitions/mergers; otherwise the new entity.
        matches = old_matches if "撤销" in event["事件类型"] and old_matches else new_matches or old_matches
        match_status = "unique" if len(matches) == 1 else "ambiguous" if matches else "unmatched"
        entity_id = matches[0] if len(matches) == 1 else ""
        if entity_id:
            crosschecked_entities.add(entity_id)
        event_links.append({
            "event_id": event["事件ID"],
            "entity_id": entity_id,
            "match_status": match_status,
            "match_basis": "old_name" if matches is old_matches else "new_name",
            "manual_review_required": "false" if match_status == "unique" else "true",
        })
    legal_rows: list[dict[str, object]] = []
    name_rows: list[dict[str, object]] = []
    entity_rows: list[dict[str, object]] = []

    for row in panel:
        entity_id = row["entity_id"]
        timeline = []
        for year in YEARS:
            name, status, verification = corrected_value(entity_id, year, row[f"name_{year}"])
            if verification == "inherited_unverified" and entity_id in crosschecked_entities:
                verification = "event_crosschecked"
            timeline.append((year, name, status, verification))
            legal_rows.append({
                "entity_id": entity_id,
                "year": year,
                "legal_name_zh": name,
                "legal_level": "prefecture" if status == "active" else "none",
                "status": status,
                "verification_status": verification,
                "source_id": SOURCE_BY_ENTITY.get(entity_id, "SRC-LEGACY-SNAPSHOT"),
            })

        start_year, prev_name, prev_status, prev_verification = timeline[0]
        for year, name, status, verification in timeline[1:] + [(2025, None, None, None)]:
            if (name, status, verification) != (prev_name, prev_status, prev_verification):
                name_rows.append({
                    "entity_id": entity_id,
                    "name_zh": prev_name or "",
                    "start_year": start_year,
                    "end_year": year - 1,
                    "legal_status": prev_status,
                    "verification_status": prev_verification,
                    "source_id": SOURCE_BY_ENTITY.get(entity_id, "SRC-LEGACY-SNAPSHOT"),
                })
                start_year, prev_name, prev_status, prev_verification = year, name, status, verification

        active_names = [name for _, name, status, _ in timeline if status == "active" and name]
        entity_verification = "wikipedia_verified" if entity_id in CORRECTIONS else "event_crosschecked" if entity_id in crosschecked_entities else "inherited_unverified"
        if entity_id in audited_entities and entity_verification == "inherited_unverified":
            entity_verification = "wikipedia_entity_verified"
        entity_rows.append({
            "entity_id": entity_id,
            "canonical_name_zh": active_names[-1],
            "province_name_zh": PROVINCES[entity_id[1:3]][0],
            "province_short_zh": PROVINCES[entity_id[1:3]][1],
            "entity_level": "prefecture_research_entity",
            "id_namespace": "project_stable_id_not_official_code",
            "verification_status": entity_verification,
        })

    write_csv(PROCESSED / "entities.csv", list(entity_rows[0]), entity_rows)
    write_csv(PROCESSED / "entity_names.csv", list(name_rows[0]), name_rows)
    write_csv(PROCESSED / "legal_roster_2000_2024.csv", list(legal_rows[0]), legal_rows)
    write_csv(PROCESSED / "event_entity_links.csv", list(event_links[0]), event_links)

    aliases = []
    suffixes = ("自治州", "地区", "盟", "市")
    common = {"恩施土家族苗族自治州": "恩施州", "湘西土家族苗族自治州": "湘西州"}
    for span in name_rows:
        if span["legal_status"] != "active" or not span["name_zh"]:
            continue
        name = str(span["name_zh"])
        for suffix in suffixes:
            if name.endswith(suffix) and len(name) > len(suffix) + 1:
                aliases.append({"alias": name[:-len(suffix)], "entity_id": span["entity_id"], "alias_type": "suffix_omitted", "start_year": span["start_year"], "end_year": span["end_year"], "level": "prefecture", "source_id": span["source_id"], "review_status": "generated_reviewed", "rule_version": RULE_VERSION})
                break
        if name in common:
            aliases.append({"alias": common[name], "entity_id": span["entity_id"], "alias_type": "common_abbreviation", "start_year": span["start_year"], "end_year": span["end_year"], "level": "prefecture", "source_id": span["source_id"], "review_status": "reviewed", "rule_version": RULE_VERSION})
    for alias, entity_id in (("亳州", "E341600"), ("毫州", "E341600"), ("亳州市", "E341600"), ("毫州市", "E341600")):
        aliases.append({"alias": alias, "entity_id": entity_id, "alias_type": "ocr_variant" if "毫" in alias else "manual_alias", "start_year": 1987, "end_year": 2026, "level": "prefecture", "source_id": "SRC-LEGACY-SNAPSHOT", "review_status": "reviewed", "rule_version": RULE_VERSION})
    aliases = list({(r["alias"], r["entity_id"], r["start_year"], r["end_year"]): r for r in aliases}.values())
    write_csv(PROCESSED / "aliases.csv", list(aliases[0]), aliases)

    exclusions = [{"name": "香格里拉市", "normalized_name": "香格里拉市", "level": "county_level_city", "parent_entity_id": "E533400", "start_year": 2015, "end_year": 2026, "risk_code": "county_level_conflict", "source_id": "SRC-WIKI-DIQING", "review_status": "reviewed", "rule_version": RULE_VERSION}]
    write_csv(PROCESSED / "name_exclusions.csv", list(exclusions[0]), exclusions)

    relation_type = {"地级市更名": "rename", "地区改设地级市": "upgrade", "盟改设地级市": "upgrade", "县级市升格为地级市": "upgrade", "以县新设地级市": "establish", "撤销办事处并新设地级市": "establish", "撤销地区并将辖区划归自治州": "abolish", "撤销地级市并分拆辖区": "split", "撤销地级市并整体并入另一地级市": "merge"}
    relations = [{"event_id": e["事件ID"], "entity_id": link["entity_id"], "relation_type": relation_type[e["事件类型"]], "from_name": e["原单位"], "to_name": e["新单位"], "year": e["年份"], "automatic_continuity": "true" if relation_type[e["事件类型"]] in {"rename", "upgrade"} else "false", "source_url": e["来源URL"], "rule_version": RULE_VERSION} for e, link in zip(events, event_links)]
    write_csv(PROCESSED / "event_relations.csv", list(relations[0]), relations)


if __name__ == "__main__":
    main()
