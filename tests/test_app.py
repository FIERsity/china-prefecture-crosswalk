from streamlit.testing.v1 import AppTest


def test_app_starts_with_three_entries():
    app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception
    assert app.title[0].value == "中国城市面板匹配工具"
    assert app.radio[0].options == ["数据库浏览与下载", "批量检查", "单个名称查询", "行政区划变更查询"]
