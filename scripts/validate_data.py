#!/usr/bin/env python3
"""Run lightweight structural checks on the three CSV master views."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (RAW / name).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    long_cols, long_rows = read_csv("entity_name_map_long.csv")
    wide_cols, wide_rows = read_csv("entity_name_map_wide.csv")
    panel_cols, panel_rows = read_csv("prefecture_master_wide_2000_2024.csv")

    require(len(long_rows) == 375, "long map row count changed")
    require(len(wide_rows) == 340, "wide map row count changed")
    require(len(panel_rows) == 340, "panel row count changed")

    for label, cols, rows in (
        ("long", long_cols, long_rows),
        ("wide", wide_cols, wide_rows),
        ("panel", panel_cols, panel_rows),
    ):
        require("entity_id" in cols, f"{label}: entity_id missing")
        ids = [row["entity_id"] for row in rows]
        require(all(ids), f"{label}: blank entity_id")
        if label != "long":
            require(len(ids) == len(set(ids)), f"{label}: duplicate entity_id")
        require(
            len(rows) == len({tuple(row[col] for col in cols) for row in rows}),
            f"{label}: duplicate rows",
        )

    wide_ids = {row["entity_id"] for row in wide_rows}
    panel_ids = {row["entity_id"] for row in panel_rows}
    long_ids = {row["entity_id"] for row in long_rows}
    require(long_ids == wide_ids == panel_ids, "entity_id coverage differs across files")

    years = list(range(2000, 2025))
    require(
        [f"name_{year}" for year in years] == panel_cols[1:],
        "panel year columns are not exactly 2000-2024",
    )

    expanded: dict[tuple[str, int], str] = {}
    for row in long_rows:
        start, end = int(row["start_year"]), int(row["end_year"])
        require(2000 <= start <= end <= 2024, f"invalid range: {row}")
        for year in range(start, end + 1):
            key = (row["entity_id"], year)
            require(key not in expanded, f"overlapping name ranges: {key}")
            expanded[key] = row["name"]

    for row in panel_rows:
        for year in years:
            require(
                expanded.get((row["entity_id"], year)) == row[f"name_{year}"],
                f"long/panel mismatch: {row['entity_id']} {year}",
            )

    print("PASS: 340 entities, 375 name spans, 25 years, no duplicate rows")
    print("PASS: entity coverage matches across all three CSV files")
    print("PASS: long name spans exactly reproduce the 2000-2024 panel")

    entities_cols, entities = read_csv_at(PROCESSED / "entities.csv")
    names_cols, names = read_csv_at(PROCESSED / "entity_names.csv")
    roster_cols, roster = read_csv_at(PROCESSED / "legal_roster_2000_2024.csv")
    _, sources = read_csv_at(PROCESSED / "sources.csv")
    _, events = read_csv_at(PROCESSED / "events_2000_2026.csv")
    _, event_links = read_csv_at(PROCESSED / "event_entity_links.csv")
    _, wiki_audit = read_csv_at(ROOT / "data" / "audit" / "wikipedia_entity_audit.csv")
    _, aliases = read_csv_at(PROCESSED / "aliases.csv")
    _, exclusions = read_csv_at(PROCESSED / "name_exclusions.csv")
    _, relations = read_csv_at(PROCESSED / "event_relations.csv")
    _, wiki_pages = read_csv_at(PROCESSED / "wikipedia_change_pages.csv")
    _, wiki_rows = read_csv_at(PROCESSED / "wikipedia_prefecture_change_rows.csv")
    _, historical_events = read_csv_at(PROCESSED / "wikipedia_normalized_events_1987_1999.csv")
    _, unified_events = read_csv_at(PROCESSED / "unified_events_1987_2026.csv")
    _, historical_entity_rows = read_csv_at(PROCESSED / "historical_entities.csv")
    _, unified_relations = read_csv_at(PROCESSED / "unified_event_relations.csv")
    _, continuity_audit = read_csv_at(ROOT / "data" / "audit" / "unified_continuity_audit.csv")
    _, extended_roster = read_csv_at(PROCESSED / "legal_roster_1987_2026.csv")
    _, extended_names = read_csv_at(PROCESSED / "entity_names_1987_2026.csv")
    _, id_crosswalk = read_csv_at(PROCESSED / "entity_id_crosswalk.csv")
    _, major_lineage = read_csv_at(PROCESSED / "major_lineage_relations.csv")
    _, county_transitions = read_csv_at(PROCESSED / "county_affiliation_transitions.csv")
    require(len(entities) == 340, "processed entities must contain 340 rows")
    require(len(roster) == 340 * 25, "legal roster must be entity-year complete")
    require(len(events) == 63, "event export must contain 63 rows")
    require(len(event_links) == 63, "every event must have an entity-link audit row")
    require(all(row["match_status"] == "unique" for row in event_links), "event/entity crosscheck has unresolved matches")
    require(len(wiki_audit) == 340, "Wikipedia entity audit must contain 340 rows")
    require(all(row["review_status"] == "verified" for row in wiki_audit), "Wikipedia entity audit has unresolved rows")
    require(all(row["page_url"].startswith("https://zh.wikipedia.org/wiki/") for row in wiki_audit), "Wikipedia audit URL missing")
    require(all(row["province_name_zh"] and row["province_short_zh"] for row in entities), "entity province missing")
    require(len(relations) == 63, "every event must have a typed relation")
    require(all(row["automatic_continuity"] == "false" for row in relations if row["relation_type"] in {"merge", "split"}), "complex relation cannot be automatic")
    require(any(row["alias"] == "恩施州" for row in aliases), "common aliases missing")
    require(any(row["normalized_name"] == "香格里拉市" for row in exclusions), "level exclusion missing")
    require(len(wiki_pages) == 37, "Wikipedia year-page inventory changed")
    require(min(int(row["year"]) for row in wiki_pages) == 1987, "Wikipedia archive start year changed")
    require(max(int(row["year"]) for row in wiki_pages) == 2026, "Wikipedia archive end year changed")
    require(len(wiki_rows) >= 900, "Wikipedia prefecture archive unexpectedly small")
    require(len(historical_events) == 81, "historical normalized event count changed")
    require(sum(row["normalization_status"].startswith("accepted_") for row in historical_events) == 81, "accepted historical event count changed")
    require(all(row["entity_id"] for row in historical_events if row["normalization_status"].startswith("accepted_")), "accepted historical event missing entity")
    require(len(unified_events) == 144, "unified event count changed")
    require(len({row["event_id"] for row in unified_events}) == len(unified_events), "duplicate unified event_id")
    signatures = [(row["year"], row["event_type"], row["old_prefecture_name"], row["new_prefecture_name"]) for row in unified_events]
    require(len(signatures) == len(set(signatures)), "duplicate unified event signature")
    require(all(row["source_url"].startswith("https://zh.wikipedia.org/wiki/") for row in unified_events), "unified event source missing")
    require(all(row["entity_id"] for row in unified_events if row["review_status"].startswith("accepted_")), "accepted unified event missing entity")
    require(sum(row["review_status"].startswith("accepted_") for row in unified_events) == 144, "accepted unified event count changed")
    require(sum(row["review_status"] == "review_required" for row in unified_events) == 0, "unresolved unified event remains")
    valid_entity_ids = {row["entity_id"] for row in entities} | {row["historical_entity_id"] for row in historical_entity_rows}
    require(all(row["entity_id"] in valid_entity_ids for row in unified_events), "unified event uses unknown entity")
    require(len(historical_entity_rows) == 7, "historical entity registry changed")
    require(sum(row["event_id"] == "WIKI-1993-029" and row["relation_type"] == "split" for row in unified_relations) == 2, "Yanbei split relations missing")
    require(sum(row["event_id"] == "WIKI-1996-056" and row["relation_type"] == "jurisdiction_transfer" and row["to_entity_id"] == "CNUR-000235" for row in unified_relations) >= 3, "1996 Chongqing transfer relations missing")
    require(len(continuity_audit) >= 1000, "continuity audit unexpectedly small")
    require(not any(row["status"] == "error" for row in continuity_audit), "continuity audit contains errors")
    require(len(extended_roster) == 347 * 40, "extended roster must contain 13,880 entity-years")
    require({int(row["year"]) for row in extended_roster} == set(range(1987, 2027)), "extended roster coverage must be 1987-2026")
    extended_by_key = {(row["entity_id"], int(row["year"])): row for row in extended_roster}
    require(extended_by_key[("CNUR-000003", 2026)]["status"] == "active", "石家庄市 must survive the 1993 prefecture-city merge")
    require(extended_by_key[("CNUR-000105", 2026)]["status"] == "active", "安庆市 must survive the 1988 prefecture-city merge")
    require(extended_by_key[("CNUR-000110", 2012)]["status"] == "abolished", "prefecture-level 巢湖市 must be abolished after 2011")
    require(extended_by_key[("CNUR-000146", 2019)]["status"] == "abolished", "莱芜市 must be abolished after the 2018 approval")
    require(extended_by_key[("CNUR-000230", 2001)]["status"] == "not_established", "崇左市 must not inherit 南宁地区")
    require(extended_by_key[("CNUR-000346", 2001)]["status"] == "active", "南宁地区 missing in 2001")
    require(extended_by_key[("CNUR-000346", 2002)]["status"] == "abolished", "南宁地区 must end before successor state")
    require(extended_by_key[("CNUR-000206", 1987)]["status"] == "not_established", "惠州市 must not inherit 惠阳地区")
    require(extended_by_key[("CNUR-000347", 1987)]["status"] == "active", "惠阳地区 missing in 1987")
    require(extended_by_key[("CNUR-000085", 1995)]["status"] == "not_established", "泰州市 must begin in 1996")
    require(extended_by_key[("CNUR-000086", 1995)]["status"] == "not_established", "宿迁市 must begin in 1996")
    require({row["entity_id"] for row in extended_roster} == {row["entity_id"] for row in id_crosswalk}, "extended roster entity coverage differs")
    require(any(row["entity_id"] == "CNUR-000121" and row["name_zh"] == "建阳地区" and row["start_year"] == "1987" for row in extended_names), "pre-2000 name chain missing")
    require(any(row["entity_id"] == "CNUR-000272" and row["name_zh"] == "普洱市" and row["end_year"] == "2026" for row in extended_names), "post-2024 name extension missing")
    require(all(row["automatic_continuity"] == "false" for row in unified_events if row["event_type"] in {"merge", "split", "abolish"}), "complex unified event cannot imply continuity")
    require(len({row["entity_id"] for row in entities}) == 340, "duplicate processed entity_id")
    require({row["entity_id"] for row in roster} == {row["entity_id"] for row in entities}, "roster entity coverage differs")
    require({row["source_id"] for row in roster} <= {row["source_id"] for row in sources}, "unknown roster source_id")
    for entity_id in ("CNUR-000110", "CNUR-000146", "CNUR-000338"):
        require(any(r["entity_id"] == entity_id and r["status"] == "abolished" for r in roster), f"{entity_id}: abolition missing")
    for entity_id in ("CNUR-000233", "CNUR-000325"):
        require(any(r["entity_id"] == entity_id and r["status"] == "not_established" for r in roster), f"{entity_id}: pre-establishment status missing")
    require(any(r["entity_id"] == "CNUR-000281" and r["legal_name_zh"] == "迪庆藏族自治州" for r in roster), "Diqing correction missing")
    require(not any(r["entity_id"] == "CNUR-000281" and "香格里拉" in r["legal_name_zh"] for r in roster), "county-level Shangri-La leaked into prefecture roster")
    require(len(id_crosswalk) == 347, "CNUR crosswalk must contain 347 entities")
    require(len({row["entity_id"] for row in id_crosswalk}) == 347, "duplicate CNUR ID")
    require(len(major_lineage) == 18, "major lineage relation inventory changed")
    require(len(county_transitions) == 70, "county transition evidence inventory changed")
    require(all(row["automatic_mapping"] == "false" for row in major_lineage), "major lineage must never auto-map values")
    require(sum(row["from_name"] == "南宁地区" for row in major_lineage) == 2, "Nanning prefecture split successors missing")
    require(sum(row["from_name"] == "惠阳地区" for row in major_lineage) == 3, "Huiyang prefecture split successors missing")
    require(all(row["entity_id"] == f"CNUR-{index:06d}" for index, row in enumerate(id_crosswalk, 1)), "CNUR sequence is not stable and contiguous")
    print("PASS: processed release has 340 entities, 8,500 entity-years, 63 events")
    print("PASS: all 63 events uniquely crosscheck to research entities")
    print("PASS: all 340 research entities have page-level and level evidence")
    print("PASS: ten audited corrections and all source references are present")
    print("PASS: extended runtime coverage is 347 entities x 40 years (1987-2026)")


def read_csv_at(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


if __name__ == "__main__":
    main()
