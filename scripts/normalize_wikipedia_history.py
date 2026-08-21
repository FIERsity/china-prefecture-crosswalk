#!/usr/bin/env python3
"""Conservatively normalize pre-2000 prefecture events from Wikipedia rows."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "wikipedia_prefecture_change_rows.csv"
OUTPUT = ROOT / "data" / "processed" / "wikipedia_normalized_events_1987_1999.csv"
ENTITIES = ROOT / "data" / "processed" / "entities.csv"
NAMES = ROOT / "data" / "processed" / "entity_names.csv"
PROVINCE_RE = re.compile(r"(?:colspan=\"?\d+\"?\|)?(北京市|天津市|上海市|重庆市|[^|]{2,12}(?:省|自治区))$")
DOC_RE = re.compile(r"(?:国函|民行批|民批|中发|中办厅字)〔?\d{4}〕?\d+号")
DATE_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日")
# Row-text fixes: some 1993 Hebei rows lost the leading 撤 character during
# table extraction ("销张家口地区" instead of "撤销张家口地区").
MISSING_ABOLISH_RE = re.compile(r"\|销([一-龥]{2,12}(?:地区|盟))，")
# "X与Y合并，组建新的Z" / "X和Y合并，组建新的Z（地级）" merge sentence forms.
MERGE_COMBINE_RE = re.compile(
    r"([一-龥·]{2,16}(?:地区|盟|自治州|市))[与和]([一-龥·]{2,16}(?:地区|盟|自治州|市))合并[，,]组建新的([一-龥·]{2,16}市)"
)
MERGE_ABOLISH_RE = re.compile(r"撤销([一-龥·]{2,16}(?:地区|盟))[，,](?:实行地、市合并|与[一-龥·]{2,16}市合并)")
HISTORICAL = ROOT / "data" / "processed" / "historical_entities.csv"
# Robust to event-id shifts: keyed by (year, description fragment) instead of
# the generated event id.
MANUAL_NAMES_BY_TEXT = {
    (1996, "三峡库区移民"): ("涪陵市、万县市、黔江地区", "重庆市"),
}
# Events that have no Wikipedia change-page row at all; sourced separately.
SUPPLEMENTAL_EVENTS = [
    {
        "year": 1989, "event_type": "upgrade", "old": "日照市", "new": "日照市",
        "entity_id": "E371100", "province": "山东省",
        "approval_date": "1989-06-12", "document_number": "国函〔1989〕43号",
        "automatic_continuity": "true", "confidence": "high",
        "normalization_status": "accepted_manual_review",
        "review_note": "1989-06-12 国务院批复日照市由县级市升为地级市（国函〔1989〕43号），行政区域、人员编制不变；1989-11-05 正式对外办公。日照县撤县设市为1985年（85国函字43号，县级）。",
        "risk_flags": "supplemental_event",
        "description": "国务院关于山东省日照市升为地级市的批复（1989年6月12日，国函〔1989〕43号）：同意日照市升为地级市，其行政区域不变，不增加人员编制。",
        "source_url": "https://zh.wikisource.org/wiki/国务院关于山东省日照市升为地级市的批复",
        "source_section": "山东省",
    },
    {
        "year": 1991, "event_type": "upgrade", "old": "潮州市", "new": "潮州市",
        "entity_id": "E445100", "province": "广东省",
        "approval_date": "1991-12-07", "document_number": "国函〔1991〕84号",
        "automatic_continuity": "true", "confidence": "high",
        "normalization_status": "accepted_manual_review",
        "review_note": "1991-12-07 国务院批复调整汕头、潮州两市行政区划（国函〔1991〕84号）：潮州市升格为地级市，设立潮州市湘桥区、潮安县，将潮安县和原汕头市的饶平县划归潮州市管辖。",
        "risk_flags": "supplemental_event",
        "description": "国务院关于广东省调整汕头潮州两市行政区划的批复（1991年12月7日，国函〔1991〕84号）：同意潮州市升格为地级市，设立潮州市湘桥区；设立潮安县，与原汕头市的饶平县一并划归潮州市管辖。",
        "source_url": "http://www.jieyang.gov.cn/zwgk/jcxxgk/zfgb/1992nian/jyzbdyq/zz/content/post_725314.html",
        "source_section": "广东省",
    },
    {
        "year": 1991, "event_type": "establish", "old": "揭阳县", "new": "揭阳市",
        "entity_id": "E445200", "province": "广东省",
        "approval_date": "1991-12-07", "document_number": "国函〔1991〕84号",
        "automatic_continuity": "false", "confidence": "high",
        "normalization_status": "accepted_manual_review",
        "review_note": "1991-12-07 国务院批复（国函〔1991〕84号）：撤销揭阳县，设立揭阳市（地级），设立揭阳市榕城区、揭东县，将揭东县和原汕头市的揭西、普宁、惠来四县划归揭阳市管辖。",
        "risk_flags": "supplemental_event",
        "description": "国务院关于广东省调整汕头潮州两市行政区划的批复（1991年12月7日，国函〔1991〕84号）：撤销揭阳县，设立揭阳市（地级），设立揭阳市榕城区；设立揭东县，与原汕头市的揭西、普宁、惠来三县一并划归揭阳市管辖。",
        "source_url": "http://www.jieyang.gov.cn/zwgk/jcxxgk/zfgb/1992nian/jyzbdyq/zz/content/post_725314.html",
        "source_section": "广东省",
    },
    {
        "year": 1997, "event_type": "abolish", "old": "万县市、涪陵市、黔江地区", "new": "万县区、涪陵区、黔江开发区",
        "entity_id": "HIST-CQ-QIANJIANG", "province": "重庆市",
        "approval_date": "1997-12-20", "document_number": "中办厅字〔1997〕34号",
        "automatic_continuity": "false", "confidence": "medium",
        "normalization_status": "accepted_manual_review",
        "review_note": "中办厅字〔1997〕34号批复（1997-12-20）：撤销万县市设立重庆市万县区（1998年5月更名万州区）、撤销涪陵市设立涪陵区、撤销黔江地区设立黔江开发区（2000年6月改设黔江区）。1996年三地已由重庆市代管（见1996年划转事件）。",
        "risk_flags": "supplemental_event|multi_entity_relation",
        "description": "中共中央办公厅、国务院办公厅关于万县市、涪陵市、黔江地区行政体制调整的批复（1997年12月20日，中办厅字〔1997〕34号）：撤销万县市，设立重庆市万县区；撤销涪陵市，设立重庆市涪陵区；撤销黔江地区，设立重庆市黔江开发区。",
        "source_url": "https://zh.wikisource.org/wiki/中共中央办公厅、国务院办公厅关于万县市、涪陵市、黔江地区行政体制调整的批复",
        "source_section": "重庆市",
    },
    {
        "year": 1997, "event_type": "upgrade", "old": "重庆市", "new": "重庆市",
        "entity_id": "E500100", "province": "重庆市",
        "approval_date": "1997-03-14", "document_number": "全国人大决定",
        "automatic_continuity": "true", "confidence": "high",
        "normalization_status": "accepted_manual_review",
        "review_note": "1997年3月14日八届全国人大五次会议批准设立重庆直辖市，1997年6月18日挂牌。重庆市由四川省辖计划单列市升格为直辖市，研究实体连续；万县市、涪陵市、黔江地区于1996年划归重庆代管（见1996年划转事件）。",
        "risk_flags": "supplemental_event",
        "description": "设立重庆直辖市（1997年3月14日八届全国人大五次会议批准）：重庆市由四川省计划单列市升格为直辖市，原万县市、涪陵市、黔江地区改由重庆市管辖。",
        "source_url": "https://zh.wikipedia.org/wiki/重庆直辖市",
        "source_section": "重庆市",
    },
]
MANUAL_ENTITY_LINKS = {
    (1988, "安庆地区"): ("CNUR-000348", "安庆地区与既有安庆市合并并析设池州地区"),
    (1988, "池州地区"): ("E341700", "池州地区 later continued as the Chizhou research entity"),
    (1988, "建阳地区"): ("E350700", "建阳地区 renamed 南平地区 and later became 南平市"),
    (1992, "宜昌地区"): ("CNUR-000349", "宜昌地区 merged into the existing 宜昌市"),
    (1992, "惠民地区"): ("E371600", "惠民地区 renamed 滨州地区 and later became 滨州市"),
    (1993, "石家庄地区"): ("CNUR-000350", "石家庄地区 merged into 石家庄市"),
    (1993, "张家口地区"): ("HIST-HE-ZHANGJIAKOU", "1993年河北地市合并：撤销张家口地区并入张家口市（国函〔1993〕89号）"),
    (1993, "沧州地区"): ("HIST-HE-CANGZHOU", "1993年河北地市合并：撤销沧州地区并入沧州市（国函〔1993〕89号）"),
    (1993, "邯郸地区"): ("HIST-HE-HANDAN", "1993年河北地市合并：撤销邯郸地区并入邯郸市（国函〔1993〕89号）"),
    (1993, "邢台地区"): ("HIST-HE-XINGTAI", "1993年河北地市合并：撤销邢台地区并入邢台市（国函〔1993〕89号）"),
    (1993, "承德地区"): ("HIST-HE-CHENGDE", "1993年河北地市合并：撤销承德地区并入承德市（国函〔1993〕89号）"),
    (1994, "保定地区"): ("HIST-HE-BAODING", "1994年保定地市合并：保定地区与保定市合并组建新的地级保定市（国函〔1994〕133号）"),
    (1994, "郧阳地区"): ("CNUR-000357", "郧阳地区 merged into 十堰市"),
    (1994, "沙市市"): ("CNUR-000358", "荆州地区 and 沙市市 merged into the new 荆沙市"),
    (1996, "松花江地区"): ("HIST-HLJ-SONGHUAJIANG", "1996年松花江地区与哈尔滨市合并（国函〔1996〕64号）"),
    (1997, "眉山地区"): ("E511400", "眉山地区 later became 眉山市"),
    (1998, "桂林地区"): ("HIST-GX-GUILIN", "1998年桂林市和桂林地区合并组建新的桂林市（国函〔1998〕73号）"),
    (1998, "资阳地区"): ("E512000", "资阳地区 later became 资阳市"),
}
MANUAL_ACCEPT_EVENTS = {
    (1988, "朔州市"): "朔州市 was explicitly established as a prefecture-level city",
    (1988, "汕尾市"): "汕尾市 was explicitly established as a prefecture-level city",
    (1988, "河源市"): "河源市 was explicitly established as a prefecture-level city",
    (1988, "阳江市"): "阳江市 was explicitly established as a prefecture-level city",
    (1988, "清远市"): "清远市 was explicitly established as a prefecture-level city",
    (1988, "安庆地区"): "安庆地区 and the existing city were merged into the unified 安庆市",
    (1992, "松原市"): "松原市 was explicitly established as a prefecture-level city",
    (1993, "孝感市"): "孝感市 was explicitly established as a prefecture-level city",
    (1993, "防城港市"): "防城港市 was explicitly established as a prefecture-level city",
    (1994, "郴州市"): "郴州市 was explicitly established as a prefecture-level city",
}
MANUAL_HISTORICAL_LINKS = {
    (1987, "海南黎族苗族自治州"): ("HIST-HN-LMZ", "abolished historical autonomous prefecture; former counties moved to direct Hainan Administrative Region control"),
    (1992, "万县地区"): ("HIST-CQ-WANXIAN", "Wanxian Prefecture continued as the historical prefecture-level Wanxian City until 1997"),
    (1993, "雁北地区"): ("HIST-SX-YANBEI", "Yanbei was abolished and split between Datong and Shuozhou"),
    (1995, "涪陵地区"): ("HIST-CQ-FULING", "Fuling Prefecture continued as historical prefecture-level Fuling City until 1997"),
    (1996, "黔江地区"): ("HIST-CQ-QIANJIANG", "multi-entity transition: Wanxian City, Fuling City, and Qianjiang Prefecture were entrusted to Chongqing administration"),
}
MANUAL_SPLIT_EVENTS = {
    (1988, "惠阳地区"): ("CNUR-000347", "惠阳地区撤销并形成惠州、汕尾、河源三个主要后继实体"),
    (1997, "梧州地区"): ("CNUR-000363", "梧州地区主要分为贺州地区并将三县市划归既有梧州市"),
}
MANUAL_MERGE_EVENTS = {
    (1994, "沙市市"): ("CNUR-000358", "荆州地区与原地级沙市市共同组建新的荆沙市"),
}


def read() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def event_type(section: str, text: str) -> str:
    if "更名" in section and "更名" in text:
        return "rename"
    if "撤销" in text and re.search(r"(?:地区|盟).{0,20}设立.{0,12}(?:地级|市（地级）)", text):
        return "upgrade"
    if ("合并" in section or "地市合并" in text) and "合并" in text:
        return "merge"
    if "撤销地级市" in text and "设立市辖区" in text:
        return "abolish"
    if re.search(r"(?:升为|设立).{0,12}(?:地级市|市（地级）)", text):
        return "establish"
    if "撤销" in text and re.search(r"(?:自治州|地区|地级市)", text):
        return "abolish"
    if "地区的增设" in section and "设立" in text and "地区" in text:
        return "establish_prefecture"
    if "驻地" in section and ("迁" in text or "更名" in text):
        return "seat_or_name_change"
    if "代管" in section and "代管" in text:
        return "jurisdiction_transfer"
    return ""


def extract_names(kind: str, text: str) -> tuple[str, str]:
    old = new = ""
    if kind == "rename":
        match = re.search(r"([\u4e00-\u9fff·]{2,20}(?:地区|盟|自治州|市))更名为([\u4e00-\u9fff·]{2,20}(?:地区|盟|自治州|市))", text)
        if match: old, new = match.groups()
    elif kind == "merge":
        match = MERGE_COMBINE_RE.search(text)
        if match:
            first, second, new = match.groups()
            old = first if first.endswith(("地区", "盟")) else second
            return old, new.removeprefix("地级")
        match = MERGE_ABOLISH_RE.search(text)
        if match:
            old = match.group(1)
            return old, old[:-2] + "市"
        # Fall through to the generic region/city extraction below when the
        # merge sentence has an unusual form (e.g. "撤销郧阳地区，将…划归…市").
    if kind != "rename":
        match = re.search(r"撤销(?:[^，|]{0,8}?省)?([\u4e00-\u9fff·]{2,16}(?:地区|盟|自治州|地级市))", text)
        if match: old = match.group(1).removeprefix("地级")
        match = re.search(r"设立(?:地级)?([\u4e00-\u9fff·]{2,12}市)(?:（地级）)?", text)
        if match: new = match.group(1)
        if kind == "establish_prefecture":
            match = re.search(r"设立([\u4e00-\u9fff·]{2,16}地区)", text)
            if match: new = match.group(1)
    return old, new


def main() -> None:
    with ENTITIES.open(encoding="utf-8", newline="") as handle:
        entities = {row["entity_id"]: row for row in csv.DictReader(handle)}
    name_to_entities: dict[str, set[str]] = {}
    with NAMES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["name_zh"]:
                name_to_entities.setdefault(row["name_zh"], set()).add(row["entity_id"])
    for entity_id, entity in entities.items():
        name_to_entities.setdefault(entity["canonical_name_zh"], set()).add(entity_id)
    # Historical entities (legacy HIST-* ids; migrated to CNUR later).
    with HISTORICAL.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            legacy = row.get("legacy_entity_id") or row["historical_entity_id"]
            if row["canonical_name_zh"]:
                name_to_entities.setdefault(row["canonical_name_zh"], set()).add(legacy)
    output, province_by_year = [], {}
    for row in read():
        year = int(row["year"])
        if year >= 2000:
            continue
        text = MISSING_ABOLISH_RE.sub(r"|撤销\1，", row["row_text"])
        section = row["section"]
        province_match = PROVINCE_RE.search(text)
        if province_match and "撤销" not in text and "设立" not in text:
            province_by_year[year] = province_match.group(1)
            continue
        kind = event_type(section, text)
        if not kind:
            continue
        old_name, new_name = extract_names(kind, text)
        old_name = old_name.removeprefix("将")
        new_name = new_name.removeprefix("新的")
        province = province_by_year.get(year, "")
        if province and old_name.startswith(province): old_name = old_name[len(province):]
        if province and new_name.startswith(province): new_name = new_name[len(province):]
        for (manual_year, fragment), (old_fix, new_fix) in MANUAL_NAMES_BY_TEXT.items():
            if manual_year == year and fragment in text:
                old_name, new_name = old_fix, new_fix
        if old_name and new_name and kind in {"establish", "abolish"} and old_name.endswith(("地区", "盟")):
            kind = "upgrade"
        # Require a prefecture-level semantic payload, not a subordinate county row.
        if not (old_name or new_name or kind in {"seat_or_name_change", "jurisdiction_transfer"}) or (kind == "abolish" and not old_name):
            continue
        date_match = DATE_RE.search(text)
        date_text = ""
        if date_match:
            date_text = f"{date_match.group(1) or year}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        doc = DOC_RE.search(text)
        entity_candidates = name_to_entities.get(new_name, set()) | name_to_entities.get(old_name, set())
        entity_id = next(iter(entity_candidates)) if len(entity_candidates) == 1 else ""
        if entity_id:
            if entity_id in entities: province = entities[entity_id]["province_name_zh"]
        risks = []
        if doc:
            doc_year = re.search(r"\d{4}", doc.group(0))
            if doc_year and int(doc_year.group(0)) != year:
                risks.append("document_year_differs_from_page_year")
        if not entity_id: risks.append("entity_unresolved")
        automatic = kind in {"rename", "upgrade"} and bool(old_name and new_name)
        event_id = f"WIKI-{year}-{len(output)+1:03d}"
        review_note = ""
        for (manual_year, fragment), (entity_value, note) in MANUAL_ENTITY_LINKS.items():
            if manual_year == year and fragment in text:
                entity_id, review_note = entity_value, note
                if entity_id in entities: province = entities[entity_id]["province_name_zh"]
                risks = [risk for risk in risks if risk != "entity_unresolved"]
        for (manual_year, fragment), note in MANUAL_ACCEPT_EVENTS.items():
            if manual_year == year and fragment in text:
                review_note = note
        for (manual_year, fragment), (entity_value, note) in MANUAL_HISTORICAL_LINKS.items():
            if manual_year == year and fragment in text:
                entity_id, review_note = entity_value, note
                risks = [risk for risk in risks if risk != "entity_unresolved"]
                if (manual_year, fragment) in {(1993, "雁北地区"), (1996, "黔江地区")}: risks.append("multi_entity_relation")
        for (manual_year, fragment), (entity_value, note) in MANUAL_SPLIT_EVENTS.items():
            if manual_year == year and fragment in text:
                entity_id, review_note = entity_value, note
                kind, automatic = "split", False
                risks = [risk for risk in risks if risk != "entity_unresolved"] + ["multi_entity_relation"]
        for (manual_year, fragment), (entity_value, note) in MANUAL_MERGE_EVENTS.items():
            if manual_year == year and fragment in text:
                entity_id, review_note = entity_value, note
                kind, automatic = "merge", False
                risks = [risk for risk in risks if risk != "entity_unresolved"] + ["multi_entity_relation"]
        status = "accepted_manual_review" if review_note else "accepted_rule_extraction" if entity_id and old_name and new_name and kind in {"rename", "upgrade"} else "review_required"
        output.append({
            "event_id": event_id, "year": year,
            "province_name": province, "event_type": kind, "entity_id": entity_id,
            "old_prefecture_name": old_name, "new_prefecture_name": new_name,
            "approval_date": date_text, "document_number": doc.group(0) if doc else "",
            "automatic_continuity": str(automatic).lower(),
            "confidence": "high" if old_name and new_name and kind in {"rename", "upgrade"} else "medium",
            "normalization_status": status, "review_note": review_note,
            "risk_flags": "|".join(risks),
            "description": text, "source_section": section, "source_url": row["source_url"],
            "revision_id": row["revision_id"], "source_row_number": row["row_number"],
        })
    for supp in SUPPLEMENTAL_EVENTS:
        year = supp["year"]
        suffixes = [int(e["event_id"].rsplit("-", 1)[1]) for e in output if int(e["year"]) == year]
        event_id = f"WIKI-{year}-{max(suffixes, default=0)+1:03d}"
        output.append({
            "event_id": event_id, "year": year, "province_name": supp["province"],
            "event_type": supp["event_type"], "entity_id": supp["entity_id"],
            "old_prefecture_name": supp["old"], "new_prefecture_name": supp["new"],
            "approval_date": supp["approval_date"], "document_number": supp["document_number"],
            "automatic_continuity": supp["automatic_continuity"], "confidence": supp["confidence"],
            "normalization_status": supp["normalization_status"], "review_note": supp["review_note"],
            "risk_flags": supp["risk_flags"], "description": supp["description"],
            "source_section": supp["source_section"], "source_url": supp["source_url"],
            "revision_id": "", "source_row_number": "",
        })
    output.sort(key=lambda item: (int(item["year"]), item["event_id"]))
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    print(f"normalized={len(output)} years={min(r['year'] for r in output)}-{max(r['year'] for r in output)}")


if __name__ == "__main__":
    main()
