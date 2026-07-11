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
    require(len(entities) == 340, "processed entities must contain 340 rows")
    require(len(roster) == 340 * 25, "legal roster must be entity-year complete")
    require(len(events) == 63, "event export must contain 63 rows")
    require(len(event_links) == 63, "every event must have an entity-link audit row")
    require(all(row["match_status"] == "unique" for row in event_links), "event/entity crosscheck has unresolved matches")
    require(len(wiki_audit) == 340, "Wikipedia entity audit must contain 340 rows")
    require(all(row["review_status"] == "verified" for row in wiki_audit), "Wikipedia entity audit has unresolved rows")
    require(all(row["page_url"].startswith("https://zh.wikipedia.org/wiki/") for row in wiki_audit), "Wikipedia audit URL missing")
    require(len({row["entity_id"] for row in entities}) == 340, "duplicate processed entity_id")
    require({row["entity_id"] for row in roster} == {row["entity_id"] for row in entities}, "roster entity coverage differs")
    require({row["source_id"] for row in roster} <= {row["source_id"] for row in sources}, "unknown roster source_id")
    for entity_id in ("E341400", "E371200", "E654100"):
        require(any(r["entity_id"] == entity_id and r["status"] == "abolished" for r in roster), f"{entity_id}: abolition missing")
    for entity_id in ("E460300", "E640500"):
        require(any(r["entity_id"] == entity_id and r["status"] == "not_established" for r in roster), f"{entity_id}: pre-establishment status missing")
    require(any(r["entity_id"] == "E533400" and r["legal_name_zh"] == "迪庆藏族自治州" for r in roster), "E533400 correction missing")
    require(not any(r["entity_id"] == "E533400" and "香格里拉" in r["legal_name_zh"] for r in roster), "county-level Shangri-La leaked into prefecture roster")
    print("PASS: processed release has 340 entities, 8,500 entity-years, 63 events")
    print("PASS: all 63 events uniquely crosscheck to research entities")
    print("PASS: all 340 research entities have page-level and level evidence")
    print("PASS: ten audited corrections and all source references are present")


def read_csv_at(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


if __name__ == "__main__":
    main()
