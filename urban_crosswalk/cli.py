from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from .matcher import CrosswalkMatcher, audit_report

VERSION = "2.0.0"


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def read_table(path: Path, sheet: str | int = 0) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        for encoding in ("utf-8-sig", "gb18030"):
            try: return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError: continue
        raise ValueError("无法识别 CSV 编码")
    if path.suffix.lower() == ".xlsx": return pd.read_excel(path, sheet_name=sheet)
    raise ValueError("仅支持 .csv 和 .xlsx")


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv": df.to_csv(path, index=False, encoding="utf-8-sig")
    elif path.suffix.lower() == ".xlsx": df.to_excel(path, index=False, sheet_name="matched")
    else: raise ValueError("输出文件必须是 .csv 或 .xlsx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cnur", description="中国地级城市研究实体匹配工具")
    parser.add_argument("--version", action="version", version=f"cnur {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)

    match = commands.add_parser("match", help="匹配单个行政区名称")
    match.add_argument("name"); match.add_argument("--year", type=int); match.add_argument("--province")
    match.add_argument("--fail-on-review", action="store_true", help="非自动匹配时返回退出码 2")

    batch = commands.add_parser("batch", help="批量匹配 CSV/XLSX")
    batch.add_argument("input", type=Path); batch.add_argument("--name-col", required=True)
    batch.add_argument("--year-col"); batch.add_argument("--province-col"); batch.add_argument("--sheet", default=0)
    batch.add_argument("--custom-rules", type=Path); batch.add_argument("--output", "-o", type=Path, required=True)
    batch.add_argument("--issues-output", type=Path); batch.add_argument("--audit-output", type=Path)
    batch.add_argument("--fail-on-review", action="store_true")

    entity = commands.add_parser("entity", help="查询当前或历史实体")
    entity.add_argument("entity_id")

    events = commands.add_parser("events", help="查询统一行政区划事件")
    events.add_argument("--entity-id"); events.add_argument("--province"); events.add_argument("--year", type=int)
    events.add_argument("--type", dest="event_type"); events.add_argument("--output", "-o", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    matcher = CrosswalkMatcher()
    try:
        if args.command == "match":
            result = matcher.match_name(args.name, args.year, args.province)
            emit({**result.output_columns(), "candidates": result.candidates or []})
            return 2 if args.fail_on_review and result.match_status != "auto_matched" else 0
        if args.command == "batch":
            sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
            source = read_table(args.input, sheet)
            rules = read_table(args.custom_rules) if args.custom_rules else None
            matched, results = matcher.match_dataframe(source, args.name_col, args.year_col, args.province_col, rules)
            write_table(matched, args.output)
            issues = matched[matched.crosswalk_match_status != "auto_matched"]
            if args.issues_output: write_table(issues, args.issues_output)
            if args.audit_output:
                report = audit_report(results, {"input": str(args.input), "name_col": args.name_col, "year_col": args.year_col, "province_col": args.province_col})
                args.audit_output.parent.mkdir(parents=True, exist_ok=True); args.audit_output.write_text(report, encoding="utf-8")
            emit({"rows": len(matched), "auto_matched": int((matched.crosswalk_match_status == "auto_matched").sum()), "requires_review": len(issues), "output": str(args.output)})
            return 2 if args.fail_on_review and len(issues) else 0
        if args.command == "entity":
            detail = matcher.query_entity(args.entity_id)
            if not detail.get("entity"): print(f"未知实体编号: {args.entity_id}", file=sys.stderr); return 1
            emit(detail); return 0
        if args.command == "events":
            rows = matcher.query_events(args.entity_id, args.province, args.year, args.event_type)
            if args.output: write_table(rows, args.output); emit({"rows": len(rows), "output": str(args.output)})
            else: emit(rows.to_dict("records"))
            return 0
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"错误: {exc}", file=sys.stderr); return 1
    return 1


if __name__ == "__main__": raise SystemExit(main())
