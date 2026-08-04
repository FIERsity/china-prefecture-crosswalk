#!/usr/bin/env python3
"""Combine the early primary-text supplement with the Wikipedia event layer."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def read(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (PROCESSED / name).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def main() -> None:
    early_fields, early = read("county_administrative_events_1983_1986.csv")
    current_fields, current = read("county_administrative_events_1987_2026.csv")
    fields = list(dict.fromkeys([*current_fields, *early_fields]))
    rows = []
    for row in [*early, *current]:
        rows.append({field: row.get(field, "") for field in fields})
    rows.sort(key=lambda row: (int(row["year"]), row["event_id"]))
    output = PROCESSED / "county_administrative_events_1983_2026.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} early={len(early)} wikipedia={len(current)} output={output}")


if __name__ == "__main__":
    main()
