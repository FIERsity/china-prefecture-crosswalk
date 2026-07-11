from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from urban_crosswalk.matcher import CrosswalkMatcher, audit_report

st.set_page_config(page_title="中国城市面板匹配工具", page_icon="🏙️", layout="wide")

@st.cache_resource
def matcher(): return CrosswalkMatcher()

def read_upload(upload):
    if upload.size > 50 * 1024 * 1024: raise ValueError("文件超过 50 MB")
    if upload.name.lower().endswith(".csv"):
        raw = upload.getvalue()
        for enc in ("utf-8-sig", "gb18030"):
            try: return {"CSV": pd.read_csv(io.BytesIO(raw), encoding=enc)}
            except UnicodeDecodeError: pass
        raise ValueError("无法识别 CSV 编码")
    book = pd.ExcelFile(upload)
    return {sheet: pd.read_excel(book, sheet_name=sheet) for sheet in book.sheet_names}

def csv_bytes(df): return df.to_csv(index=False).encode("utf-8-sig")
def xlsx_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="matched")
    return buffer.getvalue()

st.title("中国城市面板匹配工具")
st.caption("保守、可解释的中国地级行政实体名称与年份核验 · 匹配覆盖 1987—2026")
st.info("上传文件只在当前会话内存中处理，不会持久化。请勿上传包含敏感信息的数据。")
page = st.sidebar.radio("入口", ["数据库浏览与下载", "批量检查", "单个名称查询", "行政区划变更查询"])
m = matcher()

if page == "数据库浏览与下载":
    release_dir = Path(__file__).resolve().parent / "data" / "releases" / "v2.0"
    master = pd.read_csv(release_dir / "china_city_entity_master_V2.0.csv", encoding="utf-8-sig", dtype=str).fillna("")
    st.header("中国地级城市研究实体数据库 V2.0")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("研究实体", len(master))
    c2.metric("当前面板实体", int((master.entity_scope == "current_panel_entity").sum()))
    c3.metric("历史实体", int((master.entity_scope == "historical_entity").sum()))
    c4.metric("统一事件", len(m.unified_events))
    f1, f2, f3 = st.columns(3)
    province = f1.selectbox("省份", ["全部"] + sorted(master.province_name_zh.unique()))
    scope = f2.selectbox("实体范围", ["全部"] + sorted(master.entity_scope.unique()))
    keyword = f3.text_input("名称或 CNUR 编号")
    shown = master.copy()
    if province != "全部": shown = shown[shown.province_name_zh == province]
    if scope != "全部": shown = shown[shown.entity_scope == scope]
    if keyword:
        needle = keyword.strip().lower()
        shown = shown[shown.apply(lambda row: needle in row.entity_id.lower() or needle in row.canonical_name_zh.lower() or needle in row.legacy_entity_id.lower(), axis=1)]
    st.dataframe(shown, use_container_width=True, hide_index=True)
    d1, d2 = st.columns(2)
    d1.download_button("下载 V2.0 CSV", (release_dir / "china_city_entity_master_V2.0.csv").read_bytes(), "china_city_entity_master_V2.0.csv", "text/csv")
    d2.download_button("下载 V2.0 Excel", (release_dir / "china_city_entity_master_V2.0.xlsx").read_bytes(), "china_city_entity_master_V2.0.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("运行时年度状态覆盖 1987—2026。CNUR 是项目永久研究编号，不是官方行政区划代码。合并、拆分和代管关系不会自动换算研究变量。")

elif page == "批量检查":
    upload = st.file_uploader("上传 CSV 或 XLSX", type=["csv", "xlsx"])
    custom_upload = st.file_uploader("可选：个人映射 CSV（alias, entity_id）", type=["csv"], key="rules")
    if upload:
        try:
            sheets = read_upload(upload)
            sheet = st.selectbox("工作表", list(sheets)) if len(sheets) > 1 else next(iter(sheets))
            df = sheets[sheet]
            if len(df) > 500_000: raise ValueError("文件超过 500,000 行")
            st.dataframe(df.head(20), use_container_width=True)
            name_col = st.selectbox("城市名称列", list(df.columns))
            optional = ["（不使用）"] + list(df.columns)
            year_choice = st.selectbox("年份列", optional)
            province_choice = st.selectbox("省份列", optional)
            custom = pd.read_csv(custom_upload, dtype=str).fillna("") if custom_upload else None
            if st.button("开始检查", type="primary"):
                out, results = m.match_dataframe(df, name_col, None if year_choice == "（不使用）" else year_choice, None if province_choice == "（不使用）" else province_choice, custom)
                st.session_state["matched"] = out
                st.session_state["results"] = results
                st.session_state["config"] = {"name_col": name_col, "year_col": year_choice, "province_col": province_choice, "sheet": sheet}
            if "matched" in st.session_state:
                out, results = st.session_state.matched, st.session_state.results
                counts = out.crosswalk_match_status.value_counts()
                cols = st.columns(4)
                for col, status in zip(cols, ["auto_matched", "needs_confirmation", "problem", "unmatched"]): col.metric(status, int(counts.get(status, 0)))
                category = st.radio("查看分类", ["全部", "auto_matched", "needs_confirmation", "problem", "unmatched"], horizontal=True)
                shown = out if category == "全部" else out[out.crosswalk_match_status == category]
                st.dataframe(shown, use_container_width=True)
                candidate_rows = []
                for idx, result in enumerate(results):
                    for candidate in result.candidates or []: candidate_rows.append({"row_index": idx, "input": out.iloc[idx][name_col], **candidate})
                candidates = pd.DataFrame(candidate_rows)
                if len(candidates):
                    st.subheader("需要人工确认的候选")
                    edited = st.data_editor(candidates.assign(accept=False, apply_same_input=False), hide_index=True, disabled=[c for c in candidates.columns])
                    accepted = edited[edited.accept]
                    for _, row in accepted.iterrows():
                        targets = candidates[candidates.input == row.input].row_index if row.apply_same_input else [int(row.row_index)]
                        for i in targets:
                            out.loc[out.index[int(i)], "crosswalk_entity_id"] = row.entity_id; out.loc[out.index[int(i)], "crosswalk_canonical_name"] = row.canonical_name; out.loc[out.index[int(i)], "crosswalk_match_status"] = "user_confirmed"
                    st.session_state.matched = out
                issues = out[out.crosswalk_match_status != "auto_matched"]
                candidate_audit = candidates.copy() if len(candidates) else pd.DataFrame(columns=["row_index", "input", "entity_id", "canonical_name", "matched_name", "score"])
                candidate_audit["accepted"] = candidate_audit.apply(lambda r: str(out.iloc[int(r.row_index)].crosswalk_entity_id) == str(r.entity_id) and out.iloc[int(r.row_index)].crosswalk_match_status == "user_confirmed", axis=1) if len(candidate_audit) else []
                report_obj = json.loads(audit_report(results, st.session_state.config))
                report_obj["final_counts"] = out.crosswalk_match_status.value_counts().to_dict()
                report_obj["manual_confirmations"] = int((out.crosswalk_match_status == "user_confirmed").sum())
                report_obj["custom_overrides"] = int(out.crosswalk_risk_codes.str.contains("custom_override_warning", na=False).sum())
                report_obj["unresolved"] = int(out.crosswalk_match_status.isin(["needs_confirmation", "problem", "unmatched"]).sum())
                report = json.dumps(report_obj, ensure_ascii=False, indent=2)
                c1, c2, c3, c4 = st.columns(4)
                if upload.name.lower().endswith(".xlsx"):
                    c1.download_button("匹配结果 XLSX", xlsx_bytes(out), "matched.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    c1.download_button("匹配结果 CSV", csv_bytes(out), "matched.csv", "text/csv")
                c2.download_button("问题清单 CSV", csv_bytes(issues), "issues.csv", "text/csv")
                c3.download_button("候选与确认 CSV", csv_bytes(candidate_audit), "candidate_audit.csv", "text/csv")
                c4.download_button("审计报告 JSON", report.encode("utf-8"), "audit.json", "application/json")
        except Exception as exc: st.error(str(exc))

elif page == "单个名称查询":
    name = st.text_input("行政区名称")
    c1, c2 = st.columns(2)
    year = c1.number_input("年份（0 表示不提供）", min_value=0, max_value=2100, value=0)
    province = c2.text_input("省份（可选）")
    if name:
        result = m.match_name(name, year or None, province or None)
        st.json(result.output_columns())
        if result.candidates: st.dataframe(result.candidates, use_container_width=True)
        if result.entity_id:
            detail = m.query_entity(result.entity_id)
            st.subheader("名称历史"); st.dataframe(detail["names"], use_container_width=True)
            st.subheader("相关事件"); st.dataframe(detail["events"], use_container_width=True)
            st.subheader("重大实体关系"); st.dataframe(detail["major_lineage"], use_container_width=True)
        title = quote(f"别名建议：{name}")
        body = quote(f"原始写法：{name}\n年份：{year or '未提供'}\n省份：{province or '未提供'}\n建议实体：{result.entity_id}\n匹配方法：{result.match_method}")
        st.link_button("提交公共别名建议", f"https://github.com/FIERsity/china-prefecture-crosswalk/issues/new?title={title}&body={body}")

else:
    entity_options = {f"{r.canonical_name_zh} ({r.entity_id})": r.entity_id for _, r in m.entities.iterrows()}
    entity_options.update({f"{r.canonical_name_zh} ({r.historical_entity_id}, 历史)": r.historical_entity_id for _, r in m.historical_entities.iterrows()})
    c1, c2, c3, c4 = st.columns(4)
    entity_label = c1.selectbox("实体", ["全部"] + list(entity_options))
    province = c2.text_input("省份")
    year = c3.number_input("年份（0 表示全部）", min_value=0, max_value=2026, value=0)
    event_types = sorted(m.unified_events.event_type.unique())
    event_type = c4.selectbox("事件类型", ["全部"] + event_types)
    normalized_tab, lineage_tab, archive_tab = st.tabs(["统一规范事件库", "重大拆分与县级去向", "维基历史原始记录"])
    with normalized_tab:
        events = m.query_events(None if entity_label == "全部" else entity_options[entity_label], province or None, year or None, None if event_type == "全部" else event_type)
        st.dataframe(events, use_container_width=True)
        st.caption("统一覆盖 1987—2026 可获得资料；accepted_* 可用于事件检索，review_required 仅作待复核证据，不用于自动映射。")
        st.download_button("下载统一事件库", csv_bytes(events), "unified_events_1987_2026.csv", "text/csv")
    with lineage_tab:
        lineage = m.major_lineage_relations.copy()
        counties = m.county_transitions.copy()
        if year:
            lineage = lineage[lineage.year.astype(int) == year]
            counties = counties[counties.year.astype(int) == year]
        st.caption("仅收录会改变地级实体主要辖域连续性的拆分、析设和多来源组建；一两个不构成主要辖域的边缘划转通常不收录。所有复杂关系均禁止自动换算研究变量。")
        st.subheader("重大实体关系")
        st.dataframe(lineage, use_container_width=True, hide_index=True)
        st.download_button("下载重大实体关系", csv_bytes(lineage), "major_lineage_relations.csv", "text/csv")
        st.subheader("县级单位去向证据")
        st.dataframe(counties, use_container_width=True, hide_index=True)
        st.download_button("下载县级去向底表", csv_bytes(counties), "county_affiliation_transitions.csv", "text/csv")
    with archive_tab:
        keyword = st.text_input("关键词（城市、地区、盟、自治州或批文号）")
        raw_rows = m.query_wikipedia_rows(year or None, keyword or None)
        st.caption("覆盖维基可枚举的 1987—2026 年度页面；1989—1991 及更早年份没有同名年度页面。原始行仅作证据检索，不代表已完成实体关系标准化。")
        st.dataframe(raw_rows, use_container_width=True)
        st.download_button("下载维基原始记录", csv_bytes(raw_rows), "wikipedia_prefecture_change_rows.csv", "text/csv")
