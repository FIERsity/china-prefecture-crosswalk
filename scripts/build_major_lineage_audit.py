#!/usr/bin/env python3
"""Build reviewed county-level evidence for material prefecture lineage changes."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"

# A case is material when the transferred block is central to creation/dissolution
# of a prefecture entity. Incidental transfers of one or two peripheral counties
# are deliberately excluded unless they constitute the new entity's core.
CASES = [
    ("MAJOR-1987-WEIHAI",1987,"烟台市","CNUR-000140","威海市","CNUR-000144","carve_out","4","major","WIKI-RAW-1987:14-18","https://zh.wikipedia.org/wiki/1987年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1988-HUIYANG-HZ",1988,"惠阳地区","HIST-GD-HUIYANG","惠州市","CNUR-000206","split_successor","4","major","WIKI-1988-010","https://zh.wikipedia.org/wiki/1988年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1988-HUIYANG-SW",1988,"惠阳地区","HIST-GD-HUIYANG","汕尾市","CNUR-000208","split_successor","3","major","WIKI-1988-011","https://zh.wikipedia.org/wiki/1988年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1988-HUIYANG-HY",1988,"惠阳地区","HIST-GD-HUIYANG","河源市","CNUR-000209","split_successor","5","major","WIKI-1988-012","https://zh.wikipedia.org/wiki/1988年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1992-SONGYUAN",1992,"白城地区","CNUR-000058","松原市","CNUR-000057","carve_out","4","major","WIKI-1992-022","https://zh.wikipedia.org/wiki/1992年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1993-YANBEI-DT",1993,"雁北地区","CNUR-000343","大同市","CNUR-000015","split_successor","7","major","WIKI-1993-029","https://zh.wikipedia.org/wiki/1993年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1993-YANBEI-SZ",1993,"雁北地区","CNUR-000343","朔州市","CNUR-000019","split_successor","3","major","WIKI-1993-029","https://zh.wikipedia.org/wiki/1993年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1996-TAIZHOU",1996,"扬州市","CNUR-000083","泰州市","CNUR-000085","carve_out","5","major","WIKI-RAW-1996:86-91","https://zh.wikipedia.org/wiki/1996年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1996-SUQIAN",1996,"淮阴市","CNUR-000081","宿迁市","CNUR-000086","carve_out","5","major","WIKI-RAW-1996:92-97","https://zh.wikipedia.org/wiki/1996年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1997-MEISHAN",1997,"乐山市","CNUR-000245","眉山地区","CNUR-000247","carve_out","6","major","WIKI-1997-065","https://zh.wikipedia.org/wiki/1997年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-1998-ZIYANG",1998,"内江市","CNUR-000244","资阳地区","CNUR-000253","carve_out","4","major","WIKI-1998-072","https://zh.wikipedia.org/wiki/1998年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2002-NANNING-CZ",2002,"南宁地区","HIST-GX-NANNING","崇左市","CNUR-000230","split_successor","7","major","PL-2002-009","https://zh.wikipedia.org/wiki/2002年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2002-NANNING-NN",2002,"南宁地区","HIST-GX-NANNING","南宁市","CNUR-000217","split_successor","5","major","PL-2002-009","https://zh.wikipedia.org/wiki/2002年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2003-ZHONGWEI-WZ",2003,"吴忠市","CNUR-000323","中卫市","CNUR-000325","carve_out","2","majority_of_new_entity","PL-2003-006","https://zh.wikipedia.org/wiki/2003年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2003-ZHONGWEI-GY",2003,"固原市","CNUR-000324","中卫市","CNUR-000325","territory_contribution","1","secondary","PL-2003-006","https://zh.wikipedia.org/wiki/2003年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2011-CHAOHU-HF",2011,"巢湖市","CNUR-000110","合肥市","CNUR-000098","split_successor","2","major","PL-2011-001","https://zh.wikipedia.org/wiki/2011年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2011-CHAOHU-WH",2011,"巢湖市","CNUR-000110","芜湖市","CNUR-000099","split_successor","1","material_in_three_way_split","PL-2011-001","https://zh.wikipedia.org/wiki/2011年中华人民共和国县级以上行政区划变更列表"),
    ("MAJOR-2011-CHAOHU-MA",2011,"巢湖市","CNUR-000110","马鞍山市","CNUR-000102","split_successor","2","major","PL-2011-001","https://zh.wikipedia.org/wiki/2011年中华人民共和国县级以上行政区划变更列表"),
]

COUNTIES = {
    "MAJOR-1987-WEIHAI": ["县级威海市","乳山县","文登县","荣成县"],
    "MAJOR-1988-HUIYANG-HZ": ["县级惠州市","惠阳县","博罗县","惠东县"],
    "MAJOR-1988-HUIYANG-SW": ["海丰县","陆丰县","陆河县"],
    "MAJOR-1988-HUIYANG-HY": ["河源县","紫金县","和平县","连平县","龙川县"],
    "MAJOR-1992-SONGYUAN": ["扶余市","长岭县","前郭尔罗斯蒙古族自治县","乾安县"],
    "MAJOR-1993-YANBEI-DT": ["左云县","大同县","阳高县","天镇县","浑源县","广灵县","灵丘县"],
    "MAJOR-1993-YANBEI-SZ": ["怀仁县","右玉县","应县"],
    "MAJOR-1996-TAIZHOU": ["县级泰州市","兴化市","泰兴市","靖江市","姜堰市"],
    "MAJOR-1996-SUQIAN": ["县级宿迁市","沭阳县","泗阳县","泗洪县","宿豫县"],
    "MAJOR-1997-MEISHAN": ["眉山县","仁寿县","彭山县","洪雅县","丹棱县","青神县"],
    "MAJOR-1998-ZIYANG": ["县级资阳市","简阳市","乐至县","安岳县"],
    "MAJOR-2002-NANNING-CZ": ["崇左县","凭祥市","扶绥县","大新县","天等县","宁明县","龙州县"],
    "MAJOR-2002-NANNING-NN": ["隆安县","马山县","上林县","宾阳县","横县"],
    "MAJOR-2003-ZHONGWEI-WZ": ["中卫县","中宁县"],
    "MAJOR-2003-ZHONGWEI-GY": ["海原县"],
    "MAJOR-2011-CHAOHU-HF": ["居巢区（改设县级巢湖市）","庐江县"],
    "MAJOR-2011-CHAOHU-WH": ["无为县"],
    "MAJOR-2011-CHAOHU-MA": ["含山县","和县"],
}


def write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    fields = ["case_id","year","from_name","from_entity_key","to_name","to_entity_id","relation_type","county_unit_count","materiality","source_event_id","source_url","automatic_mapping","review_status"]
    relations = [dict(zip(fields[:-2], case)) | {"automatic_mapping":"false","review_status":"reviewed_county_composition"} for case in CASES]
    county_rows = []
    by_id = {r["case_id"]: r for r in relations}
    for case_id, names in COUNTIES.items():
        case = by_id[case_id]
        for name in names:
            county_rows.append({"case_id":case_id,"year":case["year"],"county_name_at_event":name,"from_prefecture_name":case["from_name"],"from_entity_key":case["from_entity_key"],"to_prefecture_name":case["to_name"],"to_entity_id":case["to_entity_id"],"source_event_id":case["source_event_id"],"source_url":case["source_url"],"review_status":"reviewed_county_composition"})
    write(OUT / "major_lineage_relations.csv", fields, relations)
    write(OUT / "county_affiliation_transitions.csv", list(county_rows[0]), county_rows)
    print(f"major_relations={len(relations)} county_transitions={len(county_rows)}")


if __name__ == "__main__": main()
