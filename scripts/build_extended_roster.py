#!/usr/bin/env python3
"""Build the V4 year-end roster, name spans, and timing audit."""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "processed"
AUDIT = ROOT / "data" / "audit"
YEARS = range(1987, 2027)
V3_ZIP = ROOT / "data" / "releases" / "v3.4.1" / "china_prefecture_crosswalk_data_v3.4.1.zip"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise AssertionError(f"refusing to write empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_v3_baseline() -> list[dict[str, str]]:
    if V3_ZIP.exists():
        with zipfile.ZipFile(V3_ZIP) as archive:
            text = archive.read("legal_roster_1987_2026.csv").decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))
    path = DATA / "legal_roster_1987_2026.csv"
    return read_csv(path) if path.exists() else []


def merge_source_ids(*values: str) -> str:
    result: list[str] = []
    for value in values:
        for source_id in (value or "").replace("|", "、").split("、"):
            source_id = source_id.strip()
            if source_id and source_id not in result:
                result.append(source_id)
    return "、".join(result)


def build_timing_reviews(events: list[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    overrides = {
        row["event_id"]: row for row in read_csv(RAW / "event_timing_overrides.csv")
    }
    unknown = sorted(set(overrides) - {row["event_id"] for row in events})
    if unknown:
        raise AssertionError(f"timing override references unknown event IDs: {unknown}")

    rows: list[dict[str, object]] = []
    by_event: dict[str, dict[str, object]] = {}
    for event in events:
        override = overrides.get(event["event_id"], {})
        approval_date = event.get("approval_date", "")
        if override:
            effective_year = int(override["annual_effective_year"])
            basis = override["annual_effective_basis"]
            precision = override["date_precision"]
            confidence = override["temporal_confidence"]
            review_status = override["review_status"]
            review_note = override["review_note"]
        elif approval_date:
            effective_year = int(approval_date[:4])
            basis = "approval_date_inferred"
            precision = "day"
            confidence = "medium"
            review_status = "inferred"
            review_note = "No later effective or implementation date is recorded; year-end transition is inferred from the approval date."
        else:
            effective_year = int(event["year"])
            basis = "event_year_only"
            precision = "year"
            confidence = "low"
            review_status = "inferred"
            review_note = "No exact approval or implementation date is recorded; the event year is used for year-end reconstruction."
        row: dict[str, object] = {
            "event_id": event["event_id"],
            "event_year": event["year"],
            "approval_date": approval_date,
            "announcement_date": override.get("announcement_date", ""),
            "effective_date": override.get("effective_date", ""),
            "implementation_date": override.get("implementation_date", ""),
            "annual_effective_year": effective_year,
            "annual_effective_basis": basis,
            "date_precision": precision,
            "temporal_confidence": confidence,
            "review_status": review_status,
            "source_ids": merge_source_ids(event.get("source_id", ""), override.get("source_ids", "")),
            "review_note": review_note,
        }
        rows.append(row)
        by_event[event["event_id"]] = row
    return rows, by_event


def compress_name_rows(roster: list[dict[str, object]]) -> list[dict[str, object]]:
    spans: list[dict[str, object]] = []
    by_entity: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in roster:
        by_entity[str(row["entity_id"])].append(row)
    compared = ("legal_name_zh", "status", "verification_status", "temporal_confidence")
    for entity_id, rows in by_entity.items():
        rows.sort(key=lambda row: int(row["year"]))
        start = int(rows[0]["year"])
        previous = rows[0]
        for row in rows[1:] + [None]:
            if row is None or tuple(row[key] for key in compared) != tuple(previous[key] for key in compared):
                spans.append({
                    "entity_id": entity_id,
                    "name_zh": previous["legal_name_zh"],
                    "start_year": start,
                    "end_year": int(row["year"]) - 1 if row else 2026,
                    "legal_status": previous["status"],
                    "year_basis": "year_end",
                    "verification_status": previous["verification_status"],
                    "temporal_confidence": previous["temporal_confidence"],
                    "derivation_basis": previous["derivation_basis"],
                    "source_ids": previous["source_ids"],
                    "provenance_kind": previous["provenance_kind"],
                })
                if row is not None:
                    start, previous = int(row["year"]), row
    return spans


def build_match_ranges(
    roster: list[dict[str, object]],
    events: list[dict[str, str]],
    timing_by_event: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    years_by_name: dict[tuple[str, str], set[int]] = defaultdict(set)
    sources_by_name: dict[tuple[str, str], str] = {}
    events_by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in roster:
        if row["status"] == "active" and row["legal_name_zh"]:
            key = (str(row["entity_id"]), str(row["legal_name_zh"]))
            years_by_name[key].add(int(row["year"]))
            sources_by_name[key] = merge_source_ids(sources_by_name.get(key, ""), str(row["source_ids"]))
    for event in events:
        if event.get("automatic_continuity") != "true":
            continue
        old_name = event.get("old_prefecture_name", "")
        if not old_name:
            continue
        key = (event["entity_id"], old_name)
        effective_year = int(timing_by_event[event["event_id"]]["annual_effective_year"])
        if effective_year in YEARS:
            years_by_name[key].add(effective_year)
            sources_by_name[key] = merge_source_ids(sources_by_name.get(key, ""), event.get("source_id", ""))
            events_by_name[key].append(event["event_id"])

    result: list[dict[str, object]] = []
    for (entity_id, name), years in sorted(years_by_name.items()):
        ordered = sorted(years)
        start = previous = ordered[0]
        for year in ordered[1:] + [None]:
            if year is None or year != previous + 1:
                result.append({
                    "entity_id": entity_id,
                    "name_zh": name,
                    "start_year": start,
                    "end_year": previous,
                    "validity_kind": "valid_during_calendar_year",
                    "transition_event_ids": "、".join(sorted(set(events_by_name[(entity_id, name)]))),
                    "source_ids": sources_by_name[(entity_id, name)],
                })
                if year is not None:
                    start = year
            if year is not None:
                previous = year
    return result


def build_diff(v3: list[dict[str, str]], v4: list[dict[str, object]], events: list[dict[str, str]]) -> list[dict[str, object]]:
    old = {(row["entity_id"], int(row["year"])): row for row in v3}
    event_ids_by_entity_year: dict[tuple[str, int], list[str]] = defaultdict(list)
    for event in events:
        event_ids_by_entity_year[(event["entity_id"], int(event["year"]))].append(event["event_id"])
    terminating_entities = {
        event["entity_id"] for event in events if event["event_type"] in {"abolish", "merge", "split"}
    }
    rows: list[dict[str, object]] = []
    for row in v4:
        key = (str(row["entity_id"]), int(row["year"]))
        before = old.get(key, {})
        changed = [field for field in ("legal_name_zh", "status", "legal_level") if before.get(field, "") != str(row[field])]
        if not changed:
            continue
        nearby_events: list[str] = []
        for year in range(int(row["year"]) - 1, int(row["year"]) + 2):
            nearby_events.extend(event_ids_by_entity_year.get((str(row["entity_id"]), year), []))
        rows.append({
            "entity_id": row["entity_id"],
            "year": row["year"],
            "changed_fields": "|".join(changed),
            "v3_name": before.get("legal_name_zh", ""),
            "v4_year_end_name": row["legal_name_zh"],
            "v3_status": before.get("status", ""),
            "v4_year_end_status": row["status"],
            "v3_level": before.get("legal_level", ""),
            "v4_year_end_level": row["legal_level"],
            "transition_event_ids": "、".join(sorted(set(nearby_events))),
            "v4_derivation_basis": row["derivation_basis"],
            "review_status": "explained" if (
                nearby_events
                or row["derivation_basis"] in {"entity_year_end_override", "reviewed_name_span_override"}
                or (row["status"] == "abolished" and row["entity_id"] in terminating_entities)
            ) else "review_required",
        })
    return rows


def main() -> None:
    entities = {row["entity_id"]: row for row in read_csv(DATA / "entities.csv")}
    historical = {row["historical_entity_id"]: row for row in read_csv(DATA / "historical_entities.csv")}
    events = read_csv(DATA / "unified_events_1987_2026.csv")
    timing_rows, timing_by_event = build_timing_reviews(events)
    write_csv(DATA / "event_timing_reviews.csv", timing_rows)

    overrides = {row["entity_id"]: row for row in read_csv(RAW / "entity_year_end_overrides.csv")}
    name_overrides_by_entity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(RAW / "entity_year_end_name_overrides.csv"):
        name_overrides_by_entity[row["entity_id"]].append(row)
    valid_ids = set(entities) | set(historical)
    unknown = sorted((set(overrides) | set(name_overrides_by_entity)) - valid_ids)
    if unknown:
        raise AssertionError(f"entity override references unknown IDs: {unknown}")

    events_by_entity: dict[str, list[dict[str, str]]] = defaultdict(list)
    for event in events:
        events_by_entity[event["entity_id"]].append(event)

    roster: list[dict[str, object]] = []
    for entity_id in [*entities, *historical]:
        meta = entities.get(entity_id) or historical[entity_id]
        is_historical = entity_id in historical
        default_name = meta["canonical_name_zh"]
        province = meta.get("province_name_zh", "") or meta.get("province_at_time", "")
        entity_sources = meta.get("source_ids", "") or "SRC-LEGACY-SNAPSHOT"
        override = overrides.get(entity_id, {})
        establishing_years = [
            int(timing_by_event[event["event_id"]]["annual_effective_year"])
            for event in events_by_entity[entity_id]
            if event["event_type"] in {"establish", "establish_prefecture"}
        ]
        inferred_first_active = min(establishing_years) if establishing_years else 1987
        first_active = int(override.get("first_active_year") or (meta.get("start_year") if is_historical else inferred_first_active))
        last_active = int(override.get("last_active_year") or (meta.get("end_year") if is_historical else 2026))
        pre_status = override.get("pre_active_status") or "not_established"
        post_status = override.get("post_active_status") or "abolished"
        timeline = sorted(
            events_by_entity[entity_id],
            key=lambda event: (int(timing_by_event[event["event_id"]]["annual_effective_year"]), event["event_id"]),
        )

        for year in YEARS:
            status = "active"
            name = default_name
            derivation = "reviewed_event_chain"
            confidence = "medium"
            row_sources = entity_sources
            if year < first_active:
                status, name = pre_status, ""
                derivation = "entity_year_end_override" if override else "entity_lifespan"
                confidence = override.get("temporal_confidence", "medium")
                row_sources = merge_source_ids(row_sources, override.get("source_ids", ""))
            elif year > last_active:
                status, name = post_status, ""
                derivation = "entity_year_end_override" if override else "entity_lifespan"
                confidence = override.get("temporal_confidence", "medium")
                row_sources = merge_source_ids(row_sources, override.get("source_ids", ""))
            else:
                terminated = False
                for event in reversed(timeline):
                    timing = timing_by_event[event["event_id"]]
                    effective_year = int(timing["annual_effective_year"])
                    if event["automatic_continuity"] == "true":
                        if year < effective_year and event.get("old_prefecture_name"):
                            name = event["old_prefecture_name"]
                        elif year >= effective_year and event.get("new_prefecture_name"):
                            name = event["new_prefecture_name"]
                            confidence = str(timing["temporal_confidence"])
                            row_sources = merge_source_ids(row_sources, str(timing["source_ids"]))
                            break
                    elif (
                        event["event_type"] in {"abolish", "merge", "split"}
                        and year >= effective_year
                        and (is_historical or event.get("old_prefecture_name") == default_name)
                    ):
                        status, name = "abolished", ""
                        confidence = str(timing["temporal_confidence"])
                        row_sources = merge_source_ids(row_sources, str(timing["source_ids"]))
                        terminated = True
                        break
                if terminated:
                    pass
                if override:
                    confidence = override.get("temporal_confidence", confidence)
                    row_sources = merge_source_ids(row_sources, override.get("source_ids", ""))

                for name_override in name_overrides_by_entity.get(entity_id, []):
                    if int(name_override["start_year"]) <= year <= int(name_override["end_year"]):
                        name = name_override["legal_name_zh"]
                        status = name_override["status"]
                        derivation = "reviewed_name_span_override"
                        confidence = name_override["temporal_confidence"]
                        row_sources = merge_source_ids(row_sources, name_override["source_ids"])
                        break

            verification = "reviewed" if derivation == "entity_year_end_override" or confidence == "high" else "inferred"
            roster.append({
                "entity_id": entity_id,
                "year": year,
                "status_as_of": f"{year}-12-31",
                "year_basis": "year_end",
                "legal_name_zh": name,
                "province_name_zh": province,
                "legal_level": "prefecture" if status == "active" else "none",
                "status": status,
                "verification_status": verification,
                "temporal_confidence": confidence,
                "derivation_basis": derivation,
                "source_ids": row_sources,
                "provenance_kind": "derived_from_reviewed_year_end_rules",
            })

    spans = compress_name_rows(roster)
    match_ranges = build_match_ranges(roster, events, timing_by_event)
    diff = build_diff(read_v3_baseline(), roster, events)

    for name in ("legal_roster_year_end_1987_2026.csv", "legal_roster_1987_2026.csv"):
        write_csv(DATA / name, roster)
    for name in ("entity_names_year_end_1987_2026.csv", "entity_names_1987_2026.csv"):
        write_csv(DATA / name, spans)
    write_csv(DATA / "entity_name_match_ranges_1987_2026.csv", match_ranges)
    if diff:
        write_csv(AUDIT / "year_end_roster_diff_v3_v4.csv", diff)
    print(
        f"entities={len(entities) + len(historical)} entity_years={len(roster)} "
        f"year_end_spans={len(spans)} match_ranges={len(match_ranges)} timing_reviews={len(timing_rows)} diffs={len(diff)}"
    )


if __name__ == "__main__":
    main()
