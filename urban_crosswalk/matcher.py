from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz, process

try:
    from opencc import OpenCC
    _converter = OpenCC("t2s")
except Exception:  # pragma: no cover
    _converter = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RULE_VERSION = "2026.07.1"
PUNCT = re.compile(r"[\s\u200b-\u200f\u2060\ufeff·•,，。.;；:：()（）\[\]【】_-]+")


def normalize_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    if _converter:
        text = _converter.convert(text)
    text = text.replace("巿", "市")
    return PUNCT.sub("", text).strip()


def normalize_province(value: Any) -> str:
    text = normalize_name(value)
    for suffix in ("壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "省", "市"):
        if text.endswith(suffix):
            return text[:-len(suffix)]
    return text


@dataclass
class MatchResult:
    entity_id: str = ""
    canonical_name: str = ""
    normalized_input: str = ""
    match_status: str = "unmatched"
    match_method: str = "none"
    confidence: float = 0.0
    year_status: str = "unknown"
    level_status: str = "unknown"
    risk_codes: str = ""
    candidate_count: int = 0
    candidates: list[dict[str, Any]] | None = None
    rule_version: str = RULE_VERSION
    builtin_entity_id: str = ""

    def output_columns(self) -> dict[str, Any]:
        return {
            "crosswalk_entity_id": self.entity_id,
            "crosswalk_canonical_name": self.canonical_name,
            "crosswalk_normalized_input": self.normalized_input,
            "crosswalk_match_status": self.match_status,
            "crosswalk_match_method": self.match_method,
            "crosswalk_confidence": self.confidence,
            "crosswalk_year_status": self.year_status,
            "crosswalk_level_status": self.level_status,
            "crosswalk_risk_codes": self.risk_codes,
            "crosswalk_candidate_count": self.candidate_count,
            "crosswalk_rule_version": self.rule_version,
        }


class CrosswalkMatcher:
    def __init__(self, data_dir: Path | str = DATA):
        data_dir = Path(data_dir)
        self.entities = pd.read_csv(data_dir / "entities.csv", dtype=str).fillna("")
        self.names = pd.read_csv(data_dir / "entity_names.csv", dtype={"entity_id": str})
        self.roster = pd.read_csv(data_dir / "legal_roster_2000_2024.csv", dtype={"entity_id": str})
        self.aliases = pd.read_csv(data_dir / "aliases.csv", dtype={"entity_id": str})
        self.exclusions = pd.read_csv(data_dir / "name_exclusions.csv", dtype=str).fillna("")
        self.events = pd.read_csv(data_dir / "events_2000_2026.csv", dtype=str).fillna("")
        self.links = pd.read_csv(data_dir / "event_entity_links.csv", dtype=str).fillna("")
        self.relations = pd.read_csv(data_dir / "event_relations.csv", dtype=str).fillna("")
        self.wikipedia_pages = pd.read_csv(data_dir / "wikipedia_change_pages.csv", dtype=str).fillna("")
        self.wikipedia_rows = pd.read_csv(data_dir / "wikipedia_prefecture_change_rows.csv", dtype=str).fillna("")
        self.wikipedia_normalized_events = pd.read_csv(data_dir / "wikipedia_normalized_events_1987_1999.csv", dtype=str).fillna("")
        self.unified_events = pd.read_csv(data_dir / "unified_events_1987_2026.csv", dtype=str).fillna("")
        self.historical_entities = pd.read_csv(data_dir / "historical_entities.csv", dtype=str).fillna("")
        self.unified_relations = pd.read_csv(data_dir / "unified_event_relations.csv", dtype=str).fillna("")
        self.entity_map = self.entities.set_index("entity_id").to_dict("index")
        self.index: dict[str, list[dict[str, Any]]] = {}
        for _, r in self.names.iterrows():
            if r["name_zh"] and r["legal_status"] == "active":
                self._add(r["name_zh"], r["entity_id"], "official_or_historical", int(r["start_year"]), int(r["end_year"]))
        for _, r in self.aliases.iterrows():
            self._add(r["alias"], r["entity_id"], r["alias_type"], int(r["start_year"]), int(r["end_year"]))
        self.choices = list(self.index)

    def _add(self, name: str, entity_id: str, method: str, start: int, end: int) -> None:
        self.index.setdefault(normalize_name(name), []).append({"entity_id": entity_id, "method": method, "start": start, "end": end})

    def _year_status(self, entity_id: str, year: int | None) -> str:
        if year is None:
            return "not_checked"
        if not 2000 <= year <= 2024:
            return "unsupported_year"
        rows = self.roster[(self.roster.entity_id == entity_id) & (self.roster.year == year)]
        return str(rows.iloc[0].status) if len(rows) else "unknown"

    def _relation_risks(self, entity_id: str, year: int | None) -> list[str]:
        if year is None:
            return []
        rows = self.relations[(self.relations.entity_id == entity_id) & (self.relations.relation_type.isin(["merge", "split"]))]
        return [f"{row.relation_type}_event" for _, row in rows.iterrows() if year >= int(row.year)]

    def match_name(self, name: Any, year: int | None = None, province: Any = None, custom_rules: pd.DataFrame | None = None) -> MatchResult:
        norm = normalize_name(name)
        if not norm:
            return MatchResult(normalized_input=norm, risk_codes="blank_name")
        try:
            year = None if year is None or pd.isna(year) or str(year).strip() == "" else int(float(year))
        except (ValueError, TypeError):
            return MatchResult(normalized_input=norm, year_status="invalid_year", risk_codes="invalid_year")
        province_norm = normalize_province(province)
        excluded = self.exclusions[self.exclusions.normalized_name.map(normalize_name) == norm]
        if len(excluded):
            r = excluded.iloc[0]
            if year is None or int(r.start_year) <= year <= int(r.end_year):
                parent = self.entity_map.get(r.parent_entity_id, {})
                return MatchResult(r.parent_entity_id, parent.get("canonical_name_zh", ""), norm, "problem", "level_exclusion", 1.0, self._year_status(r.parent_entity_id, year), "county_level_conflict", r.risk_code, 1, [{"entity_id": r.parent_entity_id, "canonical_name": parent.get("canonical_name_zh", ""), "score": 100}])

        builtin = self._exact(norm, year, province_norm)
        custom = self._custom(norm, custom_rules)
        if custom:
            entity = self.entity_map.get(custom, {})
            risks = "custom_override_warning" if builtin and builtin.entity_id != custom else ""
            return MatchResult(custom, entity.get("canonical_name_zh", ""), norm, "auto_matched", "custom_rule", 1.0, self._year_status(custom, year), "prefecture", risks, 1, None, builtin_entity_id=builtin.entity_id if builtin else "")
        if builtin:
            return builtin

        fuzzy = process.extract(norm, self.choices, scorer=fuzz.WRatio, score_cutoff=75, limit=8)
        candidates = []
        for choice, score, _ in fuzzy:
            for item in self.index[choice]:
                entity = self.entity_map[item["entity_id"]]
                if province_norm and normalize_province(entity["province_name_zh"]) != province_norm:
                    continue
                candidates.append({"entity_id": item["entity_id"], "canonical_name": entity["canonical_name_zh"], "matched_name": choice, "score": round(score, 1)})
        unique = {c["entity_id"]: c for c in sorted(candidates, key=lambda x: -x["score"])}
        top = list(unique.values())[:3]
        method = "ocr_candidate" if any(r["method"] == "ocr_variant" for r in self.index.get(norm, [])) else "fuzzy_candidate"
        return MatchResult(normalized_input=norm, match_status="needs_confirmation" if top else "unmatched", match_method=method if top else "none", confidence=(top[0]["score"] / 100 if top else 0), year_status="not_checked", level_status="candidate_only", risk_codes="manual_confirmation_required" if top else "unrecognized_name", candidate_count=len(top), candidates=top)

    def _exact(self, norm: str, year: int | None, province_norm: str) -> MatchResult | None:
        matches = self.index.get(norm, [])
        raw_matches = matches
        if province_norm:
            matches = [m for m in matches if normalize_province(self.entity_map[m["entity_id"]]["province_name_zh"]) == province_norm]
            if not matches and len({m["entity_id"] for m in raw_matches}) == 1:
                entity_id = raw_matches[0]["entity_id"]
                entity = self.entity_map[entity_id]
                return MatchResult(entity_id, entity["canonical_name_zh"], norm, "problem", "province_conflict", 1.0, self._year_status(entity_id, year), "prefecture", "province_mismatch", 1)
        if year is not None and 2000 <= year <= 2024:
            valid = [m for m in matches if m["start"] <= year <= m["end"]]
        else:
            valid = matches
        if not valid and matches and year is not None and 2000 <= year <= 2024:
            all_ids = sorted({m["entity_id"] for m in matches})
            if len(all_ids) == 1:
                entity_id = all_ids[0]
                entity = self.entity_map[entity_id]
                status = self._year_status(entity_id, year)
                risks = ["pre_establishment" if status == "not_established" else "post_abolition" if status == "abolished" else "name_year_mismatch", *self._relation_risks(entity_id, year)]
                return MatchResult(entity_id, entity["canonical_name_zh"], norm, "problem", "name_outside_valid_year", 1.0, status, "prefecture", "|".join(risks), 1)
        ids = sorted({m["entity_id"] for m in valid})
        if len(ids) != 1:
            return None
        entity_id = ids[0]
        if year is None and len({m["entity_id"] for m in matches}) != 1:
            return None
        status = self._year_status(entity_id, year)
        risks = []
        if status == "not_established": risks.append("pre_establishment")
        if status == "abolished": risks.append("post_abolition")
        if status == "unsupported_year": risks.append("unsupported_year")
        risks.extend(self._relation_risks(entity_id, year))
        method = valid[0]["method"]
        if method == "ocr_variant":
            entity = self.entity_map[entity_id]
            return MatchResult(entity_id, entity["canonical_name_zh"], norm, "needs_confirmation", "ocr_candidate", .95, status, "prefecture", "manual_confirmation_required", 1, [{"entity_id": entity_id, "canonical_name": entity["canonical_name_zh"], "score": 95}])
        entity = self.entity_map[entity_id]
        return MatchResult(entity_id, entity["canonical_name_zh"], norm, "problem" if risks else "auto_matched", method, 1.0, status, "prefecture", "|".join(risks), 1)

    @staticmethod
    def _custom(norm: str, rules: pd.DataFrame | None) -> str:
        if rules is None or rules.empty or not {"alias", "entity_id"} <= set(rules.columns):
            return ""
        rows = rules[rules["alias"].map(normalize_name) == norm]
        return str(rows.iloc[-1].entity_id) if len(rows) else ""

    def match_dataframe(self, df: pd.DataFrame, name_col: str, year_col: str | None = None, province_col: str | None = None, custom_rules: pd.DataFrame | None = None) -> tuple[pd.DataFrame, list[MatchResult]]:
        results = [self.match_name(row[name_col], row[year_col] if year_col else None, row[province_col] if province_col else None, custom_rules) for _, row in df.iterrows()]
        out = df.copy()
        for key in results[0].output_columns() if results else MatchResult().output_columns():
            out[key] = [r.output_columns()[key] for r in results]
        return out, results

    def query_entity(self, entity_id: str) -> dict[str, Any]:
        entity = self.entity_map.get(entity_id)
        if entity is None:
            rows = self.historical_entities[self.historical_entities.historical_entity_id == entity_id]
            entity = rows.iloc[0].to_dict() if len(rows) else None
        return {"entity": entity, "names": self.names[self.names.entity_id == entity_id].to_dict("records"), "events": self.query_events(entity_id=entity_id).to_dict("records")}

    def query_events(self, entity_id: str | None = None, province: str | None = None, year: int | None = None, event_type: str | None = None) -> pd.DataFrame:
        df = self.unified_events.copy()
        if entity_id: df = df[df.entity_id == entity_id]
        if province: df = df[df.province_name.map(normalize_province) == normalize_province(province)]
        if year: df = df[df.year.astype(int) == int(year)]
        if event_type: df = df[df.event_type == event_type]
        return df

    def query_wikipedia_rows(self, year: int | None = None, keyword: str | None = None) -> pd.DataFrame:
        df = self.wikipedia_rows.copy()
        if year: df = df[df.year.astype(int) == int(year)]
        if keyword:
            term = normalize_name(keyword)
            df = df[df.row_text.map(normalize_name).str.contains(re.escape(term), na=False)]
        return df

    def query_historical_events(self, entity_id: str | None = None, year: int | None = None, event_type: str | None = None, accepted_only: bool = False) -> pd.DataFrame:
        df = self.wikipedia_normalized_events.copy()
        if entity_id: df = df[df.entity_id == entity_id]
        if year: df = df[df.year.astype(int) == int(year)]
        if event_type: df = df[df.event_type == event_type]
        if accepted_only: df = df[df.normalization_status.str.startswith("accepted_")]
        return df


_default: CrosswalkMatcher | None = None
def _get() -> CrosswalkMatcher:
    global _default
    _default = _default or CrosswalkMatcher()
    return _default
def match_name(name, year=None, province=None, custom_rules=None): return _get().match_name(name, year, province, custom_rules)
def match_dataframe(df, name_col, year_col=None, province_col=None, custom_rules=None): return _get().match_dataframe(df, name_col, year_col, province_col, custom_rules)
def query_entity(entity_id): return _get().query_entity(entity_id)
def query_events(entity_id=None, province=None, year=None, event_type=None): return _get().query_events(entity_id, province, year, event_type)


def audit_report(results: list[MatchResult], config: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for result in results: counts[result.match_status] = counts.get(result.match_status, 0) + 1
    return json.dumps({"data_version": "0.1.0", "rule_version": RULE_VERSION, "configuration": config, "counts": counts, "unresolved": sum(v for k, v in counts.items() if k != "auto_matched")}, ensure_ascii=False, indent=2)
