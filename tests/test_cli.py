import json

from urban_crosswalk.cli import main


def test_cli_match(capsys):
    assert main(["match", "思茅市", "--year", "2005", "--province", "云南省"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["crosswalk_entity_id"] == "CNUR-000272"
    assert result["crosswalk_match_status"] == "auto_matched"


def test_cli_fail_on_review(capsys):
    assert main(["match", "毫州", "--year", "2010", "--fail-on-review"]) == 2
    assert json.loads(capsys.readouterr().out)["crosswalk_match_status"] == "needs_confirmation"


def test_cli_batch(tmp_path, capsys):
    source = tmp_path / "input.csv"
    source.write_text("城市,年份,省份\n普洱市,2010,云南省\n香格里拉市,2020,云南省\n", encoding="utf-8")
    output, issues, audit = tmp_path / "matched.csv", tmp_path / "issues.csv", tmp_path / "audit.json"
    code = main(["batch", str(source), "--name-col", "城市", "--year-col", "年份", "--province-col", "省份", "-o", str(output), "--issues-output", str(issues), "--audit-output", str(audit)])
    assert code == 0
    assert output.exists() and issues.exists() and audit.exists()
    summary = json.loads(capsys.readouterr().out)
    assert summary["rows"] == 2 and summary["requires_review"] == 1


def test_cli_historical_entity(capsys):
    assert main(["entity", "CNUR-000343"]) == 0
    assert json.loads(capsys.readouterr().out)["entity"]["canonical_name_zh"] == "雁北地区"
