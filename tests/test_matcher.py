import pandas as pd

from urban_crosswalk.matcher import CrosswalkMatcher, normalize_name


def test_normalization():
    assert normalize_name(" 襄陽　市\u200b ") == "襄阳市"
    assert normalize_name("亳州巿") == "亳州市"


def test_historical_names_and_suffix_aliases():
    m = CrosswalkMatcher()
    assert m.match_name("思茅市", 2005).entity_id == "E530800"
    assert m.match_name("襄樊", 2009).entity_id == "E420600"
    assert m.match_name("昌都地区", 2010).entity_id == "E540300"


def test_ocr_never_auto_accepts():
    r = CrosswalkMatcher().match_name("毫州", 2010, "安徽")
    assert r.match_status == "needs_confirmation"
    assert r.match_method == "ocr_candidate"


def test_year_and_level_risks():
    m = CrosswalkMatcher()
    assert "pre_establishment" in m.match_name("三沙市", 2005, "海南").risk_codes
    assert "pre_establishment" in m.match_name("中卫市", 2001, "宁夏").risk_codes
    assert "name_year_mismatch" in m.match_name("儋州市", 2010, "海南").risk_codes
    assert "post_abolition" in m.match_name("莱芜市", 2020, "山东").risk_codes
    assert "merge_event" in m.match_name("莱芜市", 2020, "山东").risk_codes
    assert "post_abolition" in m.match_name("巢湖市", 2015, "安徽").risk_codes
    assert "split_event" in m.match_name("巢湖市", 2015, "安徽").risk_codes
    assert "post_abolition" in m.match_name("伊犁地区", 2005, "新疆").risk_codes
    assert "county_level_conflict" in m.match_name("香格里拉市", 2020, "云南").risk_codes
    assert "province_mismatch" in m.match_name("普洱市", 2010, "安徽").risk_codes


def test_custom_override_is_audited():
    rules = pd.DataFrame([{"alias": "普洱市", "entity_id": "E530900"}])
    r = CrosswalkMatcher().match_name("普洱市", 2010, "云南", rules)
    assert r.entity_id == "E530900"
    assert r.builtin_entity_id == "E530800"
    assert "custom_override_warning" in r.risk_codes


def test_fuzzy_is_candidate_only():
    r = CrosswalkMatcher().match_name("石家庄巿区", 2010, "河北")
    assert r.match_status in {"needs_confirmation", "unmatched"}
    assert r.match_status != "auto_matched"


def test_dataframe_preserves_original_columns():
    df = pd.DataFrame({"城市": ["普洱市", "香格里拉市"], "年份": [2010, 2020], "值": [1.2, 3.4]})
    out, results = CrosswalkMatcher().match_dataframe(df, "城市", "年份")
    assert list(out["值"]) == [1.2, 3.4]
    assert len(results) == 2
    assert "crosswalk_entity_id" in out


def test_event_queries_and_complex_relations():
    m = CrosswalkMatcher()
    assert len(m.query_events(entity_id="E341400")) == 2
    complex_rows = m.relations[m.relations.relation_type.isin(["merge", "split"])]
    assert len(complex_rows) == 2
    assert set(complex_rows.automatic_continuity) == {"false"}
    historical = m.query_wikipedia_rows(year=1987, keyword="徽州地区")
    assert len(historical) >= 1
    assert historical.iloc[0].source_url.startswith("https://zh.wikipedia.org/wiki/")
    normalized = m.query_historical_events(entity_id="E341700", accepted_only=True)
    assert any(normalized.event_id == "WIKI-1988-017")
    unified = m.query_events(entity_id="E341700")
    assert set(unified.year) >= {"1988", "2000"}
