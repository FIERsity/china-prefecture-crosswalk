import pandas as pd

from urban_crosswalk.matcher import CrosswalkMatcher, normalize_name


def test_normalization():
    assert normalize_name(" 襄陽　市\u200b ") == "襄阳市"
    assert normalize_name("亳州巿") == "亳州市"


def test_historical_names_and_suffix_aliases():
    m = CrosswalkMatcher()
    assert m.match_name("思茅市", 2005).entity_id == "CNUR-000272"
    assert m.match_name("襄樊", 2009).entity_id == "CNUR-000173"
    assert m.match_name("昌都地区", 2010).entity_id == "CNUR-000284"
    assert m.match_name("建阳地区", 1987).entity_id == "CNUR-000121"
    assert m.match_name("普洱市", 2026).entity_id == "CNUR-000272"
    assert m.match_name("南宁地区", 2000).entity_id == "CNUR-000346"
    assert m.match_name("惠阳地区", 1987).entity_id == "CNUR-000347"


def test_year_end_names_accept_within_year_transitions():
    m = CrosswalkMatcher()
    old = m.match_name("襄樊市", 2010, "湖北")
    new = m.match_name("襄阳市", 2010, "湖北")
    assert old.entity_id == new.entity_id == "CNUR-000173"
    assert old.match_status == new.match_status == "auto_matched"
    assert old.year_end_name == new.year_end_name == "襄阳市"
    assert old.name_validity == "valid_during_year"
    assert new.name_validity == "year_end_name"
    assert "name_changed_during_year" in old.risk_codes
    assert old.transition_event_ids == "PL-2010-001"


def test_cross_year_implementation_controls_year_end_name():
    m = CrosswalkMatcher()
    assert m.match_name("那曲地区", 2017, "西藏").year_end_name == "那曲地区"
    assert m.match_name("那曲市", 2017, "西藏").name_validity == "outside_year"
    old = m.match_name("那曲地区", 2018, "西藏")
    new = m.match_name("那曲市", 2018, "西藏")
    assert old.match_status == new.match_status == "auto_matched"
    assert old.year_end_name == new.year_end_name == "那曲市"


def test_year_end_establishment_corrections():
    m = CrosswalkMatcher()
    for name, province in (("亳州市", "安徽"), ("随州市", "湖北")):
        assert m.match_name(name, 1999, province).year_status == "not_established"
        assert m.match_name(name, 2000, province).year_status == "active"
    assert m.match_name("儋州市", 1999, "海南").year_status == "not_prefecture_level"
    assert m.match_name("儋州市", 2015, "海南").year_status == "active"


def test_split_predecessors_do_not_leak_into_successor_identity():
    m = CrosswalkMatcher()
    assert m.match_name("崇左市", 2001).year_status == "not_established"
    assert "pre_establishment" in m.match_name("崇左市", 2001).risk_codes
    assert m.match_name("崇左市", 2002).entity_id == "CNUR-000230"
    assert m.match_name("惠州市", 1987).year_status == "not_established"
    assert m.match_name("惠州市", 1988).entity_id == "CNUR-000206"
    assert m.match_name("泰州市", 1995).year_status == "not_established"
    assert m.match_name("宿迁市", 1995).year_status == "not_established"
    assert m.match_name("柳州地区", 2001).entity_id == "CNUR-000362"
    assert m.match_name("来宾市", 2001).year_status == "not_established"
    assert m.match_name("梧州地区", 1996).entity_id == "CNUR-000363"
    assert m.match_name("贺州市", 1996).year_status == "not_established"
    assert m.match_name("荆州地区", 1993).entity_id == "CNUR-000358"
    assert m.match_name("荆州市", 1993).year_status == "not_established"


def test_late_prefecture_establishment_years():
    m = CrosswalkMatcher()
    for name, before, start in [("日照市",1988,1989),("东莞市",1987,1988),("中山市",1987,1988),("潮州市",1990,1991),("揭阳市",1990,1991),("云浮市",1993,1994),("贵港市",1994,1995)]:
        assert m.match_name(name, before).year_status == "not_established"
        assert m.match_name(name, start).entity_id


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
    assert m.match_name("普洱市", 1986).year_status == "early_event_only"
    assert "unsupported_year" in m.match_name("普洱市", 2027).risk_codes


def test_custom_override_is_audited():
    rules = pd.DataFrame([{"alias": "普洱市", "entity_id": "CNUR-000273"}])
    r = CrosswalkMatcher().match_name("普洱市", 2010, "云南", rules)
    assert r.entity_id == "CNUR-000273"
    assert r.builtin_entity_id == "CNUR-000272"
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
    assert len(m.query_events(entity_id="CNUR-000110")) == 2
    complex_rows = m.relations[m.relations.relation_type.isin(["merge", "split"])]
    assert len(complex_rows) == 2
    assert set(complex_rows.automatic_continuity) == {"false"}
    historical = m.query_wikipedia_rows(year=1987, keyword="徽州地区")
    assert len(historical) >= 1
    assert historical.iloc[0].source_url.startswith("https://zh.wikipedia.org/wiki/")
    normalized = m.query_historical_events(entity_id="CNUR-000113", accepted_only=True)
    assert any(normalized.event_id == "WIKI-1988-017")
    unified = m.query_events(entity_id="CNUR-000113")
    assert set(unified.year) >= {"1988", "2000"}


def test_early_prefecture_events_are_queryable():
    m = CrosswalkMatcher()
    rows = m.query_events(entity_id="CNUR-000018", year=1985)
    assert len(rows) == 1
    assert rows.iloc[0].new_prefecture_name == "晋城市"
    assert rows.iloc[0].source_id == "SRC-RMRB-1985-09-12"
