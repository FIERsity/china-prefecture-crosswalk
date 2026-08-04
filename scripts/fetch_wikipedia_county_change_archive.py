#!/usr/bin/env python3
"""Fetch and lightly structure county-level administrative changes from Chinese Wikipedia.

The annual Wikipedia pages use different table schemas over time. This script keeps the
source row intact, extracts the change cell where possible, and adds a deliberately loose
prefecture-entity hint for display. It does not claim to reconstruct a complete county
genealogy.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from county_unit_normalization import normalize_unit_list

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
API = "https://zh.wikipedia.org/w/api.php"
UA = "china-prefecture-crosswalk/0.4 (https://github.com/FIERsity/china-prefecture-crosswalk)"
PAGE_FIELDS = ["year", "title", "page_url", "revision_id", "county_row_count", "checked_at_utc"]
RAW_FIELDS = [
    "row_id", "year", "section", "table_number", "row_number", "row_kind",
    "header_text", "row_text", "cells_json", "raw_markup", "source_title", "source_url", "revision_id",
]
EVENT_FIELDS = [
    "event_id", "year", "section", "event_type", "prefecture_names",
    "prefecture_entity_ids", "county_names", "old_county_units", "new_county_units",
    "change_description", "county_unit_types", "scope", "description", "source_title",
    "source_url", "revision_id", "review_status",
]
TYPE_SUMMARY_FIELDS = ["unit_type", "ordinary_county_level", "event_count", "note"]
TITLE_RE = re.compile(r"^(\d{4})年中华人民共和国县级以上行政区划变更列表$")
HEADING_RE = re.compile(r"(?m)^(={2,6})\s*(.*?)\s*\1\s*$")
COUNTY_MARKERS = ("县级", "市辖区", "县和县级市", "县级单位", "县级行政区划")
HEADER_MARKERS = ("所属上级", "所属地市", "原属省市", "现属省市", "所属省市", "新属省市", "原属省市（", "现属省市（")
CHANGE_MARKERS = ("撤销", "撤消", "设立", "新设", "增设", "更名", "改名", "划归", "归", "管辖", "调整", "合并", "拆分", "迁至", "迁出", "迁入", "恢复", "改为", "改由")
COUNTY_UNIT_TYPES = ("市辖区", "县级市", "县", "自治县", "旗", "自治旗", "特区", "林区")
HISTORICAL_UNIT_TYPES = ("工农区",)
NON_COUNTY_TYPES = ("开发区",)
ATTR_RE = re.compile(r"^\s*((?:(?:rowspan|colspan|style|class|scope|align)\s*=\s*(?:\"[^\"]*\"|'[^']*'|\S+)\s*)+)\|\s*(.*)$")
ROWSPAN_RE = re.compile(r"\browspan\s*=\s*[\"']?(\d+)")
COLSPAN_RE = re.compile(r"\bcolspan\s*=\s*[\"']?(\d+)")


def api(params: dict[str, object], attempts: int = 5) -> dict:
    query = urllib.parse.urlencode({"format": "json", "maxlag": 5, **params})
    for attempt in range(attempts):
        request = urllib.request.Request(API + "?" + query, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {429, 503} or attempt == attempts - 1:
                raise
            retry_after = int(error.headers.get("Retry-After", "5"))
            time.sleep(max(retry_after, 5) * (attempt + 1))
    raise RuntimeError("Wikipedia API request exhausted retries")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def clean_wikitext(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", text, flags=re.S)
    text = re.sub(r"\{\{notetag\|.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<br\s*/?>", "；", text, flags=re.I)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip(" |!\n\t")


def link_texts(text: str) -> list[str]:
    text = remove_template_blocks(text, "notetag")
    values = []
    for match in re.finditer(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]", text):
        values.append(clean_wikitext(match.group(2) or match.group(1)))
    return [value for value in values if value]


def remove_template_blocks(text: str, template_name: str) -> str:
    marker = "{{" + template_name + "|"
    while True:
        start = text.find(marker)
        if start < 0:
            return text
        depth, position = 0, start
        while position < len(text) - 1:
            token = text[position:position + 2]
            if token == "{{":
                depth += 1
                position += 2
                continue
            if token == "}}":
                depth -= 1
                position += 2
                if depth == 0:
                    text = text[:start] + text[position:]
                    break
                continue
            position += 1
        else:
            return text[:start]


def split_cell_parts(line: str) -> list[str]:
    marker = "!!" if line.lstrip().startswith("!") else "||"
    body = line.lstrip()[1:]
    return re.split(re.escape(marker), body)


def cell_value(part: str) -> tuple[str, int, int]:
    match = ATTR_RE.match(part)
    attrs, value = (match.group(1), match.group(2)) if match else ("", part)
    rowspan = int(ROWSPAN_RE.search(attrs).group(1)) if ROWSPAN_RE.search(attrs) else 1
    colspan = int(COLSPAN_RE.search(attrs).group(1)) if COLSPAN_RE.search(attrs) else 1
    return value.strip(), rowspan, colspan


def table_ranges(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    ranges, start, chunks = [], None, []
    position = 0
    for line in lines:
        stripped = line.strip()
        if start is None and stripped.startswith("{|"):
            start, chunks = position, [line]
        elif start is not None:
            chunks.append(line)
            if stripped == "|}":
                ranges.append((start, position + len(line), "".join(chunks)))
                start, chunks = None, []
        position += len(line)
    return ranges


def headings(text: str) -> list[tuple[int, int, int, str]]:
    result = []
    for match in HEADING_RE.finditer(text):
        title = clean_wikitext(match.group(2))
        result.append((match.start(), match.end(), len(match.group(1)), title))
    return result


def heading_path(items: list[tuple[int, int, int, str]], position: int) -> list[str]:
    stack: list[tuple[int, str]] = []
    for start, _end, level, title in items:
        if start >= position:
            break
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
    return [title for _level, title in stack]


def parse_table(table: str) -> tuple[list[str], list[dict[str, object]]]:
    rows: list[list[tuple[str, int, int, str]]] = []
    current: list[tuple[str, int, int, str]] = []

    def flush() -> None:
        nonlocal current
        if current:
            rows.append(current)
            current = []

    for raw_line in table.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("{|") or line == "|}":
            continue
        if line.startswith("|-"):
            flush()
            continue
        if line.startswith("!") or (line.startswith("|") and not line.startswith("|}")):
            for part in split_cell_parts(line):
                value, rowspan, colspan = cell_value(part)
                current.append((value, rowspan, colspan, "header" if line.startswith("!") else "data"))
            continue
        if current:
            value, rowspan, colspan, kind = current[-1]
            current[-1] = (f"{value} {line}", rowspan, colspan, kind)
    flush()

    header_index = next((index for index, row in enumerate(rows) if any("原行政" in clean_wikitext(c[0]) or "所属" in clean_wikitext(c[0]) for c in row)), None)
    headers = [clean_wikitext(cell[0]) for cell in rows[header_index]] if header_index is not None else []
    output: list[dict[str, object]] = []
    carry: list[tuple[int, str]] = []
    for index, row in enumerate(rows, start=1):
        inherited = [text for remaining, text in carry if remaining > 0]
        current_values = [clean_wikitext(cell[0]) for cell in row]
        raw_values = [cell[0] for cell in row]
        values = [value for value in inherited + current_values if value]
        row_kind = "header" if header_index is not None and index - 1 == header_index else "data"
        if len(values) == 1 and re.search(r"(省|自治区|特别行政区)$", values[0]):
            row_kind = "province_marker"
        if row_kind == "data" and any(marker in " | ".join(values) for marker in ("原行政单位", "所属上级单位", "所属地市", "原属省市", "现属省市", "变更方式")):
            row_kind = "header"
        output.append({
            "row_number": index,
            "row_kind": row_kind,
            "values": values,
            "raw_values": raw_values,
            "row_text": " | ".join(values),
        })
        next_carry = [(remaining - 1, text) for remaining, text in carry if remaining > 1]
        for value, rowspan, _colspan, _kind in row:
            if rowspan > 1:
                next_carry.append((rowspan, clean_wikitext(value)))
        carry = next_carry
    return headers, output


def table_is_county_related(path: list[str], headers: list[str]) -> bool:
    path_text = " / ".join(path)
    county_path = any(marker in path_text for marker in COUNTY_MARKERS)
    header_text = " | ".join(headers)
    county_header = any(marker in header_text for marker in HEADER_MARKERS)
    has_prefecture_section = "地级" in path_text
    return (county_path or county_header) and not (has_prefecture_section and not county_path)


def event_type(section: str, row_text: str) -> str:
    text = f"{section} {row_text}"
    if "隶属" in text or "划归" in text or "归" in text and "管辖" in text:
        return "jurisdiction_transfer"
    if "合并" in text or "并入" in text:
        return "merge"
    if "拆分" in text or "分设" in text:
        return "split"
    if "更名" in text or "改名" in text:
        return "rename"
    if "驻地" in text or "迁至" in text or "迁移" in text:
        return "residence_change"
    if "撤销" in text or "撤消" in text:
        return "abolish_or_merge"
    if "设立" in text or "新设" in text or "增设" in text:
        return "establish"
    if "调整" in text:
        return "jurisdiction_adjustment"
    return "county_change"


def raw_cells(raw_markup: str) -> list[str]:
    """Split the intentionally simple cell serialization used in the raw archive."""
    return [cell.strip() for cell in raw_markup.split(" | ") if cell.strip()]


def is_unit_name(value: str, allow_plain_city: bool = False) -> bool:
    value = clean_wikitext(value).strip(" 。；，,()（）")
    if not value or value.endswith(("地区", "自治区", "开发区")):
        return False
    if value.endswith(("自治县", "特区", "林区", "自治旗", "旗", "县")):
        return True
    if value.endswith("区"):
        return True
    return allow_plain_city and value.endswith("市")


def linked_unit_names(text: str, allow_plain_city: bool = False) -> list[str]:
    return list(dict.fromkeys(
        name for name in link_texts(text)
        if is_unit_name(name, allow_plain_city=allow_plain_city)
    ))


def plain_unit_names(text: str, allow_plain_city: bool = False) -> list[str]:
    """Recover simple unlinked unit cells without treating parent prefectures as counties."""
    values = []
    for part in re.split(r"[|；;，,、]", clean_wikitext(text)):
        part = part.strip()
        if is_unit_name(part, allow_plain_city=allow_plain_city):
            values.append(part)
    return list(dict.fromkeys(values))


def side_unit_names(cells: list[str], side: str, allow_plain_city: bool = False) -> list[str]:
    """Choose the nearest unit-bearing cell, avoiding parent/code cells where possible."""
    ordered = cells if side == "old" else list(reversed(cells))
    for cell in ordered:
        names = linked_unit_names(cell, allow_plain_city=allow_plain_city)
        if not names:
            names = plain_unit_names(cell, allow_plain_city=allow_plain_city)
        if names:
            return names
    return []


def action_cell_index(cells: list[str]) -> int | None:
    candidates = [
        (index, clean_wikitext(cell))
        for index, cell in enumerate(cells)
        if any(marker in clean_wikitext(cell) for marker in CHANGE_MARKERS)
    ]
    if not candidates:
        return None
    # Prefer the cell with the densest change language; this avoids selecting a
    # parent cell merely because it contains the word “管辖”.
    return max(candidates, key=lambda item: sum(item[1].count(marker) for marker in CHANGE_MARKERS))[0]


def structured_change(row: dict[str, object]) -> tuple[list[str], list[str], str, list[str], str]:
    cells = raw_cells(str(row["raw_markup"]))
    index = action_cell_index(cells)
    if index is None:
        action = ""
        left, right = cells[:1], cells[1:]
    else:
        action = clean_wikitext(cells[index])
        left, right = cells[:index], cells[index + 1:]

    action_has_county_city = "县级市" in action or "县级" in action
    old = side_unit_names(left, "old", allow_plain_city=action_has_county_city)
    new = side_unit_names(right, "new", allow_plain_city=action_has_county_city)

    # A few older tables put the unit names directly in the change cell. Keep
    # those links as a fallback, but never let the fallback replace the full
    # change sentence shown to the user.
    action_units = linked_unit_names(" | ".join(cells[index:index + 1]) if index is not None else "", allow_plain_city=action_has_county_city)
    if not old and action_units and any(marker in action for marker in ("撤销", "撤消", "更名", "改名", "合并")):
        old = action_units[:]
    if not new and action_units and any(marker in action for marker in ("设立", "新设", "增设", "恢复", "改为", "成立")):
        new = action_units[:]

    description = action or clean_wikitext(str(row["row_text"]))
    all_text = f"{row['row_text']} {description}"
    types = []
    if "市辖区" in str(row["section"]) or "市辖区" in all_text or any(name.endswith("区") for name in old + new):
        types.append("市辖区")
    if "县级市" in all_text or re.search(r"设立[^；。]+市（县级）", all_text):
        types.append("县级市")
    if "自治县" in all_text or any("自治县" in name for name in old + new):
        types.append("自治县")
    if "自治旗" in all_text or any("自治旗" in name for name in old + new):
        types.append("自治旗")
    if "林区" in all_text or any(name.endswith("林区") for name in old + new):
        types.append("林区")
    if "特区" in all_text or any(name.endswith("特区") for name in old + new):
        types.append("特区")
    if re.search(r"(?:[\u4e00-\u9fff]{1,20})旗", all_text) and "自治旗" not in all_text:
        types.append("旗")
    if ("县" in all_text and "自治县" not in all_text) or any(name.endswith("县") for name in old + new):
        types.append("县")
    if "工农区" in all_text:
        types.append("工农区")
    if "开发区" in all_text:
        types.append("开发区")
    types = list(dict.fromkeys(types))
    scope = "non_county_development_zone" if "开发区" in types and not (old or new) else (
        "county_level" if any(item in COUNTY_UNIT_TYPES for item in types) else (
            "historical_county_level_other" if any(item in HISTORICAL_UNIT_TYPES for item in types) else "untyped_county_record"
        )
    )
    return old, new, description, types, scope


def entity_name_index() -> list[tuple[str, str]]:
    rows = read_csv(PROCESSED / "entity_names_1987_2026.csv")
    values = {(row["name_zh"], row["entity_id"]) for row in rows if row.get("name_zh") and row.get("legal_status") == "active"}
    historical = read_csv(PROCESSED / "historical_entities.csv")
    values.update(
        (row["canonical_name_zh"], row["historical_entity_id"])
        for row in historical
        if row.get("canonical_name_zh") and row.get("historical_entity_id")
    )
    return sorted(values, key=lambda item: len(item[0]), reverse=True)


def normalize_events(raw_rows: list[dict[str, object]], names: list[tuple[str, str]]) -> list[dict[str, object]]:
    events = []
    for row in raw_rows:
        if row["row_kind"] != "data" or not row["row_text"]:
            continue
        text = str(row["row_text"])
        matches = [(name, entity_id) for name, entity_id in names if name in text]
        prefecture_names = list(dict.fromkeys(name for name, _entity_id in matches))
        entity_ids = list(dict.fromkeys(entity_id for _name, entity_id in matches))
        county_names = normalize_unit_list(list(dict.fromkeys(
            name for name in link_texts(str(row["raw_markup"]))
            if name not in prefecture_names and is_unit_name(name, allow_plain_city="县级市" in text or "县级" in text)
        )))
        old_units, new_units, change_description, unit_types, scope = structured_change(row)
        old_units = normalize_unit_list(old_units)
        new_units = normalize_unit_list(new_units)
        events.append({
            "event_id": row["row_id"],
            "year": row["year"],
            "section": row["section"],
            "event_type": event_type(str(row["section"]), text),
            "prefecture_names": "、".join(prefecture_names),
            "prefecture_entity_ids": "、".join(entity_ids),
            "county_names": "、".join(county_names),
            "old_county_units": "、".join(old_units),
            "new_county_units": "、".join(new_units),
            "change_description": change_description,
            "county_unit_types": "、".join(unit_types),
            "scope": scope,
            "description": text,
            "source_title": row["source_title"],
            "source_url": row["source_url"],
            "revision_id": row["revision_id"],
            "review_status": "wikipedia_row_loose_relation" if entity_ids else "wikipedia_row_unlinked",
        })
    return events


def write_type_summary(events: list[dict[str, object]]) -> None:
    counts = Counter(
        unit_type
        for row in events
        for unit_type in str(row.get("county_unit_types", "")).split("、")
        if unit_type
    )
    notes = {
        "市辖区": "ordinary county-level type",
        "县级市": "ordinary county-level type",
        "县": "ordinary county-level type",
        "自治县": "ordinary county-level type",
        "旗": "ordinary county-level type",
        "自治旗": "ordinary county-level type",
        "特区": "ordinary county-level type",
        "林区": "ordinary county-level type",
        "工农区": "historical legacy type retained when present",
        "开发区": "retained for provenance; outside ordinary county-level scope",
    }
    rows = [{
        "unit_type": unit_type,
        "ordinary_county_level": "true" if unit_type in COUNTY_UNIT_TYPES else "false",
        "event_count": counts.get(unit_type, 0),
        "note": notes[unit_type],
    } for unit_type in (*COUNTY_UNIT_TYPES, *HISTORICAL_UNIT_TYPES, *NON_COUNTY_TYPES)]
    write_csv(PROCESSED / "county_unit_type_coverage_1987_2026.csv", TYPE_SUMMARY_FIELDS, rows)


def main() -> None:
    inventory = read_csv(PROCESSED / "wikipedia_change_pages.csv")
    names = entity_name_index()
    if "--from-cached-rows" in sys.argv:
        raw_rows = read_csv(PROCESSED / "wikipedia_county_change_rows.csv")
        events = normalize_events(raw_rows, names)
        write_csv(PROCESSED / "county_administrative_events_1987_2026.csv", EVENT_FIELDS, events)
        write_type_summary(events)
        print(f"cached raw_rows={len(raw_rows)} events={len(events)} linked={sum(bool(row['prefecture_entity_ids']) for row in events)}")
        return
    pages, raw_rows = [], []
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for page_index, page in enumerate(inventory, start=1):
        year, title = int(page["year"]), page["title"]
        parsed = api({"action": "parse", "page": title, "prop": "wikitext|revid"})["parse"]
        text = parsed["wikitext"]["*"]
        revision_id = parsed["revid"]
        page_url = page["page_url"]
        hs = headings(text)
        extracted = []
        table_number = 0
        for position, _end, table in table_ranges(text):
            table_number += 1
            path = heading_path(hs, position)
            headers, rows = parse_table(table)
            if not table_is_county_related(path, headers):
                continue
            section = " / ".join(path) or "未标注章节"
            header_text = " | ".join(headers)
            for parsed_row in rows:
                if parsed_row["row_kind"] == "header":
                    continue
                row_id = f"WIKI-COUNTY-{year}-{table_number:02d}-{parsed_row['row_number']:03d}"
                extracted.append({
                    "row_id": row_id,
                    "year": year,
                    "section": section,
                    "table_number": table_number,
                    "row_number": parsed_row["row_number"],
                    "row_kind": parsed_row["row_kind"],
                    "header_text": header_text,
                    "row_text": parsed_row["row_text"],
                    "cells_json": json.dumps(parsed_row["values"], ensure_ascii=False, separators=(",", ":")),
                    "raw_markup": " | ".join(parsed_row["raw_values"]),
                    "source_title": title,
                    "source_url": page_url,
                    "revision_id": revision_id,
                })
        raw_rows.extend(extracted)
        pages.append({"year": year, "title": title, "page_url": page_url, "revision_id": revision_id, "county_row_count": len(extracted), "checked_at_utc": checked})
        print(f"{page_index}/{len(inventory)} {year}: {len(extracted)} county rows", flush=True)
        time.sleep(1.2)

    events = normalize_events(raw_rows, names)
    write_csv(PROCESSED / "wikipedia_county_change_pages.csv", PAGE_FIELDS, pages)
    write_csv(PROCESSED / "wikipedia_county_change_rows.csv", RAW_FIELDS, raw_rows)
    write_csv(PROCESSED / "county_administrative_events_1987_2026.csv", EVENT_FIELDS, events)
    write_type_summary(events)
    print(f"pages={len(pages)} raw_rows={len(raw_rows)} events={len(events)} linked={sum(bool(row['prefecture_entity_ids']) for row in events)}")


if __name__ == "__main__":
    main()
