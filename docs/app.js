const state = { data: null, namesByNormalized: new Map(), countyNamesByNormalized: new Map(), entityMap: new Map(), mapLevel: null, mapFocusProvinceCode: "" };
let historyMap = null;
let historyLayer = null;
let mapLayerById = new Map();
let currentMapGeojson = null;
let selectedMapFeatureId = null;
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeName(value) {
  return String(value ?? "")
    .normalize("NFKC")
    .replaceAll("巿", "市")
    .replace(/[\s\u200b-\u200f\u2060\ufeff·•,，。.;；:：()（）\[\]【】_-]+/g, "")
    .trim();
}

function normalizeProvince(value) {
  let text = normalizeName(value);
  for (const suffix of ["壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "省", "市"]) {
    if (text.endsWith(suffix)) return text.slice(0, -suffix.length);
  }
  return text;
}

function number(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function coverageYears() {
  const meta = state.data?.meta || {};
  return {
    eventStart: Number(meta.eventStartYear || 1983),
    eventEnd: Number(meta.eventEndYear || 2026),
    statusStart: Number(meta.statusStartYear || 1987),
    statusEnd: Number(meta.statusEndYear || 2026),
  };
}

function yearStatusText(status) {
  return {
    not_checked: "未选择年份",
    early_event_only: "早期事件层（无年末状态）",
    unsupported_year: "年份超出项目覆盖范围",
    invalid_year: "年份格式无效",
    active: "年末存在",
    abolished: "年末已撤销",
    not_established: "年末尚未设立",
    not_prefecture_level: "年末非地级层级",
    unknown: "年末状态未核定",
  }[status] || status || "未核验";
}

function riskText(value) {
  const labels = {
    province_conflict: "省份与实体记录不一致",
    name_outside_valid_year: "名称不在所选年份的有效区间",
    pre_establishment: "所选年份早于地级实体设立",
    post_abolition: "所选年份晚于实体撤销",
    merge_event: "涉及合并事件，不能自动延续统计值",
    split_event: "涉及拆分事件，不能自动延续统计值",
    name_changed_during_year: "名称在该自然年内发生变化，结果按年末名称返回",
    unsupported_year: "年份超出项目覆盖范围",
    invalid_year: "年份必须是完整的四位整数",
    early_event_only: "该年份只有事件证据，尚无完整年末状态表",
  };
  return String(value || "").split("|").filter(Boolean).map((item) => labels[item] || item).join("、");
}

function methodText(method) {
  return {
    exact: "精确名称匹配",
    official_name_valid_during_year: "年内正式名称匹配",
    selected_candidate: "已选择候选实体",
    name_outside_valid_year: "名称年份冲突",
    province_conflict: "省份冲突",
  }[method] || method || "—";
}

function reviewStatusText(status) {
  return {
    accepted_reviewed: "已复核",
    accepted_rule_extraction: "规则提取后已接受",
    accepted_manual_review: "人工复核后已接受",
    early_source_text_parsed: "早期资料解析记录",
    inferred: "推定时间口径",
    reviewed: "时间口径已复核",
    review_required: "仍需复核",
  }[status] || "";
}

function entityFor(id) {
  return state.entityMap.get(id) || { entity_id: id, canonical_name_zh: "", province_name_zh: "" };
}

function rosterStatus(entityId, year) {
  if (year === null) return "not_checked";
  const years = coverageYears();
  if (!Number.isInteger(year)) return "invalid_year";
  if (year < years.eventStart || year > years.eventEnd) return "unsupported_year";
  if (year < years.statusStart) return "early_event_only";
  return state.data.rosterStatus[entityId]?.[String(year)] || "unknown";
}

function rosterYearEndName(entityId, year) {
  const years = coverageYears();
  if (year === null || year < years.statusStart || year > years.statusEnd) return "";
  return state.data.rosterYearEndName?.[entityId]?.[String(year)] || "";
}

function relationRisks(entityId, year) {
  if (year === null) return [];
  return [...new Set(state.data.relations
    .filter((row) => row.entity_id === entityId && ["merge", "split"].includes(row.relation_type) && year >= Number(row.year))
    .map((row) => `${row.relation_type}_event`))];
}

function similarity(a, b) {
  if (a === b) return 1;
  if (!a || !b) return 0;
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    const current = [i];
    for (let j = 1; j <= b.length; j += 1) {
      current[j] = Math.min(
        current[j - 1] + 1,
        previous[j] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
      );
    }
    previous.splice(0, previous.length, ...current);
  }
  return 1 - previous[b.length] / Math.max(a.length, b.length);
}

function partialSimilarity(query, choice) {
  if (query.length < 1 || choice.length < 2) return 0;
  const ratio = Math.min(query.length, choice.length) / Math.max(query.length, choice.length);
  if (choice.startsWith(query)) return 0.9 + ratio * 0.08;
  if (choice.includes(query)) return 0.82 + ratio * 0.1;
  if (query.startsWith(choice)) return 0.8 + ratio * 0.08;
  return 0;
}

function countySearchNames(row) {
  return [...new Set([
    ...(row.old_county_units || "").split("、"),
    ...(row.new_county_units || "").split("、"),
    ...(row.county_names || "").split("、"),
  ].map((name) => name.trim()).filter((name) => name.length >= 2))];
}

function makeResult(name, year, province) {
  const normalized = normalizeName(name);
  if (!normalized) return { status: "unmatched", method: "none", normalized, risk: "blank_name" };
  const provinceNormalized = normalizeProvince(province);
  const rawMatches = state.namesByNormalized.get(normalized) || [];
  const exactEnabled = normalized.length >= 2;
  let matches = exactEnabled ? rawMatches.filter((item) => {
    const entity = entityFor(item.entity_id);
    return !provinceNormalized || normalizeProvince(entity.province_name_zh) === provinceNormalized;
  }) : [];
  if (exactEnabled && !matches.length && rawMatches.length && provinceNormalized) {
    const unique = [...new Set(rawMatches.map((item) => item.entity_id))];
    if (unique.length === 1) return problemResult(unique[0], normalized, year, "province_conflict", "省份与实体记录不一致");
  }
  const years = coverageYears();
  if (exactEnabled && year !== null && year >= years.statusStart && year <= years.statusEnd) {
    const valid = matches.filter((item) => item.start <= year && year <= item.end);
    if (valid.length) matches = valid;
    else if (matches.length && new Set(matches.map((item) => item.entity_id)).size === 1) {
      return problemResult(matches[0].entity_id, normalized, year, "name_outside_valid_year", "名称与所选年份的有效区间不一致");
    }
  }
  const ids = [...new Set(matches.map((item) => item.entity_id))];
  if (normalized.length >= 2 && ids.length === 1 && (year !== null || new Set(rawMatches.map((item) => item.entity_id)).size === 1)) {
    const entity = entityFor(ids[0]);
    const status = rosterStatus(ids[0], year);
    const blockingRisks = relationRisks(ids[0], year);
    if (["unsupported_year", "invalid_year"].includes(status)) blockingRisks.push(status);
    if (status === "not_established" || status === "not_prefecture_level") blockingRisks.push("pre_establishment");
    if (status === "abolished") blockingRisks.push("post_abolition");
    const yearEndName = rosterYearEndName(ids[0], year);
    const nameValidity = year === null ? "not_checked" : status === "early_event_only" ? "not_reconstructed" : normalizeName(yearEndName) === normalized ? "year_end_name" : "valid_during_year";
    const informationalRisks = nameValidity === "valid_during_year" ? ["name_changed_during_year"] : status === "early_event_only" ? ["early_event_only"] : [];
    const risks = [...new Set([...blockingRisks, ...informationalRisks])];
    return { entity, entityId: ids[0], normalized, status: blockingRisks.length ? "problem" : "auto_matched", method: matches[0]?.method || "exact", confidence: 1, yearStatus: status, yearEndName, yearBasis: year === null ? "" : "year_end", nameValidity, transitionEventIds: matches[0]?.transitionEventIds || "", risk: risks.join("|") };
  }

  const candidates = [];
  const searchIndexes = [
    [state.namesByNormalized, "prefecture"],
    [state.countyNamesByNormalized, "county"],
  ];
  for (const [searchIndex, matchSource] of searchIndexes) {
    for (const [choice, items] of searchIndex.entries()) {
      const partialScore = partialSimilarity(normalized, choice);
      const fuzzyScore = similarity(normalized, choice);
      const score = Math.max(partialScore, fuzzyScore >= 0.75 ? fuzzyScore : 0);
      if (!score) continue;
      const matchType = partialScore > 0 ? "partial" : "fuzzy";
      for (const item of items) {
        const entity = entityFor(item.entity_id);
        if (provinceNormalized && normalizeProvince(entity.province_name_zh) !== provinceNormalized) continue;
        candidates.push({ entity, entityId: item.entity_id, matchedName: item.name, matchType, matchSource, score: Math.round(score * 1000) / 10 });
      }
    }
  }
  const bestByEntity = new Map();
  for (const candidate of candidates) {
    const current = bestByEntity.get(candidate.entityId);
    if (!current || candidate.score > current.score || (candidate.score === current.score && candidate.matchSource === "county" && current.matchSource !== "county")) {
      bestByEntity.set(candidate.entityId, candidate);
    }
  }
  const deduplicated = [...bestByEntity.values()].sort((a, b) => b.score - a.score || a.entity.canonical_name_zh.localeCompare(b.entity.canonical_name_zh, "zh-CN"));
  const method = deduplicated.some((candidate) => candidate.matchType === "partial") ? "partial_candidate" : "fuzzy_candidate";
  const unique = method === "partial_candidate" ? deduplicated : deduplicated.slice(0, 3);
  return { normalized, status: unique.length ? "needs_confirmation" : "unmatched", method: unique.length ? method : "none", confidence: unique[0]?.score ? unique[0].score / 100 : 0, yearStatus: "not_checked", risk: unique.length ? "manual_confirmation_required" : "unrecognized_name", candidates: unique };
}

function problemResult(entityId, normalized, year, method, risk) {
  const entity = entityFor(entityId);
  return { entity, entityId, normalized, status: "problem", method, confidence: 1, yearStatus: rosterStatus(entityId, year), yearEndName: rosterYearEndName(entityId, year), yearBasis: year === null ? "" : "year_end", nameValidity: "outside_year", risk };
}

function selectedEntityResult(entityId, name, year) {
  const risks = relationRisks(entityId, year);
  const status = rosterStatus(entityId, year);
  if (["unsupported_year", "invalid_year"].includes(status)) risks.push(status);
  if (status === "not_established") risks.push("pre_establishment");
  if (status === "abolished") risks.push("post_abolition");
  return {
    entity: entityFor(entityId),
    entityId,
    normalized: normalizeName(name),
    status: risks.length ? "problem" : "auto_matched",
    method: "selected_candidate",
    confidence: 1,
    yearStatus: status,
    yearEndName: rosterYearEndName(entityId, year),
    yearBasis: year === null ? "" : "year_end",
    nameValidity: "selected_candidate",
    risk: [...new Set(risks)].join("|"),
  };
}

function statusText(status) {
  return { auto_matched: "已匹配", needs_confirmation: "候选结果", problem: "需核对", unmatched: "未匹配" }[status] || status;
}

function canonicalNameHistoryHtml(entityId) {
  const rows = (state.data.yearEndNames || [])
    .filter((item) => item.entity_id === entityId)
    .map((item) => ({ name: item.name, start: Number(item.start), end: Number(item.end) }))
    .sort((a, b) => a.start - b.start || a.end - b.end || a.name.localeCompare(b.name, "zh-CN"));
  const unique = [...new Map(rows.map((row) => [`${row.name}|${row.start}|${row.end}`, row])).values()];
  if (!unique.length) return "";
  const years = coverageYears();
  const sequence = unique.map((row) => `${escapeHtml(row.name)}（${escapeHtml(nameSpanText(row, years))}）`).join("→");
  return `<div class="prefecture-name-block"><span>年末规范名沿革</span><p class="canonical-history-line">${sequence}</p><p class="county-history-note">项目年末名称状态覆盖：${years.statusStart}—${years.statusEnd}；事件查询覆盖：${years.eventStart}—${years.eventEnd}。覆盖边界不表示名称在边界年份自然生效或终止。</p></div>`;
}

function nameSpanText(row, years = coverageYears()) {
  if (Number(row.start) === years.statusStart && Number(row.end) === years.statusEnd) return "覆盖期内持续使用";
  if (Number(row.start) === years.statusStart) return `覆盖起点时已使用；至${row.end}年末`;
  if (Number(row.end) === years.statusEnd) return `自${row.start}年末；持续至数据终点`;
  if (Number(row.start) === Number(row.end)) return `${row.start}年末`;
  return `${row.start}—${row.end}年末`;
}

function prefectureEventTypeText(type) {
  return {
    jurisdiction_transfer: "行政隶属调整",
    jurisdiction_adjustment: "辖区调整",
    upgrade: "升格/省直管调整",
    establish: "设立",
    rename: "更名",
    merge: "合并",
    split: "拆分",
    abolish: "撤销",
  }[type] || "地级行政单位变动";
}

function prefectureSourceLabel(row) {
  if (row.source_type === "people_daily_summary") return "人民日报版面";
  if (row.source_type === "secondary_transcription") return "区划地名网转录";
  if (row.source_type === "state_council_gazette_archive") return "国务院公报";
  return "Wikipedia 年度页";
}

function prefectureDescription(row) {
  const source = String(row.description || row.review_note || "");
  const chunks = source.split("|").map((chunk) => chunk.trim()).filter(Boolean);
  const actionPattern = /撤销|设立|更名|升为|改由|恢复|划归|合并|迁至|迁驻|调整|代管|改为|升格|析置|撤地/;
  const selected = chunks.filter((chunk) => actionPattern.test(chunk)).sort((a, b) => b.length - a.length)[0] || source;
  return selected
    .replace(/<br\s*\/?>(?=\s*\S)/gi, " ")
    .replace(/<[^>]*>/g, "")
    .replace(/(?:colspan|rowspan|id)\s*=\s*["'][^"']*["']/gi, "")
    .replace(/\s+/g, " ")
    .replace(/^[|；;、\s]+|[|；;、\s]+$/g, "")
    .trim();
}

function timingBasisText(basis) {
  return {
    official_announcement_and_implementation: "按公布及实施资料",
    official_publication_and_implementation: "按公布及实施资料",
    approval_date_inferred: "按批准日期推定",
    event_year_only: "按事件年份推定",
  }[basis] || (basis ? `按${basis}` : "未标注推定依据");
}

function eventTimingText(row) {
  const dates = [];
  if (row.approval_date) dates.push(`批准 ${row.approval_date}`);
  if (row.announcement_date) dates.push(`公布 ${row.announcement_date}`);
  if (row.effective_date) dates.push(`生效 ${row.effective_date}`);
  if (row.implementation_date) dates.push(`实施 ${row.implementation_date}`);
  const annualYear = row.annual_effective_year || row.year;
  if (annualYear) dates.push(`年末口径 ${annualYear}年（${timingBasisText(row.annual_effective_basis || "event_year_only")}）`);
  if (row.date_precision && row.date_precision !== "day") dates.push(`精度：${row.date_precision === "month" ? "月" : "年"}`);
  if (row.temporal_confidence && row.temporal_confidence !== "high") dates.push(`时间置信度：${row.temporal_confidence === "medium" ? "中" : "低"}`);
  return dates.join("；") || "未记录精确日期；仅有年度变更记录";
}

function prefectureUnitTypes(row) {
  const text = `${row.prefecture_names || ""}${row.description || ""}`;
  const types = ["市", "地区", "自治州", "盟"].filter((type) => text.includes(type));
  return types.length ? types.join("、") : "地级行政单位";
}

function prefectureEventsHtml(entityId) {
  const rows = (state.data.events || [])
    .filter((row) => String(row.entity_ids || row.entity_id || "").split("、").includes(entityId))
    .sort((a, b) => Number(b.year) - Number(a.year) || a.event_id.localeCompare(b.event_id));
  const nameHistory = canonicalNameHistoryHtml(entityId);
  if (!rows.length && !nameHistory) return "";
  const visible = rows.slice(0, 12);
  const more = rows.length > visible.length ? `<p class="county-history-more">另有 ${rows.length - visible.length} 条地级行政单位记录，见仓库中的地级事件数据。</p>` : "";
  return `<div class="county-history prefecture-history"><div class="county-history-head"><div class="section-label">规范名沿革与地级行政区划变更</div><span>${rows.length} 条变更记录</span></div>${nameHistory}<p class="county-history-note">变更记录保留来源描述；地级行政单位包括市、地区、自治州、盟等。事件日期区分批准、公布、实施和年末采用口径；没有实施日时会明确标注推定依据。</p>${rows.length ? `<div class="county-event-list">${visible.map((row) => { const locator = row.source_locator ? ` · ${escapeHtml(row.source_locator)}` : ""; return `<article class="county-event"><div class="county-event-meta"><strong>${escapeHtml(row.year)}年</strong><span class="event-type">${escapeHtml(prefectureEventTypeText(row.event_type))}</span></div><div class="county-event-change"><span>变更描述</span><p>${escapeHtml(prefectureDescription(row) || "暂无描述")}</p></div><div class="county-event-change"><span>时间口径</span><p>${escapeHtml(eventTimingText(row))}</p></div><div class="county-event-foot"><span>涉及类型：${escapeHtml(prefectureUnitTypes(row))}</span>${row.source_url ? `<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(prefectureSourceLabel(row))} ↗${locator}</a>` : ""}</div></article>`; }).join("")}</div>${more}` : ""}</div>`;
}

function countyEventTypeText(type) {
  return {
    jurisdiction_transfer: "行政隶属调整",
    merge: "合并",
    split: "拆分/分设",
    rename: "更名",
    residence_change: "驻地变更",
    abolish_or_merge: "撤销/合并",
    establish: "设立",
    jurisdiction_adjustment: "辖区调整",
    county_change: "县级变动",
  }[type] || "县级变动";
}

function countyEventUnitsHtml(row) {
  const oldUnits = String(row.old_county_units || "").trim();
  const newUnits = String(row.new_county_units || "").trim();
  if (!oldUnits && !newUnits) return "";
  return `<div class="county-event-flow"><div><span>变更前 / 涉及单位</span><strong>${escapeHtml(oldUnits || "—")}</strong></div><b>→</b><div><span>变更后 / 去向单位</span><strong>${escapeHtml(newUnits || "—")}</strong></div></div>`;
}

function countyEventsHtml(entityId) {
  const rows = (state.data.countyEvents || [])
    .filter((row) => String(row.prefecture_entity_ids || "").split("、").includes(entityId) && row.scope !== "non_county_development_zone")
    .sort((a, b) => Number(b.year) - Number(a.year) || a.event_id.localeCompare(b.event_id));
  if (!rows.length) return "";
  const visible = rows.slice(0, 12);
  const more = rows.length > visible.length ? `<p class="county-history-more">另有 ${rows.length - visible.length} 条记录，见仓库中的县级事件数据。</p>` : "";
  return `<div class="county-history"><div class="county-history-head"><div class="section-label">县级变更记录</div><span>${rows.length} 条相关记录</span></div><p class="county-history-note">记录包括撤销、设立、合并、改隶、辖区调整和驻地变更。地级关联按名称匹配，县级谱系请结合原始资料核对；县级网页记录目前按来源年度展示，不把年度行误读为逐日实施日期。</p><div class="county-event-list">${visible.map((row) => { const sourceLabel = row.source_type === "people_daily_summary" ? "人民日报版面" : row.source_type === "secondary_transcription" ? "区划地名网转录" : row.source_type === "state_council_gazette_archive" ? "国务院公报" : "Wikipedia 年度页"; const locator = row.source_locator ? ` · ${escapeHtml(row.source_locator)}` : ""; return `<article class="county-event"><div class="county-event-meta"><strong>${escapeHtml(row.year)}年</strong><span class="event-type">${escapeHtml(countyEventTypeText(row.event_type))}</span></div>${countyEventUnitsHtml(row)}<div class="county-event-change"><span>变更描述</span><p>${escapeHtml(row.change_description || row.description)}</p></div><div class="county-event-foot">${row.county_unit_types ? `涉及类型：${escapeHtml(row.county_unit_types)}` : "类型未标注"}<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">${sourceLabel} ↗${locator}</a></div></article>`; }).join("")}</div>${more}</div>`;
}

function resultHtml(result, name, year, province) {
  if (result.status === "unmatched") {
    return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>没有找到确定结果</h2></div><span class="status problem">未匹配</span></div><p class="result-note">可补充年份、省份，或检查名称。</p>`;
  }
  if (result.status === "needs_confirmation") {
    const candidateNote = result.method === "partial_candidate" ? `找到 ${result.candidates.length} 个片段候选，按匹配度排列。` : "当前有多个候选，请结合年份、省份和来源判断。";
    return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>${escapeHtml(name)}</h2></div><span class="status warn">候选结果</span></div><p class="result-note">${candidateNote} 点击卡片查看实体详情。</p><div class="candidate-list"><h3>候选实体</h3>${result.candidates.map((item) => `<button class="candidate" type="button" data-candidate-id="${escapeHtml(item.entityId)}" data-candidate-name="${escapeHtml(item.matchedName)}" title="查看 ${escapeHtml(item.entity.canonical_name_zh)}"><span><strong>${escapeHtml(item.entity.canonical_name_zh)} · ${escapeHtml(item.entityId)}</strong><small>命中名称：${escapeHtml(item.matchedName)} · ${item.matchSource === "county" ? "县级关联" : item.matchType === "partial" ? "部分匹配" : "相似匹配"}</small></span><b>${item.score}%</b></button>`).join("")}</div>`;
  }
  const entity = result.entity;
  const years = coverageYears();
  const riskMessage = result.risk ? `状态：${escapeHtml(riskText(result.risk))}` : "名称、年份和层级匹配。";
  const yearNote = result.yearStatus === "early_event_only" ? `该年份（${year}）仅能查看事件证据；年末状态和名称层从${years.statusStart}年开始。` : result.yearStatus === "unsupported_year" ? `请输入${years.eventStart}—${years.eventEnd}范围内的年份。` : "";
  const statusNote = yearStatusText(result.yearStatus);
  const nameValue = year === null ? entity.canonical_name_zh : result.yearStatus === "early_event_only" ? "未重建" : result.yearStatus === "unsupported_year" || result.yearStatus === "invalid_year" ? "不适用" : result.yearEndName || "未记录";
  const nameLabel = year === null ? "当前规范名称" : `${year} 年末名称`;
  return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>${escapeHtml(entity.canonical_name_zh || result.entityId)}</h2><p class="muted">${escapeHtml(result.entityId)} · ${escapeHtml(entity.province_name_zh)}</p></div><span class="status ${result.status === "problem" ? "problem" : "ok"}">${statusText(result.status)}</span></div><div class="result-grid"><div class="result-stat"><strong>${escapeHtml(result.entityId)}</strong><span>研究实体编号</span></div><div class="result-stat"><strong>${escapeHtml(statusNote)}</strong><span>${year === null ? "年份状态" : `${year} 年末状态`}</span></div><div class="result-stat"><strong>${escapeHtml(nameValue)}</strong><span>${escapeHtml(nameLabel)}</span></div><div class="result-stat"><strong>${Math.round(result.confidence * 100)}%</strong><span>匹配置信度</span></div></div><p class="result-note">${riskMessage}${yearNote ? ` ${yearNote}` : ""}</p>${prefectureEventsHtml(result.entityId)}${countyEventsHtml(result.entityId)}<p class="result-source">输入：${escapeHtml(name)} · 规范化：${escapeHtml(result.normalized)} · 方法：${escapeHtml(methodText(result.method))}${year !== null ? ` · 口径：${year}年末` : ""}${province ? ` · 省份：${escapeHtml(province)}` : ""}</p>`;
}

function renderMatch() {
  const name = $("#name-input").value.trim();
  const province = $("#province-input").value.trim();
  const year = number($("#year-input").value);
  if (!name) return;
  $("#match-result").innerHTML = resultHtml(makeResult(name, year, province), name, year, province);
  bindCandidateCards();
}

function bindCandidateCards() {
  $$("#match-result [data-candidate-id]").forEach((card) => card.addEventListener("click", () => {
    const name = card.dataset.candidateName || card.dataset.candidateId;
    const province = $("#province-input").value.trim();
    $("#name-input").value = name;
    const year = number($("#year-input").value);
    $("#match-result").innerHTML = resultHtml(selectedEntityResult(card.dataset.candidateId, name, year), name, year, province);
  }));
}

function renderEvents() {
  const year = $("#event-year").value;
  const keyword = normalizeName($("#event-keyword").value);
  const rows = state.data.events.filter((row) => (!year || row.year === year) && (!keyword || normalizeName(`${row.province_name}${row.prefecture_names}${row.description}`).includes(keyword))).slice(0, 100);
  if (!rows.length) { $("#event-list").innerHTML = '<div class="empty-table">没有符合条件的事件。</div>'; return; }
  $("#event-list").innerHTML = `<table class="event-table"><thead><tr><th>年份</th><th>省份</th><th>类型</th><th>变更描述</th><th>时间口径</th><th>来源</th></tr></thead><tbody>${rows.map((row) => { const source = [row.document_number, row.source_locator].filter(Boolean).join(" · ") || "年度变更记录"; return `<tr><td>${escapeHtml(row.year)}</td><td>${escapeHtml(row.province_name)}</td><td><span class="event-type">${escapeHtml(prefectureEventTypeText(row.event_type))}</span></td><td>${escapeHtml(prefectureDescription(row))}</td><td>${escapeHtml(eventTimingText(row))}</td><td>${escapeHtml(source)}${reviewStatusText(row.review_status) ? `<br><small>${escapeHtml(reviewStatusText(row.review_status))}</small>` : ""}</td></tr>`; }).join("")}</tbody></table>`;
}

function mapEntityHistoryHtml(properties) {
  if (properties.external_only) {
    const levelName = properties.map_level === "province" ? "省级" : properties.map_level === "prefecture" ? "地级" : "县级";
    return `<div class="map-entity-card"><span>行政层级</span><strong>${levelName}</strong><span>名称</span><strong>${escapeHtml(properties.display_name_zh || properties.source_name)}</strong></div>`;
  }
  if (properties.map_level === "province") {
    return `<div class="map-entity-card context"><span>行政层级</span><strong>省级</strong><span>省级类型</span><strong>${escapeHtml(properties.province_type || "—")}</strong></div>`;
  }
  if (properties.map_level === "county") {
    const related = (state.data.countyEvents || []).filter((row) => normalizeName(`${row.county_names}${row.old_county_units}${row.new_county_units}`).includes(normalizeName(properties.source_name))).sort((a, b) => Number(b.year) - Number(a.year)).slice(0, 8);
    const parent = properties.parent_entity_id ? `<span>上级地级 CNUR</span><strong>${escapeHtml(properties.parent_entity_id)}</strong><span>${properties.panel_year} 年末上级名称</span><strong>${escapeHtml(properties.parent_year_end_name || properties.prefecture_name || "—")}</strong>` : `<span>上级地级 CNUR</span><strong>无（省直辖或范围外）</strong>`;
    const events = related.length ? `<div class="map-history"><span>相关县级变更记录</span>${related.map((row) => `<article><b>${escapeHtml(row.year)} · ${escapeHtml(countyEventTypeText(row.event_type))}</b><small>${escapeHtml(row.change_description || row.description)}</small>${row.source_url ? `<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">来源 ↗</a>` : ""}</article>`).join("")}</div>` : `<p class="county-history-note">当前事件库没有检索到该县级名称的相关变更记录。</p>`;
    return `<div class="map-entity-card"><span>县级类型</span><strong>${escapeHtml(properties.county_type || "—")}</strong><span>上级地级单位</span><strong>${escapeHtml(properties.prefecture_name || "省级直接管辖")}</strong>${parent}${properties.former_name ? `<span>来源曾用名</span><strong>${escapeHtml(properties.former_name)}</strong>` : ""}</div>${properties.note ? `<p class="county-history-note">来源备注：${escapeHtml(properties.note)}</p>` : ""}${events}`;
  }
  if (!properties.entity_id) {
    const label = properties.context_kind === "out_of_scope_province" ? "当前项目范围外" : "CTAmap 非地级背景要素";
    return `<div class="map-entity-card context"><span>区域类型</span><strong>${label}</strong><span>CNUR 状态</span><strong>不分配地级研究实体编号</strong></div><p class="county-history-note">该区域用于补全地图背景。多数是省直辖县级单位，但历史存在状态仍应结合年度资料核验。</p>`;
  }
  const names = (state.data.yearEndNames || []).filter((row) => row.entity_id === properties.entity_id).sort((a, b) => Number(a.start) - Number(b.start));
  const events = (state.data.events || []).filter((row) => `${row.entity_id || ""}、${row.entity_ids || ""}、${row.prefecture_entity_ids || ""}`.includes(properties.entity_id)).sort((a, b) => Number(b.year) - Number(a.year)).slice(0, 6);
  const years = coverageYears();
  const nameHistory = names.length ? `<div class="map-history"><span>年末名称沿革</span><p>${names.map((row) => `${escapeHtml(row.name)}（${escapeHtml(nameSpanText(row, years))}）`).join(" → ")}</p><small>项目年末名称状态覆盖：${years.statusStart}—${years.statusEnd}；事件查询覆盖：${years.eventStart}—${years.eventEnd}。覆盖边界不表示名称真实生效或终止。</small></div>` : "";
  const eventHistory = events.length ? `<div class="map-history"><span>相关地级事件</span>${events.map((row) => `<button type="button" data-map-event-year="${escapeHtml(row.year)}"><b>${escapeHtml(row.year)} · ${escapeHtml(prefectureEventTypeText(row.event_type))}</b><small>${escapeHtml(prefectureDescription(row))}</small><small>${escapeHtml(eventTimingText(row))}</small></button>`).join("")}</div>` : "";
  return `<div class="map-entity-card"><span>CNUR 实体</span><strong>${escapeHtml(properties.entity_id)}</strong><span>${properties.panel_year} 年末名称</span><strong>${escapeHtml(properties.year_end_name || "—")}</strong></div>${nameHistory}${eventHistory}`;
}

function mapFeatureStyle(feature) {
  if (feature.properties.external_only) return { color: "#fffefa", weight: .9, fillColor: "#c59a62", fillOpacity: .84, dashArray: "4 3" };
  if (feature.properties.map_level === "province") return { color: "#fffefa", weight: .8, fillColor: "#6f9fc6", fillOpacity: .78 };
  if (feature.properties.map_level === "county") return { color: "#fffefa", weight: .45, fillColor: feature.properties.parent_entity_id ? "#d9a05b" : "#d8ddd8", fillOpacity: .82 };
  return feature.properties.link_status === "linked" ? { color: "#fffefa", weight: .65, fillColor: "#78b999", fillOpacity: .78 } : { color: "#fffefa", weight: .55, fillColor: "#d8ddd8", fillOpacity: .82 };
}

function selectMapFeature(featureId) {
  if (selectedMapFeatureId && mapLayerById.has(selectedMapFeatureId)) {
    const previous = mapLayerById.get(selectedMapFeatureId);
    previous.layer.setStyle(mapFeatureStyle(previous.feature));
    previous.layer.getElement()?.classList.remove("map-feature-selected");
  }
  selectedMapFeatureId = featureId;
  const selected = mapLayerById.get(featureId);
  if (!selected) return;
  selected.layer.setStyle({ color: "#e9784f", weight: 3, opacity: 1, dashArray: null, lineCap: "round", lineJoin: "round" });
  selected.layer.getElement()?.classList.add("map-feature-selected");
  if (typeof selected.layer.bringToFront === "function") selected.layer.bringToFront();
}

function showMapFeature(featureId, zoom = false) {
  const item = mapLayerById.get(featureId);
  if (!item) return;
  const { feature, layer } = item;
  const p = feature.properties;
  selectMapFeature(featureId);
  if (zoom) historyMap.fitBounds(layer.getBounds(), { padding: [35, 35], maxZoom: 7 });
  historyMap.eachLayer((candidate) => { if (typeof candidate.closeTooltip === "function") candidate.closeTooltip(); });
  layer.openTooltip();
  const typeLabel = p.map_level === "province" ? p.province_type : p.map_level === "county" ? p.county_type : p.prefecture_type;
  const displayName = p.external_only ? p.display_name_zh : p.source_name;
  const mapLevelText = p.map_level === "province" ? "省级" : p.map_level === "county" ? "县级" : "地级";
  $("#map-detail").innerHTML = `<div class="section-label">${p.external_only ? mapLevelText : `${p.snapshot_year}年初 / ${p.panel_year}年末 · ${mapLevelText}`}</div><h2>${escapeHtml(displayName)}</h2><p class="muted">${escapeHtml(p.province_name || "")} · ${escapeHtml(typeLabel || "—")} · ${escapeHtml(p.source_code || "")}</p>${mapEntityHistoryHtml(p)}<p class="map-source-links"><a href="https://github.com/FIERsity/china-prefecture-crosswalk/blob/main/data/raw/external_boundaries/manifest.json" target="_blank" rel="noreferrer">来源清单与许可 ↗</a></p>`;
  $$('[data-map-event-year]').forEach((button) => button.addEventListener("click", () => { $("#event-year").value = button.dataset.mapEventYear; $("#event-keyword").value = p.source_name; switchView("events"); }));
}

function searchHistoryMap() {
  const query = normalizeName($("#map-search-input").value);
  if (!query || !currentMapGeojson) return;
  const historicalEntityIds = new Set((state.data.names || []).filter((row) => normalizeName(`${row.name}${row.normalized}`).includes(query)).map((row) => row.entity_id));
  const matches = currentMapGeojson.features.filter((feature) => {
    const p = feature.properties;
    return historicalEntityIds.has(p.entity_id) || historicalEntityIds.has(p.parent_entity_id) || [p.display_name_zh, p.source_name, p.year_end_name, p.source_code, p.entity_id, p.province_name, p.province_code, p.prefecture_name, p.prefecture_code, p.parent_entity_id, p.former_name].some((value) => normalizeName(value).includes(query));
  });
  const exact = matches.find((feature) => [feature.properties.display_name_zh, feature.properties.source_name, feature.properties.year_end_name, feature.properties.source_code, feature.properties.entity_id].some((value) => normalizeName(value) === query));
  if (exact) { showMapFeature(exact.id, true); return; }
  if (matches.length === 1) { showMapFeature(matches[0].id, true); return; }
  $("#map-detail").innerHTML = matches.length ? `<div class="section-label">SEARCH RESULT</div><h2>找到 ${matches.length} 个区域</h2><div class="map-search-results">${matches.slice(0, 20).map((feature) => `<button type="button" data-map-feature-id="${escapeHtml(feature.id)}"><strong>${escapeHtml(feature.properties.source_name)}</strong><span>${escapeHtml(feature.properties.province_name)} · ${escapeHtml(feature.properties.source_code)}</span></button>`).join("")}</div>` : `<p class="result-note">当前地图没有找到“${escapeHtml($("#map-search-input").value)}”。可尝试历史名称、六位区划码或 CNUR 编号。</p>`;
  $$('[data-map-feature-id]').forEach((button) => button.addEventListener("click", () => showMapFeature(button.dataset.mapFeatureId, true)));
}

async function renderHistoryMap() {
  const panelYear = Number($("#map-panel-year").value || 2023);
  const snapshotYear = panelYear + 1;
  const mapLevel = $("#map-level").value || "prefecture";
  const provinceCode = $("#map-province").value || "420000";
  const focusProvinceCode = mapLevel === "county" ? "" : (state.mapFocusProvinceCode || "");
  if (!window.L) { $("#map-detail").innerHTML = '<p class="result-note">地图组件加载失败，请刷新页面。</p>'; return; }
  if (!historyMap) {
    historyMap = L.map("history-map", { zoomControl: true, attributionControl: false, minZoom: 3, maxZoom: 9 });
  }
  const externalProvinceGroups = { "710000": "taiwan", "810000": "hongkong", "820000": "macau" };
  const externalGroup = provinceCode.startsWith("EXTERNAL-") ? provinceCode.slice("EXTERNAL-".length).toLowerCase() : externalProvinceGroups[provinceCode] || "";
  const mapPath = mapLevel === "county" && externalGroup ? "data/maps/external/external_county.geojson" : mapLevel === "county" ? `data/maps/county/${snapshotYear}/${provinceCode}.geojson` : `data/maps/${mapLevel}/${snapshotYear}.geojson`;
  const response = await fetch(mapPath);
  if (!response.ok) throw new Error(`map ${response.status}`);
  const geojson = await response.json();
  if (externalGroup) geojson.features = geojson.features.filter((feature) => feature.properties.external_group === externalGroup);
  if (mapLevel === "prefecture") {
    const taiwanResponse = await fetch("data/maps/external/taiwan_prefecture.geojson");
    if (taiwanResponse.ok) {
      const taiwan = await taiwanResponse.json();
      geojson.features = geojson.features.concat(taiwan.features);
    }
  }
  if (mapLevel === "province") {
    const externalResponse = await fetch("data/maps/external/external_current.geojson");
    if (externalResponse.ok) {
      const external = await externalResponse.json();
      geojson.features = geojson.features.concat(external.features);
    }
  }
  currentMapGeojson = geojson;
  mapLayerById = new Map();
  selectedMapFeatureId = null;
  if (historyLayer) historyLayer.remove();
  historyLayer = L.geoJSON(geojson, {
    style: mapFeatureStyle,
    onEachFeature(feature, layer) {
      const p = feature.properties;
      mapLayerById.set(feature.id, { feature, layer });
      const parentLabel = p.map_level === "county" && p.prefecture_name ? ` · ${p.prefecture_name}` : "";
      const tooltipLabel = p.external_only ? p.display_name_zh : p.map_level === "province" ? p.source_name : `${p.source_name} · ${p.province_name}${parentLabel}`;
      layer.bindTooltip(tooltipLabel, { sticky: true });
      layer.on({
        mouseover: () => { if (selectedMapFeatureId !== feature.id) layer.setStyle({ color: "#1f6e5a", weight: 1.5, fillOpacity: .9 }); },
        mouseout: () => { if (selectedMapFeatureId !== feature.id) layer.setStyle(mapFeatureStyle(feature)); },
        click: () => showMapFeature(feature.id),
      });
    },
  }).addTo(historyMap);
  const focusGroup = { "710000": "taiwan", "810000": "hongkong", "820000": "macau" }[focusProvinceCode] || "";
  const focusFeatures = focusProvinceCode ? geojson.features.filter((feature) => {
    const properties = feature.properties || {};
    if (focusGroup) {
      if (mapLevel === "province") return properties.external_only && properties.display_name_zh === { taiwan: "台湾省", hongkong: "香港特别行政区", macau: "澳门特别行政区" }[focusGroup];
      return properties.external_group === focusGroup;
    }
    return properties.province_code === focusProvinceCode;
  }) : [];
  const focusLayer = focusFeatures.length ? L.geoJSON({ type: "FeatureCollection", features: focusFeatures }) : null;
  if (focusLayer) historyMap.fitBounds(focusLayer.getBounds(), { padding: [25, 25], maxZoom: mapLevel === "province" ? 7 : 8 });
  else if (geojson.features.length) historyMap.fitBounds(historyLayer.getBounds(), { padding: [8, 8] });
  setTimeout(() => historyMap.invalidateSize(), 0);
  const levelName = mapLevel === "province" ? "省级" : mapLevel === "county" ? "县级" : "地级";
  const linked = geojson.features.filter((feature) => feature.properties.link_status === "linked" || feature.properties.link_status === "parent_linked").length;
  const provinceName = mapLevel === "county" ? ` · ${$("#map-province").selectedOptions[0]?.textContent || ""}` : "";
  const scopeText = mapLevel === "county" ? "" : "全国 ";
  $("#map-detail").innerHTML = `<div class="section-label">${externalGroup ? levelName : `${snapshotYear}年初 · ${levelName}${provinceName}`}</div><h2>${externalGroup ? $("#map-province").selectedOptions[0]?.textContent || "" : `${panelYear} 年经济面板`}</h2><p class="muted">当前加载${scopeText}${geojson.features.length} 个${levelName}要素${linked ? `，其中 ${linked} 个可连接地级 CNUR` : ""}。可点击地图或使用名称、代码、CNUR 查询。</p>`;
  state.mapLevel = mapLevel;
}

function switchView(view) {
  $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === view));
  $$(".view").forEach((panel) => panel.classList.toggle("active-view", panel.id === `${view}-view`));
  if (view === "events") renderEvents();
  if (view === "map") renderHistoryMap().catch((error) => { $("#map-detail").innerHTML = `<p class="result-note">地图加载失败：${escapeHtml(error.message)}</p>`; });
}

async function init() {
  try {
    const [response, mapManifestResponse] = await Promise.all([fetch("data/crosswalk.json"), fetch("data/maps/manifest.json")]);
    if (!response.ok) throw new Error(`data ${response.status}`);
    if (!mapManifestResponse.ok) throw new Error(`map manifest ${mapManifestResponse.status}`);
    state.data = await response.json();
    state.mapManifest = await mapManifestResponse.json();
    Object.entries(state.data.entities).forEach(([id, entity]) => state.entityMap.set(id, entity));
    state.data.names.forEach((item) => {
      const list = state.namesByNormalized.get(item.normalized) || [];
      list.push({ ...item, start: Number(item.start), end: Number(item.end) });
      state.namesByNormalized.set(item.normalized, list);
    });
    (state.data.countyEvents || []).forEach((row) => {
      if (row.scope === "non_county_development_zone") return;
      const entityIds = String(row.prefecture_entity_ids || "").split("、").filter(Boolean);
      countySearchNames(row).forEach((name) => {
        const normalized = normalizeName(name);
        if (!normalized || !entityIds.length) return;
        const list = state.countyNamesByNormalized.get(normalized) || [];
        entityIds.forEach((entityId) => list.push({ entity_id: entityId, name, year: row.year, event_id: row.event_id }));
        state.countyNamesByNormalized.set(normalized, list);
      });
    });
    $("#version-pill").textContent = `V${state.data.meta.version}`;
    $("#rule-version").textContent = state.data.meta.ruleVersion;
    for (let year = 1983; year <= 2026; year += 1) $("#event-year").insertAdjacentHTML("beforeend", `<option value="${year}">${year}</option>`);
    for (let year = 1999; year <= 2023; year += 1) $("#map-panel-year").insertAdjacentHTML("beforeend", `<option value="${year}"${year === 2023 ? " selected" : ""}>${year}（${year + 1}年初地图）</option>`);
    (state.mapManifest.provinces || []).forEach((province) => { const label = { "710000": "台湾省", "810000": "香港特别行政区", "820000": "澳门特别行政区" }[province.province_code] || province.province_name; $("#map-province").insertAdjacentHTML("beforeend", `<option value="${escapeHtml(province.province_code)}"${province.province_code === "420000" ? " selected" : ""}>${escapeHtml(label)}</option>`); });
    $("#match-form").addEventListener("submit", (event) => { event.preventDefault(); renderMatch(); });
    $("#event-year").addEventListener("change", renderEvents);
    $("#event-keyword").addEventListener("input", renderEvents);
    $("#map-panel-year").addEventListener("change", () => renderHistoryMap().catch((error) => { $("#map-detail").innerHTML = `<p class="result-note">地图加载失败：${escapeHtml(error.message)}</p>`; }));
    $("#map-level").addEventListener("change", () => {
      const nextLevel = $("#map-level").value;
      if (state.mapLevel === "county" && nextLevel !== "county") state.mapFocusProvinceCode = $("#map-province").value;
      if (nextLevel === "county") state.mapFocusProvinceCode = "";
      const county = $("#map-level").value === "county";
      $("#map-province-control").hidden = !county;
      $("#map-search-input").value = "";
      $("#map-search-input").placeholder = county ? "县名、县级代码或上级 CNUR" : $("#map-level").value === "province" ? "省名或省级代码" : "名称、代码或 CNUR";
      renderHistoryMap().catch((error) => { $("#map-detail").innerHTML = `<p class="result-note">地图加载失败：${escapeHtml(error.message)}</p>`; });
    });
    $("#map-province").addEventListener("change", () => { if ($("#map-level").value === "county") state.mapFocusProvinceCode = $("#map-province").value; renderHistoryMap().catch((error) => { $("#map-detail").innerHTML = `<p class="result-note">地图加载失败：${escapeHtml(error.message)}</p>`; }); });
    $("#map-search-form").addEventListener("submit", (event) => { event.preventDefault(); searchHistoryMap(); });
    $$("[data-example]").forEach((button) => button.addEventListener("click", () => { const [name, province] = button.dataset.example.split("|"); $("#name-input").value = name; $("#province-input").value = province; renderMatch(); }));
    $$("[data-view]").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));
  } catch (error) {
    $("#match-result").innerHTML = `<p class="result-note">数据加载失败：${escapeHtml(error.message)}。请刷新页面，或查看 GitHub Actions 发布状态。</p>`;
  }
}

init();
