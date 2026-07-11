from __future__ import annotations

import io
import json
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
st.caption("保守、可解释的中国地级行政实体名称与年份核验")
st.info("上传文件只在当前会话内存中处理，不会持久化。请勿上传包含敏感信息的数据。")
page = st.sidebar.radio("入口", ["批量检查", "单个名称查询", "行政区划变更查询"])
m = matcher()

if page == "批量检查":
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
    normalized_tab, archive_tab = st.tabs(["统一规范事件库", "维基历史原始记录"])
    with normalized_tab:
        events = m.query_events(None if entity_label == "全部" else entity_options[entity_label], province or None, year or None, None if event_type == "全部" else event_type)
        st.dataframe(events, use_container_width=True)
        st.caption("统一覆盖 1987—2026 可获得资料；accepted_* 可用于事件检索，review_required 仅作待复核证据，不用于自动映射。")
        st.download_button("下载统一事件库", csv_bytes(events), "unified_events_1987_2026.csv", "text/csv")
    with archive_tab:
        keyword = st.text_input("关键词（城市、地区、盟、自治州或批文号）")
        raw_rows = m.query_wikipedia_rows(year or None, keyword or None)
        st.caption("覆盖维基可枚举的 1987—2026 年度页面；1989—1991 及更早年份没有同名年度页面。原始行仅作证据检索，不代表已完成实体关系标准化。")
        st.dataframe(raw_rows, use_container_width=True)
        st.download_button("下载维基原始记录", csv_bytes(raw_rows), "wikipedia_prefecture_change_rows.csv", "text/csv")
