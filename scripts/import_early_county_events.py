#!/usr/bin/env python3
"""Import county-level changes from the early People's Daily archive.

The 1983-1986 Wikipedia annual pages used by the main pipeline do not exist.
This importer keeps the source pages as a small raw cache and emits one
descriptive event per published item.  It deliberately does not pretend to
construct a complete county genealogy: parent prefectures are linked only
when the source text names one or when a reviewed override is present.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "early_admin_change_sources"

EVENT_FIELDS = [
    "event_id", "year", "section", "event_type", "prefecture_names",
    "prefecture_entity_ids", "county_names", "old_county_units",
    "new_county_units", "change_description", "county_unit_types", "scope",
    "description", "source_title", "source_url", "source_id", "source_type",
    "source_locator", "source_confidence", "review_status",
]

SOURCES = [
    {
        "source_id": "SRC-RMRB-1983-10-28",
        "year": 1983,
        "period": "1983-01—1983-09",
        "title": "今年1至3季度全国县级以上行政区划变动情况",
        "url": "https://cn.govopendata.com/renminribao/1983/10/28/4/",
        "locator": "人民日报 1983-10-28 第4版",
    },
    {
        "source_id": "SRC-RMRB-1984-01-31",
        "year": 1984,
        "period": "1984-07—1984-12",
        "title": "一九八四年下半年全国行政区划变更情况",
        "url": "https://cn.govopendata.com/renminribao/1985/1/31/4/",
        "locator": "人民日报 1985-01-31 第4版",
    },
    {
        "source_id": "SRC-RMRB-1985-09-12",
        "year": 1985,
        "period": "1985-01—1985-06",
        "title": "1985年上半年全国县级以上行政区划变更情况",
        "url": "https://cn.govopendata.com/renminribao/1985/9/12/4/",
        "locator": "人民日报 1985-09-12 第4版",
    },
    {
        "source_id": "SRC-RMRB-1986-01-26",
        "year": 1985,
        "period": "1985-07—1985-12",
        "title": "一九八五年下半年全国县级以上行政区划变更情况",
        "url": "https://cn.govopendata.com/renminribao/1986/01/26/4/",
        "locator": "人民日报 1986-01-26 第4版",
    },
    {
        "source_id": "SRC-RMRB-1986-07-18",
        "year": 1986,
        "period": "1986-01—1986-06",
        "title": "一九八六年上半年全国县级以上行政区划变更情况",
        "url": "https://cn.govopendata.com/renminribao/1986/7/18/4/",
        "locator": "人民日报 1986-07-18 第4版",
    },
]

# These are reviewed links where the report itself only says "陕西省" or
# another province.  They keep important county-city conversions visible on
# the relevant prefecture card without claiming a legal affiliation in that
# year.
PREFECTURE_OVERRIDES = {
    "韩城县": "渭南市",
    "韩城市": "渭南市",
}

UNIT_SUFFIXES = ("自治县", "自治旗", "县级市", "市", "县", "区", "旗", "林区", "特区")
PUNCTUATION = "，。、；：,.;:（）()“”‘’　 "
NUMBERED_ITEM = re.compile(r"(?P<marker>[一二三四五六七八九十百]+、)")


class ArticleParser(HTMLParser):
    def __init__(self, heading: str):
        super().__init__()
        self.heading = heading
        self.in_target = False
        self.in_body = False
        self.heading_text = ""
        self.body_parts: list[str] = []
        self._capture_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        classes = set((attrs_map.get("class") or "").split())
        if tag == "h2" and "content-heading" in classes:
            self.heading_text = ""
            self._capture_heading = True
        if tag == "div" and "content-body" in classes and self.in_target:
            self.in_body = True
            self.in_target = False

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self._capture_heading = False
            if self.heading_text.strip() == self.heading:
                self.in_target = True
        if tag == "div" and self.in_body:
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self._capture_heading:
            self.heading_text += data
        elif self.in_body:
            self.body_parts.append(data)


def fetch_source(source: dict[str, str], refresh: bool) -> str:
    target = RAW / f"{source['source_id']}.html"
    if target.exists() and not refresh:
        return target.read_text(encoding="utf-8")
    request = urllib.request.Request(source["url"], headers={"User-Agent": "china-prefecture-crosswalk/3.2"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read().decode("utf-8")
    RAW.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return content


def article_text(source: dict[str, str], refresh: bool) -> str:
    parser = ArticleParser(source["title"])
    parser.feed(fetch_source(source, refresh))
    if not parser.body_parts:
        raise RuntimeError(f"article not found: {source['url']}")
    text = html.unescape("".join(parser.body_parts))
    return re.sub(r"\s+", "", text).replace("第4版()专栏：", "")


def split_items(text: str) -> list[tuple[str, str]]:
    # Province headings are placed on their own line in the original layout,
    # but the HTML archive stores them as adjacent text.  Split at every known
    # provincial/municipal heading and retain the heading as section context.
    headings = [
        "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
        "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
        "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
        "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省",
        "宁夏回族自治区", "新疆维吾尔自治区",
    ]
    heading_re = re.compile("(" + "|".join(map(re.escape, sorted(headings, key=len, reverse=True))) + ")")
    pieces = heading_re.split(text)
    result: list[tuple[str, str]] = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if piece in headings:
            current = piece
            continue
        if not current:
            continue
        matches = list(NUMBERED_ITEM.finditer(piece))
        if not matches:
            result.append((current, piece.strip()))
            continue
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(piece)
            item = piece[start:end].strip(PUNCTUATION)
            if item:
                result.append((current, item))
    return result


def find_units(text: str) -> list[str]:
    # Keep this intentionally conservative.  It catches named county-level
    # units while avoiding province names and bare destination descriptions.
    matches = re.findall(r"[\u4e00-\u9fff]{1,18}?(?:自治县|自治旗|县级市|市|县|区|旗|林区|特区)", text)
    units = []
    for value in matches:
        value = value.strip(PUNCTUATION)
        while value and value[0] in "撤销将把设立恢复原属以为由及和的":
            value = value[1:]
        if any(token in value for token in ("行政", "区域", "并入", "划归", "管辖", "设立", "撤销", "原属")):
            continue
        if len(value) >= 2 and value not in units and not value.endswith(("省", "自治区")):
            units.append(value)
    return units


def classify(text: str) -> str:
    if "合并" in text or "并入" in text:
        return "merge"
    if "划归" in text or "管辖" in text or "领导" in text:
        return "jurisdiction_transfer"
    if "驻地" in text or "迁至" in text:
        return "residence_change"
    if "改为" in text or "更名" in text:
        return "rename"
    if "分设" in text or "划分" in text or "设立" in text:
        return "split"
    if "撤销" in text:
        return "abolish"
    return "county_change"


def field_units(text: str, event_type: str, units: list[str]) -> tuple[str, str]:
    # The published wording is retained in change_description.  These two
    # fields are search/display aids, not a claim of a fully normalized graph.
    old_units: list[str] = []
    new_units: list[str] = []
    patterns = [
        r"撤销([^，。；]+?)(?:，|；)设立([^，。；]+)",
        r"撤销([^，。；]+?)(?:，|；)将其行政区域并入([^，。；]+)",
        r"将([^，。；]+?)(?:划归|改为|更名为)([^，。；]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            old_units = find_units(match.group(1))
            new_units = find_units(match.group(2))
            break
    old_units = [unit for unit in old_units if not unit.endswith(("地区", "盟", "自治州"))]
    new_units = [unit for unit in new_units if not unit.endswith(("地区", "盟", "自治州"))]
    if not old_units and event_type in {"abolish", "merge", "rename", "jurisdiction_transfer"}:
        old_units = units[:1]
    if not new_units and event_type in {"split", "rename", "jurisdiction_transfer", "merge"}:
        new_units = units[1:2] if len(units) > 1 else []
    return "、".join(old_units), "、".join(new_units)


def prefecture_names(text: str, county_names: list[str], all_names: set[str]) -> list[str]:
    found = [name for name in all_names if name in text]
    for county in county_names:
        override = PREFECTURE_OVERRIDES.get(county)
        if override:
            found.append(override)
    return sorted(set(found), key=lambda value: (-len(value), value))


def load_prefecture_names() -> tuple[set[str], dict[str, set[str]]]:
    names: set[str] = set()
    ids: dict[str, set[str]] = {}
    with (PROCESSED / "entity_names_1987_2026.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("legal_status") == "active" and row.get("name_zh"):
                names.add(row["name_zh"])
                ids.setdefault(row["name_zh"], set()).add(row["entity_id"])
    return names, ids


def build(refresh: bool) -> list[dict[str, str]]:
    all_prefecture_names, prefecture_ids = load_prefecture_names()
    rows: list[dict[str, str]] = []
    for source in SOURCES:
        text = article_text(source, refresh)
        for index, (province, item) in enumerate(split_items(text), 1):
            units = find_units(item)
            event_type = classify(item)
            parents = prefecture_names(item, units, all_prefecture_names)
            county_units = [unit for unit in units if unit not in parents and not unit.endswith(("地区", "盟", "自治州"))]
            old_units, new_units = field_units(item, event_type, county_units)
            county_names = "、".join(county_units)
            rows.append({
                "event_id": f"RMRB-COUNTY-{source['source_id'].removeprefix('SRC-RMRB-')}-{index:03d}",
                "year": str(source["year"]),
                "section": f"{province} / {source['period']}",
                "event_type": event_type,
                "prefecture_names": "、".join(parents),
                "prefecture_entity_ids": "、".join(sorted({entity_id for name in parents for entity_id in prefecture_ids.get(name, set())})),
                "county_names": county_names,
                "old_county_units": old_units,
                "new_county_units": new_units,
                "change_description": item,
                "county_unit_types": "、".join(sorted({next((suffix for suffix in UNIT_SUFFIXES if unit.endswith(suffix)), "") for unit in county_units if unit})),
                "scope": "county_level",
                "description": f"{province}：{item}",
                "source_title": source["title"],
                "source_url": source["url"],
                "source_id": source["source_id"],
                "source_type": "people_daily_summary",
                "source_locator": source["locator"],
                "source_confidence": "primary_text",
                "review_status": "source_text_parsed_review_required",
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="redownload the source pages")
    args = parser.parse_args()
    rows = build(args.refresh)
    output = PROCESSED / "county_administrative_events_1983_1986.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} sources={len(SOURCES)} output={output}")


if __name__ == "__main__":
    main()
