'use strict';
const { load } = require('../vendor/load');
const snap = load('decision_snapshot');
const fnv1a = (s) => { let h = 0x811c9dc5; for (const ch of s) { h ^= ch.charCodeAt(0); h = Math.imul(h, 0x01000193) >>> 0; } return 'fnv1a:' + h.toString(16).padStart(8, '0'); };
const stableStr = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map(q => [q, x[q]])) : x));
// Decision snapshot via frozen G280 decision_snapshot contract: only engine-VERIFIED facts are state=verified; model/LLM inference = unverified; absent = unknown.
function buildSnapshot(c, row, runId) {
  const ev = c.evidence || [], vOf = (kind) => ev.find(x => x.kind === kind && x.verify && x.verify.status === 'verified');
  const R = (key, label, value, ev1, reason) => ({ key, label, state: value === null || value === undefined ? 'unknown' : (ev1 ? 'verified' : 'unverified'), value: value ?? null, reason: reason || (ev1 ? null : 'model_or_inference_not_backed_by_verified_page'), sourceRef: ev1 ? ev1.url : null });
  const src = (n) => ({ contractId: 'reveng_engine_section_v1', objectId: `${c.id}:${n}`, version: 1, digest: fnv1a(stableStr(c[n] || c.id + n)) });
  const ecoM = (c.deep && c.deep.economics && c.deep.economics.baseline) || {}, ecoP = (c.deep && c.deep.economics && c.deep.economics.pessimistic) || {};
  const input = { workspaceId: 'reveng_global', opportunityId: c.id, revisionId: runId, revisionVersion: 1, capturedAt: new Date().toISOString(),
    buyer: { source: src('buyer'), rows: [R('buyer', 'Buyer', c.buyer, vOf('demand')), R('pain', 'Pain', c.pain, vOf('demand'))] },
    channel: { source: src('channel'), rows: [R('acquisition_efficiency', 'Acquisition efficiency score (0-5)', row.dimensions.acquisition_efficiency, null, 'judged score; evidence cap applied')] },
    economics: { source: src('unit_economics'), rows: [R('incumbent_price', 'Incumbent price evidence', (c.substitutes || []).map(s => `${s.name}: ${s.price_point}`).join('; ') || null, vOf('incumbent_price')),
      R('model_cash_margin_pct', 'Modelled cash margin %', ecoM.cashMarginPct, null, 'modelled in deep screen'), R('model_payback_months', 'Modelled startup payback (months)', ecoM.startupPaybackMonths, null, 'modelled in deep screen'),
      R('pessimistic_contribution_usd_month', 'Pessimistic contribution $/mo', ecoP.contributionUsdPerMonth, null, 'explicit pessimistic model: price x0.8, units x0.5, cost x0.5')] },
    resources: { source: src('startup_cash_usd'), rows: [R('startup_cash_usd', 'Startup cash (USD)', c.startup_cash_usd, null, 'estimate'), R('days_to_first_revenue', 'Days to first revenue', c.time_to_first_revenue_days, null, 'estimate'), R('owner_hours_week', 'Owner hours/week', c.owner_hours_per_week_steady, null, 'estimate')] },
    risks: { source: src('regulatory_or_platform_dependency'), rows: [R('regulatory_platform', 'Regulatory / platform dependency', c.regulatory_or_platform_dependency || null, vOf('constraint')), R('kill_reasons', 'Deep-screen kill reasons', ((c.deep || {}).kill_reasons || []).join('; ') || null, null, 'LLM-reported')] },
    openQuestions: { source: src('unknowns'), rows: [R('major_uncertainty', 'Major uncertainty', c.major_uncertainty || null, null), R('unknowns', 'Unknowns', (c.unknowns || []).concat((c.deep || {}).unknowns || []).join('; ') || null, null)] } };
  return snap.build(input);
}
function markdown({ runId, decision, candidates, scored, gateById, provisional, stats, evidenceClasses }) {
  const by = Object.fromEntries(candidates.map(c => [c.id, c])), sc = Object.fromEntries(scored.map(r => [r.id, r]));
  const L = [];
  L.push(`# RevEng v6 independent — owner-review packet`, `Run: \`${runId}\`  ·  scoring: \`reveng_v6_independent\` (profile balanced; no owner context)  ·  ${provisional ? '**PROVISIONAL (evidence not engine-verified)**' : 'engine-verified evidence'}`, '');
  L.push(`## Verdict: **${decision.verdict.toUpperCase()}**${decision.leader ? ` — leader ${decision.leader}` : ''}`, '');
  if (decision.unmet_conditions.length) { L.push('Unmet conditions:'); decision.unmet_conditions.forEach(r => L.push(`- ${r}${decision.hard_blockers.includes(r) ? '  **(blocks winner)**' : ''}`)); L.push(''); }
  L.push(`Candidates: ${candidates.length} · families: ${Object.keys(decision.families).length} · survived hard gates: ${decision.survivors} · integrity violations: ${decision.integrity_violations.length}`, '');
  L.push('## Ranking (gate survivors, adjusted score, balanced profile)', '', '| # | id | family | adjusted | raw | conf | auto/bal/def rank |', '|---|---|---|---|---|---|---|');
  decision.ranking.forEach((r, i) => { const s = sc[r.id]; L.push(`| ${i + 1} | ${r.id} ${by[r.id].name} | ${r.family} | ${r.adjusted} | ${r.raw} | ${s.evidence_confidence} | — |`); });
  if (!decision.ranking.length) L.push('| – | none survived | | | | | |');
  L.push('', '## All candidates and first failed gate', '', '| id | name | family | adjusted(unranked) | result |', '|---|---|---|---|---|');
  for (const c of candidates) { const g = gateById[c.id]; L.push(`| ${c.id} | ${c.name} | ${c.family} | ${sc[c.id] ? sc[c.id].adjusted : '–'} | ${g.passed ? 'PASS' : 'reject: ' + g.failed.join(',') + ' — ' + g.gates[g.failed[0]].reason} |`); }
  L.push('', '## Evidence classes (not promoted into each other)', '');
  for (const [k, v] of Object.entries(evidenceClasses)) L.push(`- ${k}: ${v}`);
  if (stats) L.push('', `Usage: ${JSON.stringify(stats)}`);
  return L.join('\n');
}
module.exports = { buildSnapshot, markdown };
