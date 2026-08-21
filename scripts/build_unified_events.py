#!/usr/bin/env python3
"""Combine all normalized prefecture events into one 1987-2026 schema."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTPUT = DATA / "unified_events_1987_2026.csv"
RELATIONS_OUTPUT = DATA / "unified_event_relations.csv"
TYPE_MAP = {
    "地区改设地级市": "upgrade", "盟改设地级市": "upgrade",
    "县级市升格为地级市": "upgrade", "地级市更名": "rename",
    "以县新设地级市": "establish", "撤销办事处并新设地级市": "establish",
    "撤销地区并将辖区划归自治州": "abolish", "撤销地级市并分拆辖区": "split",
    "撤销地级市并整体并入另一地级市": "merge",
}


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    historical = read("wikipedia_normalized_events_1987_1999.csv")
    current = read("events_2000_2026.csv")
    links = {row["event_id"]: row["entity_id"] for row in read("event_entity_links.csv")}
    entities = {row["entity_id"]: row for row in read("entities.csv")}
    historical_entities = {row["historical_entity_id"]: row for row in read("historical_entities.csv")}
    rows = []
    for row in historical:
        rows.append({
            "event_id": row["event_id"], "year": row["year"], "province_name": row["province_name"],
            "event_type": row["event_type"], "entity_id": row["entity_id"],
            "old_prefecture_name": row["old_prefecture_name"], "new_prefecture_name": row["new_prefecture_name"],
            "approval_date": row["approval_date"], "document_number": row["document_number"],
            "automatic_continuity": row["automatic_continuity"], "confidence": row["confidence"],
            "review_status": row["normalization_status"], "risk_flags": row["risk_flags"],
            "description": row["description"], "review_note": row["review_note"],
            "source_url": row["source_url"], "source_revision_id": row["revision_id"],
            "source_locator": f"row:{row['source_row_number']}", "source_layer": "wikipedia_semantic_normalization",
        })
    for row in current:
        entity_id = links[row["事件ID"]]
        relation_type = TYPE_MAP[row["事件类型"]]
        if row["事件ID"] == "PL-2002-009":
            entity_id, relation_type = "CNUR-000346", "split"
        if row["事件ID"] == "PL-2002-008":
            entity_id, relation_type = "CNUR-000362", "split"
        risks = []
        if relation_type in {"merge", "split"}: risks.append(f"{relation_type}_event")
        if row["年份"] == "2018" and row["事件ID"] == "PL-2018-001": risks.append("publication_year_differs")
        rows.append({
            "event_id": row["事件ID"], "year": row["年份"], "province_name": row["省级单位"],
            "event_type": relation_type, "entity_id": entity_id,
            "old_prefecture_name": row["原单位"], "new_prefecture_name": row["新单位"],
            "approval_date": row["批准日期"], "document_number": row["批复文号"],
            "automatic_continuity": "true" if relation_type in {"rename", "upgrade"} else "false",
            "confidence": "high" if row["置信度"] == "高" else "medium",
            "review_status": "accepted_reviewed", "risk_flags": "|".join(risks),
            "description": row["处理凭证（释义）"], "review_note": row["判定备注"],
            "source_url": row["来源URL"], "source_revision_id": "",
            "source_locator": row["网页行号凭证"], "source_layer": "reviewed_event_workbook",
        })
    rows.sort(key=lambda item: (int(item["year"]), item["event_id"]))
    # Reconcile province from the linked entity, preserving explicit historical scope in notes.
    for row in rows:
        if row["entity_id"] and row["entity_id"] in entities:
            expected = entities[row["entity_id"]]["province_name_zh"]
            if row["province_name"] and row["province_name"] != expected:
                row["risk_flags"] = "|".join(filter(None, [row["risk_flags"], "historical_province_differs_from_current_entity"]));
            elif not row["province_name"]:
                row["province_name"] = expected
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    relations = []
    for row in rows:
        if row["entity_id"]:
            relations.append({"event_id": row["event_id"], "from_entity_id": row["entity_id"], "to_entity_id": row["entity_id"] if row["automatic_continuity"] == "true" else "", "relation_type": row["event_type"], "mapping_quality": "exact" if row["automatic_continuity"] == "true" else "event_only", "automatic_mapping": row["automatic_continuity"], "review_note": row["review_note"]})
    # Explicit non-1:1 relationships found during final network review.
    # Event ids are resolved from (year, description fragment) so that
    # inserting earlier events never breaks the relation graph.
    def eid(year: int, fragment: str) -> str:
        for row in rows:
            if int(row["year"]) == year and fragment in row["description"]:
                return row["event_id"]
        raise KeyError(f"relation target not found: {year} {fragment}")

    def rel(year: int, fragment: str, from_id: str, to_id: str, rtype: str, quality: str, note: str) -> dict:
        return {"event_id": eid(year, fragment), "from_entity_id": from_id, "to_entity_id": to_id,
                "relation_type": rtype, "mapping_quality": quality, "automatic_mapping": "false", "review_note": note}

    relations.extend([
        rel(1993, "雁北地区", "HIST-SX-YANBEI", "E140200", "split", "disaggregate", "seven former Yanbei counties transferred to Datong"),
        rel(1993, "雁北地区", "HIST-SX-YANBEI", "E140600", "split", "disaggregate", "Huairen, Youyu, and Ying counties transferred to Shuozhou"),
        rel(1993, "张家口地区", "HIST-HE-ZHANGJIAKOU", "E130700", "merge", "aggregate", "1993年河北地市合并：张家口地区并入张家口市（国函〔1993〕89号）"),
        rel(1993, "沧州地区", "HIST-HE-CANGZHOU", "E130900", "merge", "aggregate", "1993年河北地市合并：沧州地区并入沧州市（国函〔1993〕89号）"),
        rel(1993, "邯郸地区", "HIST-HE-HANDAN", "E130400", "merge", "aggregate", "1993年河北地市合并：邯郸地区并入邯郸市（国函〔1993〕89号）"),
        rel(1993, "邢台地区", "HIST-HE-XINGTAI", "E130500", "merge", "aggregate", "1993年河北地市合并：邢台地区并入邢台市（国函〔1993〕89号）"),
        rel(1993, "承德地区", "HIST-HE-CHENGDE", "E130800", "merge", "aggregate", "1993年河北地市合并：承德地区并入承德市（国函〔1993〕89号）"),
        rel(1993, "石家庄地区", "HIST-HE-SHIJIAZHUANG", "E130100", "merge", "aggregate", "1993年河北地市合并：石家庄地区并入石家庄市（国函〔1993〕89号）"),
        rel(1994, "保定地区", "HIST-HE-BAODING", "E130600", "merge", "aggregate", "1994年保定地市合并（国函〔1994〕133号）：保定地区并入保定市"),
        rel(1994, "郧阳地区", "HIST-HB-YUNYANG", "E420300", "merge", "aggregate", "郧阳地区 merged into 十堰市"),
        rel(1994, "沙市市", "HIST-HB-JINGZHOU", "E421000", "merge", "aggregate", "荆州地区与原地级沙市市共同组建新的荆沙市（后更名荆州市）"),
        rel(1994, "沙市市", "HIST-HB-SHASHI", "E421000", "merge", "aggregate", "原地级沙市市与荆州地区共同组建新的荆沙市"),
        rel(1988, "惠阳地区", "HIST-GD-HUIYANG", "E441300", "split", "disaggregate", "惠阳地区撤销，惠州城区及部分县设立地级惠州市"),
        rel(1988, "惠阳地区", "HIST-GD-HUIYANG", "E441500", "split", "disaggregate", "惠阳地区析出海丰、陆丰设立汕尾市"),
        rel(1988, "惠阳地区", "HIST-GD-HUIYANG", "E441600", "split", "disaggregate", "惠阳地区析出河源县等设立河源市"),
        rel(1997, "梧州地区", "HIST-GX-WUZHOU", "E450400", "split", "disaggregate", "梧州地区撤销，岑溪等县市划归梧州市"),
        rel(1997, "梧州地区", "HIST-GX-WUZHOU", "E451100", "split", "disaggregate", "梧州地区主体更名为贺州地区（1997年）"),
        rel(1996, "松花江地区", "HIST-HLJ-SONGHUAJIANG", "E230100", "merge", "aggregate", "1996年松花江地区与哈尔滨市合并（国函〔1996〕64号）"),
        rel(1998, "桂林地区", "HIST-GX-GUILIN", "E450300", "merge", "aggregate", "1998年桂林市和桂林地区合并组建新的桂林市（国函〔1998〕73号）"),
        rel(1996, "三峡库区移民", "HIST-CQ-WANXIAN", "E500100", "jurisdiction_transfer", "aggregate", "entrusted to Chongqing administration in 1996"),
        rel(1996, "三峡库区移民", "HIST-CQ-FULING", "E500100", "jurisdiction_transfer", "aggregate", "entrusted to Chongqing administration in 1996"),
        rel(1996, "三峡库区移民", "HIST-CQ-QIANJIANG", "E500100", "jurisdiction_transfer", "aggregate", "entrusted to Chongqing administration in 1996"),
        rel(1997, "中办厅字〔1997〕34号", "HIST-CQ-WANXIAN", "E500100", "abolish", "aggregate", "1997年12月撤销万县市设立重庆市万县区（1998年5月更名万州区）"),
        rel(1997, "中办厅字〔1997〕34号", "HIST-CQ-FULING", "E500100", "abolish", "aggregate", "1997年12月撤销涪陵市设立重庆市涪陵区"),
        rel(1997, "中办厅字〔1997〕34号", "HIST-CQ-QIANJIANG", "E500100", "abolish", "aggregate", "1997年12月撤销黔江地区设立重庆市黔江开发区（2000年6月改设黔江区）"),
        rel(2002, "撤销柳州地区", "CNUR-000362", "E450200", "split", "disaggregate", "柳州地区撤销，柳江等县划归柳州市"),
        rel(2002, "撤销柳州地区", "CNUR-000362", "E451300", "split", "disaggregate", "柳州地区析设地级来宾市"),
        rel(2002, "撤销南宁地区", "CNUR-000346", "E450100", "split", "disaggregate", "南宁地区撤销，部分县划归南宁市"),
        rel(2002, "撤销南宁地区", "CNUR-000346", "E451400", "split", "disaggregate", "南宁地区析设地级崇左市"),
        rel(2011, "巢湖市", "CNUR-000110", "E340100", "split", "disaggregate", "巢湖市撤销，居巢区、庐江县划归合肥市"),
        rel(2011, "巢湖市", "CNUR-000110", "E340200", "split", "disaggregate", "巢湖市撤销，无为县划归芜湖市"),
        rel(2011, "巢湖市", "CNUR-000110", "E340500", "split", "disaggregate", "巢湖市撤销，含山县、和县划归马鞍山市"),
        rel(2018, "莱芜市", "CNUR-000146", "E370100", "merge", "aggregate", "莱芜市并入济南市（2019年1月公布实施）"),
    ])
    with RELATIONS_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(relations[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(relations)
    print(f"events={len(rows)} years={rows[0]['year']}-{rows[-1]['year']}")


if __name__ == "__main__":
    main()
