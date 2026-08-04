import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_wikipedia_county_change_archive import parse_table


def test_rowspan_does_not_leak_into_the_next_record():
    table = """
    {| class="wikitable"
    ! 原行政单位 !! 所属上级单位 !! 变更方式 !! 新行政建制
    |-
    | 奉贤县
    | rowspan="2" | 上海市
    | 撤销上海市奉贤县，设立上海市奉贤区
    | 奉贤区
    |-
    | 南汇县
    | 撤销上海市南汇县，设立上海市南汇区
    | 南汇区
    |-
    | 无
    | 广东省茂名市
    | 设立广东省茂名市茂港区
    | 茂港区
    |}
    """

    _headers, rows = parse_table(table)
    data_rows = [row for row in rows if row["row_kind"] == "data"]

    assert "上海市" in data_rows[0]["values"]
    assert "上海市" in data_rows[1]["values"]
    assert "上海市" not in data_rows[2]["values"]
    assert data_rows[2]["row_text"] == "无 | 广东省茂名市 | 设立广东省茂名市茂港区 | 茂港区"
