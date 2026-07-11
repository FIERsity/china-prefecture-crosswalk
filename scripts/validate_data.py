#!/usr/bin/env python3
"""Run lightweight structural checks on the three CSV master views."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


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


if __name__ == "__main__":
    main()

