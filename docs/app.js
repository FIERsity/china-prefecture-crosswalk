const state = { data: null, namesByNormalized: new Map(), countyNamesByNormalized: new Map(), entityMap: new Map() };
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
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function entityFor(id) {
  return state.entityMap.get(id) || { entity_id: id, canonical_name_zh: "", province_name_zh: "" };
}

function rosterStatus(entityId, year) {
  if (year === null) return "not_checked";
  if (year < 1983 || year > 2026) return "unsupported_year";
  if (year < 1987) return "early_event_only";
  return state.data.rosterStatus[entityId]?.[String(year)] || "unknown";
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
  if (exactEnabled && year !== null && year >= 1987 && year <= 2026) {
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
    const risks = relationRisks(ids[0], year);
    if (status === "not_established") risks.push("pre_establishment");
    if (status === "abolished") risks.push("post_abolition");
    return { entity, entityId: ids[0], normalized, status: risks.length ? "problem" : "auto_matched", method: matches[0]?.method || "exact", confidence: 1, yearStatus: status, risk: [...new Set(risks)].join("|") };
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
  return { entity, entityId, normalized, status: "problem", method, confidence: 1, yearStatus: rosterStatus(entityId, year), risk };
}

function selectedEntityResult(entityId, name, year) {
  const risks = relationRisks(entityId, year);
  const status = rosterStatus(entityId, year);
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
    risk: [...new Set(risks)].join("|"),
  };
}

function statusText(status) {
  return { auto_matched: "已匹配", needs_confirmation: "候选结果", problem: "需核对", unmatched: "未匹配" }[status] || status;
}

function canonicalNameHistoryHtml(entityId) {
  const rows = state.data.names
    .filter((item) => item.entity_id === entityId && item.method === "official_or_historical")
    .map((item) => ({ name: item.name, start: Number(item.start), end: Number(item.end) }))
    .sort((a, b) => a.start - b.start || a.end - b.end || a.name.localeCompare(b.name, "zh-CN"));
  const unique = [...new Map(rows.map((row) => [`${row.name}|${row.start}|${row.end}`, row])).values()];
  if (!unique.length) return "";
  const sequence = unique.map((row) => `${escapeHtml(row.name)}（${row.start}年——${row.end}年）`).join("→");
  return `<div class="prefecture-name-block"><span>规范名沿革</span><p class="canonical-history-line">${sequence}</p></div>`;
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
  return `<div class="county-history prefecture-history"><div class="county-history-head"><div class="section-label">规范名沿革与地级行政区划变更</div><span>${rows.length} 条变更记录</span></div>${nameHistory}<p class="county-history-note">变更记录保留来源描述；地级行政单位包括市、地区、自治州、盟等。</p>${rows.length ? `<div class="county-event-list">${visible.map((row) => { const locator = row.source_locator ? ` · ${escapeHtml(row.source_locator)}` : ""; return `<article class="county-event"><div class="county-event-meta"><strong>${escapeHtml(row.year)}年</strong><span class="event-type">${escapeHtml(prefectureEventTypeText(row.event_type))}</span></div><div class="county-event-change"><span>变更描述</span><p>${escapeHtml(prefectureDescription(row) || "暂无描述")}</p></div><div class="county-event-foot"><span>涉及类型：${escapeHtml(prefectureUnitTypes(row))}</span>${row.source_url ? `<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">对应来源 ↗${locator}</a>` : ""}</div></article>`; }).join("")}</div>${more}` : ""}</div>`;
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
  return `<div class="county-history"><div class="county-history-head"><div class="section-label">县级变更记录</div><span>${rows.length} 条相关记录</span></div><p class="county-history-note">记录包括撤销、设立、合并、改隶、辖区调整和驻地变更。地级关联按名称匹配，县级谱系请结合原始资料核对。</p><div class="county-event-list">${visible.map((row) => { const sourceLabel = row.source_type === "people_daily_summary" ? "人民日报版面" : row.source_type === "secondary_transcription" ? "区划地名网转录" : row.source_type === "state_council_gazette_archive" ? "国务院公报" : "Wikipedia 年度页"; const locator = row.source_locator ? ` · ${escapeHtml(row.source_locator)}` : ""; return `<article class="county-event"><div class="county-event-meta"><strong>${escapeHtml(row.year)}年</strong><span class="event-type">${escapeHtml(countyEventTypeText(row.event_type))}</span></div>${countyEventUnitsHtml(row)}<div class="county-event-change"><span>变更描述</span><p>${escapeHtml(row.change_description || row.description)}</p></div><div class="county-event-foot">${row.county_unit_types ? `涉及类型：${escapeHtml(row.county_unit_types)}` : "类型未标注"}<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">${sourceLabel} ↗${locator}</a></div></article>`; }).join("")}</div>${more}</div>`;
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
  const riskMessage = result.risk ? `状态：${escapeHtml(result.risk.replaceAll("|", "、"))}` : "名称、年份和层级匹配。";
  const yearNote = result.yearStatus === "early_event_only" ? "该年份展示地级行政单位和县级事件记录；年度状态表从1987年开始。" : "";
  return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>${escapeHtml(entity.canonical_name_zh || result.entityId)}</h2><p class="muted">${escapeHtml(result.entityId)} · ${escapeHtml(entity.province_name_zh)}</p></div><span class="status ${result.status === "problem" ? "problem" : "ok"}">${statusText(result.status)}</span></div><div class="result-grid"><div class="result-stat"><strong>${escapeHtml(result.entityId)}</strong><span>研究实体编号</span></div><div class="result-stat"><strong>${result.yearStatus === "not_checked" ? "未核验" : result.yearStatus === "early_event_only" ? "早期事件层" : escapeHtml(result.yearStatus)}</strong><span>${year === null ? "年度状态" : `${year} 年状态`}</span></div><div class="result-stat"><strong>${Math.round(result.confidence * 100)}%</strong><span>匹配置信度</span></div></div><p class="result-note">${riskMessage}${yearNote ? ` ${yearNote}` : ""}</p>${prefectureEventsHtml(result.entityId)}${countyEventsHtml(result.entityId)}<p class="result-source">输入：${escapeHtml(name)} · 规范化：${escapeHtml(result.normalized)} · 方法：${escapeHtml(result.method)}${province ? ` · 省份：${escapeHtml(province)}` : ""}</p>`;
}

function renderMatch() {
  const name = $("#name-input").value.trim();
  const yearValue = $("#year-input").value.trim();
  const year = yearValue ? number(yearValue) : null;
  const province = $("#province-input").value.trim();
  if (!name) return;
  $("#match-result").innerHTML = resultHtml(makeResult(name, year, province), name, year, province);
  bindCandidateCards();
}

function bindCandidateCards() {
  $$("#match-result [data-candidate-id]").forEach((card) => card.addEventListener("click", () => {
    const name = card.dataset.candidateName || card.dataset.candidateId;
    const yearValue = $("#year-input").value.trim();
    const year = yearValue ? number(yearValue) : null;
    const province = $("#province-input").value.trim();
    $("#name-input").value = name;
    $("#match-result").innerHTML = resultHtml(selectedEntityResult(card.dataset.candidateId, name, year), name, year, province);
  }));
}

function renderEvents() {
  const year = $("#event-year").value;
  const keyword = normalizeName($("#event-keyword").value);
  const rows = state.data.events.filter((row) => (!year || row.year === year) && (!keyword || normalizeName(`${row.province_name}${row.prefecture_names}${row.description}`).includes(keyword))).slice(0, 100);
  if (!rows.length) { $("#event-list").innerHTML = '<div class="empty-table">没有符合条件的事件。</div>'; return; }
  $("#event-list").innerHTML = `<table class="event-table"><thead><tr><th>年份</th><th>省份</th><th>类型</th><th>变更描述</th><th>来源摘要</th></tr></thead><tbody>${rows.map((row) => { const source = [row.approval_date, row.document_number].filter(Boolean).join(" · ") || "年度变更记录"; return `<tr><td>${escapeHtml(row.year)}</td><td>${escapeHtml(row.province_name)}</td><td><span class="event-type">${escapeHtml(prefectureEventTypeText(row.event_type))}</span></td><td>${escapeHtml(prefectureDescription(row))}</td><td>${escapeHtml(source)}<br><small>${escapeHtml(row.review_status || "")}</small></td></tr>`; }).join("")}</tbody></table>`;
}

function switchView(view) {
  $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === view));
  $$(".view").forEach((panel) => panel.classList.toggle("active-view", panel.id === `${view}-view`));
  if (view === "events") renderEvents();
}

async function init() {
  try {
    const response = await fetch("data/crosswalk.json");
    if (!response.ok) throw new Error(`data ${response.status}`);
    state.data = await response.json();
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
    $("#match-form").addEventListener("submit", (event) => { event.preventDefault(); renderMatch(); });
    $("#event-year").addEventListener("change", renderEvents);
    $("#event-keyword").addEventListener("input", renderEvents);
    $$("[data-example]").forEach((button) => button.addEventListener("click", () => { const [name, year, province] = button.dataset.example.split("|"); $("#name-input").value = name; $("#year-input").value = year; $("#province-input").value = province; renderMatch(); }));
    $$("[data-view]").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));
  } catch (error) {
    $("#match-result").innerHTML = `<p class="result-note">数据加载失败：${escapeHtml(error.message)}。请刷新页面，或查看 GitHub Actions 发布状态。</p>`;
  }
}

init();
