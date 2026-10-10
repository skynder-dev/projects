'use strict';
const { extractJson } = require('./llm/json');
const { discoverPrompts } = require('./prompts');
const { validateCandidate, JUDGED } = require('./schema');
const CODES = { games: 'GAM', saas_or_micro_saas: 'SAS', ecommerce_or_dropshipping: 'ECO', services: 'SVC', marketplaces: 'MKT', digital_or_data_products: 'DAT', physical_products: 'PHY', media_or_content: 'MED', education_training: 'EDU', b2b_api_devtools: 'DEV' };
const LENSES = ['current unmet needs: recent complaints, workarounds, people paying for manual solutions', 'pricing gaps: where incumbents leave a clearly underserved price/feature tier', 'platform or policy changes in the last 12 months that opened or closed a gap', 'public data or free resources that lack a good paid, packaged product'];
const SIGNAL_PLAN = { games: [['steam', 'new indie'], ['itunes', 'puzzle game']], saas_or_micro_saas: [['hackernews', 'Ask HN looking for a tool'], ['github', 'self-hosted alternative']], b2b_api_devtools: [['npm', 'webhook'], ['stackexchange', 'api rate limit']],
  digital_or_data_products: [['hackernews', 'dataset api'], ['github', 'open data']], education_training: [['hackernews', 'learn course'], ['itunes', 'learn app']], media_or_content: [['hackernews', 'newsletter niche']], marketplaces: [['hackernews', 'marketplace niche']], services: [['hackernews', 'productized service']] };
// Normalize an LLM candidate: assign ids, resolve E# references in dimension_evidence to real evidence ids, coerce schema defaults.
function normalizeLLMCandidate(raw, family, code, idx) {
  const c = { ...raw }; c.family = family; c.id = `${code}-${String(idx).padStart(2, '0')}`;
  c.evidence = (c.evidence || []).map((x, i) => ({ ...x, id: `${c.id}-E${i + 1}` }));
  const map = {}; c.evidence.forEach((x, i) => { map[`E${i + 1}`] = x.id; });
  const de = {}; for (const [d, refs] of Object.entries(c.dimension_evidence || {})) de[d] = (Array.isArray(refs) ? refs : []).map(r => map[String(r)] || String(r));
  c.dimension_evidence = de;
  c.unknowns = c.unknowns || []; c.source = 'llm_discovery';
  return c;
}
async function discoverFamily({ provider, fetcher, collect, family, perFamily, signalsEnabled = true, bases }) {
  const code = CODES[family] || family.slice(0, 3).toUpperCase(), found = [], dropped = [], searchUrls = new Set(), log = [];
  let signals = [];
  if (signalsEnabled && SIGNAL_PLAN[family]) { const r = await collect(fetcher, SIGNAL_PLAN[family].map(([source, query]) => ({ source, query })), { bases }); signals = r.signals; log.push({ signals: signals.length, signal_errors: r.errors.length }); }
  for (let attempt = 0; attempt < LENSES.length && found.length < perFamily; attempt++) {
    const need = perFamily - found.length;
    const { system, user } = discoverPrompts({ family, code, n: need, lens: LENSES[attempt], signals, avoid: found.map(c => c.name) });
    const res = await provider.complete({ system, user, webSearch: true });
    for (const u of res.searchUrls) searchUrls.add(u);
    let arr; try { arr = extractJson(res.text); } catch (e) { log.push({ attempt, error: e.message }); continue; }
    for (const raw of Array.isArray(arr) ? arr : []) {
      if (found.length >= perFamily) break;
      const c = normalizeLLMCandidate(raw, family, code, found.length + 1), errs = validateCandidate(c);
      if (errs.length) dropped.push({ name: raw && raw.name, errors: errs.slice(0, 4) }); else found.push(c);
    }
    log.push({ attempt, lens: LENSES[attempt], got: found.length });
  }
  return { family, candidates: found, dropped, searchUrls: [...searchUrls], log };
}
module.exports = { discoverFamily, normalizeLLMCandidate, CODES, LENSES };
