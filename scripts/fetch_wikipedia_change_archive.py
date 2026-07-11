#!/usr/bin/env python3
"""Fetch all available Chinese Wikipedia prefecture-change year pages."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
API = "https://zh.wikipedia.org/w/api.php"
UA = "china-prefecture-crosswalk/0.2 (https://github.com/FIERsity/china-prefecture-crosswalk)"
TITLE_RE = re.compile(r"^(\d{4})年中华人民共和国县级以上行政区划变更列表$")


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({"format": "json", **params})
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def discover_titles() -> list[str]:
    results, offset = [], 0
    while True:
        data = api({"action": "query", "list": "search", "srsearch": "intitle:中华人民共和国县级以上行政区划变更列表", "srnamespace": 0, "srlimit": 500, "sroffset": offset})
        results.extend(item["title"] for item in data["query"]["search"] if TITLE_RE.match(item["title"]))
        if "continue" not in data:
            break
        offset = data["continue"]["sroffset"]
    return sorted(set(results), key=lambda title: int(TITLE_RE.match(title).group(1)))


def clean_wikitext(text: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", text, flags=re.S)
    text = re.sub(r"\{\{notetag\|.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip(" |!\n\t")


def section_rows(wikitext: str, year: int, title: str, page_url: str, revision_id: int) -> list[dict]:
    headings = list(re.finditer(r"(?m)^(={2,6})\s*(.*?)\s*\1\s*$", wikitext))
    targets = [item for item in headings if "地级" in clean_wikitext(item.group(2))]
    rows, seen = [], set()
    for target in targets:
        level = len(target.group(1)); section = clean_wikitext(target.group(2))
        end = len(wikitext)
        for candidate in headings:
            if candidate.start() > target.start() and len(candidate.group(1)) <= level:
                end = candidate.start(); break
        section_text = wikitext[target.end():end]
        for block in re.split(r"(?m)^\|-\s*$", section_text):
            subheading = re.search(r"(?m)^===+\s*(.*?)\s*===+\s*$", block)
            if subheading:
                section = clean_wikitext(subheading.group(1))
            lines = [line for line in block.splitlines() if line.startswith(("|", "!")) and not line.startswith(("{|", "|}"))]
            text = clean_wikitext(" ".join(lines))
            key = (section, text)
            if text and key not in seen and not ("原行政单位" in text and "新行政建制" in text):
                seen.add(key)
                rows.append({"year": year, "section": section, "row_number": len(rows) + 1, "row_text": text, "source_title": title, "source_url": page_url, "revision_id": revision_id})
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pages, rows = [], []
    for title in discover_titles():
        year = int(TITLE_RE.match(title).group(1))
        data = api({"action": "parse", "page": title, "prop": "wikitext|revid|displaytitle"})["parse"]
        url = "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        extracted = section_rows(data["wikitext"]["*"], year, title, url, data["revid"])
        pages.append({"year": year, "title": title, "page_url": url, "revision_id": data["revid"], "prefecture_row_count": len(extracted), "checked_at_utc": checked})
        rows.extend(extracted)
        print(year, len(extracted))
        time.sleep(0.1)
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "wikipedia_change_pages.csv", pages)
    write(OUT / "wikipedia_prefecture_change_rows.csv", rows)
    print(f"pages={len(pages)} rows={len(rows)} years={pages[0]['year']}-{pages[-1]['year']}")


if __name__ == "__main__":
    main()
