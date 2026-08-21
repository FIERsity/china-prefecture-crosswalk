#!/usr/bin/env python3
"""Run lightweight structural checks on the three CSV master views."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from county_unit_normalization import is_counted_unit_phrase


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
    _, source_registry = read_csv_at(PROCESSED / "source_registry.csv")
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
    _, early_prefecture_events = read_csv_at(PROCESSED / "prefecture_events_early_1983_1986.csv")
    _, prefecture_events = read_csv_at(PROCESSED / "prefecture_administrative_events_1983_2026.csv")
    _, historical_entity_rows = read_csv_at(PROCESSED / "historical_entities.csv")
    _, unified_relations = read_csv_at(PROCESSED / "unified_event_relations.csv")
    _, continuity_audit = read_csv_at(ROOT / "data" / "audit" / "unified_continuity_audit.csv")
    _, extended_roster = read_csv_at(PROCESSED / "legal_roster_1987_2026.csv")
    _, extended_names = read_csv_at(PROCESSED / "entity_names_1987_2026.csv")
    _, year_end_roster = read_csv_at(PROCESSED / "legal_roster_year_end_1987_2026.csv")
    _, year_end_names = read_csv_at(PROCESSED / "entity_names_year_end_1987_2026.csv")
    _, match_ranges = read_csv_at(PROCESSED / "entity_name_match_ranges_1987_2026.csv")
    _, timing_reviews = read_csv_at(PROCESSED / "event_timing_reviews.csv")
    _, id_crosswalk = read_csv_at(PROCESSED / "entity_id_crosswalk.csv")
    _, major_lineage = read_csv_at(PROCESSED / "major_lineage_relations.csv")
    _, county_transitions = read_csv_at(PROCESSED / "county_affiliation_transitions.csv")
    _, county_pages = read_csv_at(PROCESSED / "wikipedia_county_change_pages.csv")
    _, county_rows = read_csv_at(PROCESSED / "wikipedia_county_change_rows.csv")
    _, county_events = read_csv_at(PROCESSED / "county_administrative_events_1987_2026.csv")
    _, early_county_events = read_csv_at(PROCESSED / "county_administrative_events_1983_1986.csv")
    _, all_county_events = read_csv_at(PROCESSED / "county_administrative_events_1983_2026.csv")
    _, county_type_coverage = read_csv_at(PROCESSED / "county_unit_type_coverage_1987_2026.csv")
    _, year_end_diff = read_csv_at(ROOT / "data" / "audit" / "year_end_roster_diff_v3_v4.csv")
    _, ctamap_snapshots = read_csv_at(PROCESSED / "ctamap_snapshots.csv")
    _, ctamap_links = read_csv_at(PROCESSED / "ctamap_prefecture_links.csv")
    _, ctamap_issues = read_csv_at(ROOT / "data" / "audit" / "ctamap_alignment_issues.csv")
    require(len(entities) == 340, "processed entities must contain 340 rows")
    source_ids = {row["source_id"] for row in source_registry}
    require(source_ids == {row["source_id"] for row in sources}, "source registry and source table differ")
    require(len(source_registry) >= 49, "source registry unexpectedly small")
    require(all(row.get("source_id") in source_ids for row in county_events), "Wikipedia county event has unknown source_id")
    require(all(row.get("source_id") in source_ids for row in early_county_events), "early county event has unknown source_id")
    require(all(row.get("source_id") in source_ids for row in unified_events), "unified event has unknown source_id")
    require(all(row.get("source_id") in source_ids for row in early_prefecture_events), "early prefecture event has unknown source_id")
    require(all(row.get("source_id") in source_ids for row in prefecture_events), "combined prefecture event has unknown source_id")
    require(all(row.get("source_ids") for row in entities), "entity provenance is missing")
    require(all(row.get("source_ids") for row in extended_roster), "extended roster provenance is missing")
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
    require(len(early_prefecture_events) == 67, "early prefecture event count changed")
    require(len(prefecture_events) == len(unified_events) + len(early_prefecture_events), "combined prefecture event layer is incomplete")
    require(len({row["event_id"] for row in prefecture_events}) == len(prefecture_events), "combined prefecture event IDs are not unique")
    require(min(int(row["year"]) for row in prefecture_events) == 1983, "prefecture event coverage does not start in 1983")
    require(max(int(row["year"]) for row in prefecture_events) == max(int(row["year"]) for row in unified_events), "combined prefecture event layer changed the current event endpoint")
    require(all(row["description"] for row in early_prefecture_events), "early prefecture event lost source description")
    require(any(row["event_id"] == "EARLY-PREFECTURE-RMRB-COUNTY-1985-09-12-002" and row["new_prefecture_name"] == "晋城市" for row in early_prefecture_events), "Jincheng prefecture upgrade missing")
    require(any(row["event_id"] == "EARLY-PREFECTURE-XZQH-COUNTY-1983-Q4-004" and row["document_number"] == "(83)国函字218号" for row in early_prefecture_events), "Chifeng approval number missing")
    require(all(row["entity_id"] in valid_entity_ids for row in early_prefecture_events if row["entity_id"]), "early prefecture event uses unknown entity")
    require(len(historical_entity_rows) == 23, "historical entity registry changed")
    require(sum(row["event_id"] == "WIKI-1993-029" and row["relation_type"] == "split" for row in unified_relations) == 2, "Yanbei split relations missing")
    require(sum(row["event_id"] == "WIKI-1996-056" and row["relation_type"] == "jurisdiction_transfer" and row["to_entity_id"] == "CNUR-000235" for row in unified_relations) >= 3, "1996 Chongqing transfer relations missing")
    require(len(continuity_audit) >= 1000, "continuity audit unexpectedly small")
    require(not any(row["status"] == "error" for row in continuity_audit), "continuity audit contains errors")
    require(len(extended_roster) == 363 * 40, "extended roster must contain 14,520 entity-years")
    require(extended_roster == year_end_roster, "compatibility roster and explicit year-end roster differ")
    require(extended_names == year_end_names, "compatibility name spans and explicit year-end spans differ")
    require(all(row["year_basis"] == "year_end" for row in year_end_roster), "year-end roster contains another year basis")
    require(all(row["status_as_of"] == f"{row['year']}-12-31" for row in year_end_roster), "year-end status date is inconsistent")
    require(len(timing_reviews) == len(unified_events), "every unified event must have a timing review")
    require({row["event_id"] for row in timing_reviews} == {row["event_id"] for row in unified_events}, "timing review event coverage differs")
    require(all(row["annual_effective_year"] and row["annual_effective_basis"] for row in timing_reviews), "timing review is incomplete")
    require(all(row["review_status"] in {"reviewed", "inferred"} for row in timing_reviews), "timing review has unresolved status")
    require(match_ranges and all(row["validity_kind"] == "valid_during_calendar_year" for row in match_ranges), "calendar-year match ranges missing")
    require(year_end_diff and all(row["review_status"] == "explained" for row in year_end_diff), "V3-to-V4 year-end diff has unexplained rows")
    require({int(row["year"]) for row in extended_roster} == set(range(1987, 2027)), "extended roster coverage must be 1987-2026")
    extended_by_key = {(row["entity_id"], int(row["year"])): row for row in extended_roster}
    require(extended_by_key[("CNUR-000003", 2026)]["status"] == "active", "石家庄市 must survive the 1993 prefecture-city merge")
    require(extended_by_key[("CNUR-000105", 2026)]["status"] == "active", "安庆市 must survive the 1988 prefecture-city merge")
    require(extended_by_key[("CNUR-000110", 2012)]["status"] == "abolished", "prefecture-level 巢湖市 must be abolished after 2011")
    require(extended_by_key[("CNUR-000146", 2019)]["status"] == "abolished", "莱芜市 must be abolished after the 2018 approval")
    require(extended_by_key[("CNUR-000112", 1999)]["status"] == "not_established", "亳州市 must not be prefecture-level in 1999 year-end roster")
    require(extended_by_key[("CNUR-000180", 1999)]["status"] == "not_established", "随州市 must not be prefecture-level in 1999 year-end roster")
    require(extended_by_key[("CNUR-000234", 1999)]["status"] == "not_prefecture_level", "儋州 must not be prefecture-level in 1999 year-end roster")
    require(extended_by_key[("CNUR-000287", 2017)]["legal_name_zh"] == "那曲地区", "2017 year-end must retain 那曲地区")
    require(extended_by_key[("CNUR-000287", 2018)]["legal_name_zh"] == "那曲市", "2018 year-end must use 那曲市")
    require(extended_by_key[("CNUR-000230", 2001)]["status"] == "not_established", "崇左市 must not inherit 南宁地区")
    require(extended_by_key[("CNUR-000346", 2001)]["status"] == "active", "南宁地区 missing in 2001")
    require(extended_by_key[("CNUR-000346", 2002)]["status"] == "abolished", "南宁地区 must end before successor state")
    require(extended_by_key[("CNUR-000206", 1987)]["status"] == "not_established", "惠州市 must not inherit 惠阳地区")
    require(extended_by_key[("CNUR-000347", 1987)]["status"] == "active", "惠阳地区 missing in 1987")
    require(extended_by_key[("CNUR-000085", 1995)]["status"] == "not_established", "泰州市 must begin in 1996")
    require(extended_by_key[("CNUR-000086", 1995)]["status"] == "not_established", "宿迁市 must begin in 1996")
    require(extended_by_key[("CNUR-000177", 1993)]["status"] == "not_established", "荆沙/荆州市 entity must begin in 1994")
    require(extended_by_key[("CNUR-000358", 1993)]["status"] == "active", "荆州地区 predecessor missing")
    require(extended_by_key[("CNUR-000359", 1993)]["status"] == "active", "沙市市 predecessor missing")
    require(extended_by_key[("CNUR-000229", 2001)]["status"] == "not_established", "来宾市 must not inherit 柳州地区")
    require(extended_by_key[("CNUR-000362", 2001)]["status"] == "active", "柳州地区 predecessor missing")
    require(extended_by_key[("CNUR-000227", 1996)]["status"] == "not_established", "贺州 entity must not inherit 梧州地区")
    require(extended_by_key[("CNUR-000363", 1996)]["status"] == "active", "梧州地区 predecessor missing")
    for entity_id, year in {"CNUR-000145":1989,"CNUR-000189":1988,"CNUR-000212":1988,"CNUR-000213":1988,"CNUR-000214":1991,"CNUR-000215":1991,"CNUR-000216":1994,"CNUR-000224":1995}.items():
        require(extended_by_key[(entity_id, year - 1)]["status"] == "not_established", f"{entity_id} establishment year regression")
    require({row["entity_id"] for row in extended_roster} == {row["entity_id"] for row in id_crosswalk}, "extended roster entity coverage differs")
    require(len(ctamap_snapshots) == 50, "CTAmap snapshot inventory must contain 25 years x 2 levels")
    require(len(ctamap_links) == 8423, "CTAmap prefecture feature count changed")
    require(all(row["link_status"] == "linked" for row in ctamap_links), "CTAmap contains unresolved prefecture links")
    require(all(row["geometry_status"] == "valid" for row in ctamap_links), "CTAmap contains invalid linked geometry")
    require(all(row["source_year_verified"] == "true" for row in ctamap_links), "CTAmap feature year mismatch")
    require({row["issue_type"] for row in ctamap_issues} <= {"source_name_differs_from_year_end", "year_end_entity_missing_from_snapshot"}, "CTAmap audit contains unexpected issues")
    map_manifest_path = ROOT / "docs" / "data" / "maps" / "manifest.json"
    map_manifest = json.loads(map_manifest_path.read_text(encoding="utf-8"))
    require(len(map_manifest["years"]) == 25, "web map manifest must contain 25 snapshots")
    require(all(row["feature_count"] == row["linked_feature_count"] + row["context_feature_count"] for row in map_manifest["years"]), "web map feature classification is incomplete")
    require(all(row["context_feature_count"] > 0 for row in map_manifest["years"]), "web map is missing context regions")
    require(all((map_manifest_path.parent / row["file"]).exists() for row in map_manifest["years"]), "web map file missing")
    latest_map = json.loads((map_manifest_path.parent / "prefecture" / "2024.geojson").read_text(encoding="utf-8"))
    require(len(latest_map["features"]) == 372, "2024 web map must contain linked and context features")
    require(any(feature["properties"]["link_status"] == "context_only" for feature in latest_map["features"]), "2024 web map context classification missing")
    require(set(map_manifest["levels"]) == {"province", "prefecture", "county"}, "web map level inventory is incomplete")
    province_years = map_manifest["levels"]["province"]["years"]
    prefecture_years = map_manifest["levels"]["prefecture"]["years"]
    county_years = map_manifest["levels"]["county"]["years"]
    require(sum(row["feature_count"] for row in province_years) == 850, "province web map count changed")
    require(sum(row["feature_count"] for row in prefecture_years) == 9199, "prefecture web map count changed")
    require(sum(row["feature_count"] for row in county_years) == 71610, "county web map count changed")
    require(all(row["province_count"] >= 34 for row in county_years), "county web map province partitions are incomplete")
    require(all((map_manifest_path.parent / row["file"]).exists() for row in province_years + prefecture_years), "province or prefecture web map file missing")
    require(all((map_manifest_path.parent / file["file"]).exists() for row in county_years for file in row["files"]), "county web map partition missing")
    early_county_file = next(file for file in county_years[0]["files"] if file["province_code"] == "230000")
    early_county = json.loads((map_manifest_path.parent / early_county_file["file"]).read_text(encoding="utf-8"))
    first_coordinate = early_county["features"][0]["geometry"]["coordinates"][0][0][0]
    require(-180 <= first_coordinate[0] <= 180 and -90 <= first_coordinate[1] <= 90, "early county Web Mercator geometry was not transformed to WGS84")
    latest_hubei_file = next(file for file in county_years[-1]["files"] if file["province_code"] == "420000")
    latest_hubei = json.loads((map_manifest_path.parent / latest_hubei_file["file"]).read_text(encoding="utf-8"))
    require(all(feature["properties"]["map_level"] == "county" for feature in latest_hubei["features"]), "county map level property missing")
    require(any(feature["properties"]["parent_entity_id"] for feature in latest_hubei["features"]), "county parent CNUR links missing")
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
    require(len(id_crosswalk) == 363, "CNUR crosswalk must contain 363 entities")
    require(len({row["entity_id"] for row in id_crosswalk}) == 363, "duplicate CNUR ID")
    require(len(major_lineage) == 37, "major lineage relation inventory changed")
    require(len(county_transitions) == 90, "county transition evidence inventory changed")
    require(all(row["automatic_mapping"] == "false" for row in major_lineage), "major lineage must never auto-map values")
    require(len(county_pages) == 37, "county Wikipedia page inventory changed")
    require(len(county_rows) >= 1100, "county Wikipedia archive unexpectedly small")
    require(len(county_events) >= 1100, "county event supplement unexpectedly small")
    require(len(early_county_events) >= 200, "early county event supplement unexpectedly small")
    early_source_ids = {row["source_id"] for row in early_county_events}
    require(
        {
            "SRC-RMRB-1983-10-28", "SRC-XZQH-1983-Q4",
            "SRC-XZQH-1984-H1", "SRC-RMRB-1984-01-31",
            "SRC-RMRB-1985-09-12", "SRC-RMRB-1986-01-26",
            "SRC-RMRB-1986-07-18", "SRC-RMRB-1987-02-10",
        } <= early_source_ids,
        "early county coverage is missing one or more 1983-1986 source windows",
    )
    require(
        sum(row["source_type"] == "secondary_transcription" for row in early_county_events) > 0,
        "secondary early county transcription layer is missing",
    )
    require(len(all_county_events) == len(early_county_events) + len(county_events), "combined county event layer is incomplete")
    require(len({row["event_id"] for row in all_county_events}) == len(all_county_events), "combined county event IDs are not unique")
    for row in all_county_events:
        for field in ("county_names", "old_county_units", "new_county_units"):
            leaked = [
                token for token in row.get(field, "").replace("，", "、").split("、")
                if is_counted_unit_phrase(token)
            ]
            require(not leaked, f"count phrase leaked into {field}: {row['event_id']}={leaked}")
    require(min(int(row["year"]) for row in all_county_events) == 1983, "early county coverage does not start in 1983")
    require(max(int(row["year"]) for row in all_county_events) == 2026, "combined county coverage does not reach 2026")
    require(any("撤销韩城县" in row["change_description"] and row["prefecture_entity_ids"] == "CNUR-000293" for row in early_county_events), "Hancheng county-to-city event missing")
    required_county_event_fields = {
        "old_county_units", "new_county_units", "change_description", "county_unit_types", "scope",
    }
    require(required_county_event_fields <= set(read_csv_at(PROCESSED / "county_administrative_events_1987_2026.csv")[0]), "county event change fields missing")
    require(len({row["row_id"] for row in county_rows}) == len(county_rows), "duplicate county source row id")
    require(len({row["event_id"] for row in county_events}) == len(county_events), "duplicate county event id")
    require(all(row["source_url"].startswith("https://zh.wikipedia.org/wiki/") for row in county_events), "county event source missing")
    require(sum(bool(row["change_description"]) for row in county_events) >= 1100, "county change descriptions unexpectedly small")
    require(sum(row["scope"] == "county_level" for row in county_events) >= 1100, "county-level event scope unexpectedly small")
    require(any(row["event_type"] == "merge" for row in county_events), "county merge events missing")
    require(any(row["event_type"] == "jurisdiction_transfer" for row in county_events), "county jurisdiction-transfer events missing")
    require(any(row["event_type"] == "rename" for row in county_events), "county rename events missing")
    ordinary_types = {"市辖区", "县级市", "县", "自治县", "旗", "自治旗", "特区", "林区"}
    require({row["unit_type"] for row in county_type_coverage if row["ordinary_county_level"] == "true"} == ordinary_types, "county type coverage audit is incomplete")
    require(len(county_type_coverage) == 10, "county type coverage audit row count changed")
    require(sum(bool(row["prefecture_entity_ids"]) for row in county_events) >= 1100, "county entity linkage unexpectedly small")
    require(any(row["event_id"] == "WIKI-COUNTY-1993-07-010" and row["prefecture_entity_ids"] == "CNUR-000272" for row in county_events), "Pu'er county event example missing")
    require(sum(row["from_name"] == "南宁地区" for row in major_lineage) == 2, "Nanning prefecture split successors missing")
    require(sum(row["from_name"] == "惠阳地区" for row in major_lineage) == 3, "Huiyang prefecture split successors missing")
    xian_event = next((row for row in early_county_events if row["event_id"] == "RMRB-COUNTY-1983-10-28-094"), None)
    require(xian_event is not None, "1983 Xi'an county transfer event missing")
    require(xian_event["prefecture_entity_ids"] == "CNUR-000293、CNUR-000292、CNUR-000289", "1983 Xi'an county transfer parent IDs mismatch")
    require(xian_event["county_names"] == "临潼县、蓝田县、户县、周至县、高陵县", "1983 Xi'an county names were not normalized individually")
    require("二县" in xian_event["change_description"] and "三县" in xian_event["change_description"], "original counted wording was not retained as source text")
    require("二县" not in xian_event["county_names"] and "三县" not in xian_event["county_names"], "count phrase leaked into county names")
    require(xian_event["review_status"] == "reviewed_manual_override", "1983 Xi'an county transfer review status missing")
    require(all(row["entity_id"] == f"CNUR-{index:06d}" for index, row in enumerate(id_crosswalk, 1)), "CNUR sequence is not stable and contiguous")
    print("PASS: processed release has 340 entities, 8,500 entity-years, 63 events")
    print("PASS: all 63 events uniquely crosscheck to research entities")
    print(f"PASS: prefecture event layer has {len(prefecture_events)} rows, including {len(early_prefecture_events)} early descriptive records")
    print("PASS: all 340 research entities have page-level and level evidence")
    print("PASS: ten audited corrections and all source references are present")
    print("PASS: extended runtime coverage is 363 entities x 40 years (1987-2026)")
    print(f"PASS: source registry has {len(source_registry)} sources and county events cover 1983-2026")


def read_csv_at(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


if __name__ == "__main__":
    main()
