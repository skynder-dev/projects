'use strict';
// Two-phase research. Phase 1 (web search ON): prose notes -> the search tool attaches CITATIONS (url + cited_text) to text.
// Phase 2 (search OFF): convert notes to JSON where every evidence item is a REFERENCE to a returned citation (C#) or search result (S#).
// Evidence text/URLs therefore come from the provider, never from the model's memory. No third-party page is opened by the engine.
const { extractJson } = require('./llm/json');
function buildRefIndex(res) {
  const excerpts = [], results = [], seen = new Set(), seenU = new Set();
  for (const c of res.citations || []) { const k = c.url + '|' + c.cited_text; if (c.cited_text && !seen.has(k)) { seen.add(k); excerpts.push({ id: 'C' + (excerpts.length + 1), url: c.url, title: c.title || '', cited_text: String(c.cited_text).slice(0, 300) }); } }
  for (const r of res.searchResults || []) if (!seenU.has(r.url)) { seenU.add(r.url); results.push({ id: 'S' + (results.length + 1), url: r.url, title: r.title || '', page_age: r.page_age || null }); }
  const byId = Object.fromEntries([...excerpts, ...results].map(x => [x.id, x]));
  return { excerpts: excerpts.slice(0, 70), results: results.slice(0, 40), byId };
}
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (_) { return ''; } };
// raw items: [{ref:'C3', kind, shows, class}] -> resolved evidence + E#->id map. Unknown refs are dropped and counted.
function resolveEvidence(items, idx, idPrefix) {
  const evidence = [], map = {}; let dropped = 0;
  (Array.isArray(items) ? items : []).forEach((it, i) => {
    const ref = it && String(it.ref || '').trim(), src = ref && idx.byId[ref];
    if (!src || !['incumbent_price', 'demand', 'constraint', 'other'].includes(it.kind)) { dropped++; return; }
    const isC = ref[0] === 'C', id = `${idPrefix}${evidence.length + 1}`;
    evidence.push({ id, url: src.url, publisher: src.title || host(src.url), date: src.page_age || 'undated', quote: isC ? src.cited_text : null, shows: String(it.shows || ''), kind: it.kind, class: it.class === 'inference' ? 'inference' : 'fact', ref,
      verify: { status: isC ? 'verified' : 'search_confirmed', method: isC ? 'provider_citation_excerpt' : 'provider_search_result_url' } });
    map[`E${i + 1}`] = id;
  });
  return { evidence, map, dropped };
}
async function twoPhase({ provider, p1, buildP2, maxUses, expect }) {
  const r1 = await provider.complete({ system: p1.system, user: p1.user, webSearch: true, maxUses });
  const idx = buildRefIndex(r1), diags = [];
  const memo = r1.finalText && r1.finalText.length > 200 ? r1.finalText : r1.text;
  if (!memo || memo.trim().length < 50) return { ok: false, error: 'empty_research_memo', idx, r1, diags: [{ phase: 1, ...(r1.diag || {}) }] };
  const p2 = buildP2(memo, idx), r2 = await provider.complete({ system: p2.system, user: p2.user, webSearch: false });
  let data = null, perr = null;
  for (const t of [r2.finalText, r2.text]) { if (!t) continue; try { data = extractJson(t, expect); break; } catch (e) { perr = e.message; } }
  if (data === null) return { ok: false, error: perr || 'empty_json_output', idx, r1, r2, memo, diags: [{ phase: 2, ...(r2.diag || {}) }] };
  return { ok: true, data, idx, r1, r2, memo, diags };
}
module.exports = { buildRefIndex, resolveEvidence, twoPhase };
