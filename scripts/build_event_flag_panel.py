#!/usr/bin/env python3
"""Build a one-merge-ready city x panel-year event-flag panel.

Merges the whole-city fixed-boundary map with the district-layer map into
a complete prefecture x year grid for 1999—2020, with per-year event
counts and flags that can be left-joined onto any city panel:

- ``whole_city_break_flag``: 1 if a whole-city scope event (merge / split
  / abolish / cross-prefecture transfer / major county transfer) was
  effective in that year;
- ``district_jump_flag``: 1 if a county/县级市-to-district conversion was
  effective in that year (municipal-district statistics jump; annexed
  county leaves county panels);
- ``sample_entry_flag``: 1 in the first year a unit entered the city
  sample of statistical yearbooks (e.g. a 撤地设市 upgrade after 1999).

``treatment_summary`` composes the advice: aggregate-safe events vs
weighted splits vs break flags.

Output: ``fixed_boundary_event_flags_1999_2020.csv`` (prefecture x year).
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

PANEL_START, PANEL_END = 1999, 2020

FIELDS = [
    "prefecture_entity_id", "prefecture_name", "year",
    "whole_city_break_count", "district_jump_count", "district_merge_count",
    "whole_city_break_flag", "district_jump_flag", "sample_entry_flag",
    "treatment_summary",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    units = read_csv(DATA / "fixed_boundary_reference_units_2020.csv")
    district_breaks = read_csv(DATA / "fixed_boundary_district_breaks_1999_2020.csv")

    by_city_year: dict[tuple[str, int], dict[str, object]] = {}
    for row in district_breaks:
        by_city_year[(row["prefecture_entity_id"], int(row["year"]))] = row

    rows: list[dict[str, object]] = []
    for unit in units:
        pid, name = unit["entity_id"], unit["canonical_name"]
        break_years = {int(y) for y in unit["break_years"].split("、") if y}
        sample_year = int(unit["sample_entry_year"]) if unit["sample_entry_year"] else 0
        for year in range(PANEL_START, PANEL_END + 1):
            db = by_city_year.get((pid, year), {})
            district_jump = int(db.get("county_to_district_count", "0") or 0)
            district_merge = int(db.get("district_merge_count", "0") or 0)
            whole_break = 1 if year in break_years else 0
            jump = 1 if district_jump else 0
            entry = 1 if sample_year == year else 0
            hints: list[str] = []
            if whole_break:
                hints.append("whole_city_break")
            if jump:
                hints.append("district_scope_jump")
            if district_merge:
                hints.append("district_merge")
            if entry:
                hints.append("sample_entry")
            rows.append({
                "prefecture_entity_id": pid,
                "prefecture_name": name,
                "year": year,
                "whole_city_break_count": whole_break,
                "district_jump_count": district_jump,
                "district_merge_count": district_merge,
                "whole_city_break_flag": whole_break,
                "district_jump_flag": jump,
                "sample_entry_flag": entry,
                "treatment_summary": "|".join(hints) if hints else "stable",
            })

    write_csv(DATA / "fixed_boundary_event_flags_1999_2020.csv", rows)
    print(f"event_flags={len(rows)} ({PANEL_START}-{PANEL_END}, {len(rows)//(PANEL_END-PANEL_START+1)} cities)")


if __name__ == "__main__":
    main()
