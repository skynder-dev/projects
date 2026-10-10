'use strict';
const { extractJson } = require('./llm/json');
const { deepPrompts } = require('./prompts');
const { verifyEvidenceItem } = require('./evidence');
const { load } = require('../vendor/load');
const econ = load('economics_contract');
const MODEL_KEYS = ['price', 'units', 'revenue', 'cashCost', 'contribution', 'ownerHours', 'startup', 'automation', 'launchDays'];
// Economics via frozen G280 economics_contract.normalize (cashMargin, startupPayback, firstYearStartupRoi). Pessimistic = explicit MODEL, not evidence.
function economics(model) {
  if (!model || typeof model !== 'object') return { status: 'no_model' };
  const raw = Object.fromEntries(MODEL_KEYS.filter(k => Number.isFinite(Number(model[k]))).map(k => [k, Number(model[k])]));
  const base = econ.normalize(raw, { source: 'deep_screen_model' });
  const val = (m, k) => (m[k] && m[k].known ? m[k].value : null);
  const pess = { ...raw, price: raw.price * 0.8, units: raw.units * 0.5, revenue: raw.revenue * 0.4, cashCost: raw.cashCost * 0.5 };
  pess.contribution = pess.revenue - pess.cashCost;
  const p = econ.normalize(pess, { source: 'deep_screen_pessimistic_model' });
  return { status: 'computed', class: 'model', assumptions: model.assumptions || [],
    baseline: { cashMarginPct: val(base, 'cashMargin'), profitPerOwnerHour: val(base, 'profitOwnerHour'), startupPaybackMonths: val(base, 'startupPayback'), firstYearRoiPct: val(base, 'firstYearStartupRoi'), contributionUsdPerMonth: val(base, 'contribution') },
    pessimistic: { rule: 'price x0.8, units x0.5, cash cost x0.5', cashMarginPct: val(p, 'cashMargin'), contributionUsdPerMonth: val(p, 'contribution'), startupPaybackMonths: val(p, 'startupPayback') },
    survives_pessimistic: val(p, 'contribution') !== null && val(p, 'contribution') > 0 };
}
async function deepScreen({ provider, fetcher, candidate, minVerified = 3 }) {
  const { system, user } = deepPrompts({ candidate });
  const res = await provider.complete({ system, user, webSearch: true });
  const d = extractJson(res.text), searchUrls = new Set(res.searchUrls || []);
  const c = JSON.parse(JSON.stringify(candidate)), newEv = [];
  const map = {};
  for (let i = 0; i < (d.evidence || []).length; i++) {
    const it = { ...d.evidence[i], id: `${c.id}-D${i + 1}`, stage: 'deep' };
    if (!/^https?:\/\//.test(it.url || '') || !['incumbent_price', 'demand', 'constraint', 'other'].includes(it.kind)) continue;
    const v = await verifyEvidenceItem(it, fetcher, searchUrls); delete v._text; newEv.push(v); map[`E${i + 1}`] = it.id;
  }
  c.evidence = [...(c.evidence || []), ...newEv];
  const rv = d.revised || {};
  const num = (k) => (Number.isFinite(rv[k]) ? rv[k] : c[k]);
  c.startup_cash_usd = num('startup_cash_usd'); c.time_to_first_revenue_days = num('time_to_first_revenue_days');
  c.owner_hours_per_week_steady = num('owner_hours_per_week_steady'); c.automation_potential_pct = num('automation_potential_pct');
  if (rv.contribution_margin_pct !== undefined) c.unit_economics = { ...c.unit_economics, contribution_margin_pct: rv.contribution_margin_pct, class: 'model' };
  if (rv.dimension_scores) { for (const [k, v] of Object.entries(rv.dimension_scores)) if (Number.isInteger(v) && v >= 0 && v <= 5 && k in c.dimension_scores) c.dimension_scores[k] = v; }
  if (rv.dimension_evidence) { const de = {}; for (const [k, refs] of Object.entries(rv.dimension_evidence)) de[k] = (Array.isArray(refs) ? refs : []).map(r => map[String(r)] || String(r)); c.dimension_evidence = de; }
  if (rv.entrant_edge && typeof rv.entrant_edge === 'object') c.entrant_edge = rv.entrant_edge;
  const ver = newEv.filter(x => x.verify.status === 'verified').length;
  c.deep = { done: true, verified_deep_evidence: ver, complete: ver >= minVerified, competitors: d.competitors || [], constraints: d.constraints || [], kill_reasons: d.kill_reasons || [], unknowns: d.unknowns || [],
    economics: economics(d.monthly_model), usage: res.usage };
  return c;
}
module.exports = { deepScreen, economics };
