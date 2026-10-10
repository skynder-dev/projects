'use strict';
const { extractJson } = require('./llm/json');
const { discoverPrompts } = require('./prompts');
const { validateCandidate } = require('./schema');
const CODES = { games: 'GAM', saas_or_micro_saas: 'SAS', ecommerce_or_dropshipping: 'ECO', services: 'SVC', marketplaces: 'MKT', digital_or_data_products: 'DAT', physical_products: 'PHY', media_or_content: 'MED', education_training: 'EDU', b2b_api_devtools: 'DEV' };
const LENSES = ['current unmet needs: recent complaints, workarounds, people paying for manual solutions', 'pricing gaps: where incumbents leave a clearly underserved price/feature tier', 'platform or policy changes in the last 12 months that opened or closed a gap', 'public data or free resources that lack a good paid, packaged product'];
const SIGNAL_PLAN = { games: [['itunes', 'puzzle game']], saas_or_micro_saas: [['hackernews', 'Ask HN looking for a tool'], ['github', 'self-hosted alternative']], b2b_api_devtools: [['npm', 'webhook'], ['stackexchange', 'api rate limit']],
  digital_or_data_products: [['hackernews', 'dataset api'], ['github', 'open data']], education_training: [['hackernews', 'learn course'], ['itunes', 'learn app']], media_or_content: [['hackernews', 'newsletter niche']], marketplaces: [['hackernews', 'marketplace niche']], services: [['hackernews', 'productized service']] };
class DiscoveryAborted extends Error { constructor(msg, diags) { super(msg); this.name = 'DiscoveryAborted'; this.diags = diags; } }
function normalizeLLMCandidate(raw, family, code, idx) {
  const c = { ...raw }; c.family = family; c.id = `${code}-${String(idx).padStart(2, '0')}`;
  c.evidence = (c.evidence || []).map((x, i) => ({ ...x, id: `${c.id}-E${i + 1}` }));
  const map = {}; c.evidence.forEach((x, i) => { map[`E${i + 1}`] = x.id; });
  const de = {}; for (const [d, refs] of Object.entries(c.dimension_evidence || {})) de[d] = (Array.isArray(refs) ? refs : []).map(r => map[String(r)] || String(r));
  c.dimension_evidence = de; c.unknowns = c.unknowns || []; c.source = 'llm_discovery';
  return c;
}
// breaker: shared {fails, max}; two consecutive unparseable/failed model answers abort the whole run (fail fast, save raw diagnostics).
async function discoverFamily({ provider, fetcher, collect, family, perFamily, signalsEnabled = true, bases, breaker = { fails: 0, max: 2 }, maxUses, maxAttempts = LENSES.length }) {
  const code = CODES[family] || family.slice(0, 3).toUpperCase(), found = [], dropped = [], log = [], diags = [], citations = [], searchResults = [];
  let signals = [], blockedCount = 0;
  if (signalsEnabled && SIGNAL_PLAN[family] && fetcher) {
    const r = await collect(fetcher, SIGNAL_PLAN[family].map(([source, query]) => ({ source, query })), { bases });
    signals = r.signals; blockedCount = r.errors.length; log.push({ signals: signals.length, signal_errors: r.errors });
  }
  let want = perFamily;
  for (let attempt = 0; attempt < Math.min(LENSES.length, maxAttempts) && found.length < perFamily; attempt++) {
    const need = Math.min(want, perFamily - found.length);
    const { system, user } = discoverPrompts({ family, code, n: need, lens: LENSES[attempt], signals, avoid: found.map(c => c.name) });
    let res;
    try { res = await provider.complete({ system, user, webSearch: true, maxUses }); }
    catch (e) { if (e.name === 'SpendNotAuthorized' || e.name === 'BudgetExceeded') throw e; diags.push({ family, attempt, error: e.message }); breaker.fails++; if (breaker.fails >= breaker.max) throw new DiscoveryAborted(`provider error x${breaker.fails}: ${e.message}`, diags); continue; }
    citations.push(...(res.citations || [])); searchResults.push(...(res.searchResults || []));
    let arr = null, perr = null;
    for (const text of [res.finalText, res.text]) { if (!text) continue; try { arr = extractJson(text, 'array'); break; } catch (e) { perr = e.message; } }
    if (!arr) {
      const d = { family, attempt, error: perr || 'empty_model_output', ...(res.diag || {}), usage: res.usage }; diags.push(d); log.push({ attempt, error: d.error, stop_reason: d.stop_reason });
      if (res.stop_reason === 'max_tokens') want = Math.max(1, Math.ceil(want / 2));
      breaker.fails++; if (breaker.fails >= breaker.max) throw new DiscoveryAborted(`unparseable model output x${breaker.fails} (stop_reason=${d.stop_reason})`, diags);
      continue;
    }
    breaker.fails = 0;
    for (const raw of arr) {
      if (found.length >= perFamily) break;
      const c = normalizeLLMCandidate(raw, family, code, found.length + 1), errs = validateCandidate(c);
      if (errs.length) dropped.push({ name: raw && raw.name, errors: errs.slice(0, 4) }); else found.push(c);
    }
    log.push({ attempt, lens: LENSES[attempt], got: found.length, usage: res.usage });
  }
  return { family, candidates: found, dropped, citations, searchResults, log, diags };
}
module.exports = { discoverFamily, normalizeLLMCandidate, CODES, LENSES, DiscoveryAborted };
