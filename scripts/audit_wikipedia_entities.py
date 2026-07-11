#!/usr/bin/env python3
"""Audit every research entity against Chinese Wikipedia page metadata."""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "data" / "processed" / "entities.csv"
OUTPUT = ROOT / "data" / "audit" / "wikipedia_entity_audit.csv"
API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "china-prefecture-crosswalk/0.1 (https://github.com/FIERsity/china-prefecture-crosswalk)"
MUNICIPALITIES = {"北京市", "天津市", "上海市", "重庆市"}
TITLE_OVERRIDES = {
    "E220600": "白山市 (吉林省)",
    "E220700": "松原市 (吉林省)",
    "E341400": "巢湖市 (地级市)",
}
LEVEL_MARKERS = ("地级市", "地级行政区", "中国自治州", "自治区的盟", "地区 (地级行政区)")
WIKIDATA_LEVEL_CLASSES = {"Q748149", "Q788104", "Q288653", "Q1065118"}


def query(titles: list[str]) -> dict:
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "prop": "categories|info|extracts|pageprops",
        "exintro": 1,
        "explaintext": 1,
        "cllimit": "max",
        "inprop": "url",
        "redirects": 1,
        "titles": "|".join(titles),
    })
    request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def query_wikidata(ids: list[str]) -> dict:
    params = urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "ids": "|".join(ids), "props": "claims"})
    request = urllib.request.Request(f"{WIKIDATA_API}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response).get("entities", {})


def main() -> None:
    with ENTITIES.open(encoding="utf-8", newline="") as handle:
        entities = list(csv.DictReader(handle))
    rows = []
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pages_by_query = {}
    for offset in range(0, len(entities), 40):
        batch = entities[offset:offset + 40]
        requested = [TITLE_OVERRIDES.get(entity["entity_id"], entity["canonical_name_zh"]) for entity in batch]
        try:
            payload = query(requested)
            normalized = {item["from"]: item["to"] for item in payload.get("query", {}).get("normalized", [])}
            redirects = {item["from"]: item["to"] for item in payload.get("query", {}).get("redirects", [])}
            pages = {page.get("title", ""): page for page in payload["query"]["pages"].values()}
            for title in requested:
                resolved = redirects.get(normalized.get(title, title), normalized.get(title, title))
                pages_by_query[title] = pages.get(resolved, {"title": resolved, "missing": True})
        except Exception as exc:
            for title in requested:
                pages_by_query[title] = {"title": title, "request_error": f"{type(exc).__name__}: {exc}"}
        print(f"fetched {min(offset + 40, len(entities))}/{len(entities)}")
        time.sleep(0.1)

    qids = sorted({page.get("pageprops", {}).get("wikibase_item") for page in pages_by_query.values()} - {None})
    wikidata = {}
    for offset in range(0, len(qids), 40):
        wikidata.update(query_wikidata(qids[offset:offset + 40]))

    for entity in entities:
        title = TITLE_OVERRIDES.get(entity["entity_id"], entity["canonical_name_zh"])
        page = pages_by_query[title]
        try:
            if "request_error" in page:
                raise RuntimeError(page["request_error"])
            categories = [item["title"].removeprefix("Category:") for item in page.get("categories", [])]
            matched = [category for category in categories if any(marker in category for marker in LEVEL_MARKERS)]
            intro = page.get("extract", "")
            intro_markers = [marker for marker in ("地级市", "地级行政区", "自治州", "地区", "盟") if marker in intro[:600]]
            wikidata_id = page.get("pageprops", {}).get("wikibase_item", "")
            claims = wikidata.get(wikidata_id, {}).get("claims", {}).get("P31", [])
            instance_ids = [claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "") for claim in claims]
            matched_classes = sorted(set(instance_ids) & WIKIDATA_LEVEL_CLASSES)
            exists = "missing" not in page
            level_verified = exists and (bool(matched) or bool(intro_markers) or bool(matched_classes) or title in MUNICIPALITIES)
            rows.append({
                "entity_id": entity["entity_id"],
                "query_title": title,
                "resolved_title": page.get("title", ""),
                "page_exists": str(exists).lower(),
                "level_verified": str(level_verified).lower(),
                "matched_categories": " | ".join(matched),
                "matched_intro_terms": " | ".join(intro_markers),
                "wikidata_id": wikidata_id,
                "matched_instance_classes": " | ".join(matched_classes),
                "page_id": page.get("pageid", ""),
                "revision_id": page.get("lastrevid", ""),
                "page_url": page.get("canonicalurl", ""),
                "checked_at_utc": checked_at,
                "review_status": "verified" if level_verified else "manual_review",
                "review_note": "municipality rule" if title in MUNICIPALITIES else "category evidence" if matched else "intro evidence" if intro_markers else "wikidata instance evidence" if matched_classes else "no prefecture-level evidence matched",
            })
        except Exception as exc:
            rows.append({
                "entity_id": entity["entity_id"], "query_title": title, "resolved_title": "",
                "page_exists": "", "level_verified": "", "matched_categories": "", "matched_intro_terms": "", "wikidata_id": "", "matched_instance_classes": "", "page_id": "",
                "revision_id": "", "page_url": "", "checked_at_utc": checked_at,
                "review_status": "request_error", "review_note": f"{type(exc).__name__}: {exc}",
            })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(OUTPUT)


if __name__ == "__main__":
    main()
