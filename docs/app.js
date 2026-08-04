const state = { data: null, namesByNormalized: new Map(), entityMap: new Map() };
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
  if (year < 1987 || year > 2026) return "unsupported_year";
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

function makeResult(name, year, province) {
  const normalized = normalizeName(name);
  if (!normalized) return { status: "unmatched", method: "none", normalized, risk: "blank_name" };
  const provinceNormalized = normalizeProvince(province);
  const rawMatches = state.namesByNormalized.get(normalized) || [];
  let matches = rawMatches.filter((item) => {
    const entity = entityFor(item.entity_id);
    return !provinceNormalized || normalizeProvince(entity.province_name_zh) === provinceNormalized;
  });
  if (!matches.length && rawMatches.length && provinceNormalized) {
    const unique = [...new Set(rawMatches.map((item) => item.entity_id))];
    if (unique.length === 1) return problemResult(unique[0], normalized, year, "province_conflict", "省份与实体记录不一致");
  }
  if (year !== null && year >= 1987 && year <= 2026) {
    const valid = matches.filter((item) => item.start <= year && year <= item.end);
    if (valid.length) matches = valid;
    else if (matches.length && new Set(matches.map((item) => item.entity_id)).size === 1) {
      return problemResult(matches[0].entity_id, normalized, year, "name_outside_valid_year", "名称与所选年份的有效区间不一致");
    }
  }
  const ids = [...new Set(matches.map((item) => item.entity_id))];
  if (ids.length === 1 && (year !== null || new Set(rawMatches.map((item) => item.entity_id)).size === 1)) {
    const entity = entityFor(ids[0]);
    const status = rosterStatus(ids[0], year);
    const risks = relationRisks(ids[0], year);
    if (status === "not_established") risks.push("pre_establishment");
    if (status === "abolished") risks.push("post_abolition");
    return { entity, entityId: ids[0], normalized, status: risks.length ? "problem" : "auto_matched", method: matches[0]?.method || "exact", confidence: 1, yearStatus: status, risk: [...new Set(risks)].join("|") };
  }

  const candidates = [];
  for (const [choice, items] of state.namesByNormalized.entries()) {
    const score = similarity(normalized, choice);
    if (score < 0.75) continue;
    for (const item of items) {
      const entity = entityFor(item.entity_id);
      if (provinceNormalized && normalizeProvince(entity.province_name_zh) !== provinceNormalized) continue;
      candidates.push({ entity, entityId: item.entity_id, matchedName: item.name, score: Math.round(score * 1000) / 10 });
    }
  }
  const unique = [...new Map(candidates.sort((a, b) => b.score - a.score).map((candidate) => [candidate.entityId, candidate])).values()].slice(0, 3);
  return { normalized, status: unique.length ? "needs_confirmation" : "unmatched", method: unique.length ? "fuzzy_candidate" : "none", confidence: unique[0]?.score ? unique[0].score / 100 : 0, yearStatus: "not_checked", risk: unique.length ? "manual_confirmation_required" : "unrecognized_name", candidates: unique };
}

function problemResult(entityId, normalized, year, method, risk) {
  const entity = entityFor(entityId);
  return { entity, entityId, normalized, status: "problem", method, confidence: 1, yearStatus: rosterStatus(entityId, year), risk };
}

function statusText(status) {
  return { auto_matched: "自动接受", needs_confirmation: "需要确认", problem: "发现风险", unmatched: "未匹配" }[status] || status;
}

function canonicalNameHistoryHtml(entityId) {
  const rows = state.data.names
    .filter((item) => item.entity_id === entityId && item.method === "official_or_historical")
    .map((item) => ({ name: item.name, start: Number(item.start), end: Number(item.end) }))
    .sort((a, b) => a.start - b.start || a.end - b.end || a.name.localeCompare(b.name, "zh-CN"));
  const unique = [...new Map(rows.map((row) => [`${row.name}|${row.start}|${row.end}`, row])).values()];
  if (!unique.length) return "";
  const sequence = unique.map((row) => `${escapeHtml(row.name)}（${row.start}年——${row.end}年）`).join("→");
  return `<div class="canonical-history"><div class="section-label">规范名沿革</div><p class="canonical-history-line">${sequence}</p></div>`;
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
  return `<div class="county-history"><div class="county-history-head"><div class="section-label">县级变更记录</div><span>${rows.length} 条相关记录</span></div><p class="county-history-note">这里展示的是县级行政区划的事件记录，包括撤销、设立、合并、改隶、辖区调整和驻地变更；相关地级实体采用宽松文本命中，仅用于提示，不等同完整县级谱系。</p><div class="county-event-list">${visible.map((row) => `<article class="county-event"><div class="county-event-meta"><strong>${escapeHtml(row.year)}年</strong><span class="event-type">${escapeHtml(countyEventTypeText(row.event_type))}</span></div>${countyEventUnitsHtml(row)}<div class="county-event-change"><span>变更描述</span><p>${escapeHtml(row.change_description || row.description)}</p></div><div class="county-event-foot">${row.county_unit_types ? `涉及类型：${escapeHtml(row.county_unit_types)}` : "县级类型未从该行明确提取"}<a href="${escapeHtml(row.source_url)}" target="_blank" rel="noreferrer">Wikipedia 年度页 ↗</a></div></article>`).join("")}</div>${more}</div>`;
}

function resultHtml(result, name, year, province) {
  if (result.status === "unmatched") {
    return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>没有找到确定结果</h2></div><span class="status problem">未匹配</span></div><p class="result-note">“${escapeHtml(name)}”没有达到自动接受条件。可以补充年份、省份，或检查是否存在错别字。</p>`;
  }
  if (result.status === "needs_confirmation") {
    return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>${escapeHtml(name)}</h2></div><span class="status warn">需要确认</span></div><p class="result-note">工具找到候选，但没有足够证据自动替你决定。请结合原始资料和官方来源人工确认。</p><div class="candidate-list"><h3>候选实体</h3>${result.candidates.map((item) => `<div class="candidate"><span>${escapeHtml(item.entity.canonical_name_zh)} · ${escapeHtml(item.entityId)}</span><b>${item.score}%</b></div>`).join("")}</div>`;
  }
  const entity = result.entity;
  const riskMessage = result.risk ? `需要注意：${escapeHtml(result.risk.replaceAll("|", "、"))}` : "全国唯一、年份有效且层级一致。可以作为自动匹配结果使用。";
  return `<div class="result-head"><div><div class="section-label">MATCH RESULT</div><h2>${escapeHtml(entity.canonical_name_zh || result.entityId)}</h2><p class="muted">${escapeHtml(result.entityId)} · ${escapeHtml(entity.province_name_zh)}</p></div><span class="status ${result.status === "problem" ? "problem" : "ok"}">${statusText(result.status)}</span></div><div class="result-grid"><div class="result-stat"><strong>${escapeHtml(result.entityId)}</strong><span>研究实体编号</span></div><div class="result-stat"><strong>${result.yearStatus === "not_checked" ? "未核验" : escapeHtml(result.yearStatus)}</strong><span>${year === null ? "年度状态" : `${year} 年状态`}</span></div><div class="result-stat"><strong>${Math.round(result.confidence * 100)}%</strong><span>匹配置信度</span></div></div><p class="result-note">${riskMessage}</p>${canonicalNameHistoryHtml(result.entityId)}${countyEventsHtml(result.entityId)}<p class="result-source">输入：${escapeHtml(name)} · 规范化：${escapeHtml(result.normalized)} · 方法：${escapeHtml(result.method)}${province ? ` · 省份：${escapeHtml(province)}` : ""}</p>`;
}

function renderMatch() {
  const name = $("#name-input").value.trim();
  const yearValue = $("#year-input").value.trim();
  const year = yearValue ? number(yearValue) : null;
  const province = $("#province-input").value.trim();
  if (!name) return;
  $("#match-result").innerHTML = resultHtml(makeResult(name, year, province), name, year, province);
}

function renderEvents() {
  const year = $("#event-year").value;
  const keyword = normalizeName($("#event-keyword").value);
  const rows = state.data.events.filter((row) => (!year || row.year === year) && (!keyword || normalizeName(`${row.province_name}${row.old_prefecture_name}${row.new_prefecture_name}${row.description}`).includes(keyword))).slice(0, 100);
  if (!rows.length) { $("#event-list").innerHTML = '<div class="empty-table">没有符合条件的事件。</div>'; return; }
  $("#event-list").innerHTML = `<table class="event-table"><thead><tr><th>年份</th><th>省份</th><th>类型</th><th>变更</th><th>来源摘要</th></tr></thead><tbody>${rows.map((row) => { const source = [row.approval_date, row.document_number].filter(Boolean).join(" · ") || "年度变更记录"; return `<tr><td>${escapeHtml(row.year)}</td><td>${escapeHtml(row.province_name)}</td><td><span class="event-type">${escapeHtml(row.event_type)}</span></td><td>${escapeHtml(row.old_prefecture_name || "")} → ${escapeHtml(row.new_prefecture_name || "")}</td><td>${escapeHtml(source)}<br><small>${escapeHtml(row.review_status || "")}</small></td></tr>`; }).join("")}</tbody></table>`;
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
    $("#version-pill").textContent = `V${state.data.meta.version}`;
    $("#rule-version").textContent = state.data.meta.ruleVersion;
    for (let year = 1987; year <= 2026; year += 1) $("#event-year").insertAdjacentHTML("beforeend", `<option value="${year}">${year}</option>`);
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
